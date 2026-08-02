import assert from "node:assert/strict";
import test from "node:test";

import {
  MarketIntelligenceRuntimeAdapter,
  buildMarketIntelligenceRuntimeReport,
  resolvePredictionHorizon,
} from "../analysis/market-intelligence-runtime-adapter.js";

function prediction(horizon, {
  status = "ready",
  direction = "上昇",
  score = 82,
  confidence = 88,
} = {}) {
  return {
    horizon,
    status,
    direction,
    score,
    confidence: {
      score: confidence,
      coverage: 92,
      isProbability: false,
    },
    expectedReturn: 2,
    executionAllowed: false,
  };
}

function predictionResult(overrides = {}) {
  return {
    status: "ready",
    features: {
      status: "ready",
      confidence: 88,
      coverage: 92,
    },
    predictions: [1, 3, 5, 10, 20].map((horizon) =>
      prediction(horizon),
    ),
    executionAllowed: false,
    ...overrides,
  };
}

test("Runtime adapter selects the nearest supported horizon and builds a vote", () => {
  const report = buildMarketIntelligenceRuntimeReport({
    source: predictionResult(),
    requestedHorizon: 7,
    weight: 1.5,
  });

  assert.equal(resolvePredictionHorizon(7), 5);
  assert.equal(report.selectedHorizon, 5);
  assert.equal(report.participating, true);
  assert.equal(report.engine.name, "market-intelligence");
  assert.equal(report.engine.weight, 1.5);
  assert.equal(report.engine.result.action, "BUY");
  assert.equal(report.engine.result.score, 82);
  assert.equal(report.executionAllowed, false);
});

test("Low-confidence forecasts remain visible but cannot join consensus", () => {
  const source = predictionResult();
  source.predictions[2] = prediction(5, {
    status: "low_confidence",
    confidence: 30,
  });
  const report = buildMarketIntelligenceRuntimeReport({
    source,
    requestedHorizon: 5,
  });

  assert.equal(report.enabled, true);
  assert.equal(report.participating, false);
  assert.equal(report.engine, null);
  assert.equal(report.selectedPrediction.status, "low_confidence");
});

test("A reusable runtime report is reselected when the horizon changes", () => {
  const first = buildMarketIntelligenceRuntimeReport({
    source: predictionResult(),
    requestedHorizon: 5,
  });
  const second = buildMarketIntelligenceRuntimeReport({
    source: first,
    requestedHorizon: 20,
    weight: 2,
  });

  assert.equal(first.selectedHorizon, 5);
  assert.equal(second.selectedHorizon, 20);
  assert.equal(second.engine.weight, 2);
  assert.equal(second.result, first.result);
});

test("Missing Market Intelligence preserves the legacy runtime path", async () => {
  const adapter = new MarketIntelligenceRuntimeAdapter({
    orchestrator: { async analyze() {} },
    predictionEngine: { analyze() {} },
  });
  const asyncReport = await adapter.analyze({ period: 10 });
  const syncReport = adapter.analyzeSync({ period: 10 });

  assert.equal(asyncReport.status, "not_requested");
  assert.equal(asyncReport.enabled, false);
  assert.equal(syncReport.engine, null);
  assert.equal(syncReport.selectedHorizon, 10);
});

test("A Market Intelligence failure is isolated from Runtime v3", async () => {
  const adapter = new MarketIntelligenceRuntimeAdapter({
    orchestrator: {
      async analyze() {
        throw new Error("provider failed");
      },
    },
    predictionEngine: { analyze() {} },
  });
  const report = await adapter.analyze({
    marketIntelligence: { marketData: [] },
    predictionHorizon: 3,
  });

  assert.equal(report.status, "error");
  assert.equal(report.participating, false);
  assert.equal(report.engine, null);
  assert.match(report.error.message, /provider failed/);
});

test("Adapter validates replaceable engines", () => {
  assert.throws(
    () => new MarketIntelligenceRuntimeAdapter({ orchestrator: {} }),
    /orchestrator is invalid/,
  );
  assert.throws(
    () => new MarketIntelligenceRuntimeAdapter({ predictionEngine: {} }),
    /prediction engine is invalid/,
  );
});
