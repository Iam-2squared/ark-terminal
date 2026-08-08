import test from 'node:test';
import assert from 'node:assert/strict';
import {
  estimatePhase55ExecutionCost,
  evaluatePhase55IntradayOos,
  PHASE55_SAFETY,
} from '../trading/phase55-intraday-oos-cost-model.js';

function rows(count = 24) {
  return Array.from({ length: count }, (_, index) => ({
    id: `row-${index}`,
    symbol: '7203.T',
    sessionDate: `2026-07-${String((index % 28) + 1).padStart(2, '0')}`,
    probability: index % 3 === 0 ? 0.4 : 0.65,
    actualReturn: index % 3 === 0 ? -0.004 : 0.008,
    liquidityYen: index % 5 === 0 ? 5_000_000 : 30_000_000,
  }));
}

test('Phase55 execution cost includes liquidity penalty only when constrained', () => {
  const liquid = estimatePhase55ExecutionCost({ liquidityYen: 50_000_000 });
  const thin = estimatePhase55ExecutionCost({ liquidityYen: 1_000_000 });
  assert.equal(liquid.liquidityConstrained, false);
  assert.equal(thin.liquidityConstrained, true);
  assert.ok(thin.totalRate > liquid.totalRate);
});

test('Phase55 evaluates OOS strategy net of costs and benchmark', () => {
  const input = rows();
  const benchmarkReturns = input.map(() => 0.001);
  const result = evaluatePhase55IntradayOos({ rows: input, threshold: 0.55, benchmarkReturns });
  assert.equal(result.phase, '55');
  assert.equal(result.status, 'OOS_COST_EVALUATED');
  assert.equal(result.strategy.tradeCount, input.length);
  assert.ok(Number.isFinite(result.strategy.netReturn));
  assert.ok(Number.isFinite(result.strategy.profitFactor));
  assert.ok(Number.isFinite(result.benchmarkExcessReturn));
  assert.equal(result.executionAllowed, false);
  assert.equal(result.liveTradingAllowed, false);
  assert.equal(result.transmitted, false);
  assert.equal(result.automaticPromotionAllowed, false);
});

test('Phase55 does not claim promotion without a benchmark', () => {
  const result = evaluatePhase55IntradayOos({ rows: rows(), threshold: 0.55 });
  assert.equal(result.benchmark, null);
  assert.equal(result.benchmarkExcessReturn, null);
  assert.equal(result.promotionEligible, false);
});

test('Phase55 safety boundary remains strictly read-only', () => {
  assert.deepEqual(PHASE55_SAFETY, {
    mode: 'INTRADAY_OOS_COST_MODEL_READ_ONLY',
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
