import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { STRATEGY_IDS } from "../realtime/phase57-stateful-contract.js";
import { rebuildPhase57MsiiDashboardArtifacts, PHASE57_MSII_DASHBOARD_WATCH_SAFETY } from "../../tools/phase57_msii_dashboard_watch.mjs";

const SAFE = {
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
};
function score(at) {
  return {
    status: "PHASE57_MSII_SHADOW_EXECUTION_SCORED",
    sessionDate: "2026-09-04",
    sessionQuality: "FULL_FRESH_MSII",
    strategyCount: 28,
    decisionCount: 28,
    fillRatePercent: 100,
    partialFillRatePercent: 0,
    noFillRatePercent: 0,
    expiredRatePercent: 0,
    sourceNotReadyRatePercent: 0,
    averageDecisionToFillLatencyMs: 100,
    closedTrades: 7,
    netPnlJpy: 700,
    netReturnPercent: 0.0025,
    spreadCostJpy: 100,
    slippageJpy: 50,
    coverage: { decisionAt: at, coveragePercent: 100, missingSymbols: [] },
    strategies: STRATEGY_IDS.map((strategyId) => ({ strategyId, intentCount: 1, fillRatePercent: 100, partialFillRatePercent: 0, noFillRatePercent: 0, closedTrades: 0, wins: 0, winRate: null, realizedPnl: 0, netPercent: 0, equity: 1_000_000, profitFactor: null, maxDrawdownPercent: 0, openPositions: 0 })),
    safety: SAFE,
  };
}
function pair(at) {
  return { status: "LANE_Y_MSII_PAIRED_COMPARISON_READY", pairCount: 1, unmatchedLaneYCount: 0, unmatchedLaneMCount: 0, pairs: [{ strategyId: STRATEGY_IDS[0], symbol: "7203.T", decisionAt: at, laneMFillStatus: "FILLED" }], safety: SAFE };
}
function write(file, value) { fs.writeFileSync(file, `${JSON.stringify(value)}\n`, "utf8"); }

test("dashboard watcher waits for score/pair and persists monotonic latest/history artifacts", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "phase57-msii-dashboard-"));
  try {
    const waiting = rebuildPhase57MsiiDashboardArtifacts(dir);
    assert.equal(waiting.status, "WAITING_FOR_LANE_M_SCORE_PAIR");
    const firstAt = "2026-09-04T00:35:00.000Z";
    write(path.join(dir, "latest-score.json"), score(firstAt));
    write(path.join(dir, "latest-pair.json"), pair(firstAt));
    const first = rebuildPhase57MsiiDashboardArtifacts(dir);
    assert.equal(first.status, "PHASE57_MSII_DASHBOARD_UPDATED");
    assert.equal(first.historyPointCount, 1);
    assert.equal(JSON.parse(fs.readFileSync(path.join(dir, "dashboard-latest.json"), "utf8")).strategies.length, 28);
    const same = rebuildPhase57MsiiDashboardArtifacts(dir);
    assert.equal(same.status, "PHASE57_MSII_DASHBOARD_CURRENT");
    assert.equal(same.historyPointCount, 1);
    const secondAt = "2026-09-04T00:40:00.000Z";
    write(path.join(dir, "latest-score.json"), score(secondAt));
    write(path.join(dir, "latest-pair.json"), pair(secondAt));
    const second = rebuildPhase57MsiiDashboardArtifacts(dir);
    assert.equal(second.status, "PHASE57_MSII_DASHBOARD_UPDATED");
    assert.equal(second.historyPointCount, 2);
    assert.equal(JSON.parse(fs.readFileSync(path.join(dir, "dashboard-history.json"), "utf8")).length, 2);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("dashboard watcher safety remains read-only", () => {
  for (const key of ["executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed"]) assert.equal(PHASE57_MSII_DASHBOARD_WATCH_SAFETY[key], false);
});
