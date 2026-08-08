import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluatePhase55Finalization, PHASE55_X_SAFETY } from '../trading/phase55-finalization.js';

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

test('Phase55.x closes as review candidate only when robustness passes', () => {
  const input = rows();
  const result = evaluatePhase55Finalization({
    rows: input,
    benchmarkReturns: input.map(() => 0),
    robustnessPolicy: {
      foldCount: 4,
      minimumRowsPerFold: 10,
      minimumPassingFolds: 3,
      maximumFailingStressScenarios: 1,
      stressMultipliers: [1, 1.5, 2],
    },
  });
  assert.equal(result.phase, '55.x');
  assert.equal(result.status, 'PHASE55_REVIEW_CANDIDATE');
  assert.equal(result.handoff.nextFocus, 'CHART_INTELLIGENCE_CORE');
  assert.equal(result.paperTradingAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.transmitted, false);
});

test('Phase55.x fails closed without aligned benchmark', () => {
  const result = evaluatePhase55Finalization({ rows: rows(), benchmarkReturns: [] });
  assert.equal(result.status, 'OBSERVE');
  assert.ok(result.blockers.includes('BENCHMARK_REQUIRED'));
  assert.equal(result.liveTradingAllowed, false);
});

test('Phase55.x safety remains fully read-only', () => {
  assert.deepEqual(PHASE55_X_SAFETY, {
    mode: 'INTRADAY_OOS_FINAL_REVIEW_ONLY',
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    paperTradingAllowed: false,
    humanApprovalRequired: true,
  });
});
