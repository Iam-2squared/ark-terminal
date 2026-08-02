import test from "node:test";
import assert from "node:assert/strict";

import {
  PREDICTION_FEATURE_KEYS,
  PREDICTION_FEATURE_VERSION,
  createPredictionFeatureSet,
} from "../market-intelligence/prediction-feature-model.js";

const TIMESTAMP = "2026-08-02T12:00:00Z";

function details(score = 75) {
  return Object.fromEntries(
    PREDICTION_FEATURE_KEYS.map((key) => [
      key,
      {
        score,
        confidence: 90,
        coverage: 100,
        source: `source-${key}`,
        sourceTimestamp: TIMESTAMP,
      },
    ]),
  );
}

test("Prediction feature model exposes all ten canonical values", () => {
  const result = createPredictionFeatureSet({
    details: details(),
    confidence: 90,
    coverage: 100,
    timestamp: TIMESTAMP,
  });

  assert.equal(result.version, PREDICTION_FEATURE_VERSION);
  assert.equal(result.requestedCount, 10);
  assert.equal(result.availableCount, 10);
  assert.equal(result.marketScore, 75);
  assert.equal(result.compositeAI, 75);
  assert.equal(result.status, "ready");
  assert.equal(result.isProbability, false);
});

test("Feature values, details and availability are immutable", () => {
  const result = createPredictionFeatureSet({
    details: details(),
    confidence: 90,
    coverage: 100,
    timestamp: TIMESTAMP,
  });

  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.values), true);
  assert.equal(Object.isFrozen(result.details), true);
  assert.equal(Object.isFrozen(result.details.marketScore), true);
  assert.equal(Object.isFrozen(result.availability), true);
});

test("Missing scores remain unavailable instead of becoming neutral", () => {
  const input = details();
  input.newsScore = {
    score: null,
    confidence: 100,
    source: "news",
  };
  input.compositeAI = {
    score: null,
    confidence: 0,
    source: "composite",
  };
  const result = createPredictionFeatureSet({
    details: input,
    confidence: 0,
    coverage: 0,
    timestamp: TIMESTAMP,
  });

  assert.equal(result.newsScore, null);
  assert.equal(result.availability.newsScore, false);
  assert.equal(result.status, "unavailable");
});

test("Volatility retains explicit risk polarity and timestamps validate", () => {
  const result = createPredictionFeatureSet({
    details: details(),
    confidence: 90,
    coverage: 100,
    timestamp: TIMESTAMP,
  });

  assert.equal(result.details.volatility.polarity, "risk");
  assert.throws(
    () =>
      createPredictionFeatureSet({
        details: details(),
        timestamp: "invalid",
      }),
    /timestamp is invalid/,
  );
});
