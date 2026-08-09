import test from 'node:test';
import assert from 'node:assert/strict';
import { preparePhase56TrainingRows, trainPhase56MultifactorArtifact } from '../chart/phase56-multifactor-training.js';
import { scoreInteractionAwareLogistic } from '../chart/phase56-multifactor-model.js';

function isoDay(offset) {
  const d = new Date(Date.UTC(2025, 0, 1 + offset));
  return d.toISOString().slice(0, 10);
}

function syntheticRows(count = 80) {
  return Array.from({ length: count }, (_, i) => {
    const a = ((i % 9) - 4) / 4;
    const b = (((i * 5) % 11) - 5) / 5;
    const interaction = a * b;
    const actualReturn = interaction + 0.2 * a > 0 ? 0.012 + (i % 3) * 0.001 : -0.011 - (i % 2) * 0.001;
    return {
      id: `row-${i}`,
      symbol: i % 2 ? 'AAA.T' : 'BBB.T',
      sessionDate: isoDay(i),
      featureCutoff: isoDay(i),
      outcomeAt: isoDay(i + 1),
      actualReturn,
      featureVector: { a, b, noise: ((i * 7) % 13) / 13 },
    };
  });
}

test('P11 trains a P8-compatible interaction-aware logistic artifact', () => {
  const rows = syntheticRows();
  const result = trainPhase56MultifactorArtifact({
    rows,
    trainingAsOf: isoDay(100),
    baseFeatures: ['a', 'b', 'noise'],
    interactions: [{ id: 'a_x_b', features: ['a', 'b'] }],
    options: { iterations: 220, learningRate: 0.08, l2: 0.0005 },
  });
  assert.equal(result.status, 'MULTIFACTOR_ARTIFACT_TRAINED');
  assert.equal(result.oosValidated, false);
  assert.ok(result.model.terms.some((term) => term.features.length === 2 && term.features.includes('a') && term.features.includes('b')));
  const positive = scoreInteractionAwareLogistic({ featureVector: { a: 1, b: 1, noise: 0 }, model: result.model });
  const negative = scoreInteractionAwareLogistic({ featureVector: { a: 1, b: -1, noise: 0 }, model: result.model });
  assert.equal(positive.status, 'SCORED');
  assert.ok(positive.probability > negative.probability);
});

test('P11 blocks labels whose outcomes were not known at training cutoff', () => {
  const rows = syntheticRows(30);
  rows.push({
    id: 'future-outcome', symbol: 'AAA.T', sessionDate: isoDay(29), featureCutoff: isoDay(29),
    outcomeAt: isoDay(90), actualReturn: 0.5, featureVector: { a: 99, b: 99, noise: 0 },
  });
  const prepared = preparePhase56TrainingRows({
    rows,
    trainingAsOf: isoDay(40),
    baseFeatures: ['a', 'b'],
    interactions: [{ id: 'a_x_b', features: ['a', 'b'] }],
  });
  assert.equal(prepared.pointInTimeEnforced, true);
  assert.equal(prepared.futureOutcomeBlocked, true);
  assert.ok(prepared.rejected.some((item) => item.id === 'future-outcome' && item.reason === 'OUTCOME_NOT_KNOWN_AT_TRAINING_CUTOFF'));
});

test('P11 blocks future feature cutoffs and never enables trading writes', () => {
  const rows = syntheticRows(30);
  rows[0] = { ...rows[0], featureCutoff: isoDay(2) };
  const result = trainPhase56MultifactorArtifact({ rows, trainingAsOf: isoDay(50), baseFeatures: ['a', 'b'] });
  assert.ok(result.rejected.some((item) => item.reason === 'FEATURE_FUTURE_LEAK_BLOCKED'));
  for (const key of ['executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed', 'liveTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed']) {
    assert.equal(result[key], false, key);
  }
  assert.equal(result.safety.paperTradingAllowed, false);
  assert.equal(result.edgeClaimAllowed, false);
  assert.equal(result.transmitted, false);
  assert.equal(result.humanApprovalRequired, true);
});
