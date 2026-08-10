import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P21_4_SAFETY,
  summarizeNetExpectancy,
  evaluateNetExpectancyEvidence,
} from '../daytrade/phase57-net-expectancy-objective.js';

function robustRows({ n = 150 } = {}) {
  const symbols = ['7203.T', '6758.T', '9984.T', '8306.T', '8035.T'];
  return Array.from({ length: n }, (_, index) => {
    const fold = Math.floor(index / 30);
    const loss = index % 7 === 0;
    const netReturnPct = loss ? -0.08 : 0.32 + (index % 5) * 0.01;
    const label = index % 2;
    const probability = label ? 0.72 : 0.28;
    return {
      id: `R${index}`,
      symbol: symbols[index % symbols.length],
      fold,
      featureCutoff: new Date(Date.UTC(2026, 0, 5, 0, index * 5)).toISOString(),
      netReturnPct,
      probability,
      label,
      mfePct: 0.6 + (index % 3) * 0.1,
      maePct: -0.2 - (index % 2) * 0.05,
      barsHeld: 12,
    };
  });
}

test('P21.4 summarizes OOS net expectancy, confidence, calibration, drawdown and stability', () => {
  const rows = robustRows();
  const result = summarizeNetExpectancy(rows, {
    researchRowCount: 1000,
    bootstrap: { iterations: 500, seed: 12345 },
  });
  assert.equal(result.sampleCount, 150);
  assert.ok(result.netAverageReturnPct > 0);
  assert.ok(result.medianNetReturnPct > 0);
  assert.ok(result.profitFactor > 1.2);
  assert.ok(result.confidenceInterval.lowerPct > 0);
  assert.equal(result.confidenceInterval.method, 'DETERMINISTIC_FOLD_CLUSTER_BOOTSTRAP');
  assert.equal(result.foldStability.groupCount, 5);
  assert.equal(result.symbolStability.groupCount, 5);
  assert.equal(result.coverage, 0.15);
  assert.equal(result.calibration.sampleCount, 150);
  assert.ok(result.calibration.brierScore < 0.1);
  assert.ok(result.maxDrawdownPct >= 0);
});

test('robust positive evidence can pass only the research evidence gate', () => {
  const result = evaluateNetExpectancyEvidence(robustRows(), {
    minSignals: 100,
    minimumProfitFactor: 1.2,
    maximumDrawdownPct: 10,
    minimumFoldGroups: 3,
    minimumPositiveFoldFraction: 0.6,
    requireCrossSymbolStability: true,
    minimumSymbolGroups: 3,
    minimumPositiveSymbolFraction: 0.6,
    maximumSingleSymbolShare: 0.6,
    bootstrap: { iterations: 500, seed: 7 },
  });
  assert.equal(result.status, 'RESEARCH_EVIDENCE_GATE_PASSED');
  assert.equal(result.evidenceGatePassed, true);
  assert.equal(result.researchOnly, true);
  assert.equal(result.recommendationAllowed, false);
  assert.equal(result.oosSelectionAllowed, false);
  assert.equal(result.paperTradingAllowed, false);
  assert.equal(result.executionAllowed, false);
});

test('tiny high-return sample is rejected instead of being treated as a hero result', () => {
  const rows = Array.from({ length: 10 }, (_, index) => ({
    symbol: '8306.T', fold: index % 2, netReturnPct: 1.5, featureCutoff: `2026-01-${String(index + 1).padStart(2, '0')}T00:00:00.000Z`,
  }));
  const result = evaluateNetExpectancyEvidence(rows, { minSignals: 100, minimumFoldGroups: 3 });
  assert.equal(result.evidenceGatePassed, false);
  assert.ok(result.failureReasons.includes('INSUFFICIENT_SAMPLE'));
  assert.ok(result.failureReasons.includes('INSUFFICIENT_FOLD_STABILITY_SAMPLE'));
});

test('positive point estimate still abstains when conservative confidence lower bound is not positive', () => {
  const foldMeans = [0.50, -0.40, 0.50, -0.40, 0.10];
  const rows = Array.from({ length: 120 }, (_, index) => {
    const fold = Math.floor(index / 24);
    return {
      symbol: ['A', 'B', 'C'][index % 3],
      fold,
      featureCutoff: new Date(Date.UTC(2026, 0, 5, 0, index * 5)).toISOString(),
      netReturnPct: foldMeans[fold],
    };
  });
  const result = evaluateNetExpectancyEvidence(rows, {
    minSignals: 100,
    minimumProfitFactor: 0.5,
    maximumDrawdownPct: 100,
    minimumPositiveFoldFraction: 0,
    bootstrap: { iterations: 2000, seed: 17 },
  });
  assert.ok(result.metrics.netAverageReturnPct > 0);
  assert.ok(result.metrics.confidenceInterval.lowerPct <= 0);
  assert.equal(result.evidenceGatePassed, false);
  assert.ok(result.failureReasons.includes('NET_EXPECTANCY_LOWER_BOUND_NOT_POSITIVE'));
});

test('cross-symbol concentration is reported and can be required as a research gate', () => {
  const rows = robustRows().map((row, index) => ({ ...row, symbol: index < 130 ? '8035.T' : `OTHER${index % 4}` }));
  const result = evaluateNetExpectancyEvidence(rows, {
    requireCrossSymbolStability: true,
    maximumSingleSymbolShare: 0.6,
    minimumSymbolGroups: 3,
    minimumPositiveSymbolFraction: 0,
    bootstrap: { iterations: 300, seed: 9 },
  });
  assert.ok(result.metrics.concentration.maxSingleSymbolShare > 0.8);
  assert.ok(result.failureReasons.includes('SINGLE_SYMBOL_CONCENTRATION_TOO_HIGH'));
});

test('P21.4 never enables execution, writes, paper/live trading or OOS post-selection', () => {
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'oosSelectionAllowed',
  ]) assert.equal(PHASE57_P21_4_SAFETY[key], false);
  assert.equal(PHASE57_P21_4_SAFETY.overnightHoldingAllowed, false);
});
