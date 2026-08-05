import test from "node:test";
import assert from "node:assert/strict";

import { buildFeatureIntelligence } from "../features/feature-intelligence-v1.js";
import { enhanceModelDecision } from "../model/model-enhancement-v1.js";
import { analyzeNewsAndEarnings } from "../intelligence/news-earnings-intelligence-v1.js";

test("feature intelligence builds volume, breadth, rotation and correlation features", () => {
  const result = buildFeatureIntelligence({
    candles: [
      { timestamp: "2026-01-01", close: 100, volume: 1000 },
      { timestamp: "2026-01-02", close: 103, volume: 2000 },
      { timestamp: "2026-01-03", close: 101, volume: 1500 },
    ],
    benchmarkReturns: [0.03, -0.0194],
    sectorReturns: { TECH: [0.02, 0.01], AUTO: [-0.01, 0] },
    breadth: { advancers: 1200, decliners: 800 },
    asOf: "2026-01-03",
  });
  assert.equal(result.status, "READY");
  assert.equal(result.features.marketBreadth.ratio, 1.5);
  assert.equal(result.features.sectorRotation[0].sector, "TECH");
  assert.equal(result.quality.futureLeakDetected, false);
});

test("feature intelligence blocks future data leakage", () => {
  const result = buildFeatureIntelligence({
    candles: [{ timestamp: "2026-01-04", close: 100, volume: 1000 }],
    asOf: "2026-01-03",
  });
  assert.equal(result.status, "BLOCKED");
  assert.equal(result.quality.futureLeakDetected, true);
});

test("model enhancement ensembles models but keeps promotion approval-gated", () => {
  const result = enhanceModelDecision({
    models: [
      { name: "trend", score: 70, confidence: 80, weight: 2 },
      { name: "momentum", score: 50, confidence: 60, weight: 1 },
    ],
    calibration: [
      { confidence: 0.8, outcome: 1 },
      { confidence: 0.6, outcome: 0 },
    ],
    featureImportance: { rsi: 0.2, macd: 0.4 },
    candidateMetrics: { accuracy: 65, profitFactor: 1.4, expectedValue: 0.03 },
    productionMetrics: { accuracy: 60, profitFactor: 1.2, expectedValue: 0.01 },
  });
  assert.equal(result.status, "READY");
  assert.ok(result.ensemble.score > 60);
  assert.equal(result.featureImportance[0].feature, "macd");
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.humanApprovalRequired, true);
});

test("news and earnings intelligence scores events and detects guidance", () => {
  const result = analyzeNewsAndEarnings({
    earnings: {
      revenue: 120,
      priorRevenue: 100,
      consensusRevenue: 110,
      operatingProfit: 30,
      priorOperatingProfit: 20,
      consensusOperatingProfit: 25,
      guidance: 150,
      priorGuidance: 120,
    },
    news: [
      { id: "n1", title: "業績上方修正と大型受注", publishedAt: "2026-01-03T00:00:00Z" },
    ],
    asOf: "2026-01-03T06:00:00Z",
  });
  assert.equal(result.status, "READY");
  assert.equal(result.earnings.guidanceDirection, "RAISED");
  assert.ok(result.news.topEvents[0].categories.includes("EARNINGS"));
  assert.equal(result.brokerExecutionAllowed, false);
});

test("news intelligence blocks future-published events", () => {
  const result = analyzeNewsAndEarnings({
    news: [{ title: "future", publishedAt: "2026-01-04T00:00:00Z" }],
    asOf: "2026-01-03T00:00:00Z",
  });
  assert.equal(result.status, "BLOCKED");
  assert.equal(result.quality.futureLeakDetected, true);
});
