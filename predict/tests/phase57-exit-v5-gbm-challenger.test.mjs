import assert from 'node:assert/strict';
import test from 'node:test';
import { buildPurgedExitV5Split } from '../daytrade/phase57-exit-v5-continuation-dataset.js';
import {
  PHASE57_EXIT_V5_GBM_CHALLENGER_MODEL_IDS,
  PHASE57_EXIT_V5_GBM_CHALLENGER_POLICY,
  PHASE57_EXIT_V5_GBM_CHALLENGER_SAFETY,
  assertExitV5GbmChallengerSafety,
  fitExitV5GbmChallengerModelsFromPurgedSplit,
  runExitV5GbmChallengerPairedEvaluation,
} from '../daytrade/phase57-exit-v5-gbm-challenger.js';

const FIVE_MINUTES = 5 * 60_000;
const DEVELOPMENT_BASE = Date.parse('2026-06-01T00:00:00.000Z');
const EVALUATION_BASE = Date.parse('2026-08-06T00:00:00.000Z');

const CONTRACT = Object.freeze({
  selectorPolicyId: 'DYNAMIC5M_FROZEN_TEST',
  entryPolicyId: 'P21_FROZEN_ENTRY_TEST',
  marketDataPolicyId: 'FINALIZED_5M_TEST',
  transactionCostPolicyId: 'ROUND_TRIP_005_TEST',
  capitalAllocationPolicyId: 'FROZEN_ALLOCATION_TEST',
});

function featureVector(index) {
  const signal = ((index % 20) - 10) / 10;
  return Object.freeze({
    featureAt: new Date(DEVELOPMENT_BASE + index * FIVE_MINUTES).toISOString(),
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
    directionSign: 1,
  });
}

function developmentSamples() {
  return Array.from({ length: 80 }, (_, index) => {
    const features = featureVector(index);
    const label = features.currentReturnAtr > 0 ? 0.3 + features.currentReturnAtr * 0.1 : -0.2 + features.currentReturnAtr * 0.1;
    return Object.freeze({
      features,
      labels: Object.freeze({
        labelAt: features.featureAt,
        labelThrough: new Date(Date.parse(features.featureAt) + 3 * FIVE_MINUTES).toISOString(),
        incrementalLiquidationReturnPctByHorizon: Object.freeze({ 3: label }),
      }),
    });
  });
}

function purgedSplit() {
  return buildPurgedExitV5Split(developmentSamples(), {
    developmentEnd: '2026-06-02T00:00:00.000Z',
    validationEnd: '2026-08-12T23:59:59.999Z',
    oosEnd: '2026-08-31T23:59:59.999Z',
  });
}

function contextBars() {
  return Array.from({ length: 7 }, (_, index) => ({
    timestamp: new Date(EVALUATION_BASE + index * FIVE_MINUTES).toISOString(),
    open: 100,
    high: 100.4,
    low: 99.6,
    close: 100,
    volume: 10_000 + index * 100,
  }));
}

function futureBars() {
  return [100.3, 100.6, 100.9, 100.7, 101.1, 101.3, 101.0, 101.4].map((close, index) => ({
    timestamp: new Date(EVALUATION_BASE + (index + 8) * FIVE_MINUTES).toISOString(),
    open: close,
    high: close + 0.3,
    low: close - 0.3,
    close,
    volume: 12_000 + index * 200,
  }));
}

function evaluationRow() {
  return {
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol: '7203.T',
    sector: 'AUTO',
    setup: 'MOMENTUM',
    volatilityRegime: 'NORMAL',
    timeOfDayBucket: 'OPENING',
    sessionDate: '2026-08-06',
    entryTimestamp: new Date(EVALUATION_BASE + 7 * FIVE_MINUTES).toISOString(),
    entryPrice: 100,
    signalDirection: 1,
    direction: 'LONG',
    contextBars: contextBars(),
    futureBars: futureBars(),
  };
}

function analogPool() {
  return Array.from({ length: 40 }, (_, index) => ({
    sessionDate: '2026-05-01',
    symbol: `${1000 + index}.T`,
    direction: 'LONG',
    timestamp: '2026-05-01T00:30:00.000Z',
    fullyRealizedAt: '2026-05-01T01:00:00.000Z',
    state: {
      currentReturnPct: 0.3,
      bestReturnPct: 0.5,
      givebackPctPoints: 0.2,
      atrPct: 1,
      momentumPct: 0.1,
      bodyPressure: 0.2,
      directionalRangePos: 0.7,
      elapsedBars: 2,
    },
    labels: { 1: 0.1, 3: 0.2, 6: 0.3 },
  }));
}

function fitted() {
  return fitExitV5GbmChallengerModelsFromPurgedSplit(purgedSplit(), {
    baseModelOptions: { lambda: 1, lowerQuantile: 0.1, k: 5, minNeighbors: 3 },
    gbmModelOptions: {
      rounds: 10,
      learningRate: 0.1,
      maxThresholdCandidates: 8,
      minLeafSize: 5,
      lambda: 1,
      lowerQuantile: 0.1,
    },
  });
}

test('GBM challenger extends the unchanged four-way evidence with one exact paired outcome', () => {
  const split = purgedSplit();
  const models = fitExitV5GbmChallengerModelsFromPurgedSplit(split, {
    baseModelOptions: { lambda: 1, lowerQuantile: 0.1, k: 5, minNeighbors: 3 },
    gbmModelOptions: { rounds: 10, learningRate: 0.1, maxThresholdCandidates: 8, minLeafSize: 5, lambda: 1, lowerQuantile: 0.1 },
  });
  const result = runExitV5GbmChallengerPairedEvaluation({
    evaluationRows: [evaluationRow()],
    purgedSplit: split,
    analogPool: analogPool(),
    fittedModels: models,
    splitName: 'validation',
    pairedContract: CONTRACT,
    roundTripCostPct: 0.05,
    incrementalCostPct: 0,
    evaluationHorizons: [1, 3, 6],
  });

  assert.equal(result.status, 'EXIT_V5_GBM_FIVE_WAY_PAIRED_EVALUATED');
  assert.deepEqual(result.comparisonModels, PHASE57_EXIT_V5_GBM_CHALLENGER_MODEL_IDS);
  assert.equal(result.pairedCount, 1);
  assert.equal(result.splitAudit.fullTradeTrajectoryContained, true);
  assert.equal(result.methodology.originalFourWayPolicyUnchanged, true);
  assert.equal(result.methodology.exactSameFrozenInputForAllFiveModels, true);
  assert.equal(result.methodology.sameDevelopmentSamplesForAllV5Models, true);
  assert.equal(result.developmentRefitPerformed, false);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.gbmModelFingerprint, models.gbm.modelFingerprint);

  const [pair] = result.pairs;
  for (const modelId of PHASE57_EXIT_V5_GBM_CHALLENGER_MODEL_IDS) {
    assert.equal(pair.outcomes[modelId].invariantSha256, pair.invariant.invariantSha256);
    assert.equal(pair.evaluation[modelId].outcomeWindowsNeverUsedByDecisionPolicy, true);
    assert.equal(result.summary.models[modelId].tradeCount, 1);
  }
  assert.ok(pair.calibration.V5_GBM.every((row) => row.evaluationOnly));
  assert.equal(result.summary.pairedDeltas.V5_GBM_MINUS_V4.pairedCount, 1);
  assert.equal(result.summary.pairedDeltas.V5_GBM_MINUS_V5_CONDITIONAL.pairedCount, 1);
});

test('GBM challenger fit fails closed without an audited split or identical lineage', () => {
  assert.throws(
    () => fitExitV5GbmChallengerModelsFromPurgedSplit({ development: developmentSamples(), splitPolicy: {} }),
    /audited label- and session-purged split/,
  );
  const models = fitted();
  assert.equal(models.sameDevelopmentSamplesForAllV5Models, true);
  assert.equal(models.sampleCount, models.gbm.sampleCount);
  assert.equal(models.refitAllowed, false);
});

test('GBM challenger governance remains research-only with every write/promotion flag false', () => {
  assert.equal(assertExitV5GbmChallengerSafety(), true);
  assert.equal(PHASE57_EXIT_V5_GBM_CHALLENGER_POLICY.fitSplit, 'development');
  assert.equal(PHASE57_EXIT_V5_GBM_CHALLENGER_POLICY.validationRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_GBM_CHALLENGER_POLICY.outerOosRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_GBM_CHALLENGER_POLICY.prospectiveRetuningAllowed, false);
  for (const key of [
    'executionAllowed',
    'brokerWriteAllowed',
    'excelOrderWriteAllowed',
    'rssOrderFunctionAllowed',
    'liveTradingAllowed',
    'paperTradingAllowed',
    'automaticPromotionAllowed',
    'productionUpdateAllowed',
    'transmitted',
  ]) assert.equal(PHASE57_EXIT_V5_GBM_CHALLENGER_SAFETY[key], false, key);
});
