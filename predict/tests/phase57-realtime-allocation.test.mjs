import assert from "node:assert/strict";
import test from "node:test";
import { createRealtimeSessionState, STRATEGY_IDS } from "../realtime/phase57-stateful-contract.js";
import { allocateRealtimeFrozenEntries, markRealtimeStrategies, PHASE57_REALTIME_ALLOCATION_SAFETY } from "../realtime/phase57-realtime-allocation.js";

const AT = "2026-09-03T00:35:00.000Z";

function entry(variant, symbol, price = 100) {
  const cells = variant === "V1" ? ["V1_V3", "V1_V4"] : ["V2_V3", "V2_V4"];
  const strategyIds = STRATEGY_IDS.filter((id) => cells.some((cell) => id.startsWith(`${cell}__`)));
  return Object.freeze({
    candidateId: `2026-09-03|${AT}|DYNAMIC5M_${variant}|${symbol}`,
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol,
    sessionDate: "2026-09-03",
    entryTimestamp: AT,
    signalDirection: 1,
    entryPrice: price,
    confidence: 0.8,
    probability: 0.75,
    sector: "TEST",
    selectionLineage: Object.freeze({
      variant,
      opportunityScore: 0.8,
      v2Score: variant === "V2" ? 0.82 : null,
    }),
    strategyLineage: Object.freeze({ cells: Object.freeze(cells), strategyIds: Object.freeze(strategyIds) }),
  });
}

test("allocates one causal Frozen Entry into all 28 strategy identities", () => {
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  const result = allocateRealtimeFrozenEntries(state, {
    at: AT,
    entries: [entry("V1", "7203"), entry("V2", "8306")],
    marksBySymbol: { "7203": 100, "8306": 100 },
  });
  assert.equal(result.strategyCount, 28);
  assert.equal(result.decisions.filter((x) => x.status === "ACCEPTED").length, 28);
  for (const id of STRATEGY_IDS) assert.equal(Object.keys(state.strategies[id].positions).length, 1, id);
  assert.equal(state.strategies["V1_V3__MAX_10"].positions["7203"].quantity, 1000);
  assert.equal(state.strategies["V2_V4__MAX_10"].positions["8306"].quantity, 1000);
});

test("same timestamp allocation replay is idempotent", () => {
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  const args = { at: AT, entries: [entry("V1", "7203")], marksBySymbol: { "7203": 100 } };
  const first = allocateRealtimeFrozenEntries(state, args);
  const ledgerLength = state.ledger.length;
  const second = allocateRealtimeFrozenEntries(state, args);
  assert.equal(second, first);
  assert.equal(state.ledger.length, ledgerLength);
});

test("mark-to-market updates all strategy equity without creating execution capability", () => {
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  allocateRealtimeFrozenEntries(state, { at: AT, entries: [entry("V1", "7203")], marksBySymbol: { "7203": 100 } });
  markRealtimeStrategies(state, { at: "2026-09-03T00:40:00.000Z", marksBySymbol: { "7203": 101 } });
  assert.ok(state.strategies["V1_V3__MAX_10"].unrealizedPnl > 0);
  for (const key of ["executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed"]) {
    assert.equal(PHASE57_REALTIME_ALLOCATION_SAFETY[key], false, key);
  }
});

test("rejects backward allocation timestamps", () => {
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  allocateRealtimeFrozenEntries(state, { at: AT, entries: [], marksBySymbol: {} });
  assert.throws(() => allocateRealtimeFrozenEntries(state, { at: "2026-09-03T00:30:00.000Z", entries: [], marksBySymbol: {} }), /cannot move backward/);
});
