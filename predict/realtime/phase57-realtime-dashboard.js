import { SAFETY, STRATEGY_IDS, appendLedgerEvent, strategySnapshot, verifyRealtimeLedger } from "./phase57-stateful-contract.js";

const FALSE_KEYS = [
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
];

function assertSafety() {
  for (const key of FALSE_KEYS) if (SAFETY[key] !== false) throw new Error(`unsafe realtime dashboard ${key}`);
}
function finite(v) { return v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v)); }
function currentPriceOf(position) { return Number(position?.lastMarkPrice ?? position?.exitReferencePrice ?? position?.entryReferencePrice ?? 0); }
function positionReturnPercent(position) {
  const entry = Number(position?.entryReferencePrice ?? 0), current = currentPriceOf(position), direction = Number(position?.signalDirection ?? 1);
  if (!(entry > 0) || !(current > 0)) return null;
  return ((current / entry) - 1) * 100 * (direction === -1 ? -1 : 1);
}
function openPositionRows(state) {
  const rows = [];
  for (const strategyId of STRATEGY_IDS) {
    const strategy = state.strategies[strategyId];
    for (const position of Object.values(strategy.positions ?? {})) {
      rows.push(Object.freeze({
        strategyId,
        symbol: position.symbol,
        selectionLineage: position.selectionLineage?.variant ?? null,
        exitLineage: String(strategyId).split("__")[0].endsWith("_V4") ? "V4" : "V3",
        entryPrice: Number(position.entryReferencePrice),
        currentPrice: currentPriceOf(position),
        currentReturnPercent: positionReturnPercent(position),
        positionState: position.status,
        exitDecision: position.exitState?.managementDecisions?.at(-1)?.gate?.decision ?? null,
        exitReason: null,
        allocatedCapital: Number(position.referenceNotional ?? position.entryExecutionNotional ?? 0),
        unrealizedPnl: Number(position.unrealizedPnl ?? 0),
      }));
    }
  }
  return Object.freeze(rows);
}
function closedPositionRows(state) {
  const rows = [];
  for (const strategyId of STRATEGY_IDS) {
    const strategy = state.strategies[strategyId];
    for (const position of strategy.closedTradeRecords ?? []) {
      rows.push(Object.freeze({
        strategyId,
        symbol: position.symbol,
        selectionLineage: position.selectionLineage?.variant ?? null,
        exitLineage: position.exitState?.model ?? (String(strategyId).split("__")[0].endsWith("_V4") ? "V4" : "V3"),
        entryPrice: Number(position.entryReferencePrice),
        currentPrice: Number(position.exitReferencePrice),
        currentReturnPercent: finite(position.netReturnPct) ? Number(position.netReturnPct) : positionReturnPercent(position),
        positionState: position.status,
        exitDecision: "CLOSED",
        exitReason: position.exitReason ?? null,
        allocatedCapital: Number(position.referenceNotional ?? position.entryExecutionNotional ?? 0),
        realizedPnl: Number(position.realizedPnlJpy ?? 0),
      }));
    }
  }
  return Object.freeze(rows);
}

export function ensureRealtimeDashboardState(state) {
  state.dashboard ??= { lastSnapshotTime: null, history: [] };
  state.dashboard.history ??= [];
  return state.dashboard;
}

export function buildRealtimeDashboardSnapshot(state, { at = state.lastBarTime, sessionQuality = "UNKNOWN", missingBucketCount = 0 } = {}) {
  assertSafety();
  if (!at || !Number.isFinite(Date.parse(String(at)))) throw new Error("dashboard timestamp required");
  verifyRealtimeLedger(state.ledger, { sessionDate: state.sessionDate });
  const strategies = Object.freeze(STRATEGY_IDS.map((id) => Object.freeze({ ...strategySnapshot(state.strategies[id], at), cash: Number(state.strategies[id].cash) })));
  const openPositions = openPositionRows(state);
  const closedPositions = closedPositionRows(state);
  return Object.freeze({
    schemaVersion: 1,
    status: "PHASE57_REALTIME_DASHBOARD_READY",
    sessionDate: state.sessionDate,
    at,
    sessionQuality,
    missingBucketCount: Number(missingBucketCount),
    strategyCount: STRATEGY_IDS.length,
    strategies,
    openPositions,
    closedPositions,
    ledgerEventCount: state.ledger.length,
    ledgerHeadHash: state.ledgerHeadHash,
    safety: SAFETY,
  });
}

export function commitRealtimeDashboardSnapshot(state, options = {}) {
  const dashboard = ensureRealtimeDashboardState(state);
  const snapshot = buildRealtimeDashboardSnapshot(state, options);
  if (dashboard.lastSnapshotTime && Date.parse(snapshot.at) < Date.parse(dashboard.lastSnapshotTime)) throw new Error("dashboard timestamp cannot move backward");
  if (dashboard.lastSnapshotTime === snapshot.at) return dashboard.history.at(-1);
  dashboard.lastSnapshotTime = snapshot.at;
  dashboard.history.push(snapshot);
  appendLedgerEvent(state, {
    eventId: `${state.sessionDate}:${snapshot.at}:REALTIME_DASHBOARD_SNAPSHOT`,
    at: snapshot.at,
    type: "STRATEGY_SNAPSHOT_COMMITTED",
    strategyCount: snapshot.strategyCount,
    sessionQuality: snapshot.sessionQuality,
    missingBucketCount: snapshot.missingBucketCount,
  });
  return snapshot;
}

export function realtimeIntradayNetCurve(state) {
  return Object.freeze((state.dashboard?.history ?? []).map((snapshot) => Object.freeze({
    at: snapshot.at,
    strategies: Object.freeze(snapshot.strategies.map((row) => Object.freeze({ strategyId: row.strategyId, netPercent: row.netPercent }))),
  })));
}

export const PHASE57_REALTIME_DASHBOARD_SAFETY = SAFETY;
