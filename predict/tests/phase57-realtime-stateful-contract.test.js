import test from "node:test";
import assert from "node:assert/strict";
import {
  SAFETY,
  STRATEGY_IDS,
  createRealtimeSessionState,
  appendLedgerEvent,
  dashboardSnapshot,
} from "../realtime/phase57-stateful-contract.js";

test("realtime contract exposes exactly 28 Dynamic5m strategies", () => {
  assert.equal(STRATEGY_IDS.length, 28);
  assert.equal(new Set(STRATEGY_IDS).size, 28);
});

test("all trading/write safety stays fail-closed", () => {
  for (const key of ["executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed"]) {
    assert.equal(SAFETY[key], false, key);
  }
});

test("ledger is append-only by event id and causal ordering", () => {
  const s = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  s.lastBarTime = "2026-09-03T09:05:00+09:00";
  appendLedgerEvent(s, { eventId: "a", at: s.lastBarTime, type: "BAR_COMMITTED" });
  assert.throws(() => appendLedgerEvent(s, { eventId: "a", at: s.lastBarTime, type: "BAR_COMMITTED" }), /duplicate/);
  assert.throws(() => appendLedgerEvent(s, { eventId: "b", at: "2026-09-03T09:00:00+09:00", type: "BAR_COMMITTED" }), /non-causal/);
});

test("dashboard has realtime metrics for every strategy", () => {
  const s = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  const d = dashboardSnapshot(s, "2026-09-03T10:35:00+09:00");
  assert.equal(d.strategyCount, 28);
  assert.equal(d.strategies.length, 28);
  for (const x of d.strategies) {
    for (const key of ["netPercent","realizedPnl","unrealizedPnl","openPositions","closedTrades","winRate","profitFactor","maxDrawdownPercent"]) assert.ok(key in x);
  }
});
