import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_EXIT_RESEARCH_TRACE_SAFETY,
  buildP25ExitDecisionTrace,
  buildP25ExitPairedDecisionTrace,
} from '../daytrade/phase57-exit-research-decision-trace.js';

const DATE = '2026-09-03';
const ENTRY_AT = '2026-09-03T00:30:00.000Z';
const T1 = '2026-09-03T00:35:00.000Z';
const T2 = '2026-09-03T00:40:00.000Z';

function contextBars() {
  return Array.from({ length: 6 }, (_, index) => ({
    timestamp: new Date(Date.parse('2026-09-03T00:00:00.000Z') + index * 5 * 60_000).toISOString(),
    open: 100,
    high: 101,
    low: 99,
    close: 100,
    volume: 10_000,
  }));
}

function futureBars(secondClose = 99) {
  return [
    { timestamp: T1, open: 100, high: 100.2, low: 99.4, close: 99.5, volume: 10_000 },
    { timestamp: T2, open: 99.5, high: 99.6, low: 98.8, close: secondClose, volume: 11_000 },
  ];
}

function analogPool(label = -0.5) {
  return Array.from({ length: 40 }, (_, index) => ({
    sessionDate: '2026-08-01',
    symbol: `${1000 + index}.T`,
    direction: 'LONG',
    timestamp: '2026-08-01T00:30:00.000Z',
    fullyRealizedAt: '2026-08-01T01:00:00.000Z',
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

function row(secondClose = 99) {
  return {
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol: '7203.T',
    sessionDate: DATE,
    entryTimestamp: ENTRY_AT,
    entryPrice: 100,
    signalDirection: 1,
    direction: 'LONG',
    contextBars: contextBars(),
    futureBars: futureBars(secondClose),
  };
}

function closeEnough(actual, expected, label) {
  assert.ok(Math.abs(Number(actual) - Number(expected)) < 1e-10, `${label}: ${actual} !== ${expected}`);
}

test('research trace exposes per-bar v3/v4 diagnostics without changing policy behavior', () => {
  const paired = buildP25ExitPairedDecisionTrace({ row: row(), analogPool: analogPool(), roundTripCostPct: 0.05 });
  assert.equal(paired.invariant.selectorEntryMarketDataAndAllocationFrozen, true);
  assert.equal(paired.v3.summary.exitTimestamp, T1);
  assert.equal(paired.v4.summary.exitTimestamp, T2);
  assert.equal(paired.v3.trace.length, 1);
  assert.equal(paired.v4.trace.length, 2);

  const first = paired.v4.trace[0];
  assert.equal(first.timestamp, T1);
  assert.equal(first.price, 99.5);
  closeEnough(first.unrealizedReturnPct, -0.5, 'unrealized');
  closeEnough(first.mfePct, 0.2, 'running MFE');
  closeEnough(first.maePct, -0.6, 'running MAE');
  closeEnough(first.givebackPct, 0.7, 'giveback');
  closeEnough(first.captureRatio, -2.5, 'capture ratio');
  assert.equal(first.stateBucket, 'LOSER_RESCUE');
  assert.equal(first.gateResult, 'HOLD');
  assert.equal(first.exitReason, null);
  assert.equal(first.holdReason, 'V4_LOSER_RISK_NOT_CONFIRMED');
  assert.equal(first.downsideProbabilityH1, 1);
  assert.equal(first.winnerExitStreak, 0);
  assert.equal(first.neutralLossStreak, 0);

  const final = paired.v4.trace.at(-1);
  assert.equal(final.gateResult, 'EXIT');
  assert.equal(final.exitReason, paired.v4.summary.exitReason);
  closeEnough(final.mfePct, paired.v4.summary.mfePct, 'summary MFE parity');
  closeEnough(final.maePct, paired.v4.summary.maePct, 'summary MAE parity');
});

test('first decision trace is invariant to unseen later-bar changes', () => {
  const pool = analogPool();
  const baseline = buildP25ExitDecisionTrace({ row: row(99), analogPool: pool, model: 'V4' });
  const alteredFuture = buildP25ExitDecisionTrace({ row: row(70), analogPool: pool, model: 'V4' });
  assert.deepEqual(baseline.trace[0], alteredFuture.trace[0]);
});

test('research trace rejects non-frozen or outcome-contaminated Entry rows', () => {
  const pool = analogPool();
  assert.throws(
    () => buildP25ExitDecisionTrace({ row: { ...row(), frozenBeforeOutcome: false }, analogPool: pool, model: 'V3' }),
    /outcome-free frozen Entry/,
  );
  assert.throws(
    () => buildP25ExitDecisionTrace({ row: { ...row(), currentOutcomeUsed: true }, analogPool: pool, model: 'V4' }),
    /outcome-free frozen Entry/,
  );
});

test('EXIT research trace remains shadow/research only', () => {
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted',
  ]) assert.equal(PHASE57_EXIT_RESEARCH_TRACE_SAFETY[key], false, key);
  assert.equal(PHASE57_EXIT_RESEARCH_TRACE_SAFETY.researchOnly, true);
});
