import test from 'node:test';
import assert from 'node:assert/strict';
import {
  evaluatePhase55IntradayRobustness,
  PHASE55_2_SAFETY,
} from '../trading/phase55-intraday-oos-robustness.js';

function rows(count = 48) {
  return Array.from({ length: count }, (_, index) => ({
    id: `row-${String(index).padStart(3, '0')}`,
    symbol: '7203.T',
    sessionDate: `2026-${String(Math.floor(index / 28) + 6).padStart(2, '0')}-${String((index % 28) + 1).padStart(2, '0')}`,
    probability: index % 4 === 0 ? 0.35 : 0.7,
    actualReturn: index % 4 === 0 ? -0.006 : 0.012,
    liquidityYen: 50_000_000,
  }));
}

test('Phase55.2 validates chronological folds and stressed execution costs', () => {
  const input = rows();
  const result = evaluatePhase55IntradayRobustness({
    rows: input,
    benchmarkReturns: input.map(() => 0),
    threshold: 0.55,
    policy: {
      foldCount: 4,
      minimumRowsPerFold: 10,
      minimumPassingFolds: 3,
      maximumFailingStressScenarios: 1,
      stressMultipliers: [1, 1.5, 2],
    },
  });

  assert.equal(result.phase, '55.2');
  assert.equal(result.foldCount, 4);
  assert.equal(result.usableFolds, 4);
  assert.ok(result.passingFolds >= 3);
  assert.equal(result.status, 'ROBUSTNESS_REVIEW_CANDIDATE');
  assert.equal(result.promotionEligible, true);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.transmitted, false);
});

test('Phase55.2 fails closed when benchmark is missing', () => {
  const result = evaluatePhase55IntradayRobustness({ rows: rows() });
  assert.equal(result.status, 'OBSERVE');
  assert.equal(result.promotionEligible, false);
  assert.ok(result.blockers.includes('BENCHMARK_MISSING_OR_MISALIGNED'));
});

test('Phase55.2 blocks fragile strategies under severe cost stress', () => {
  const input = rows();
  const marginal = input.map((row, index) => ({
    ...row,
    actualReturn: index % 4 === 0 ? -0.0025 : 0.003,
  }));
  const result = evaluatePhase55IntradayRobustness({
    rows: marginal,
    benchmarkReturns: marginal.map(() => 0),
    costPolicy: { spreadBps: 10, slippageBps: 10, latencyBps: 3 },
    policy: {
      foldCount: 4,
      minimumRowsPerFold: 10,
      minimumPassingFolds: 3,
      maximumFailingStressScenarios: 0,
      stressMultipliers: [1, 2, 4],
    },
  });

  assert.equal(result.status, 'OBSERVE');
  assert.ok(result.blockers.includes('COST_STRESS_FRAGILE') || result.blockers.includes('FOLD_STABILITY_NOT_PROVEN'));
  assert.equal(result.liveTradingAllowed, false);
});

test('Phase55.2 safety boundary stays read-only', () => {
  assert.deepEqual(PHASE55_2_SAFETY, {
    mode: 'INTRADAY_OOS_ROBUSTNESS_READ_ONLY',
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  });
});
