import assert from 'node:assert/strict';

export const DYNAMIC_STATE_V1 = Object.freeze({
  id: 'PHASE57_EXIT_V5_DYNAMIC_STATE_V1_DEV',
  observationHorizonBars: 6,
  transactionCostBps: 5,
  states: Object.freeze(['NEUTRAL', 'DEFENSIVE', 'RECOVERED']),
  adverseBoundaryPct: 0,
  reclaimBoundaryPct: 0,
  status: 'DEVELOPMENT_CANDIDATE_NOT_FROZEN'
});

function normalizedBars(managedBars) {
  assert.ok(Array.isArray(managedBars), 'managedBars must be an array');
  return managedBars
    .map((bar) => ({
      elapsedBars: Number(bar.elapsedBars),
      currentReturnPct: Number(bar.currentReturnPct),
      timestamp: bar.timestamp ?? null,
      close: bar.close ?? null
    }))
    .filter((bar) => Number.isFinite(bar.elapsedBars) && Number.isFinite(bar.currentReturnPct))
    .sort((a, b) => a.elapsedBars - b.elapsedBars);
}

export function runDynamicStateV1({ managedBars, continuationExit, config = DYNAMIC_STATE_V1 }) {
  const bars = normalizedBars(managedBars);
  assert.ok(continuationExit && Number.isFinite(Number(continuationExit.netReturnPct)), 'continuationExit.netReturnPct required');
  assert.equal(config.observationHorizonBars, 6, 'v1 observation horizon is fixed at frozen family horizon 6');
  assert.equal(config.adverseBoundaryPct, 0, 'v1 adverse boundary must be natural zero boundary');
  assert.equal(config.reclaimBoundaryPct, 0, 'v1 reclaim boundary must be natural zero boundary');

  const first = bars.find((bar) => bar.elapsedBars === 1) ?? bars[0];
  if (!first) {
    return {
      ...continuationExit,
      dynamicState: 'NEUTRAL',
      dynamicReason: 'NO_MANAGED_BAR_CONTINUATION_FALLBACK',
      stateTransitions: []
    };
  }

  if (first.currentReturnPct >= config.adverseBoundaryPct) {
    return {
      ...continuationExit,
      dynamicState: 'RECOVERED',
      dynamicReason: 'FIRST_BAR_NON_ADVERSE_CONTINUATION',
      stateTransitions: [{ elapsedBars: first.elapsedBars, from: 'NEUTRAL', to: 'RECOVERED', reason: 'FIRST_BAR_NON_ADVERSE' }]
    };
  }

  const transitions = [{ elapsedBars: first.elapsedBars, from: 'NEUTRAL', to: 'DEFENSIVE', reason: 'FIRST_BAR_ADVERSE' }];
  for (const bar of bars) {
    if (bar.elapsedBars <= first.elapsedBars || bar.elapsedBars > config.observationHorizonBars) continue;
    if (bar.currentReturnPct >= config.reclaimBoundaryPct) {
      transitions.push({ elapsedBars: bar.elapsedBars, from: 'DEFENSIVE', to: 'RECOVERED', reason: 'ENTRY_PRICE_CLOSE_RECLAIM' });
      return {
        ...continuationExit,
        dynamicState: 'RECOVERED',
        dynamicReason: 'RECLAIMED_BEFORE_HORIZON_CONTINUATION',
        stateTransitions: transitions
      };
    }
  }

  const horizon = bars.find((bar) => bar.elapsedBars === config.observationHorizonBars);
  if (!horizon) {
    return {
      ...continuationExit,
      dynamicState: 'DEFENSIVE',
      dynamicReason: 'HORIZON_NOT_AVAILABLE_CONTINUATION_FALLBACK',
      stateTransitions: transitions
    };
  }

  const costPct = config.transactionCostBps / 100;
  return {
    exitTimestamp: horizon.timestamp,
    exitPrice: horizon.close,
    exitReason: 'V5_DYNAMIC_STATE_NO_RECLAIM_BY_BAR6',
    barsHeld: config.observationHorizonBars,
    grossReturnPct: horizon.currentReturnPct,
    netReturnPct: horizon.currentReturnPct - costPct,
    dynamicState: 'DEFENSIVE',
    dynamicReason: 'NO_RECLAIM_BY_HORIZON_EXIT',
    stateTransitions: transitions
  };
}
