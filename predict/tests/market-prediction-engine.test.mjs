import test from "node:test";
import assert from "node:assert/strict";

import { MarketPredictionEngine } from "../market-intelligence/market-prediction-engine.js";
import { PredictionFeatureComposer } from "../market-intelligence/prediction-feature-composer.js";

const NOW = Date.parse("2026-08-02T12:00:00Z");
const SOURCE_TIME = "2026-08-02T11:00:00Z";

function report(score) {
  return {
    score,
    confidence: 100,
    coverage: 100,
    timestamp: SOURCE_TIME,
  };
}

function input() {
  return {
    marketSnapshot: {
      indexes: report(80),
      macro: {
        ...report(75),
        vixLevel: 15,
        items: [
          {
            symbol: "VIX",
            price: 15,
            confidence: 100,
            available: true,
          },
        ],
      },
      timestamp: SOURCE_TIME,
    },
    breadth: report(85),
    liquidity: report(80),
    sectorStrength: report(82),
    newsIntelligence: report(88),
    momentum: report(85),
    technical: { atrPercent: 2 },
  };
}

test("Market Prediction Engine composes features and all horizons", () => {
  const engine = new MarketPredictionEngine({
    featureComposer: new PredictionFeatureComposer({ now: () => NOW }),
  });
  const result = engine.analyze(input());

  assert.equal(result.status, "ready");
  assert.equal(result.timestamp, "2026-08-02T12:00:00.000Z");
  assert.deepEqual(result.horizons, [1, 3, 5, 10, 20]);
  assert.equal(result.features.availableCount, 10);
  assert.equal(result.predictions.length, 5);
  assert.equal(result.executionAllowed, false);
});

test("Engine builds feedback only through the explicit adapter call", () => {
  const engine = new MarketPredictionEngine({
    featureComposer: new PredictionFeatureComposer({ now: () => NOW }),
  });
  const result = engine.analyze(input());
  const feedback = engine.buildFeedback(result, {
    symbol: "7203.T",
    predictionPrice: 3000,
  });

  assert.equal(feedback.length, 5);
  assert.equal(feedback.every((record) => record.status === "pending"), true);
  assert.equal(feedback.every((record) => record.executionAllowed === false), true);
});

test("Empty inputs stay unavailable rather than producing neutral forecasts", () => {
  const engine = new MarketPredictionEngine({
    featureComposer: new PredictionFeatureComposer({ now: () => NOW }),
  });
  const result = engine.analyze({});

  assert.equal(result.status, "unavailable");
  assert.equal(result.features.compositeAI, null);
  assert.equal(
    result.predictions.every((prediction) => prediction.score === null),
    true,
  );
});

test("Engine validates replaceable module contracts", () => {
  assert.throws(
    () => new MarketPredictionEngine({ featureComposer: {} }),
    /feature composer is invalid/,
  );
  assert.throws(
    () => new MarketPredictionEngine({ predictionEngine: {} }),
    /horizon engine is invalid/,
  );
});
