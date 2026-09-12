import test from 'node:test';
import assert from 'node:assert/strict';
import { runDynamicStateV1, DYNAMIC_STATE_V1 } from '../lib/phase57-exit-v5-dynamic-state.mjs';

const v4 = {
  exitTimestamp: 'T20',
  exitPrice: 120,
  exitReason: 'V4_CONTINUATION',
  barsHeld: 20,
  grossReturnPct: 2.0,
  netReturnPct: 1.95,
  internalStateSentinel: { neutralLossStreak: 2, winnerExitStreak: 1 }
};

function bars(values) {
  return values.map((currentReturnPct, i) => ({
    elapsedBars: i + 1,
    currentReturnPct,
    timestamp: `T${i + 1}`,
    close: 100 + i
  }));
}

test('first bar non-adverse passes through continuation without resetting continuation state', () => {
  const out = runDynamicStateV1({ managedBars: bars([0.1, 0.2, 0.3]), continuationExit: v4 });
  assert.equal(out.netReturnPct, v4.netReturnPct);
  assert.equal(out.exitTimestamp, v4.exitTimestamp);
  assert.equal(out.exitReason, v4.exitReason);
  assert.deepEqual(out.internalStateSentinel, v4.internalStateSentinel);
  assert.equal(out.dynamicState, 'RECOVERED');
  assert.equal(out.dynamicReason, 'FIRST_BAR_NON_ADVERSE_CONTINUATION');
});

test('initial adverse trade can recover on the next completed bar and promote without symbol-specific override', () => {
  // Regression shape modeled on exposed recovery cases, intentionally symbol-free.
  const out = runDynamicStateV1({ managedBars: bars([-1.23, 0.82, 2.46, 2.05, 0.82, 4.92]), continuationExit: v4 });
  assert.equal(out.netReturnPct, v4.netReturnPct);
  assert.equal(out.dynamicState, 'RECOVERED');
  assert.equal(out.stateTransitions.at(-1).elapsedBars, 2);
  assert.equal(out.stateTransitions.at(-1).reason, 'ENTRY_PRICE_CLOSE_RECLAIM');
});

test('initial adverse trade can recover sharply before horizon and continuation outcome is preserved', () => {
  // Second exposed-shape regression; no event/symbol key is available to the state machine.
  const out = runDynamicStateV1({ managedBars: bars([-3.36, 5.37]), continuationExit: v4 });
  assert.equal(out.netReturnPct, v4.netReturnPct);
  assert.equal(out.exitReason, v4.exitReason);
  assert.equal(out.dynamicState, 'RECOVERED');
  assert.equal(out.stateTransitions.at(-1).elapsedBars, 2);
});

test('initial adverse trade with no reclaim exits at bar 6 close with exactly 5bps cost', () => {
  const out = runDynamicStateV1({ managedBars: bars([-0.5, -0.8, -1.0, -0.7, -0.6, -0.4]), continuationExit: v4 });
  assert.equal(out.exitReason, 'V5_DYNAMIC_STATE_NO_RECLAIM_BY_BAR6');
  assert.equal(out.barsHeld, 6);
  assert.equal(out.exitTimestamp, 'T6');
  assert.equal(out.exitPrice, 105);
  assert.equal(out.grossReturnPct, -0.4);
  assert.equal(out.netReturnPct, -0.45);
});

test('future reclaim after bar 6 cannot change the bar 6 decision', () => {
  const out = runDynamicStateV1({ managedBars: bars([-0.4, -0.3, -0.2, -0.1, -0.05, -0.02, 3.0]), continuationExit: v4 });
  assert.equal(out.exitReason, 'V5_DYNAMIC_STATE_NO_RECLAIM_BY_BAR6');
  assert.equal(out.exitTimestamp, 'T6');
  assert.equal(out.dynamicState, 'DEFENSIVE');
});

test('input order cannot create future access because bars are causally ordered by elapsedBars', () => {
  const shuffled = [
    { elapsedBars: 7, currentReturnPct: 4, timestamp: 'T7', close: 107 },
    { elapsedBars: 1, currentReturnPct: -1, timestamp: 'T1', close: 101 },
    { elapsedBars: 6, currentReturnPct: -0.2, timestamp: 'T6', close: 106 },
    { elapsedBars: 2, currentReturnPct: -0.8, timestamp: 'T2', close: 102 }
  ];
  const out = runDynamicStateV1({ managedBars: shuffled, continuationExit: v4 });
  assert.equal(out.exitTimestamp, 'T6');
  assert.equal(out.dynamicReason, 'NO_RECLAIM_BY_HORIZON_EXIT');
});

test('insufficient horizon fails closed to continuation instead of synthesizing a future bar', () => {
  const out = runDynamicStateV1({ managedBars: bars([-0.5, -0.4, -0.2]), continuationExit: v4 });
  assert.equal(out.netReturnPct, v4.netReturnPct);
  assert.equal(out.exitReason, v4.exitReason);
  assert.equal(out.dynamicReason, 'HORIZON_NOT_AVAILABLE_CONTINUATION_FALLBACK');
});

test('v1 contract has zero free return thresholds and existing horizon 6 only', () => {
  assert.equal(DYNAMIC_STATE_V1.adverseBoundaryPct, 0);
  assert.equal(DYNAMIC_STATE_V1.reclaimBoundaryPct, 0);
  assert.equal(DYNAMIC_STATE_V1.observationHorizonBars, 6);
  assert.equal(DYNAMIC_STATE_V1.transactionCostBps, 5);
});
