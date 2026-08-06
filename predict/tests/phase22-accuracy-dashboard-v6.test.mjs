import assert from "node:assert/strict";
import test from "node:test";

import { buildAccuracyDashboardV6 } from "../analysis/accuracy-dashboard-v6.js";

function row(overrides = {}) {
  return {
    id: crypto.randomUUID(),
    symbol: "7203.T",
    industry: "Transport Equipment",
    signal: "BUY",
    status: "resolved",
    directionHit: true,
    costAdjustedReturn: 2,
    evaluationHorizon: 5,
    confidence: 0.85,
    marketRegime: "BULL",
    ...overrides,
  };
}

test("Accuracy Dashboard v6 separates overall, BUY, SELL and high-confidence metrics", () => {
  const dashboard = buildAccuracyDashboardV6({
    rows: [
      row(),
      row({ id: "buy-loss", directionHit: false, costAdjustedReturn: -1, confidence: 0.7 }),
      row({ id: "sell-win", signal: "SELL", directionHit: true, costAdjustedReturn: 3, confidence: 0.9 }),
      row({ id: "pending", status: "pending", directionHit: null, costAdjustedReturn: null }),
      row({ id: "hold", signal: "HOLD", directionHit: null, costAdjustedReturn: 0 }),
    ],
    options: { generatedAt: "2026-08-06T00:00:00.000Z" },
  });

  assert.equal(dashboard.version, "accuracy-dashboard-v6");
  assert.equal(dashboard.overall.sampleCount, 3);
  assert.equal(dashboard.overall.accuracy, 2 / 3);
  assert.equal(dashboard.buy.sampleCount, 2);
  assert.equal(dashboard.buy.accuracy, 0.5);
  assert.equal(dashboard.sell.sampleCount, 1);
  assert.equal(dashboard.sell.accuracy, 1);
  assert.equal(dashboard.highConfidence.sampleCount, 2);
  assert.equal(dashboard.sample.source, 5);
  assert.equal(dashboard.sample.eligible, 3);
  assert.equal(dashboard.safety.liveTradingAllowed, false);
  assert.equal(dashboard.safety.automaticPromotionAllowed, false);
});

test("Accuracy Dashboard v6 reports horizon, symbol, industry and market-regime slices", () => {
  const dashboard = buildAccuracyDashboardV6({
    rows: [
      row({ id: "h1", evaluationHorizon: 1, marketRegime: "BULL" }),
      row({ id: "h3", evaluationHorizon: 3, symbol: "6758.T", industry: "Electric Appliances", marketRegime: "BEAR", directionHit: false, costAdjustedReturn: -2 }),
      row({ id: "h5", evaluationHorizon: 5, marketRegime: "HIGH_VOLATILITY", costAdjustedReturn: 1 }),
    ],
  });

  assert.equal(dashboard.byHorizon["1"].sampleCount, 1);
  assert.equal(dashboard.byHorizon["3"].accuracy, 0);
  assert.equal(dashboard.bySymbol["6758.T"].sampleCount, 1);
  assert.equal(dashboard.byIndustry["Electric Appliances"].sampleCount, 1);
  assert.equal(dashboard.byMarketRegime.BULL.accuracy, 1);
  assert.equal(dashboard.byMarketRegime.BEAR.accuracy, 0);
  assert.equal(dashboard.byMarketRegime.HIGH_VOLATILITY.sampleCount, 1);
});

test("Accuracy Dashboard v6 exposes calibration buckets, ECE and Brier score", () => {
  const dashboard = buildAccuracyDashboardV6({
    rows: [
      row({ id: "c1", confidence: 0.85, directionHit: true }),
      row({ id: "c2", confidence: 0.85, directionHit: false, costAdjustedReturn: -1 }),
      row({ id: "c3", confidence: 0.55, directionHit: true }),
    ],
  });

  assert.equal(dashboard.confidenceCalibration.count, 3);
  assert.ok(dashboard.confidenceCalibration.bins.length > 0);
  assert.ok(Number.isFinite(dashboard.calibrationError));
  assert.ok(Number.isFinite(dashboard.brierScore));
  assert.equal(dashboard.byConfidenceBucket["80-90%"].sampleCount, 2);
  assert.equal(dashboard.byConfidenceBucket["50-60%"].sampleCount, 1);
});

test("Accuracy Dashboard v6 includes a Wilson confidence interval and performance metrics", () => {
  const dashboard = buildAccuracyDashboardV6({
    rows: [
      row({ id: "one", costAdjustedReturn: 2 }),
      row({ id: "two", costAdjustedReturn: -1, directionHit: false }),
      row({ id: "three", costAdjustedReturn: 4 }),
    ],
  });

  assert.ok(dashboard.overall.confidenceInterval.lower >= 0);
  assert.ok(dashboard.overall.confidenceInterval.upper <= 1);
  assert.equal(dashboard.overall.medianReturn, 2);
  assert.equal(dashboard.overall.averageReturn, 5 / 3);
  assert.equal(dashboard.overall.profitFactor, 6);
  assert.ok("sharpe" in dashboard.overall);
  assert.ok("maxDrawdown" in dashboard.overall);
});
