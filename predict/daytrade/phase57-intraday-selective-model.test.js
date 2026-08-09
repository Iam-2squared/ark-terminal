import test from 'node:test';
import assert from 'node:assert/strict';
import { fitIntradayLogisticPredictor, evaluateIntradaySelectiveModel, PHASE57_P6_SAFETY } from './phase57-intraday-selective-model.js';

const row = (n, label) => ({
  symbol: '7203.T', sessionDate: '2026-08-08',
  featureCutoff: new Date(Date.UTC(2026,7,8,0,n,0)).toISOString(),
  outcomeAt: new Date(Date.UTC(2026,7,8,0,n+1,0)).toISOString(),
  label, barrierBps: 20, pointInTimeValid: true,
  features: { returnFromOpen: label ? 0.3 : -0.3, rangePosition: label ? 0.8 : 0.2, shortMomentum: label ? 0.2 : -0.2, relativeVolume: 1.2, spreadBps: 4, bookImbalance: label ? 0.4 : -0.4, depthImbalance: label ? 0.3 : -0.3, aggressiveBuyRatio: label ? 0.7 : 0.3, tradeIntensity: 1.1 },
  interactions: { vwapFlow: label ? 0.2 : -0.2, rangeBookPressure: label ? 0.15 : -0.15 },
});

test('logistic predictor learns a directional separation without future fields', () => {
  const rows = Array.from({length: 30}, (_,i) => row(i, i % 2));
  const predict = fitIntradayLogisticPredictor(rows);
  assert.ok(predict(row(31,1)) > predict(row(32,0)));
});

test('selective model remains research-only with hard locks', () => {
  const rows = Array.from({length: 50}, (_,i) => row(i, i % 2));
  const out = evaluateIntradaySelectiveModel(rows, { thresholds: [0.5, 0.6], trainFraction: 0.6, testFraction: 0.2, minTrainRows: 20 });
  assert.equal(out.phase, '57.p6');
  assert.equal(out.evaluations.length, 2);
  assert.match(out.selectionWarning, /Nested inner selection/);
  for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(out[key], false);
  assert.equal(PHASE57_P6_SAFETY.executionAllowed, false);
});
