import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateAdaptiveHorizonStability, PHASE53_2_SAFETY } from '../adaptive/phase53-horizon-stability.js';

function row(period, strategyReturn, createdAt) {
  return {
    status: 'resolved',
    period,
    actualReturn: strategyReturn,
    strategyReturn,
    hit: strategyReturn > 0,
    createdAt,
  };
}

function stableWindow(day) {
  const stamp = (offset) => new Date(Date.UTC(2026, 7, day, 0, offset, 0)).toISOString();
  return [
    ...Array.from({ length: 5 }, (_, i) => row(1, i < 3 ? 0.2 : -0.2, stamp(i))),
    ...Array.from({ length: 5 }, (_, i) => row(3, 1.0, stamp(i + 5))),
    ...Array.from({ length: 5 }, (_, i) => row(5, i < 2 ? 0.4 : -0.4, stamp(i + 10))),
  ];
}

test('promotes only a horizon that remains dominant across chronological windows', () => {
  const records = [
    ...stableWindow(1),
    ...stableWindow(2),
    ...stableWindow(3),
  ];
  const result = evaluateAdaptiveHorizonStability(records, {
    windowSize: 15,
    minimumSamples: 5,
    minimumComparableWindows: 3,
    minimumDominance: 0.6,
    maximumSwitches: 1,
  });

  assert.equal(result.status, 'STABLE_HORIZON_CANDIDATE');
  assert.equal(result.dominantHorizon, 3);
  assert.equal(result.comparableWindowCount, 3);
  assert.equal(result.dominance, 1);
  assert.equal(result.switches, 0);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.liveTradingAllowed, false);
  assert.equal(result.transmitted, false);
});

test('fails closed when there are not enough comparable windows', () => {
  const result = evaluateAdaptiveHorizonStability(stableWindow(1), {
    windowSize: 15,
    minimumSamples: 5,
    minimumComparableWindows: 3,
  });

  assert.equal(result.status, 'OBSERVE');
  assert.equal(result.dominantHorizon, null);
  assert.ok(result.blockers.includes('INSUFFICIENT_STABILITY_WINDOWS'));
  assert.equal(result.executionAllowed, false);
});

test('keeps Phase53.2 operational boundaries read-only', () => {
  assert.deepEqual(PHASE53_2_SAFETY, {
    mode: 'ADAPTIVE_HORIZON_STABILITY_REVIEW_ONLY',
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  });
});
