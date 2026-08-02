import test from "node:test";
import assert from "node:assert/strict";

import {
  calculateRiskAdjustedMetrics,
  normalizeReturns,
} from "../analysis/risk-adjusted-metrics.js";

test("Risk adjusted metrics calculate Sharpe and drawdown", () => {
  const result = calculateRiskAdjustedMetrics(
    [0.02, -0.01, 0.03, -0.005, 0.01],
    {
      periodsPerYear: 252,
    },
  );

  assert.equal(result.count, 5);
  assert.ok(result.averageReturn > 0);
  assert.ok(result.volatility > 0);
  assert.ok(result.sharpeRatio > 0);
  assert.ok(result.maxDrawdown > 0);
});

test("Risk adjusted metrics handle empty returns", () => {
  const result = calculateRiskAdjustedMetrics([]);

  assert.deepEqual(result, {
    count: 0,
    averageReturn: 0,
    volatility: 0,
    downsideDeviation: 0,
    annualizedReturn: 0,
    annualizedVolatility: 0,
    sharpeRatio: 0,
    sortinoRatio: 0,
    calmarRatio: 0,
    maxDrawdown: 0,
  });
});

test("Return normalization reads result objects", () => {
  assert.deepEqual(
    normalizeReturns([
      { returnRate: 0.1 },
      { pnl: -0.02 },
      { result: { profit: 0.03 } },
      { return: "invalid" },
    ]),
    [0.1, -0.02, 0.03],
  );
});

test("Risk adjusted metrics validates input", () => {
  assert.throws(
    () => calculateRiskAdjustedMetrics(null),
    {
      name: "TypeError",
    },
  );
});
