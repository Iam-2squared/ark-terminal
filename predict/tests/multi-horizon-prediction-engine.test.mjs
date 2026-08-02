import test from "node:test";
import assert from "node:assert/strict";

import {
  HORIZON_FEATURE_WEIGHTS,
  PREDICTION_HORIZONS,
  MultiHorizonPredictionEngine,
  predictMultipleHorizons,
} from "../market-intelligence/multi-horizon-prediction-engine.js";
import {
  PREDICTION_FEATURE_KEYS,
  createPredictionFeatureSet,
} from "../market-intelligence/prediction-feature-model.js";

const TIMESTAMP = "2026-08-02T12:00:00Z";

function featureSet(score = 80, volatility = 20) {
  return createPredictionFeatureSet({
    details: Object.fromEntries(
      PREDICTION_FEATURE_KEYS.map((key) => [
        key,
        {
          score: key === "volatility" ? volatility : score,
          confidence: 100,
          coverage: 100,
          source: key,
          sourceTimestamp: TIMESTAMP,
        },
      ]),
    ),
    confidence: 100,
    coverage: 100,
    timestamp: TIMESTAMP,
  });
}

test("Prediction Engine always returns 1, 3, 5, 10 and 20 trading days", () => {
  const predictions = predictMultipleHorizons(featureSet(), { atrPercent: 2 });

  assert.deepEqual(
    predictions.map((prediction) => prediction.horizon),
    PREDICTION_HORIZONS,
  );
  assert.equal(predictions.length, 5);
  assert.equal(predictions.every((prediction) => prediction.score === 80), true);
  assert.equal(predictions.every((prediction) => prediction.direction === "強気"), true);
  assert.equal(predictions.every((prediction) => prediction.status === "ready"), true);
  assert.equal(
    predictions.every(
      (prediction) => prediction.decision.executionAllowed === false,
    ),
    true,
  );
});

test("Expected move reuses the existing ATR square-root contract", () => {
  const predictions = predictMultipleHorizons(featureSet(), { atrPercent: 2 });
  const oneDay = predictions[0];
  const twentyDay = predictions.at(-1);

  assert.equal(oneDay.expectedMoveRange.amplitude, 2);
  assert.equal(oneDay.expectedReturn, 0.42);
  assert.equal(
    twentyDay.expectedMoveRange.amplitude,
    2 * Math.sqrt(20),
  );
});

test("Horizon configurations each have a complete 100-point weight budget", () => {
  PREDICTION_HORIZONS.forEach((horizon) => {
    const total = Object.values(HORIZON_FEATURE_WEIGHTS[horizon]).reduce(
      (sum, weight) => sum + weight,
      0,
    );
    assert.equal(total, 100);
  });
});

test("Short horizon emphasizes news more than the long horizon", () => {
  const source = featureSet(50, 50);
  const details = Object.fromEntries(
    PREDICTION_FEATURE_KEYS.map((key) => [
      key,
      {
        score: key === "newsScore" ? 100 : 50,
        confidence: 100,
        coverage: 100,
        source: key,
        sourceTimestamp: TIMESTAMP,
      },
    ]),
  );
  const newsShock = createPredictionFeatureSet({
    details,
    confidence: source.confidence,
    coverage: source.coverage,
    timestamp: TIMESTAMP,
  });
  const predictions = predictMultipleHorizons(newsShock);

  assert.ok(predictions[0].score > predictions.at(-1).score);
});

test("Unavailable features stay unavailable across every horizon", () => {
  const empty = createPredictionFeatureSet({
    details: {},
    confidence: 0,
    coverage: 0,
    timestamp: TIMESTAMP,
  });
  const predictions = predictMultipleHorizons(empty, { atrPercent: 2 });

  assert.equal(predictions.every((prediction) => prediction.score === null), true);
  assert.equal(
    predictions.every((prediction) => prediction.expectedMoveRange === null),
    true,
  );
  assert.equal(
    predictions.every((prediction) => prediction.direction === "判定不能"),
    true,
  );
});

test("Confidence is data quality, never a probability", () => {
  const engine = new MultiHorizonPredictionEngine();
  const predictions = engine.predict(featureSet(), { atrPercent: null });

  assert.equal(
    predictions.every((prediction) => prediction.confidence.isProbability === false),
    true,
  );
  assert.equal(
    predictions.every((prediction) => prediction.expectedMoveRange === null),
    true,
  );
  assert.throws(() => predictMultipleHorizons(null), /feature set is required/);
});
