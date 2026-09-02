import assert from "node:assert/strict";
import test from "node:test";
import { simulateP25ExitV3DualGate } from "../daytrade/phase57-p25-exit-v3-dual-gate.js";
import { simulateP25ExitV4 } from "../daytrade/phase57-p25-exit-v4-structural-risk.js";
import { createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import {
  POSITION_STATUS,
  commitShadowPositionEntry,
} from "../realtime/phase57-realtime-entry-position.js";
import {
  PHASE57_REALTIME_EXIT_SAFETY,
  applyRealtimeExitBar,
} from "../realtime/phase57-realtime-exit-v3-v4.js";

const DATE = "2026-09-03";
const SYMBOL = "7203.T";
const ENTRY_AT = "2026-09-03T00:30:00.000Z";
const T1 = "2026-09-03T00:35:00.000Z";
const T2 = "2026-09-03T00:40:00.000Z";

function contextBars() {
  return Array.from({ length: 6 }, (_, index) => ({
    timestamp: new Date(Date.parse("2026-09-03T00:00:00.000Z") + index * 5 * 60_000).toISOString(),
    open: 100,
    high: 101,
    low: 99,
    close: 100,
    volume: 10_000,
  }));
}

const future = Object.freeze([
  Object.freeze({ timestamp: T1, open: 100, high: 100.2, low: 99.4, close: 99.5, volume: 10_000 }),
  Object.freeze({ timestamp: T2, open: 99.5, high: 99.6, low: 98.8, close: 99, volume: 11_000 }),
]);

function analogPool(label = -0.5) {
  return Array.from({ length: 40 }, (_, index) => ({
    sessionDate: "2026-08-01",
    symbol: `${1000 + index}.T`,
    direction: "LONG",
    timestamp: "2026-08-01T00:30:00.000Z",
    fullyRealizedAt: "2026-08-01T01:00:00.000Z",
    state: {
      currentReturnPct: -0.5,
      bestReturnPct: 0,
      givebackPctPoints: 0.5,
      atrPct: 1,
      momentumPct: -0.2,
      bodyPressure: -0.5,
      directionalRangePos: 0.2,
      elapsedBars: 1,
    },
    labels: { 1: label, 3: label, 6: label },
  }));
}

function entry(strategyId, candidateSuffix = "base") {
  const cell = strategyId.split("__")[0];
  return Object.freeze({
    candidateId: `${DATE}|${ENTRY_AT}|DYNAMIC5M_V1|${SYMBOL}|${candidateSuffix}`,
    entryAccepted: true,
    symbol: SYMBOL,
    sessionDate: DATE,
    entryTimestamp: ENTRY_AT,
    featureCutoff: "2026-09-03T00:25:00.000Z",
    signalDirection: 1,
    direction: "LONG",
    baseHorizonBars: 1,
    confidence: 0.8,
    probability: 0.8,
    sector: "AUTO",
    entryPrice: 100,
    contextBars: Object.freeze(contextBars()),
    outcomePending: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    selectionLineage: Object.freeze({ variant: "V1", variantId: "DYNAMIC5M_V1", selectionTimestamp: ENTRY_AT }),
    strategyLineage: Object.freeze({ cells: Object.freeze([cell]), strategyIds: Object.freeze([strategyId]) }),
  });
}

function accounting() {
  return Object.freeze({
    quantity: 100,
    entryExecutionPrice: 100,
    referenceNotional: 10_000,
    entryExecutionNotional: 10_000,
    entryCostJpy: 2.5,
    entrySlippageCostJpy: 0,
    collateralJpy: 10_000,
    cashRequiredJpy: 10_002.5,
  });
}

function open(session, strategyId, candidateSuffix) {
  return commitShadowPositionEntry(session, { strategyId, entry: entry(strategyId, candidateSuffix), accounting: accounting() });
}

function batchRow() {
  return {
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol: SYMBOL,
    sessionDate: DATE,
    entryTimestamp: ENTRY_AT,
    entryPrice: 100,
    signalDirection: 1,
    direction: "LONG",
    contextBars: contextBars(),
    futureBars: future,
  };
}

function closeEnough(actual, expected, message) {
  assert.ok(Math.abs(Number(actual) - Number(expected)) < 1e-10, `${message}: ${actual} !== ${expected}`);
}

test("Realtime EXIT v3/v4 independently match their existing batch simulations", () => {
  const pool = analogPool();
  const expectedV3 = simulateP25ExitV3DualGate({ row: batchRow(), analogPool: pool, roundTripCostPct: 0.05 });
  const expectedV4 = simulateP25ExitV4({ row: batchRow(), analogPool: pool, roundTripCostPct: 0.05 });
  assert.equal(expectedV3.exitTimestamp, T1);
  assert.equal(expectedV4.exitTimestamp, T2);

  const session = createRealtimeSessionState({ sessionDate: DATE });
  const v3Strategy = "V1_V3__MAX_10";
  const v4Strategy = "V1_V4__MAX_10";
  open(session, v3Strategy, "v3");
  open(session, v4Strategy, "v4");

  const first = applyRealtimeExitBar(session, { at: T1, barsBySymbol: { [SYMBOL]: future[0] }, analogPool: pool });
  assert.equal(first.closed.length, 1);
  assert.equal(session.strategies[v3Strategy].positionStates[SYMBOL].status, POSITION_STATUS.CLOSED);
  assert.equal(session.strategies[v4Strategy].positionStates[SYMBOL].status, POSITION_STATUS.OPEN);
  closeEnough(session.strategies[v4Strategy].unrealizedPnl, -50, "OPEN unrealized PnL");

  const second = applyRealtimeExitBar(session, { at: T2, barsBySymbol: { [SYMBOL]: future[1] }, analogPool: pool });
  assert.equal(second.closed.length, 1);
  const actualV3 = session.strategies[v3Strategy].positionStates[SYMBOL];
  const actualV4 = session.strategies[v4Strategy].positionStates[SYMBOL];
  for (const [actual, expected] of [[actualV3, expectedV3], [actualV4, expectedV4]]) {
    assert.equal(actual.status, POSITION_STATUS.CLOSED);
    assert.equal(actual.exitTimestamp, expected.exitTimestamp);
    assert.equal(actual.exitReferencePrice, expected.exitPrice);
    assert.equal(actual.exitReason, expected.exitReason);
    assert.equal(actual.barsHeld, expected.barsHeld);
    assert.equal(actual.exitState.policySha256, expected.policySha256);
    for (const key of ["grossReturnPct", "netReturnPct", "mfePct", "maePct", "givebackPct", "captureRatio"]) closeEnough(actual[key], expected[key], key);
    closeEnough(actual.realizedPnlJpy / actual.referenceNotional * 100, expected.netReturnPct, "realized return parity");
  }
  assert.equal(session.strategies[v3Strategy].unrealizedPnl, 0);
  assert.equal(session.strategies[v4Strategy].unrealizedPnl, 0);

  const replayed = applyRealtimeExitBar(session, { at: T2, barsBySymbol: { [SYMBOL]: future[1] }, analogPool: pool });
  assert.equal(replayed, second);
  assert.equal(session.exit.history.length, 2);
  assert.equal(session.ledger.filter((event) => event.type === "SHADOW_POSITION_CLOSED").length, 2);
  assert.throws(
    () => commitShadowPositionEntry(session, { strategyId: v4Strategy, entry: { ...entry(v4Strategy, "reopen"), entryTimestamp: "2026-09-03T00:45:00.000Z" }, accounting: accounting() }),
    /is not FLAT/,
  );
});

test("SESSION_END closure matches batch fallback without changing EXIT policy", () => {
  const pool = analogPool(0.5);
  const row = { ...batchRow(), futureBars: [future[0]] };
  const expected = simulateP25ExitV3DualGate({ row, analogPool: pool, roundTripCostPct: 0.05 });
  assert.equal(expected.exitReason, "SESSION_END");
  const session = createRealtimeSessionState({ sessionDate: DATE });
  const strategyId = "V1_V3__MAX_4";
  open(session, strategyId, "session-end");
  applyRealtimeExitBar(session, { at: T1, barsBySymbol: { [SYMBOL]: future[0] }, analogPool: pool, sessionEnd: true });
  const closed = session.strategies[strategyId].positionStates[SYMBOL];
  assert.equal(closed.exitReason, expected.exitReason);
  assert.equal(closed.exitTimestamp, expected.exitTimestamp);
  closeEnough(closed.netReturnPct, expected.netReturnPct, "session end net return");
});

test("duplicate conflicts and backward EXIT timestamps fail closed", () => {
  const pool = analogPool();
  const session = createRealtimeSessionState({ sessionDate: DATE });
  open(session, "V1_V4__MAX_3", "causal");
  applyRealtimeExitBar(session, { at: T1, barsBySymbol: { [SYMBOL]: future[0] }, analogPool: pool });
  assert.throws(
    () => applyRealtimeExitBar(session, { at: T1, barsBySymbol: { [SYMBOL]: { ...future[0], close: 99.4 } }, analogPool: pool }),
    /conflicting duplicate EXIT evaluation timestamp/,
  );
  assert.throws(
    () => applyRealtimeExitBar(session, { at: ENTRY_AT, barsBySymbol: {}, analogPool: pool }),
    /cannot move backward/,
  );
});

test("R5 remains Shadow-only with every write and trading surface false", () => {
  for (const key of [
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
    "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
  ]) assert.equal(PHASE57_REALTIME_EXIT_SAFETY[key], false, key);
});
