import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_EXIT_V5_GBM_POLICY,
  assertExitV5GbmPolicy,
  fitExitV5GbmModel,
  predictExitV5Gbm,
  scoreExitV5GbmSplit,
} from '../daytrade/phase57-exit-v5-gbm-model.js';

const START = Date.parse('2026-06-01T00:00:00.000Z');

function features(index, { start = START, signal = ((index % 20) - 10) / 10 } = {}) {
  return {
    featureAt: new Date(start + index * 5 * 60_000).toISOString(),
    currentReturnAtr: signal,
    runningMfeAtr: Math.max(0, signal) + 0.2,
    runningMaeAtr: Math.min(0, signal) - 0.1,
    givebackAtr: Math.max(0, -signal),
    captureRatio: signal / 2,
    mfeVelocityPctPerBar: signal * 0.08,
    barsSinceLastMfe: index % 7,
    barsSinceLastMae: index % 5,
    vwapDistancePct: signal * 0.3,
    vwapSlopePctPerBar: signal * 0.04,
    rvol: 1 + ((index % 9) / 10),
    currentMomentumPct: signal * 0.5,
    momentumDecelerationPct: -signal * 0.1,
    elapsedBars: 2 + (index % 30),
    directionSign: index % 2 ? -1 : 1,
  };
}

function sample(index, options = {}) {
  const built = features(index, options);
  const signal = built.currentReturnAtr;
  const label = options.label ?? (signal > 0
    ? 0.22 + signal * 0.18 + (index % 3) * 0.01
    : -0.18 + signal * 0.14 - (index % 4) * 0.01);
  return {
    features: built,
    labels: {
      labelThrough: new Date(Date.parse(built.featureAt) + 15 * 60_000).toISOString(),
      incrementalLiquidationReturnPctByHorizon: { 3: label },
    },
  };
}

const FIT_OPTIONS = Object.freeze({
  rounds: 14,
  learningRate: 0.1,
  maxThresholdCandidates: 10,
  minLeafSize: 8,
  lambda: 1,
  lowerQuantile: 0.1,
});

test('EXIT v5 GBM deterministically fits Development-only mean and q10 models', () => {
  const development = Array.from({ length: 120 }, (_, index) => sample(index));
  const first = fitExitV5GbmModel(development, FIT_OPTIONS);
  const second = fitExitV5GbmModel(development, FIT_OPTIONS);

  assert.equal(first.modelType, PHASE57_EXIT_V5_GBM_POLICY.modelType);
  assert.equal(first.trainedOn, 'development');
  assert.equal(first.sampleCount, 120);
  assert.equal(first.meanModel.objective, 'MEAN');
  assert.equal(first.quantileModel.objective, 'QUANTILE');
  assert.equal(first.meanModel.trees.length, FIT_OPTIONS.rounds);
  assert.equal(first.quantileModel.trees.length, FIT_OPTIONS.rounds);
  assert.equal(first.modelFingerprint, second.modelFingerprint);
  assert.deepEqual(first.meanModel, second.meanModel);
  assert.deepEqual(first.quantileModel, second.quantileModel);
  assert.equal(first.refitAllowed, false);
  assert.equal(first.automaticPromotionAllowed, false);
  assert.equal(first.productionUpdateAllowed, false);
  assert.equal(first.transmitted, false);

  const low = predictExitV5Gbm(features(200, { signal: -0.9 }), first);
  const high = predictExitV5Gbm(features(201, { signal: 0.9 }), first);
  assert.equal(low.ready, true);
  assert.equal(high.ready, true);
  assert.ok(high.meanIncrementalReturnPct > low.meanIncrementalReturnPct);
  assert.ok(low.q10IncrementalReturnPct <= low.meanIncrementalReturnPct);
  assert.ok(high.q10IncrementalReturnPct <= high.meanIncrementalReturnPct);
  assert.ok(['HOLD', 'EXIT'].includes(low.decision));
  assert.ok(['HOLD', 'EXIT'].includes(high.decision));
});

test('EXIT v5 GBM scores Validation without refit and never uses Validation labels as features', () => {
  const development = Array.from({ length: 100 }, (_, index) => sample(index));
  const model = fitExitV5GbmModel(development, FIT_OPTIONS);
  const validationStart = Date.parse('2026-08-06T00:00:00.000Z');
  const validation = Array.from({ length: 20 }, (_, index) => sample(index, { start: validationStart }));
  const relabeled = validation.map((row) => ({
    ...row,
    labels: {
      ...row.labels,
      incrementalLiquidationReturnPctByHorizon: {
        ...row.labels.incrementalLiquidationReturnPctByHorizon,
        3: -row.labels.incrementalLiquidationReturnPctByHorizon[3] + 0.07,
      },
    },
  }));

  const original = scoreExitV5GbmSplit(validation, model, { splitName: 'validation' });
  const changedLabels = scoreExitV5GbmSplit(relabeled, model, { splitName: 'validation' });
  const decisionView = (row) => ({
    featureAt: row.featureAt,
    meanIncrementalReturnPct: row.meanIncrementalReturnPct,
    q10IncrementalReturnPct: row.q10IncrementalReturnPct,
    continuationScorePct: row.continuationScorePct,
    decision: row.decision,
  });

  assert.deepEqual(original.rows.map(decisionView), changedLabels.rows.map(decisionView));
  assert.notDeepEqual(
    original.rows.map((row) => row.realizedIncrementalReturnPct),
    changedLabels.rows.map((row) => row.realizedIncrementalReturnPct),
  );
  assert.equal(original.refitPerformed, false);
  assert.equal(original.developmentFingerprint, model.developmentFingerprint);
  assert.equal(original.modelFingerprint, model.modelFingerprint);
  assert.equal(original.automaticPromotionAllowed, false);
  assert.equal(original.productionUpdateAllowed, false);
  assert.equal(original.transmitted, false);
});

test('EXIT v5 GBM fails closed on chronology, fit options, or non-Development models', () => {
  const development = Array.from({ length: 40 }, (_, index) => sample(index));
  const reversed = [...development].reverse();
  assert.throws(() => fitExitV5GbmModel(reversed, { ...FIT_OPTIONS, minLeafSize: 4 }), /chronological/);
  assert.throws(() => fitExitV5GbmModel(development, { ...FIT_OPTIONS, rounds: 0, minLeafSize: 4 }), /rounds/);
  assert.throws(() => fitExitV5GbmModel(development, { ...FIT_OPTIONS, minLeafSize: 21 }), /minLeafSize/);
  assert.throws(() => predictExitV5Gbm(features(1), { modelType: PHASE57_EXIT_V5_GBM_POLICY.modelType, trainedOn: 'validation' }), /development-fitted/);
  assert.throws(() => scoreExitV5GbmSplit(development, fitExitV5GbmModel(development, { ...FIT_OPTIONS, minLeafSize: 4 }), { splitName: 'development' }), /splitName/);
});

test('EXIT v5 GBM governance remains research-only and retuning-disabled', () => {
  assert.equal(assertExitV5GbmPolicy(), true);
  assert.equal(PHASE57_EXIT_V5_GBM_POLICY.fitSplit, 'development');
  assert.equal(PHASE57_EXIT_V5_GBM_POLICY.shuffleAllowed, false);
  assert.equal(PHASE57_EXIT_V5_GBM_POLICY.validationRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_GBM_POLICY.outerOosRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_GBM_POLICY.prospectiveRetuningAllowed, false);
});
