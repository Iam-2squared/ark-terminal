import test from "node:test";
import assert from "node:assert/strict";

import {
  generateLearningReport,
  LearningReportStoreV1,
} from "../learning/learning-report-v1.js";

function memoryStorage() {
  const values = new Map();
  return {
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); },
    removeItem(key) { values.delete(key); },
  };
}

function reportInput(overrides = {}) {
  return {
    generatedAt: "2026-08-05T00:00:00.000Z",
    periods: {
      day7: { accuracy: 61 },
      day30: { accuracy: 64 },
      day90: { accuracy: 60 },
    },
    accuracy: {
      predictionAccuracy: 64,
      tradeWinRate: 58,
      buyWinRate: 60,
      sellWinRate: 55,
      pending: 4,
      noTrade: 12,
    },
    performance: {
      profitFactor: 1.35,
      sharpe: 1.1,
      maxDrawdown: 12,
      averageReturnPercent: 0.8,
    },
    learningIntelligence: {
      sample: { count: 40, wins: 23, losses: 17 },
    },
    weightOptimization: {
      outOfSampleRequired: true,
      featureImportance: Array.from({ length: 12 }, (_, index) => ({
        feature: `feature_${index}`,
        score: 12 - index,
        sampleSize: 40,
      })),
    },
    confidenceCalibration: {
      sampleSize: 40,
      expectedCalibrationError: 0.14,
      brierScore: 0.21,
      warnings: ["INSUFFICIENT_CALIBRATION_SAMPLE"],
    },
    driftDetection: {
      driftDetected: true,
      driftedFeatures: ["rsi"],
      regime: { baseline: "BULL", current: "BEAR", changed: true },
      action: "REVIEW_CANDIDATE_AND_RECALIBRATE",
    },
    candidateModel: {
      version: "candidate-2",
      metrics: { accuracy: 66, profitFactor: 1.4, sharpe: 1.2, maxDrawdown: 11, averageReturn: 0.9 },
    },
    productionModel: {
      version: "production-1",
      metrics: { accuracy: 64, profitFactor: 1.35, sharpe: 1.1, maxDrawdown: 12, averageReturn: 0.8 },
    },
    ...overrides,
  };
}

test("Part5 generates a complete learning report without allowing production promotion", () => {
  const report = generateLearningReport(reportInput());

  assert.equal(report.metrics.accuracy, 64);
  assert.equal(report.metrics.profitFactor, 1.35);
  assert.equal(report.periods.day30.accuracy, 64);
  assert.equal(report.featureImportanceTop10.length, 10);
  assert.equal(report.featureImportanceTop10[0].feature, "feature_0");
  assert.equal(report.drift.detected, true);
  assert.equal(report.candidateComparison.available, true);
  assert.equal(report.candidateComparison.recommendation, "REVIEW_CANDIDATE_FOR_HUMAN_APPROVAL");
  assert.equal(report.candidateComparison.promotionAllowed, false);
  assert.equal(report.safety.productionUpdateAllowed, false);
  assert.equal(report.safety.humanApprovalRequired, true);
  assert.equal(report.safety.brokerExecutionAllowed, false);
  assert.ok(report.recommendations.includes("RUN_OUT_OF_SAMPLE_VALIDATION"));
  assert.ok(report.recommendations.includes("RECALIBRATE_CONFIDENCE"));
  assert.ok(report.recommendations.includes("REVIEW_DRIFT_BEFORE_NEXT_CANDIDATE"));
});

test("Part5 keeps production when candidate metrics are weaker", () => {
  const report = generateLearningReport(reportInput({
    candidateModel: {
      version: "candidate-weak",
      metrics: { accuracy: 60, profitFactor: 1.1, sharpe: 0.8, maxDrawdown: 18, averageReturn: 0.2 },
    },
  }));

  assert.equal(report.candidateComparison.recommendation, "KEEP_PRODUCTION_AND_REVIEW_CANDIDATE");
  assert.equal(report.candidateComparison.promotionAllowed, false);
});

test("Part5 stores, reloads, deduplicates, limits, and clears report history", () => {
  const storage = memoryStorage();
  const store = new LearningReportStoreV1({ storage, maxReports: 2 });
  const first = generateLearningReport(reportInput());
  const second = generateLearningReport(reportInput({ generatedAt: "2026-08-06T00:00:00.000Z" }));
  const third = generateLearningReport(reportInput({ generatedAt: "2026-08-07T00:00:00.000Z" }));

  store.save(first);
  store.save(second);
  store.save(second);
  assert.equal(store.list().length, 2);
  assert.equal(store.latest().id, second.id);

  store.save(third);
  assert.equal(store.list().length, 2);
  assert.equal(store.latest().id, third.id);
  assert.equal(store.list()[1].id, second.id);

  store.clear();
  assert.deepEqual(store.list(), []);
});

test("Part5 handles corrupt storage and missing model comparison safely", () => {
  const storage = memoryStorage();
  storage.setItem("broken", "not-json");
  const store = new LearningReportStoreV1({ storage, key: "broken" });
  assert.deepEqual(store.list(), []);

  const report = generateLearningReport({ generatedAt: "2026-08-05T00:00:00.000Z" });
  assert.equal(report.candidateComparison.available, false);
  assert.equal(report.candidateComparison.promotionAllowed, false);
  assert.equal(report.safety.productionUpdateAllowed, false);
});
