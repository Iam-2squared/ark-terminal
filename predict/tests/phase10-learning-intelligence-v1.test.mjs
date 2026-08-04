import test from "node:test";
import assert from "node:assert/strict";

import { analyzeLearningIntelligence } from "../learning/learning-intelligence-v1.js";
import { analyzeWeightOptimization } from "../learning/weight-optimization-v1.js";
import { buildConfidenceCalibration } from "../learning/confidence-calibration-v1.js";
import { detectDrift } from "../learning/drift-detection-v1.js";

function sampleTrades() {
  return [
    { action: "BUY", status: "WIN", returnPercent: 4, confidence: 90, sector: "AUTO", marketRegime: "BULL", features: { rsi: 60, macd: 2 } },
    { action: "BUY", status: "LOSS", returnPercent: -2, confidence: 80, sector: "AUTO", marketRegime: "BULL", features: { rsi: 40, macd: -1 } },
    { action: "SELL", status: "WIN", returnPercent: 3, confidence: 70, sector: "TECH", marketRegime: "BEAR", features: { rsi: 35, macd: -2 } },
    { action: "SELL", status: "LOSS", returnPercent: -1, confidence: 60, sector: "TECH", marketRegime: "BEAR", features: { rsi: 55, macd: 1 } },
    { action: "NO_TRADE", status: "WIN", returnPercent: 10, confidence: 95, sector: "TECH", marketRegime: "BULL", features: { rsi: 80, macd: 5 } },
    { action: "BUY", status: "PENDING", confidence: 75, sector: "AUTO", marketRegime: "BULL", features: { rsi: 50, macd: 0 } },
  ];
}

test("Part1 Learning Intelligence explains closed execution-derived trades", () => {
  const result = analyzeLearningIntelligence(sampleTrades());
  assert.equal(result.sample.count, 4);
  assert.equal(result.sample.wins, 2);
  assert.equal(result.sample.losses, 2);
  assert.equal(result.byRegime.BULL.count, 2);
  assert.equal(result.bySector.TECH.count, 2);
  assert.ok(result.featureEffects.some((item) => item.feature === "rsi"));
  assert.ok(result.warnings.includes("INSUFFICIENT_TRADE_SAMPLE"));
});

test("Part2 Weight Optimization proposes candidate-only weights by regime and sector", () => {
  const result = analyzeWeightOptimization(sampleTrades(), {
    evaluator: ({ permutedFeature }) => permutedFeature === "rsi" ? 0.2 : 0.1,
  });
  assert.equal(result.sampleSize, 4);
  assert.equal(result.permutationImportance[0].feature, "rsi");
  assert.ok(Object.hasOwn(result.byRegime, "BULL"));
  assert.ok(Object.hasOwn(result.byRegime, "BEAR"));
  assert.ok(Object.hasOwn(result.bySector, "AUTO"));
  assert.equal(result.outOfSampleRequired, true);
  assert.equal(result.productionUpdateAllowed, false);
});

test("Part3 Confidence Calibration calculates ECE and Brier score", () => {
  const result = buildConfidenceCalibration(sampleTrades(), { bins: 5 });
  assert.equal(result.sampleSize, 4);
  assert.equal(result.bins.length, 5);
  assert.ok(Number.isFinite(result.expectedCalibrationError));
  assert.ok(Number.isFinite(result.brierScore));
  assert.ok(Number.isFinite(result.calibrate(80)));
  assert.ok(result.warnings.includes("INSUFFICIENT_CALIBRATION_SAMPLE"));
});

test("Part4 Drift Detection identifies feature and regime changes without production update", () => {
  const baseline = Array.from({ length: 12 }, (_, i) => ({
    marketRegime: "BULL",
    features: { rsi: 45 + (i % 3), macd: 1 + (i % 2) },
  }));
  const current = Array.from({ length: 12 }, (_, i) => ({
    marketRegime: "BEAR",
    features: { rsi: 70 + (i % 3), macd: -2 - (i % 2) },
  }));
  const result = detectDrift({ baseline, current, zThreshold: 1, minSample: 10 });
  assert.equal(result.driftDetected, true);
  assert.equal(result.regime.changed, true);
  assert.ok(result.driftedFeatures.includes("rsi"));
  assert.equal(result.productionUpdateAllowed, false);
});

test("Parts1-4 ignore pending and NO_TRADE records for learning", () => {
  const records = sampleTrades();
  assert.equal(analyzeLearningIntelligence(records).sample.count, 4);
  assert.equal(analyzeWeightOptimization(records).sampleSize, 4);
  assert.equal(buildConfidenceCalibration(records).sampleSize, 4);
});
