import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_EXIT_V5_CONDITIONAL_POLICY,
  assertExitV5ConditionalPolicy,
  fitExitV5ConditionalModel,
  predictExitV5Conditional,
  scoreExitV5ConditionalSplit,
} from '../daytrade/phase57-exit-v5-conditional-model.js';

function features(minute, x, directionSign = 1) {
  return Object.freeze({
    featureAt: `2026-09-01T00:${String(minute).padStart(2, '0')}:00.000Z`,
    currentReturnAtr: x,
    runningMfeAtr: x + 0.2,
    runningMaeAtr: -Math.abs(x) * 0.2,
    givebackAtr: Math.max(0, 0.3 - x),
    captureRatio: x,
    mfeVelocityPctPerBar: x * 0.1,
    barsSinceLastMfe: Math.max(0, 3 - Math.round(x)),
    barsSinceLastMae: 2 + Math.round(Math.abs(x)),
    vwapDistancePct: x * 0.2,
    vwapSlopePctPerBar: x * 0.05,
    rvol: 1 + x * 0.1,
    currentMomentumPct: x * 0.1,
    momentumDecelerationPct: -x * 0.03,
    elapsedBars: 2 + minute / 5,
    directionSign,
  });
}

function sample(minute, x, label, directionSign = 1) {
  const f = features(minute, x, directionSign);
  return Object.freeze({
    features: f,
    labels: Object.freeze({
      labelAt: f.featureAt,
      labelThrough: f.featureAt,
      incrementalLiquidationReturnPctByHorizon: Object.freeze({ 3: label }),
    }),
  });
}

test('conditional policy remains development-only and non-promoting', () => {
  assert.equal(assertExitV5ConditionalPolicy(), true);
  assert.equal(PHASE57_EXIT_V5_CONDITIONAL_POLICY.fitSplit, 'development');
  assert.equal(PHASE57_EXIT_V5_CONDITIONAL_POLICY.outerOosRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_CONDITIONAL_POLICY.prospectiveRetuningAllowed, false);
});

test('conditional model uses nearby development states rather than unconditional labels', () => {
  const development = [
    sample(5, -2, -1.0),
    sample(10, -1.5, -0.8),
    sample(15, -1, -0.6),
    sample(20, 1, 0.5),
    sample(25, 1.5, 0.8),
    sample(30, 2, 1.0),
  ];
  const model = fitExitV5ConditionalModel(development, { k: 3, minNeighbors: 3, lambda: 0 });
  const weak = predictExitV5Conditional(features(35, -1.8), model);
  const strong = predictExitV5Conditional(features(40, 1.8), model);
  assert.equal(weak.ready, true);
  assert.equal(strong.ready, true);
  assert.ok(weak.meanIncrementalReturnPct < 0);
  assert.ok(strong.meanIncrementalReturnPct > 0);
  assert.equal(weak.decision, 'EXIT');
  assert.equal(strong.decision, 'HOLD');
});

test('evaluation labels cannot alter conditional predictions or trigger refit', () => {
  const development = [
    sample(5, -1, -0.5),
    sample(10, -0.5, -0.2),
    sample(15, 0.5, 0.3),
    sample(20, 1, 0.7),
  ];
  const model = fitExitV5ConditionalModel(development, { k: 2, minNeighbors: 2, lambda: 0.25 });
  const normal = scoreExitV5ConditionalSplit([sample(30, 0.8, 0.2)], model, { splitName: 'validation' });
  const altered = scoreExitV5ConditionalSplit([sample(30, 0.8, -99)], model, { splitName: 'validation' });
  assert.equal(normal.refitPerformed, false);
  assert.equal(altered.refitPerformed, false);
  assert.equal(normal.rows[0].meanIncrementalReturnPct, altered.rows[0].meanIncrementalReturnPct);
  assert.equal(normal.rows[0].q10IncrementalReturnPct, altered.rows[0].q10IncrementalReturnPct);
  assert.equal(normal.rows[0].decision, altered.rows[0].decision);
  assert.notEqual(normal.metrics.rmsePct, altered.metrics.rmsePct);
});

test('model scaler is frozen from development and safety outputs remain false', () => {
  const development = [sample(5, -1, -0.4), sample(10, 0, 0), sample(15, 1, 0.4)];
  const model = fitExitV5ConditionalModel(development, { k: 2, minNeighbors: 2 });
  const before = JSON.stringify(model.scaler);
  const result = scoreExitV5ConditionalSplit([sample(20, 50, 99)], model, { splitName: 'oos' });
  assert.equal(JSON.stringify(model.scaler), before);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.transmitted, false);
});

test('conditional fit rejects non-chronological development and invalid neighbor policy', () => {
  assert.throws(() => fitExitV5ConditionalModel([sample(10, 0, 0), sample(5, 1, 1)], { k: 2, minNeighbors: 2 }), /chronological/);
  assert.throws(() => fitExitV5ConditionalModel([sample(5, 0, 0), sample(10, 1, 1)], { k: 1, minNeighbors: 2 }), /minNeighbors/);
});
