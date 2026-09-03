import assert from "node:assert/strict";
import test from "node:test";
import { STRATEGY_IDS } from "../realtime/phase57-stateful-contract.js";
import {
  appendPhase57MsiiDashboardHistory,
  buildPhase57MsiiDashboardSnapshot,
  PHASE57_MSII_DASHBOARD_SAFETY,
} from "../realtime/phase57-msii-dashboard.js";

const SAFE = Object.freeze({
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

function score() {
  return {
    status: "PHASE57_MSII_SHADOW_EXECUTION_SCORED",
    sessionDate: "2026-09-04",
    sessionQuality: "FULL_FRESH_MSII",
    strategyCount: STRATEGY_IDS.length,
    decisionCount: 56,
    fillRatePercent: 75,
    partialFillRatePercent: 5,
    noFillRatePercent: 15,
    expiredRatePercent: 2,
    sourceNotReadyRatePercent: 8,
    averageDecisionToFillLatencyMs: 240,
    closedTrades: 14,
    netPnlJpy: 12345,
    netReturnPercent: 0.044,
    spreadCostJpy: 900,
    slippageJpy: 180,
    strategies: STRATEGY_IDS.map((strategyId, index) => ({
      strategyId,
      intentCount: 2,
      fillRatePercent: 50 + (index % 2) * 50,
      partialFillRatePercent: 0,
      noFillRatePercent: 0,
      closedTrades: index % 3,
      wins: index % 2,
      winRate: index % 3 ? 50 : null,
      realizedPnl: index * 10,
      netPercent: index / 100,
      equity: 1_000_000 + index * 10,
      profitFactor: index % 2 ? 1.5 : null,
      maxDrawdownPercent: index / 10,
      openPositions: index % 2,
    })),
    safety: SAFE,
  };
}

function pair() {
  return {
    status: "LANE_Y_MSII_PAIRED_COMPARISON_READY",
    pairCount: 2,
    unmatchedLaneYCount: 1,
    unmatchedLaneMCount: 0,
    pairs: [
      { strategyId: STRATEGY_IDS[0], symbol: "7203.T", decisionAt: "2026-09-04T00:35:00.000Z", laneMFillStatus: "FILLED" },
      { strategyId: STRATEGY_IDS[1], symbol: "7203.T", decisionAt: "2026-09-04T00:35:00.000Z", laneMFillStatus: "PARTIAL" },
    ],
    safety: SAFE,
  };
}

test("Lane M dashboard exposes all 28 strategy rows without recomputing research decisions", () => {
  const snapshot = buildPhase57MsiiDashboardSnapshot({
    score: score(),
    pair: pair(),
    coverage: { decisionAt: "2026-09-04T00:35:00.000Z", coveragePercent: 80, missingSymbols: ["9984.T"] },
  });
  assert.equal(snapshot.status, "PHASE57_MSII_DASHBOARD_READY");
  assert.equal(snapshot.strategies.length, 28);
  assert.equal(snapshot.aggregate.strategyCount, 28);
  assert.equal(snapshot.aggregate.coveragePercent, 80);
  assert.deepEqual(snapshot.aggregate.missingSymbols, ["9984.T"]);
  assert.equal(snapshot.strategies[0].matrixCell, "V1_V3");
  assert.equal(snapshot.strategies[0].allocationProfile, "MAX_10");
  assert.equal(snapshot.strategies[0].pairedFilledCount, 1);
  assert.equal(snapshot.strategies[1].pairedPartialCount, 1);
  assert.equal(snapshot.methodology.decisionRecomputationPerformed, false);
  assert.equal(snapshot.methodology.fillRecomputationPerformed, false);
});

test("Lane M dashboard history is monotonic and idempotent", () => {
  const first = buildPhase57MsiiDashboardSnapshot({ score: score(), pair: pair(), coverage: { decisionAt: "2026-09-04T00:35:00.000Z", coveragePercent: 100, missingSymbols: [] } });
  const same = appendPhase57MsiiDashboardHistory([first], first);
  assert.equal(same.length, 1);
  const later = buildPhase57MsiiDashboardSnapshot({ score: score(), pair: pair(), coverage: { decisionAt: "2026-09-04T00:40:00.000Z", coveragePercent: 100, missingSymbols: [] } });
  const history = appendPhase57MsiiDashboardHistory(same, later);
  assert.equal(history.length, 2);
  const earlier = { ...later, at: "2026-09-04T00:30:00.000Z" };
  assert.throws(() => appendPhase57MsiiDashboardHistory(history, earlier), /cannot move backward/);
});

test("Lane M dashboard safety remains read-only", () => {
  for (const key of [
    "executionAllowed",
    "brokerWriteAllowed",
    "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed",
    "liveTradingAllowed",
    "paperTradingAllowed",
    "automaticPromotionAllowed",
    "productionUpdateAllowed",
  ]) assert.equal(PHASE57_MSII_DASHBOARD_SAFETY[key], false);
});
