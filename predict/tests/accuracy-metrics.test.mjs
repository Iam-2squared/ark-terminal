import test from "node:test";
import assert from "node:assert/strict";

import {
  calculateAccuracyMetrics,
  normalizeAccuracyRows,
} from "../analysis/accuracy-metrics.js";

test("Accuracy metrics calculates dashboard summary", () => {
  const result = calculateAccuracyMetrics([
    { signal: "BUY", correct: true, profit: 10 },
    { signal: "BUY", correct: false, profit: -4 },
    { signal: "SELL", correct: true, profit: 6 },
    { signal: "SELL", correct: false, profit: -2 },
  ]);

  assert.equal(result.total, 4);
  assert.equal(result.correct, 2);
  assert.equal(result.accuracy, 0.5);
  assert.equal(result.buy.winRate, 0.5);
  assert.equal(result.sell.winRate, 0.5);
  assert.equal(result.grossProfit, 16);
  assert.equal(result.grossLoss, 6);
  assert.equal(result.netProfit, 10);
  assert.equal(result.averageProfit, 8);
  assert.equal(result.averageLoss, 3);
  assert.equal(result.expectancy, 2.5);
  assert.equal(result.profitFactor, 2.666667);
});

test("Accuracy metrics handles empty rows", () => {
  const result = calculateAccuracyMetrics([]);

  assert.equal(result.total, 0);
  assert.equal(result.accuracy, 0);
  assert.equal(result.profitFactor, 0);
  assert.equal(result.maxDrawdown, 0);
});

test("Accuracy rows support alternate field names", () => {
  const rows = normalizeAccuracyRows([
    {
      prediction: "long",
      pnl: 5,
      isCorrect: true,
    },
  ]);

  assert.equal(rows[0].signal, "BUY");
  assert.equal(rows[0].profit, 5);
  assert.equal(rows[0].correct, true);
});

test("Accuracy metrics validates rows", () => {
  assert.throws(
    () => calculateAccuracyMetrics(null),
    {
      name: "TypeError",
    },
  );
});
