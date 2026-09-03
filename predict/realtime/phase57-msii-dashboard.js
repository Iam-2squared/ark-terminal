import { STRATEGY_IDS } from "./phase57-stateful-contract.js";

const FALSE_KEYS = Object.freeze([
  "executionAllowed",
  "brokerWriteAllowed",
  "excelOrderWriteAllowed",
  "rssOrderFunctionAllowed",
  "liveTradingAllowed",
  "paperTradingAllowed",
  "automaticPromotionAllowed",
  "productionUpdateAllowed",
]);

export const PHASE57_MSII_DASHBOARD_SAFETY = Object.freeze({
  mode: "LANE_M_DASHBOARD_READ_ONLY",
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

function assertSafety(value, label) {
  if (!value || typeof value !== "object") throw new Error(`${label} safety required`);
  for (const key of FALSE_KEYS) if (value[key] !== false) throw new Error(`${label}.${key} must remain false`);
  if (value.transmitted !== undefined && value.transmitted !== false) throw new Error(`${label}.transmitted must remain false`);
}

function iso(value, label = "timestamp") {
  const parsed = Date.parse(String(value ?? ""));
  if (!Number.isFinite(parsed)) throw new Error(`${label} invalid`);
  return new Date(parsed).toISOString();
}

function finiteOrNull(value) {
  return value !== null && value !== undefined && Number.isFinite(Number(value)) ? Number(value) : null;
}

function strategyIdentity(strategyId) {
  const [matrixCell, allocationProfile] = String(strategyId).split("__");
  if (!matrixCell || !allocationProfile) throw new Error(`invalid strategyId ${strategyId}`);
  return { matrixCell, allocationProfile };
}

function pairCounts(strategyId, pair) {
  const rows = (pair?.pairs ?? []).filter((row) => row.strategyId === strategyId);
  const counts = { FILLED: 0, PARTIAL: 0, NO_FILL: 0, EXPIRED: 0, SOURCE_NOT_READY: 0 };
  for (const row of rows) {
    const status = String(row.laneMFillStatus ?? "SOURCE_NOT_READY");
    if (Object.hasOwn(counts, status)) counts[status] += 1;
  }
  return Object.freeze({
    pairedDecisionCount: rows.length,
    pairedFilledCount: counts.FILLED,
    pairedPartialCount: counts.PARTIAL,
    pairedNoFillCount: counts.NO_FILL,
    pairedExpiredCount: counts.EXPIRED,
    pairedSourceNotReadyCount: counts.SOURCE_NOT_READY,
  });
}

/**
 * Build a presentation-only snapshot from already-computed Lane M artifacts.
 * This function never recreates Selection, Entry, EXIT, Allocation, or fill decisions.
 */
export function buildPhase57MsiiDashboardSnapshot({ score, pair, coverage, at = null } = {}) {
  assertSafety(PHASE57_MSII_DASHBOARD_SAFETY, "dashboard");
  if (!score || score.status !== "PHASE57_MSII_SHADOW_EXECUTION_SCORED") throw new Error("Lane M scored artifact required");
  if (!pair || pair.status !== "LANE_Y_MSII_PAIRED_COMPARISON_READY") throw new Error("Lane Y/M pair artifact required");
  assertSafety(score.safety, "score");
  assertSafety(pair.safety, "pair");
  if (Number(score.strategyCount) !== STRATEGY_IDS.length) throw new Error("Lane M dashboard requires all 28 strategy identities");
  if (!Array.isArray(score.strategies) || score.strategies.length !== STRATEGY_IDS.length) throw new Error("Lane M strategy score surface must contain 28 rows");
  const scoreById = new Map(score.strategies.map((row) => [row.strategyId, row]));
  const strategies = STRATEGY_IDS.map((strategyId) => {
    const row = scoreById.get(strategyId);
    if (!row) throw new Error(`missing Lane M strategy score ${strategyId}`);
    const { matrixCell, allocationProfile } = strategyIdentity(strategyId);
    return Object.freeze({
      strategyId,
      matrixCell,
      allocationProfile,
      intentCount: Number(row.intentCount ?? 0),
      fillRatePercent: finiteOrNull(row.fillRatePercent),
      partialFillRatePercent: finiteOrNull(row.partialFillRatePercent),
      noFillRatePercent: finiteOrNull(row.noFillRatePercent),
      closedTrades: Number(row.closedTrades ?? 0),
      wins: Number(row.wins ?? 0),
      winRate: finiteOrNull(row.winRate),
      realizedPnlJpy: finiteOrNull(row.realizedPnl),
      netPercent: finiteOrNull(row.netPercent),
      equity: finiteOrNull(row.equity),
      profitFactor: Number.isFinite(Number(row.profitFactor)) ? Number(row.profitFactor) : row.profitFactor ?? null,
      maxDrawdownPercent: finiteOrNull(row.maxDrawdownPercent),
      openPositions: Number(row.openPositions ?? 0),
      ...pairCounts(strategyId, pair),
    });
  });
  const effectiveAt = at ?? coverage?.decisionAt ?? pair?.pairs?.at(-1)?.decisionAt ?? score?.sessionDate;
  const coveragePercent = finiteOrNull(coverage?.coveragePercent ?? coverage?.occurrenceCoveragePercent);
  const missingSymbols = Object.freeze([...(coverage?.missingSymbols ?? coverage?.distinctMissingSymbols ?? [])]);
  const snapshot = {
    schemaVersion: 1,
    phase: "57.msii.dashboard.r1",
    status: "PHASE57_MSII_DASHBOARD_READY",
    sessionDate: score.sessionDate ?? null,
    at: effectiveAt && String(effectiveAt).includes("T") ? iso(effectiveAt, "dashboard at") : null,
    sessionQuality: score.sessionQuality ?? null,
    aggregate: Object.freeze({
      strategyCount: STRATEGY_IDS.length,
      decisionCount: Number(score.decisionCount ?? score.intentCount ?? 0),
      fillRatePercent: finiteOrNull(score.fillRatePercent),
      partialFillRatePercent: finiteOrNull(score.partialFillRatePercent),
      noFillRatePercent: finiteOrNull(score.noFillRatePercent),
      expiredRatePercent: finiteOrNull(score.expiredRatePercent),
      sourceNotReadyRatePercent: finiteOrNull(score.sourceNotReadyRatePercent),
      averageDecisionToFillLatencyMs: finiteOrNull(score.averageDecisionToFillLatencyMs),
      closedTrades: Number(score.closedTrades ?? 0),
      netPnlJpy: finiteOrNull(score.netPnlJpy),
      netReturnPercent: finiteOrNull(score.netReturnPercent),
      spreadCostJpy: finiteOrNull(score.spreadCostJpy),
      slippageJpy: finiteOrNull(score.slippageJpy),
      pairCount: Number(pair.pairCount ?? 0),
      unmatchedLaneYCount: Number(pair.unmatchedLaneYCount ?? 0),
      unmatchedLaneMCount: Number(pair.unmatchedLaneMCount ?? 0),
      coveragePercent,
      missingSymbolCount: missingSymbols.length,
      missingSymbols,
    }),
    strategies: Object.freeze(strategies),
    methodology: Object.freeze({
      ledgerReadOnly: true,
      decisionRecomputationPerformed: false,
      fillRecomputationPerformed: false,
      diagnosticOnly: true,
      exactLaneYDecisionPairingPreserved: true,
    }),
    safety: PHASE57_MSII_DASHBOARD_SAFETY,
  };
  return Object.freeze(snapshot);
}

export function appendPhase57MsiiDashboardHistory(history = [], snapshot) {
  if (snapshot?.status !== "PHASE57_MSII_DASHBOARD_READY") throw new Error("valid Lane M dashboard snapshot required");
  assertSafety(snapshot.safety, "snapshot");
  const out = [...history];
  const prior = out.at(-1);
  if (snapshot.at && prior?.at && Date.parse(snapshot.at) < Date.parse(prior.at)) throw new Error("Lane M dashboard history cannot move backward");
  if (snapshot.at && prior?.at === snapshot.at) {
    if (JSON.stringify(prior) !== JSON.stringify(snapshot)) throw new Error("Lane M dashboard same-timestamp conflict");
    return Object.freeze(out);
  }
  out.push(snapshot);
  return Object.freeze(out);
}

export default {
  buildPhase57MsiiDashboardSnapshot,
  appendPhase57MsiiDashboardHistory,
};
