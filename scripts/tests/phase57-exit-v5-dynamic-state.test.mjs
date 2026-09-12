import test from 'node:test';
import assert from 'node:assert/strict';
import { runDynamicStateV1, DYNAMIC_STATE_V1 } from '../lib/phase57-exit-v5-dynamic-state.mjs';

const v4 = { exitTimestamp: 'T20', exitPrice: 120, exitReason: 'V4_CONTINUATION', barsHeld: 20, grossReturnPct: 2.0, netReturnPct: 1.95 };

function bars(values) {
  return values.map((currentReturnPct, i) => ({ elapsedBars: i + 1, currentReturnPct, timestamp: `T${i + 1}`, close: 100 + i }));
}

test('first bar non-adverse passes through continuation', () => {
  const out = runDynamicStateV1({ managedBars: bars([0.1, 0.2, 0.3]), continuationExit: v4 });
  assert.equal(out.netReturnPct, v4.netReturnPct);
  assert.equal(out.dynamicState, 'RECOVERED');
  assert.equal(out.dynamicReason, 'FIRST_BAR_NON_ADVERSE_CONTINUATION');
});

test('initial adverse trade can recover and promote without symbol-specific override', () => {
  const out = runDynamicStateV1({ managedBars: bars([-1.2, -0.7, -0.2, 0.1, 0.8, 1.4]), continuationExit: v4 });
  assert.equal(out.netReturnPct, v4.netReturnPct);
  assert.equal(out.dynamicState, 'RECOVERED');
  assert.equal(out.stateTransitions.at(-1).reason, 'ENTRY_PRICE_CLOSE_RECLAIM');
});

test('initial adverse trade with no reclaim exits at bar 6 close', () => {
  const out = runDynamicStateV1({ managedBars: bars([-0.5, -0.8, -1.0, -0.7, -0.6, -0.4]), continuationExit: v4 });
  assert.equal(out.exitReason, 'V5_DYNAMIC_STATE_NO_RECLAIM_BY_BAR6');
  assert.equal(out.barsHeld, 6);
  assert.equal(out.grossReturnPct, -0.4);
  assert.equal(out.netReturnPct, -0.45);
});

test('insufficient horizon fails closed to continuation instead of synthesizing a future bar', () => {
  const out = runDynamicStateV1({ managedBars: bars([-0.5, -0.4, -0.2]), continuationExit: v4 });
  assert.equal(out.netReturnPct, v4.netReturnPct);
  assert.equal(out.dynamicReason, 'HORIZON_NOT_AVAILABLE_CONTINUATION_FALLBACK');
});

test('v1 contract has zero free return thresholds and existing horizon 6 only', () => {
  assert.equal(DYNAMIC_STATE_V1.adverseBoundaryPct, 0);
  assert.equal(DYNAMIC_STATE_V1.reclaimBoundaryPct, 0);
  assert.equal(DYNAMIC_STATE_V1.observationHorizonBars, 6);
  assert.equal(DYNAMIC_STATE_V1.transactionCostBps, 5);
});
