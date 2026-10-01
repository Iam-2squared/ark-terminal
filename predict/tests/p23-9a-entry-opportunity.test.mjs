import assert from 'node:assert/strict';
import {
  PHASE57_P23_9A_SAFETY,
  deriveEntryOpportunityFeatures,
  deriveFixedHorizonOpportunityTargets,
  buildEntryOpportunityExample,
  fitEntryOpportunityRidge,
  evaluateEntryOpportunityWalkForward,
} from '../daytrade/phase57-entry-opportunity-intelligence.js';

for (const key of [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
]) assert.equal(PHASE57_P23_9A_SAFETY[key], false, `${key} must remain false`);

function bars(count = 20, start = 100, drift = 0.2, sessionDate = '2026-08-01') {
  const startMs = Date.parse('2026-08-01T00:00:00.000Z');
  return Array.from({ length: count }, (_, index) => {
    const open = start + drift * index;
    const close = open + drift * 0.5;
    return {
      timestamp: new Date(startMs + index * 5 * 60_000).toISOString(),
      sessionDate,
      open,
      high: Math.max(open, close) + 0.15,
      low: Math.min(open, close) - 0.12,
      close,
      volume: 1000 + index * 10,
    };
  });
}

{
  const context = bars(8);
  const fLong = deriveEntryOpportunityFeatures({ contextBars: context, direction: 'LONG' });
  const fShort = deriveEntryOpportunityFeatures({ contextBars: context, direction: 'SHORT' });
  assert.equal(fLong.directionSign, 1);
  assert.equal(fShort.directionSign, -1);
  assert.ok(fLong.directionalReturnFromOpenPct > 0);
  assert.ok(fShort.directionalReturnFromOpenPct < 0);
  assert.ok(Number.isFinite(fLong.atrPct10));
  assert.ok(Number.isFinite(fLong.relativeVolume5));
}

{
  const future = [
    { timestamp: '2026-08-01T00:05:00.000Z', open: 100, high: 102, low: 99, close: 101, volume: 1, sessionDate: '2026-08-01' },
    { timestamp: '2026-08-01T00:10:00.000Z', open: 101, high: 103, low: 100, close: 102, volume: 1, sessionDate: '2026-08-01' },
  ];
  const long = deriveFixedHorizonOpportunityTargets({ entryPrice: 100, direction: 'LONG', futureBars: future, horizonBars: 2, roundTripCostPct: 0.05 });
  assert.ok(Math.abs(long.mfePct - 3) < 1e-12);
  assert.ok(Math.abs(long.adversePct - 1) < 1e-12);
  assert.ok(Math.abs(long.endpointNetReturnPct - 1.95) < 1e-12);
  assert.ok(Math.abs(long.opportunityScorePct - 1.95) < 1e-12);
  const short = deriveFixedHorizonOpportunityTargets({ entryPrice: 100, direction: 'SHORT', futureBars: future, horizonBars: 2, roundTripCostPct: 0.05 });
  assert.ok(Math.abs(short.mfePct - ((100 / 99 - 1) * 100)) < 1e-12);
  assert.ok(Math.abs(short.adversePct - (-(100 / 103 - 1) * 100)) < 1e-12);
  assert.ok(Math.abs(short.endpointNetReturnPct - (-2.0107843137254832)) < 1e-9);
  assert.equal(long.futureBarsUsedAsPredictors, false);
}

{
  const context = bars(6);
  const future = bars(8, context.at(-1).close, 0.15).map((bar, index) => ({ ...bar, timestamp: new Date(Date.parse(context.at(-1).timestamp) + (index + 1) * 5 * 60_000).toISOString() }));
  const example = buildEntryOpportunityExample({
    symbol: 'TEST', sessionDate: '2026-08-01', featureCutoff: context.at(-1).timestamp,
    contextBars: context, futureBars: future, entryPrice: context.at(-1).close, direction: 'LONG', horizonBars: 6,
  });
  assert.equal(example.pointInTimeFeaturesOnly, true);
  assert.equal(example.futureTargetsEvaluationOnly, true);
  assert.equal(example.targets.eligibleForModelFeatures, false);
}

{
  const synthetic = [];
  for (let i = 0; i < 120; i += 1) {
    const context = bars(8, 100 + i * 0.01, (i % 2 ? 0.3 : -0.2), `2026-07-${String(1 + Math.floor(i / 10)).padStart(2, '0')}`);
    const direction = i % 3 ? 'LONG' : 'SHORT';
    const features = deriveEntryOpportunityFeatures({ contextBars: context, direction });
    const x = features.directionalMomentum3Pct + features.directionalReturnFromOpenPct;
    synthetic.push({
      symbol: 'SYN', sessionDate: `2026-07-${String(1 + Math.floor(i / 10)).padStart(2, '0')}`,
      featureCutoff: context.at(-1).timestamp, direction,
      features,
      targets: {
        mfePct: Math.max(0, 0.8 + x * 0.4),
        adversePct: Math.max(0, 0.4 - x * 0.1),
        endpointNetReturnPct: x * 0.5,
        opportunityScorePct: x * 0.5,
      },
      pointInTimeFeaturesOnly: true,
      futureTargetsEvaluationOnly: true,
    });
  }
  const model = fitEntryOpportunityRidge(synthetic, { lambda: 2 });
  const p = model.predict(synthetic.at(-1).features);
  assert.ok(Number.isFinite(p.expectedMfePct));
  assert.ok(Number.isFinite(p.expectedAdversePct));
  assert.ok(Number.isFinite(p.expectedNetReturnPct));
  assert.equal(p.futureOutcomeUsedForPrediction, false);
}

{
  const train = [];
  const test = [];
  for (let day = 1; day <= 8; day += 1) {
    const date = `2026-07-${String(day).padStart(2, '0')}`;
    for (let i = 0; i < 40; i += 1) {
      const context = bars(8, 100 + i, i % 2 ? 0.25 : -0.15, date);
      const features = deriveEntryOpportunityFeatures({ contextBars: context, direction: 'LONG' });
      const value = features.directionalReturnFromOpenPct;
      train.push({
        symbol: 'WF', sessionDate: date, featureCutoff: context.at(-1).timestamp, direction: 'LONG', features,
        targets: { mfePct: Math.max(0, 1 + value), adversePct: 0.3, endpointNetReturnPct: value, opportunityScorePct: value },
        pointInTimeFeaturesOnly: true, futureTargetsEvaluationOnly: true,
      });
    }
  }
  for (const date of ['2026-07-07', '2026-07-08']) {
    const context = bars(8, 120, 0.3, date);
    const features = deriveEntryOpportunityFeatures({ contextBars: context, direction: 'LONG' });
    test.push({
      symbol: 'WF', sessionDate: date, featureCutoff: context.at(-1).timestamp, direction: 'LONG', features,
      targets: { mfePct: 1.5, adversePct: 0.2, endpointNetReturnPct: 0.4, opportunityScorePct: 1.25 },
      realizedRatchetNetReturnPct: 0.3,
      pointInTimeFeaturesOnly: true, futureTargetsEvaluationOnly: true,
    });
  }
  const result = evaluateEntryOpportunityWalkForward({ trainingExamples: train, frozenTestExamples: test, minTrainRows: 100, lambda: 2 });
  assert.equal(result.integrity.trainingUsesPriorSessionsOnly, true);
  assert.equal(result.integrity.sameSessionTrainingForbidden, true);
  assert.equal(result.integrity.futureExtremaUsedAsFeatures, false);
  assert.equal(result.edgeClaimAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.ok(result.predictionCount >= 1);
  for (const row of result.predictions) assert.equal(row.outerOutcomeUsedForModelFit, false);
}

console.log('P23.9A entry opportunity tests passed');
