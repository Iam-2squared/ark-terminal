import assert from "node:assert/strict";
import test from "node:test";
import { createRealtimeSessionState, STRATEGY_IDS } from "../realtime/phase57-stateful-contract.js";
import { commitRealtimeDashboardSnapshot, realtimeIntradayNetCurve, PHASE57_REALTIME_DASHBOARD_SAFETY } from "../realtime/phase57-realtime-dashboard.js";

const AT = "2026-09-03T01:35:00.000Z";

test("dashboard exposes all 28 strategy metrics and shadow safety", () => {
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  state.lastBarTime = AT;
  const snap = commitRealtimeDashboardSnapshot(state, { at: AT, sessionQuality: "FULL_FRESH", missingBucketCount: 0 });
  assert.equal(snap.strategyCount, 28);
  assert.equal(snap.strategies.length, 28);
  assert.deepEqual(new Set(snap.strategies.map((x) => x.strategyId)), new Set(STRATEGY_IDS));
  for (const row of snap.strategies) {
    for (const key of ["netPercent", "realizedPnl", "unrealizedPnl", "equity", "cash", "openPositions", "closedTrades", "winRate", "profitFactor", "maxDrawdownPercent"]) assert.ok(key in row, `${row.strategyId}:${key}`);
  }
  for (const key of ["executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed"]) assert.equal(PHASE57_REALTIME_DASHBOARD_SAFETY[key], false);
});

test("dashboard snapshots are append-only and form an intraday Net curve", () => {
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  state.lastBarTime = AT;
  const first = commitRealtimeDashboardSnapshot(state, { at: AT });
  const duplicate = commitRealtimeDashboardSnapshot(state, { at: AT });
  assert.equal(first, duplicate);
  state.lastBarTime = "2026-09-03T01:40:00.000Z";
  state.strategies["V1_V3__MAX_10"].equity = 1_010_000;
  state.strategies["V1_V3__MAX_10"].netPercent = 1;
  commitRealtimeDashboardSnapshot(state, { at: state.lastBarTime });
  const curve = realtimeIntradayNetCurve(state);
  assert.equal(curve.length, 2);
  assert.equal(curve[1].strategies.find((x) => x.strategyId === "V1_V3__MAX_10").netPercent, 1);
  assert.throws(() => commitRealtimeDashboardSnapshot(state, { at: "2026-09-03T01:30:00.000Z" }), /cannot move backward/);
});

test("dashboard includes open position lineage and live mark", () => {
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  state.lastBarTime = AT;
  state.strategies["V1_V3__MAX_10"].positions["7203"] = {
    status: "OPEN", symbol: "7203", entryReferencePrice: 100, entryExecutionPrice: 100,
    signalDirection: 1, quantity: 100, referenceNotional: 10_000, lastMarkPrice: 102,
    unrealizedPnl: 200, selectionLineage: { variant: "V1" }, exitState: { managementDecisions: [] },
  };
  const snap = commitRealtimeDashboardSnapshot(state, { at: AT });
  const row = snap.openPositions.find((x) => x.strategyId === "V1_V3__MAX_10" && x.symbol === "7203");
  assert.equal(row.selectionLineage, "V1");
  assert.equal(row.exitLineage, "V3");
  assert.equal(row.currentPrice, 102);
  assert.equal(row.currentReturnPercent, 2);
});
