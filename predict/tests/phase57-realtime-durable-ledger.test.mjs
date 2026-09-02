import assert from "node:assert/strict";
import test from "node:test";
import {
  SAFETY,
  appendLedgerEvent,
  createRealtimeCheckpoint,
  createRealtimeSessionState,
  verifyRealtimeCheckpoint,
  verifyRealtimeLedger,
} from "../realtime/phase57-stateful-contract.js";

const A = "2026-09-03T00:35:00.000Z";
const B = "2026-09-03T00:40:00.000Z";

function seeded() {
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  appendLedgerEvent(state, { eventId: "e1", at: A, type: "BAR_FINALIZED", source: "fixture" });
  appendLedgerEvent(state, { eventId: "e2", at: A, type: "SELECTION_COMMITTED", source: "fixture" });
  appendLedgerEvent(state, { eventId: "e3", at: B, type: "STRATEGY_SNAPSHOT_COMMITTED", strategyId: "V1_V3__MAX_10" });
  return state;
}

test("ledger events are sequence-ordered and hash chained", () => {
  const state = seeded();
  assert.equal(state.ledger.length, 3);
  assert.equal(state.ledger[0].sequence, 0);
  assert.equal(state.ledger[1].previousHash, state.ledger[0].eventHash);
  assert.equal(state.ledgerHeadHash, state.ledger.at(-1).eventHash);
  assert.equal(verifyRealtimeLedger(state.ledger, { sessionDate: state.sessionDate }).valid, true);
});

test("tampering is detected without reconstructing decisions", () => {
  const state = seeded();
  const copy = state.ledger.map((row) => ({ ...row }));
  copy[1].type = "MUTATED";
  assert.throws(() => verifyRealtimeLedger(copy, { sessionDate: state.sessionDate }), /eventHash mismatch/);
});

test("duplicate ids and backward timestamps fail closed", () => {
  const state = seeded();
  assert.throws(() => appendLedgerEvent(state, { eventId: "e3", at: B, type: "DUP" }), /duplicate eventId/);
  assert.throws(() => appendLedgerEvent(state, { eventId: "e4", at: A, type: "BACKWARD" }), /non-causal ledger ordering/);
});

test("checkpoint anchors immutable ledger prefix and detects corruption", () => {
  const state = seeded();
  state.lastBarTime = B;
  const checkpoint = createRealtimeCheckpoint(state);
  assert.equal(checkpoint.ledgerEventCount, 3);
  assert.equal(verifyRealtimeCheckpoint(checkpoint, state.ledger).valid, true);

  appendLedgerEvent(state, { eventId: "e4", at: B, type: "SESSION_QUALITY_UPDATED", completeness: "PARTIAL_INCOMPLETE_SESSION" });
  assert.equal(verifyRealtimeCheckpoint(checkpoint, state.ledger).valid, true);

  const corrupted = state.ledger.map((row) => ({ ...row }));
  corrupted[2].eventHash = "f".repeat(64);
  assert.throws(() => verifyRealtimeCheckpoint(checkpoint, corrupted), /eventHash mismatch|anchor mismatch/);
});

test("durable ledger remains shadow-only", () => {
  for (const key of ["executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed"]) {
    assert.equal(SAFETY[key], false, key);
  }
  for (const row of seeded().ledger) assert.equal(row.executable, false);
});
