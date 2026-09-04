import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_EXIT_V5_PAIRED_MODEL_IDS,
  PHASE57_EXIT_V5_PAIRED_POLICY,
  PHASE57_EXIT_V5_PAIRED_SAFETY,
  assertExitV5PairedSafety,
  buildExitV5PairedInvariant,
  fitExitV5PairedDevelopmentModels,
  fitExitV5PairedModelsFromPurgedSplit,
  runExitV5FourWayPairedEvaluation,
  simulateExitV5FrozenPolicy,
} from '../daytrade/phase57-exit-v5-paired-evaluator.js';
import { buildPurgedExitV5Split } from '../daytrade/phase57-exit-v5-continuation-dataset.js';

const FIVE_MINUTES = 5 * 60_000;
const DEVELOPMENT_BASE = Date.parse('2026-09-01T00:00:00.000Z');
const DEVELOPMENT_END = '2026-09-01T01:00:00.000Z';
const EVALUATION_BASE = Date.parse('2026-09-03T00:00:00.000Z');

const CONTRACT = Object.freeze({
  selectorPolicyId: 'DYNAMIC5M_FROZEN_TEST',
  entryPolicyId: 'P21_FROZEN_ENTRY_TEST',
  marketDataPolicyId: 'FINALIZED_5M_TEST',
  transactionCostPolicyId: 'ROUND_TRIP_005_TEST',
  capitalAllocationPolicyId: 'FROZEN_ALLOCATION_TEST',
});

function featureVector(index, x, directionSign = 1, timestamp = null) {
  return Object.freeze({
    featureAt: timestamp ?? new Date(DEVELOPMENT_BASE + index * FIVE_MINUTES).toISOString(),
    currentReturnAtr: x,
    runningMfeAtr: Math.max(0, x + 0.5),
    runningMaeAtr: Math.min(0, x - 0.5),
    givebackAtr: Math.max(0, 0.5 - x),
    captureRatio: x,
    mfeVelocityPctPerBar: x * 0.1,
    barsSinceLastMfe: Math.max(0, 4 - index),
    barsSinceLastMae: index,
    vwapDistancePct: x * 0.2,
    vwapSlopePctPerBar: x * 0.05,
    rvol: 1 + x * 0.1,
    currentMomentumPct: x * 0.1,
    momentumDecelerationPct: -x * 0.05,
    elapsedBars: index + 2,
    directionSign,
  });
}

function developmentSample(index, x, label, options = {}) {
  const features = featureVector(index, x, options.directionSign ?? 1, options.timestamp ?? null);
  const labelThrough = options.labelThrough ?? new Date(Date.parse(features.featureAt) + 3 * FIVE_MINUTES).toISOString();
  return Object.freeze({
    features,
    labels: Object.freeze({
      labelAt: features.featureAt,
      labelThrough,
      incrementalLiquidationReturnPctByHorizon: Object.freeze({ 3: label }),
    }),
  });
}

function developmentSamples() {
  return [
    developmentSample(1, -2, -1.0),
    developmentSample(2, -1.5, -0.8),
    developmentSample(3, -1, -0.6),
    developmentSample(4, 1, 0.3),
    developmentSample(5, 1.5, 0.5),
    developmentSample(6, 2, 0.8),
  ];
}

function contextBars() {
  return Array.from({ length: 6 }, (_, index) => ({
    timestamp: new Date(EVALUATION_BASE + index * FIVE_MINUTES).toISOString(),
    open: 100,
    high: 101,
    low: 99,
    close: 100,
    volume: 10_000 + index * 100,
  }));
}

function futureBars({ direction = 'LONG', changedLateClose = null } = {}) {
  const longCloses = [99.5, 99.0, 98.8, 99.2, 100.5, 101.0, 100.7, 101.2];
  const shortCloses = [100.5, 101.0, 101.2, 100.8, 99.5, 99.0, 99.3, 98.8];
  const closes = direction === 'LONG' ? longCloses : shortCloses;
  if (changedLateClose !== null) closes[4] = changedLateClose;
  return closes.map((close, index) => ({
    timestamp: new Date(EVALUATION_BASE + (index + 7) * FIVE_MINUTES).toISOString(),
    open: close,
    high: close + 0.4,
    low: close - 0.4,
    close,
    volume: 12_000 + index * 250,
  }));
}

function evaluationRow({ symbol = '7203.T', direction = 'LONG', changedLateClose = null } = {}) {
  return {
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol,
    sector: direction === 'LONG' ? 'AUTO' : 'TECH',
    setup: direction === 'LONG' ? 'PULLBACK' : 'BREAKDOWN',
    volatilityRegime: 'NORMAL',
    timeOfDayBucket: 'OPENING',
    sessionDate: '2026-09-03',
    entryTimestamp: new Date(EVALUATION_BASE + 6 * FIVE_MINUTES).toISOString(),
    entryPrice: 100,
    signalDirection: direction === 'LONG' ? 1 : -1,
    direction,
    contextBars: contextBars(),
    futureBars: futureBars({ direction, changedLateClose }),
  };
}

function analogPool() {
  return ['LONG', 'SHORT'].flatMap((direction) => Array.from({ length: 40 }, (_, index) => ({
    sessionDate: '2026-08-01',
    symbol: `${direction === 'LONG' ? 1000 : 2000 + index}.T`,
    direction,
    timestamp: '2026-08-01T00:30:00.000Z',
    fullyRealizedAt: '2026-08-01T01:00:00.000Z',
    state: {
      currentReturnPct: -0.5,
      bestReturnPct: 0,
      givebackPctPoints: 0.5,
      atrPct: 1,
      momentumPct: -0.2,
      bodyPressure: -0.5,
      directionalRangePos: 0.2,
      elapsedBars: 1,
    },
    labels: { 1: -0.5, 3: -0.5, 6: -0.5 },
  })));
}

function fittedModels(overrides = {}) {
  return fitExitV5PairedDevelopmentModels(developmentSamples(), {
    developmentEnd: DEVELOPMENT_END,
    boundaryPurgingConfirmed: true,
    sessionPurgingConfirmed: true,
    lambda: 0,
    lowerQuantile: 0.1,
    k: 3,
    minNeighbors: 2,
    ...overrides,
  });
}

test('paired development fit requires an explicit purged boundary and identical sample lineage', () => {
  assert.throws(
    () => fitExitV5PairedDevelopmentModels(developmentSamples(), { developmentEnd: DEVELOPMENT_END, k: 3, minNeighbors: 2 }),
    /boundaryPurgingConfirmed/,
  );
  const crossing = [
    ...developmentSamples().slice(0, -1),
    developmentSample(6, 2, 0.8, { labelThrough: '2026-09-01T01:05:00.000Z' }),
  ];
  assert.throws(
    () => fitExitV5PairedDevelopmentModels(crossing, {
      developmentEnd: DEVELOPMENT_END,
      boundaryPurgingConfirmed: true,
      sessionPurgingConfirmed: true,
      k: 3,
      minNeighbors: 2,
    }),
    /crosses the purged development boundary/,
  );

  const fitted = fittedModels();
  assert.equal(fitted.trainedOn, 'development');
  assert.equal(fitted.sampleCount, fitted.unconditional.sampleCount);
  assert.equal(fitted.sampleCount, fitted.conditional.sampleCount);
  assert.equal(fitted.refitAllowed, false);
  assert.equal(fitted.developmentFingerprint.length, 64);
});

test('preferred paired fit consumes audited split metadata instead of caller assertions', () => {
  const split = buildPurgedExitV5Split(developmentSamples(), {
    developmentEnd: DEVELOPMENT_END,
    validationEnd: '2026-09-02T01:00:00.000Z',
    oosEnd: '2026-09-03T01:00:00.000Z',
  });
  const fitted = fitExitV5PairedModelsFromPurgedSplit(split, { lambda: 0, k: 3, minNeighbors: 2 });
  assert.equal(fitted.boundaryPurgingConfirmed, true);
  assert.equal(fitted.sessionPurgingConfirmed, true);
  assert.equal(fitted.developmentEnd, DEVELOPMENT_END);
  assert.throws(
    () => fitExitV5PairedModelsFromPurgedSplit({ development: developmentSamples(), splitPolicy: {} }),
    /audited label- and session-purged split/,
  );
});

test('four-way evaluator uses one fully asserted invariant for v3, v4 and both v5 baselines', () => {
  const result = runExitV5FourWayPairedEvaluation({
    evaluationRows: [
      evaluationRow({ symbol: '7203.T', direction: 'LONG' }),
      evaluationRow({ symbol: '6758.T', direction: 'SHORT' }),
    ],
    analogPool: analogPool(),
    fittedModels: fittedModels(),
    splitName: 'validation',
    pairedContract: CONTRACT,
    roundTripCostPct: 0.05,
    incrementalCostPct: 0,
    evaluationHorizons: [1, 3, 6],
  });

  assert.equal(result.status, 'EXIT_V5_FOUR_WAY_PAIRED_EVALUATED');
  assert.equal(result.pairedCount, 2);
  assert.deepEqual(result.comparisonModels, PHASE57_EXIT_V5_PAIRED_MODEL_IDS);
  assert.equal(result.developmentRefitPerformed, false);
  assert.equal(result.methodology.exactSameFrozenInputForAllModels, true);
  assert.equal(result.methodology.evaluationLabelsUsedByDecision, false);
  assert.equal(result.automaticPromotionAllowed, false);

  for (const pair of result.pairs) {
    assert.equal(pair.invariant.singleFrozenInputAppliedToAllModels, true);
    assert.equal(pair.invariant.marketDataFingerprint.length, 64);
    for (const modelId of PHASE57_EXIT_V5_PAIRED_MODEL_IDS) {
      const outcome = pair.outcomes[modelId];
      assert.equal(outcome.invariantSha256, pair.invariant.invariantSha256);
      assert.ok(Math.abs(outcome.netReturnPct - (outcome.grossReturnPct - 0.05)) < 1e-10);
      assert.equal(pair.evaluation[modelId].outcomeWindowsNeverUsedByDecisionPolicy, true);
    }
    assert.ok(pair.calibration.V5_UNCONDITIONAL.every((row) => row.evaluationOnly));
    assert.ok(pair.calibration.V5_CONDITIONAL.every((row) => row.evaluationOnly));
  }

  for (const modelId of PHASE57_EXIT_V5_PAIRED_MODEL_IDS) {
    assert.equal(result.summary.models[modelId].tradeCount, 2);
    assert.equal(result.summary.models[modelId].segments.direction.LONG.tradeCount, 1);
    assert.equal(result.summary.models[modelId].segments.direction.SHORT.tradeCount, 1);
  }
  assert.equal(result.summary.pairedDeltas.V5_CONDITIONAL_MINUS_V4.pairedCount, 2);
});

test('paired invariant rejects policy drift and evaluator rejects development overlap', () => {
  const drifted = { ...evaluationRow(), selectorPolicyId: 'OTHER_SELECTOR' };
  assert.throws(
    () => buildExitV5PairedInvariant({ row: drifted, pairedContract: CONTRACT }),
    /invariant mismatch for selectorPolicyId/,
  );
  assert.throws(
    () => runExitV5FourWayPairedEvaluation({
      evaluationRows: [{ ...evaluationRow(), entryTimestamp: '2026-09-01T00:55:00.000Z' }],
      analogPool: analogPool(),
      fittedModels: fittedModels(),
      splitName: 'validation',
      pairedContract: CONTRACT,
    }),
    /strictly after the frozen development boundary/,
  );
});

test('v5 decision prefix is invariant to bars not yet observed', () => {
  const fitted = fittedModels({ lambda: 1 });
  const baseline = simulateExitV5FrozenPolicy({
    row: evaluationRow({ changedLateClose: 105 }),
    fittedModel: fitted.conditional,
    modelId: 'V5_CONDITIONAL',
  });
  const altered = simulateExitV5FrozenPolicy({
    row: evaluationRow({ changedLateClose: 70 }),
    fittedModel: fitted.conditional,
    modelId: 'V5_CONDITIONAL',
  });
  assert.deepEqual(baseline.managementDecisions.slice(0, 2), altered.managementDecisions.slice(0, 2));
});

test('a missing five-minute observation never creates a synthetic bar or advances state twice', () => {
  const fitted = fittedModels();
  const sparse = evaluationRow();
  sparse.futureBars = sparse.futureBars.filter((_bar, index) => index !== 1);
  const outcome = simulateExitV5FrozenPolicy({
    row: sparse,
    fittedModel: fitted.unconditional,
    modelId: 'V5_UNCONDITIONAL',
  });
  assert.equal(outcome.managementDecisions[0].timestamp, sparse.futureBars[0].timestamp);
  assert.equal(outcome.managementDecisions[0].observedBarCount, 1);
  assert.equal(outcome.managementDecisions[1].timestamp, sparse.futureBars[1].timestamp);
  assert.equal(outcome.managementDecisions[1].observedBarCount, 2);
  assert.ok(outcome.managementDecisions.length <= sparse.futureBars.length);
});

test('post-exit future changes may alter calibration diagnostics but never the frozen decision prefix', () => {
  const shared = {
    analogPool: analogPool(),
    fittedModels: fittedModels({ lambda: 1 }),
    splitName: 'oos',
    pairedContract: CONTRACT,
  };
  const favorable = runExitV5FourWayPairedEvaluation({
    ...shared,
    evaluationRows: [evaluationRow({ changedLateClose: 110 })],
  });
  const adverse = runExitV5FourWayPairedEvaluation({
    ...shared,
    evaluationRows: [evaluationRow({ changedLateClose: 80 })],
  });
  const favorableOutcome = favorable.pairs[0].outcomes.V5_UNCONDITIONAL;
  const adverseOutcome = adverse.pairs[0].outcomes.V5_UNCONDITIONAL;
  assert.deepEqual(favorableOutcome.managementDecisions.slice(0, 2), adverseOutcome.managementDecisions.slice(0, 2));
  assert.notDeepEqual(favorable.pairs[0].calibration.V5_UNCONDITIONAL, adverse.pairs[0].calibration.V5_UNCONDITIONAL);
});

test('paired evaluator remains research/shadow only with no promotion path', () => {
  assert.equal(assertExitV5PairedSafety(), true);
  assert.equal(PHASE57_EXIT_V5_PAIRED_POLICY.outerOosRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_PAIRED_POLICY.prospectiveRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_PAIRED_POLICY.evaluationLabelsUsedByDecision, false);
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted',
  ]) assert.equal(PHASE57_EXIT_V5_PAIRED_SAFETY[key], false, key);
});
