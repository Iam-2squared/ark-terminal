import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_EXIT_V5_TRAINING_POLICY,
  assertExitV5TrainingPolicy,
  fitExitV5DevelopmentBaseline,
  runExitV5BaselineWalkForward,
  scoreExitV5Split,
} from '../daytrade/phase57-exit-v5-training-harness.js';

function sample(minute, label) {
  const ts = `2026-09-01T00:${String(minute).padStart(2, '0')}:00.000Z`;
  return Object.freeze({
    features: Object.freeze({ featureAt: ts, currentReturnAtr: minute / 10 }),
    labels: Object.freeze({
      labelAt: ts,
      labelThrough: ts,
      incrementalLiquidationReturnPctByHorizon: Object.freeze({ 3: label }),
    }),
  });
}

test('training policy freezes chronology, purging and outer retuning', () => {
  assert.equal(assertExitV5TrainingPolicy(), true);
  assert.equal(PHASE57_EXIT_V5_TRAINING_POLICY.shuffleAllowed, false);
  assert.equal(PHASE57_EXIT_V5_TRAINING_POLICY.boundaryPurgingRequired, true);
  assert.equal(PHASE57_EXIT_V5_TRAINING_POLICY.outerOosRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_TRAINING_POLICY.prospectiveRetuningAllowed, false);
});

test('baseline fit uses development labels only and freezes model spec', () => {
  const development = [sample(5, -0.4), sample(10, 0.2), sample(15, 0.5)];
  const model = fitExitV5DevelopmentBaseline(development, { lambda: 0.5 });
  assert.equal(model.trainedOn, 'development');
  assert.equal(model.sampleCount, 3);
  assert.ok(Math.abs(model.meanIncrementalReturnPct - 0.1) < 1e-12);
  assert.equal(model.spec.selectedOn, 'development');
  assert.equal(model.automaticPromotionAllowed, false);
  assert.equal(model.productionUpdateAllowed, false);
  assert.equal(model.transmitted, false);
});

test('validation outcomes cannot refit or alter development-fitted forecasts', () => {
  const model = fitExitV5DevelopmentBaseline([sample(5, -0.2), sample(10, 0.4)], { lambda: 0 });
  const normal = scoreExitV5Split([sample(20, 0.1), sample(25, 0.2)], model, { splitName: 'validation' });
  const extreme = scoreExitV5Split([sample(20, -99), sample(25, 99)], model, { splitName: 'validation' });
  assert.equal(normal.refitPerformed, false);
  assert.equal(extreme.refitPerformed, false);
  assert.deepEqual(normal.rows.map((r) => r.meanIncrementalReturnPct), extreme.rows.map((r) => r.meanIncrementalReturnPct));
  assert.deepEqual(normal.rows.map((r) => r.q10IncrementalReturnPct), extreme.rows.map((r) => r.q10IncrementalReturnPct));
  assert.notEqual(normal.metrics.rmsePct, extreme.metrics.rmsePct);
});

test('harness rejects shuffled/non-chronological samples and development evaluation', () => {
  assert.throws(() => fitExitV5DevelopmentBaseline([sample(10, 0.1), sample(5, 0.2)]), /chronological/);
  const model = fitExitV5DevelopmentBaseline([sample(5, 0.1), sample(10, 0.2)]);
  assert.throws(() => scoreExitV5Split([sample(20, 0.2)], model, { splitName: 'development' }), /validation, oos, or prospective/);
});

test('same-timestamp samples from different symbols are valid chronological development observations', () => {
  const model = fitExitV5DevelopmentBaseline([sample(5, -0.1), sample(5, 0.3)]);
  assert.equal(model.sampleCount, 2);
  assert.ok(Math.abs(model.meanIncrementalReturnPct - 0.1) < 1e-12);
});

test('walk-forward harness never auto-promotes research output', () => {
  const split = Object.freeze({
    development: Object.freeze([sample(5, -0.3), sample(10, 0.4)]),
    validation: Object.freeze([sample(20, 0.1)]),
    oos: Object.freeze([sample(30, -0.2)]),
    prospective: Object.freeze([]),
    purged: Object.freeze([]),
  });
  const result = runExitV5BaselineWalkForward(split, { lambda: 0.5 });
  assert.equal(result.validation.automaticPromotionAllowed, false);
  assert.equal(result.validation.productionUpdateAllowed, false);
  assert.equal(result.validation.transmitted, false);
  assert.equal(result.oos.refitPerformed, false);
});
