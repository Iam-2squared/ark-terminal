import test from 'node:test';
import assert from 'node:assert/strict';
import { selectInnerThreshold, evaluateNestedIntradaySelection } from './phase57-intraday-nested-selection.js';

const makeRow = (n, label) => ({
  symbol: '7203.T',
  sessionDate: '2026-08-08',
  featureCutoff: new Date(Date.UTC(2026,7,8,0,n,0)).toISOString(),
  outcomeAt: new Date(Date.UTC(2026,7,8,0,n+1,0)).toISOString(),
  label,
  barrierBps: 20,
  pointInTimeValid: true,
  features: { returnFromOpen: label ? 0.3 : -0.3, rangePosition: label ? 0.8 : 0.2, shortMomentum: label ? 0.2 : -0.2, relativeVolume: 1.2, spreadBps: 4, bookImbalance: label ? 0.4 : -0.4, depthImbalance: label ? 0.3 : -0.3, aggressiveBuyRatio: label ? 0.7 : 0.3, tradeIntensity: 1.1 },
  interactions: { vwapFlow: label ? 0.2 : -0.2, rangeBookPressure: label ? 0.15 : -0.15 },
});

test('inner selection stays inside declared threshold set', () => {
  const rows = Array.from({length: 60}, (_,i) => makeRow(i, i % 2));
  const out = selectInnerThreshold(rows, { thresholds: [0.55, 0.65], innerMinTrainRows: 10 });
  assert.ok([0.55, 0.65].includes(out.selectedThreshold));
  assert.equal(out.candidates.length, 2);
});

test('nested evaluation keeps inner and outer samples separated', () => {
  const rows = Array.from({length: 80}, (_,i) => makeRow(i, i % 2));
  const out = evaluateNestedIntradaySelection(rows, { thresholds: [0.55, 0.65], minTrainRows: 20, innerMinTrainRows: 10, testFraction: 0.2 });
  assert.equal(out.phase, '57.p7');
  assert.equal(out.selectionIntegrity.thresholdSelectedOnInnerOnly, true);
  assert.equal(out.selectionIntegrity.outerTestNeverUsedForSelection, true);
  assert.equal(out.selectionIntegrity.outerTestNeverUsedForFit, true);
  assert.equal(out.executionAllowed, false);
  assert.equal(out.brokerWriteAllowed, false);
  assert.equal(out.automaticPromotionAllowed, false);
  assert.equal(out.productionUpdateAllowed, false);
});
