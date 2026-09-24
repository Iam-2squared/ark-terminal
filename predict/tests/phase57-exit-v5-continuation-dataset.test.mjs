import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_EXIT_V5_DATASET_POLICY,
  PHASE57_EXIT_V5_RESEARCH_SAFETY,
  assertExitV5ResearchSafety,
  buildExitV5Features,
  buildExitV5Labels,
  buildExitV5TrainingSample,
  buildExitV5TrainingSamplesFromFrozenRows,
  buildPurgedExitV5Split,
} from '../daytrade/phase57-exit-v5-continuation-dataset.js';

const BASE = Date.parse('2026-09-03T00:00:00.000Z');

function bar(index, close, volume = 10_000) {
  return {
    timestamp: new Date(BASE + index * 5 * 60_000).toISOString(),
    open: close - 0.1,
    high: close + 0.5,
    low: close - 0.5,
    close,
    volume,
  };
}

function observed() {
  return [bar(1, 100), bar(2, 101), bar(3, 102), bar(4, 101.5)];
}

function futures(last = 104) {
  return [bar(5, 102), bar(6, 103), bar(7, last), bar(8, 105), bar(9, 106), bar(10, 107)];
}

function sampleAt(featureAt, labelThrough, sessionDate = featureAt.slice(0, 10)) {
  return {
    provenance: { sessionDate },
    features: { featureAt },
    labels: { labelThrough, incrementalLiquidationReturnPctByHorizon: { 3: 0.1 } },
  };
}

test('v5 feature builder is causal and has no future-bars input surface', () => {
  assert.equal(PHASE57_EXIT_V5_DATASET_POLICY.futureDataAllowedInFeatures, false);
  assert.equal(buildExitV5Features.length, 1);
  const baseline = buildExitV5Features({ entryPrice: 100, direction: 'LONG', observedBars: observed() });
  const sameObserved = buildExitV5Features({ entryPrice: 100, direction: 'LONG', observedBars: observed() });
  assert.deepEqual(baseline, sameObserved);
  assert.equal(baseline.featureAt, observed().at(-1).timestamp);
  assert.ok(Number.isFinite(baseline.currentReturnAtr));
  assert.ok(Number.isFinite(baseline.runningMfeAtr));
  assert.ok(Number.isFinite(baseline.runningMaeAtr));
  assert.ok(Number.isFinite(baseline.vwapDistancePct));
  assert.equal(baseline.elapsedBars, observed().length);
});

test('v5 labels encode incremental liquidation value, not total trade return', () => {
  const currentBar = observed().at(-1);
  const labels = buildExitV5Labels({ currentBar, futureBars: futures(), direction: 'LONG' });
  const expected3 = ((104 - 101.5) / 101.5) * 100;
  assert.ok(Math.abs(labels.incrementalLiquidationReturnPctByHorizon[3] - expected3) < 1e-12);
  assert.equal(labels.labelAt, currentBar.timestamp);
  assert.equal(labels.labelThrough, futures()[5].timestamp);

  const shortLabels = buildExitV5Labels({ currentBar, futureBars: futures(), direction: 'SHORT' });
  assert.ok(shortLabels.incrementalLiquidationReturnPctByHorizon[3] < 0);
});

test('changing future labels cannot alter features at t', () => {
  const before = buildExitV5TrainingSample({ entryPrice: 100, direction: 'LONG', observedBars: observed(), futureBars: futures(104) });
  const after = buildExitV5TrainingSample({ entryPrice: 100, direction: 'LONG', observedBars: observed(), futureBars: futures(70) });
  assert.deepEqual(before.features, after.features);
  assert.notDeepEqual(before.labels, after.labels);
});

test('frozen Entry rows materialize causal per-bar samples only when the primary label is complete', () => {
  const row = {
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol: '7203.T',
    sessionDate: '2026-09-03',
    entryTimestamp: '2026-09-03T00:00:00.000Z',
    entryPrice: 100,
    direction: 'LONG',
    futureBars: [...observed(), ...futures()],
  };
  const samples = buildExitV5TrainingSamplesFromFrozenRows([row]);
  assert.equal(samples.length, row.futureBars.length - 4);
  assert.equal(samples[0].provenance.symbol, '7203.T');
  assert.equal(samples[0].provenance.sessionDate, '2026-09-03');
  assert.equal(samples[0].features.featureAt, row.futureBars[1].timestamp);
  assert.ok(Number.isFinite(samples[0].labels.incrementalLiquidationReturnPctByHorizon[3]));
  assert.throws(
    () => buildExitV5TrainingSamplesFromFrozenRows([{ ...row, currentOutcomeUsed: true }]),
    /outcome-free frozen Entry/,
  );
});

test('purged split rejects samples whose forward label window crosses a boundary', () => {
  const devEnd = '2026-09-03T01:00:00.000Z';
  const valEnd = '2026-09-03T02:00:00.000Z';
  const oosEnd = '2026-09-03T03:00:00.000Z';
  const samples = [
    sampleAt('2026-09-03T00:30:00.000Z', '2026-09-03T00:45:00.000Z', 'SESSION_A'),
    sampleAt('2026-09-03T00:55:00.000Z', '2026-09-03T01:10:00.000Z', 'SESSION_B'),
    sampleAt('2026-09-03T01:10:00.000Z', '2026-09-03T01:25:00.000Z', 'SESSION_C'),
    sampleAt('2026-09-03T01:55:00.000Z', '2026-09-03T02:10:00.000Z', 'SESSION_D'),
    sampleAt('2026-09-03T02:10:00.000Z', '2026-09-03T02:25:00.000Z', 'SESSION_E'),
    sampleAt('2026-09-03T03:10:00.000Z', '2026-09-03T03:25:00.000Z', 'SESSION_F'),
  ];
  const split = buildPurgedExitV5Split(samples, { developmentEnd: devEnd, validationEnd: valEnd, oosEnd });
  assert.equal(split.development.length, 1);
  assert.equal(split.validation.length, 1);
  assert.equal(split.oos.length, 1);
  assert.equal(split.prospective.length, 1);
  assert.equal(split.purged.length, 2);
  assert.equal(split.splitPolicy.sessionAware, true);
  assert.equal(split.splitPolicy.boundarySessionTreatment, 'PURGE_ENTIRE_SESSION');
});

test('session-aware split purges an entire session rather than placing it in two partitions', () => {
  const split = buildPurgedExitV5Split([
    sampleAt('2026-09-03T00:30:00.000Z', '2026-09-03T00:40:00.000Z', 'BOUNDARY_SESSION'),
    sampleAt('2026-09-03T01:10:00.000Z', '2026-09-03T01:20:00.000Z', 'BOUNDARY_SESSION'),
    sampleAt('2026-09-03T02:10:00.000Z', '2026-09-03T02:20:00.000Z', 'SAFE_OOS_SESSION'),
  ], {
    developmentEnd: '2026-09-03T01:00:00.000Z',
    validationEnd: '2026-09-03T02:00:00.000Z',
    oosEnd: '2026-09-03T03:00:00.000Z',
  });
  assert.equal(split.development.length, 0);
  assert.equal(split.validation.length, 0);
  assert.equal(split.oos.length, 1);
  assert.equal(split.purged.length, 2);
  assert.deepEqual(split.splitPolicy.purgedSessionKeys, ['BOUNDARY_SESSION']);
});

test('v5 research safety remains fully non-executing', () => {
  assert.equal(assertExitV5ResearchSafety(), true);
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted',
  ]) assert.equal(PHASE57_EXIT_V5_RESEARCH_SAFETY[key], false, key);
  assert.equal(PHASE57_EXIT_V5_RESEARCH_SAFETY.researchOnly, true);
});
