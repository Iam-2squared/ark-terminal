import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluatePhase53Finalization } from '../adaptive/phase53-finalization.js';

function record(index, winner = 3) {
  const horizons = [1, 3, 5, 10, 20];
  return {
    status: 'resolved',
    resolvedAt: new Date(Date.UTC(2026, 0, index + 1)).toISOString(),
    horizons: Object.fromEntries(horizons.map((h) => [h, {
      directionCorrect: h === winner,
      returnPct: h === winner ? 0.02 : -0.005,
    }])),
  };
}

test('Phase53.x exposes stable horizon only as review candidate', () => {
  const records = Array.from({ length: 90 }, (_, index) => record(index, 3));
  const result = evaluatePhase53Finalization(records, {
    windowSize: 30,
    minimumSamples: 5,
    minimumComparableWindows: 3,
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
    ...Array.from({ length: 30 }, (_, i) => record(i, 1)),
    ...Array.from({ length: 30 }, (_, i) => record(i + 30, 3)),
    ...Array.from({ length: 30 }, (_, i) => record(i + 60, 5)),
  ];
  const result = evaluatePhase53Finalization(records, {
    windowSize: 30,
    minimumSamples: 5,
    minimumComparableWindows: 3,
    minimumDominance: 0.6,
  });
  assert.equal(result.reviewStatus, 'OBSERVE');
  assert.ok(result.blockers.length > 0);
  assert.equal(result.liveTradingAllowed, false);
  assert.equal(result.brokerWriteAllowed, false);
  assert.equal(result.excelOrderWriteAllowed, false);
  assert.equal(result.rssOrderFunctionAllowed, false);
});
