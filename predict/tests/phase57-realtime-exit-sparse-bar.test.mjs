import assert from "node:assert/strict";
import test from "node:test";
import { createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import {
  POSITION_STATUS,
  commitShadowPositionEntry,
} from "../realtime/phase57-realtime-entry-position.js";
import { applyRealtimeExitBar } from "../realtime/phase57-realtime-exit-v3-v4.js";

const DATE = "2026-09-04";
const SYMBOL = "8918.T";
const ENTRY_AT = "2026-09-04T01:45:00.000Z";
const GAP_AT = "2026-09-04T02:05:00.000Z";
const NEXT_AT = "2026-09-04T02:10:00.000Z";
const STRATEGY_ID = "V1_V3__MAX_10";

function contextBars() {
  return Array.from({ length: 6 }, (_, index) => ({
    timestamp: new Date(Date.parse("2026-09-04T01:15:00.000Z") + index * 5 * 60_000).toISOString(),
    open: 100,
    high: 101,
    low: 99,
    close: 100,
    volume: 10_000,
  }));
}

function openPosition(session) {
  const entry = Object.freeze({
    candidateId: `${DATE}|${ENTRY_AT}|DYNAMIC5M_V1|${SYMBOL}|sparse`,
    entryAccepted: true,
    symbol: SYMBOL,
    sessionDate: DATE,
    entryTimestamp: ENTRY_AT,
    featureCutoff: "2026-09-04T01:40:00.000Z",
    signalDirection: 1,
    direction: "LONG",
    baseHorizonBars: 1,
    confidence: 0.8,
    probability: 0.8,
    sector: "OTHER",
    entryPrice: 100,
    contextBars: Object.freeze(contextBars()),
    outcomePending: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    selectionLineage: Object.freeze({ variant: "V1", variantId: "DYNAMIC5M_V1", selectionTimestamp: ENTRY_AT }),
    strategyLineage: Object.freeze({ cells: Object.freeze(["V1_V3"]), strategyIds: Object.freeze([STRATEGY_ID]) }),
  });
  const accounting = Object.freeze({
    quantity: 100,
    entryExecutionPrice: 100,
    referenceNotional: 10_000,
    entryExecutionNotional: 10_000,
    entryCostJpy: 2.5,
    entrySlippageCostJpy: 0,
    collateralJpy: 10_000,
    cashRequiredJpy: 10_002.5,
  });
  return commitShadowPositionEntry(session, { strategyId: STRATEGY_ID, entry, accounting });
}

test("sparse no-trade interval is not synthesized into an EXIT observation", () => {
  const session = createRealtimeSessionState({ sessionDate: DATE });
  openPosition(session);

  const gap = applyRealtimeExitBar(session, { at: GAP_AT, barsBySymbol: {}, analogPool: [] });
  assert.equal(gap.evaluated.length, 0);
  assert.equal(gap.closed.length, 0);
  assert.equal(gap.skipped.length, 1);
  assert.deepEqual(gap.skipped[0], {
    strategyId: STRATEGY_ID,
    symbol: SYMBOL,
    decision: "NO_OBSERVATION",
    reason: "NO_FINALIZED_BAR",
  });
  assert.equal(session.strategies[STRATEGY_ID].positionStates[SYMBOL].status, POSITION_STATUS.OPEN);
  assert.equal(session.strategies[STRATEGY_ID].positionStates[SYMBOL].lastMarkPrice, 100);

  const nextBar = { timestamp: NEXT_AT, open: 100, high: 100.4, low: 99.8, close: 100.2, volume: 12_000 };
  const next = applyRealtimeExitBar(session, { at: NEXT_AT, barsBySymbol: { [SYMBOL]: nextBar }, analogPool: [] });
  assert.equal(next.skipped.length, 0);
  assert.equal(next.evaluated.length, 1);
  assert.equal(session.strategies[STRATEGY_ID].positionStates[SYMBOL].exitState.observedBars.length, 1);
  assert.equal(session.strategies[STRATEGY_ID].positionStates[SYMBOL].exitState.observedBars[0].timestamp, NEXT_AT);
});

test("session-end still fails closed when an open position has no finalized bar", () => {
  const session = createRealtimeSessionState({ sessionDate: DATE });
  openPosition(session);
  assert.throws(
    () => applyRealtimeExitBar(session, { at: GAP_AT, barsBySymbol: {}, analogPool: [], sessionEnd: true }),
    /missing finalized EXIT bar at session end/,
  );
});
