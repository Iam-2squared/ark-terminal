import assert from "node:assert/strict";
import test from "node:test";

import {
  PHASE22_EVALUATION_HORIZONS,
  evaluatePredictionAcrossHorizons,
  evaluatePredictionsAcrossHorizons,
} from "../analysis/multi-horizon-outcome.js";

function candles(count = 25, start = 100, symbol = "7203.T") {
  return Array.from({ length: count }, (_, index) => ({
    symbol,
    time: 1_700_000_000 + index * 86_400,
    close: start + index,
  }));
}

function prediction(overrides = {}) {
  return {
    id: "prediction-1",
    symbol: "7203.T",
    analysisTime: 1_700_000_000,
    predictionPrice: 100,
    signal: "BUY",
    evaluationThreshold: 1,
    confidence: 0.85,
    marketRegime: "BULL",
    industry: "Transport Equipment",
    status: "pending",
    ...overrides,
  };
}

test("Phase22 resolves 1, 3, 5, 10 and 20 trading-session outcomes", () => {
  const result = evaluatePredictionAcrossHorizons(prediction(), candles(), {
    symbol: "7203.T",
    costs: { commissionBpsPerSide: 5, slippageBpsPerSide: 5 },
  });

  assert.deepEqual(
    result.outcomes.map((row) => row.evaluationHorizon),
    PHASE22_EVALUATION_HORIZONS,
  );
  assert.deepEqual(result.pendingHorizons, []);
  assert.equal(result.outcomes[0].entryPrice, 100);
  assert.equal(result.outcomes[0].futurePrice, 101);
  assert.equal(result.outcomes[0].actualReturn, 1);
  assert.equal(result.outcomes[0].directionHit, true);
  assert.equal(result.outcomes[0].thresholdHit, true);
  assert.equal(result.outcomes[0].costAdjustedReturn, 0.8);
  assert.equal(result.outcomes[0].status, "resolved");
  assert.equal(result.outcomes[0].executionAllowed, false);
  assert.equal(result.outcomes[0].brokerWriteAllowed, false);
});

test("Phase22 leaves unavailable long horizons pending without inventing prices", () => {
  const result = evaluatePredictionAcrossHorizons(prediction(), candles(7), {
    symbol: "7203.T",
  });

  assert.deepEqual(
    result.outcomes.map((row) => row.evaluationHorizon),
    [1, 3, 5],
  );
  assert.deepEqual(result.pendingHorizons, [10, 20]);
});

test("Phase22 refuses cross-symbol fallback", () => {
  const result = evaluatePredictionAcrossHorizons(prediction(), candles(), {
    symbol: "6758.T",
  });

  assert.equal(result.rejected, true);
  assert.equal(result.reason, "SYMBOL_MISMATCH");
  assert.deepEqual(result.outcomes, []);
});

test("Batch evaluation touches only the requested symbol", () => {
  const result = evaluatePredictionsAcrossHorizons(
    [prediction(), prediction({ id: "other", symbol: "6758.T" })],
    "7203.T",
    candles(),
    { horizons: [1] },
  );

  assert.equal(result.outcomes.length, 1);
  assert.equal(result.outcomes[0].parentPredictionId, "prediction-1");
  assert.equal(result.outcomes[0].symbol, "7203.T");
  assert.equal(result.executionAllowed, false);
});

test("Duplicate trading timestamps are deduplicated before horizon counting", () => {
  const history = candles(4);
  history.splice(1, 0, { ...history[0], close: 999 });
  const result = evaluatePredictionAcrossHorizons(prediction(), history, {
    symbol: "7203.T",
    horizons: [1],
  });

  assert.equal(result.outcomes[0].futurePrice, 101);
});
