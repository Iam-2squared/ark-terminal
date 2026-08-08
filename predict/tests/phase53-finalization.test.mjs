import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluatePhase53Finalization } from '../adaptive/phase53-finalization.js';

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

function windowWithWinner(day, winner = 3) {
  const horizons = [1, 3, 5, 10, 20];
  const stamp = (offset) => new Date(Date.UTC(2026, 7, day, 0, offset, 0)).toISOString();
  return horizons.flatMap((horizon, horizonIndex) =>
    Array.from({ length: 5 }, (_, sampleIndex) => {
      const strategyReturn = horizon === winner
        ? 1.0
        : (sampleIndex < 2 ? 0.2 : -0.2);
      return row(horizon, strategyReturn, stamp(horizonIndex * 5 + sampleIndex));
    }),
  );
}

test('Phase53.x exposes stable horizon only as review candidate', () => {
  const records = [
    ...windowWithWinner(1, 3),
    ...windowWithWinner(2, 3),
    ...windowWithWinner(3, 3),
  ];
  const result = evaluatePhase53Finalization(records, {
    windowSize: 25,
    minimumSamples: 5,
    minimumComparableWindows: 3,
    minimumDominance: 0.6,
    maximumSwitches: 1,
  });
  assert.equal(result.reviewStatus, 'REVIEW_CANDIDATE');
  assert.equal(result.candidateHorizon, 3);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.transmitted, false);
});

test('Phase53.x remains observe when horizon stability is not proven', () => {
  const records = [
    ...windowWithWinner(1, 1),
    ...windowWithWinner(2, 3),
    ...windowWithWinner(3, 5),
  ];
  const result = evaluatePhase53Finalization(records, {
    windowSize: 25,
    minimumSamples: 5,
    minimumComparableWindows: 3,
    minimumDominance: 0.6,
    maximumSwitches: 1,
  });
  assert.equal(result.reviewStatus, 'OBSERVE');
  assert.ok(result.blockers.length > 0);
  assert.equal(result.liveTradingAllowed, false);
  assert.equal(result.brokerWriteAllowed, false);
  assert.equal(result.excelOrderWriteAllowed, false);
  assert.equal(result.rssOrderFunctionAllowed, false);
});
