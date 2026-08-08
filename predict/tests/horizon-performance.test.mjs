import test from 'node:test';
import assert from 'node:assert/strict';
import { compareHorizonPerformance } from '../analysis/horizon-performance.js';

function row(period, strategyReturn, hit = strategyReturn > 0) {
  return {
    status: 'resolved',
    period,
    actualReturn: strategyReturn,
    strategyReturn,
    hit,
    createdAt: '2026-08-01T00:00:00.000Z',
  };
}

test('compares only supported horizons and selects strongest eligible horizon', () => {
  const records = [
    ...Array.from({ length: 5 }, () => row(1, 0.2, true)),
    ...Array.from({ length: 5 }, () => row(3, 1.0, true)),
    ...Array.from({ length: 5 }, (_, index) => row(5, index < 2 ? 0.5 : -0.5, index < 2)),
    row(99, 10, true),
  ];
  const result = compareHorizonPerformance(records, { minimumSamples: 5 });
  assert.equal(result.status, 'COMPARABLE');
  assert.equal(result.bestHorizon, 3);
  assert.deepEqual(result.horizons.map((item) => item.horizon), [1, 3, 5, 10, 20]);
  assert.equal(result.horizons.find((item) => item.horizon === 10).sampleCount, 0);
});

test('does not declare a best horizon with insufficient samples', () => {
  const result = compareHorizonPerformance([row(1, 1, true)], { minimumSamples: 5 });
  assert.equal(result.status, 'INSUFFICIENT_DATA');
  assert.equal(result.bestHorizon, null);
});
