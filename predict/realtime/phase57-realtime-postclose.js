import { SAFETY, STRATEGY_IDS, verifyRealtimeLedger } from "./phase57-stateful-contract.js";

const FALSE_KEYS = [
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
];

function assertSafety() {
  for (const key of FALSE_KEYS) if (SAFETY[key] !== false) throw new Error(`unsafe realtime post-close ${key}`);
}
function snapshotsFromLedger(ledger) {
  return ledger.filter((event) => event.type === "STRATEGY_SNAPSHOT_COMMITTED" && Array.isArray(event.strategies));
}
function latestSnapshotEvent(ledger) {
  return snapshotsFromLedger(ledger).at(-1) ?? null;
}
function finiteOrNull(value) {
  return Number.isFinite(Number(value)) ? Number(value) : null;
}

export function scoreRealtimeSessionFromLedger(ledger, { sessionDate = null } = {}) {
  assertSafety();
  const verified = verifyRealtimeLedger(ledger, { sessionDate });
  const latest = latestSnapshotEvent(ledger);
  if (!latest) throw new Error("no durable realtime strategy snapshot in ledger");
  if (latest.strategyCount !== STRATEGY_IDS.length || latest.strategies.length !== STRATEGY_IDS.length) throw new Error("strategy snapshot must contain exactly 28 strategies");
  const byId = new Map(latest.strategies.map((row) => [row.strategyId, row]));
  for (const id of STRATEGY_IDS) if (!byId.has(id)) throw new Error(`missing realtime strategy ${id}`);
  const missingBucketCount = Math.max(0, Number(latest.missingBucketCount) || 0);
  const expectedBucketCount = finiteOrNull(latest.expectedBucketCount);
  const coveragePercent = finiteOrNull(latest.coveragePercent);
  const complete = latest.sessionQuality === "FULL_FRESH" && missingBucketCount === 0;
  return Object.freeze({
    schemaVersion: 1,
    status: "PHASE57_REALTIME_POST_CLOSE_SCORED",
    sessionDate: latest.sessionDate,
    at: latest.at,
    ledgerEventCount: verified.eventCount,
    ledgerHeadHash: verified.headHash,
    sessionQuality: latest.sessionQuality ?? "UNKNOWN",
    complete,
    missingBucketCount,
    expectedBucketCount,
    coveragePercent,
    strategyCount: STRATEGY_IDS.length,
    strategies: Object.freeze(STRATEGY_IDS.map((strategyId) => {
      const row = byId.get(strategyId);
      return Object.freeze({
        strategyId,
        n: Number(row.closedTrades ?? 0),
        netPercent: Number(row.netPercent ?? 0),
        realizedPnl: Number(row.realizedPnl ?? 0),
        unrealizedPnl: Number(row.unrealizedPnl ?? 0),
        equity: Number(row.equity ?? 0),
        cash: Number(row.cash ?? 0),
        openPositions: Number(row.openPositions ?? 0),
        winRate: row.winRate == null ? null : Number(row.winRate),
        profitFactor: row.profitFactor == null ? null : Number(row.profitFactor),
        maxDrawdownPercent: Number(row.maxDrawdownPercent ?? 0),
      });
    })),
    safety: SAFETY,
  });
}

export function replayRealtimeSnapshotsFromLedger(ledger, { sessionDate = null } = {}) {
  assertSafety();
  const verified = verifyRealtimeLedger(ledger, { sessionDate });
  const snapshots = snapshotsFromLedger(ledger);
  let previousAt = null;
  for (const event of snapshots) {
    if (previousAt && Date.parse(event.at) <= Date.parse(previousAt)) throw new Error("realtime snapshot timestamps must be strictly increasing");
    if (event.strategyCount !== STRATEGY_IDS.length || event.strategies.length !== STRATEGY_IDS.length) throw new Error("invalid realtime strategy snapshot width");
    previousAt = event.at;
  }
  const netCurve = Object.freeze(snapshots.map((event) => Object.freeze({
    at: event.at,
    strategies: Object.freeze(event.strategies.map((row) => Object.freeze({ strategyId: row.strategyId, netPercent: Number(row.netPercent ?? 0) }))),
  })));
  return Object.freeze({
    valid: true,
    sessionDate: sessionDate ?? snapshots.at(-1)?.sessionDate ?? null,
    ledgerEventCount: verified.eventCount,
    ledgerHeadHash: verified.headHash,
    snapshotCount: snapshots.length,
    netCurve,
  });
}

export function compareRealtimePostCloseToBatch(realtimeScore, batchRows, { tolerance = 1e-9 } = {}) {
  if (!realtimeScore?.strategies || !Array.isArray(batchRows)) throw new Error("realtimeScore and batchRows required");
  const batchById = new Map(batchRows.map((row) => [row.strategyId, row]));
  const fields = ["n", "netPercent", "realizedPnl", "unrealizedPnl", "equity", "openPositions", "maxDrawdownPercent"];
  const mismatches = [];
  for (const realtime of realtimeScore.strategies) {
    const batch = batchById.get(realtime.strategyId);
    if (!batch) {
      mismatches.push({ strategyId: realtime.strategyId, field: "strategyId", realtime: realtime.strategyId, batch: null });
      continue;
    }
    for (const field of fields) {
      if (!(field in batch)) continue;
      const a = Number(realtime[field]);
      const b = Number(batch[field]);
      if (!Number.isFinite(a) || !Number.isFinite(b) || Math.abs(a - b) > tolerance) mismatches.push({ strategyId: realtime.strategyId, field, realtime: realtime[field], batch: batch[field] });
    }
  }
  return Object.freeze({ parity: mismatches.length === 0, mismatchCount: mismatches.length, mismatches: Object.freeze(mismatches) });
}

export const PHASE57_REALTIME_POSTCLOSE_SAFETY = SAFETY;
