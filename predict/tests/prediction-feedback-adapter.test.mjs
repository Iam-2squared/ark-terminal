import test from "node:test";
import assert from "node:assert/strict";

import { resolvePredictions } from "../backtest/engine.js";
import { buildMachineLearningDataset } from "../learning/dataset.js";
import { optimizeWeights } from "../learning/weight-optimizer.js";
import {
  PREDICTION_FEATURE_KEYS,
  createPredictionFeatureSet,
} from "../market-intelligence/prediction-feature-model.js";
import { predictMultipleHorizons } from "../market-intelligence/multi-horizon-prediction-engine.js";
import {
  createHistoricalMarketSnapshot,
  createHistoricalMarketSnapshotReference,
} from "../market-intelligence/historical-market-snapshot-model.js";
import {
  buildPredictionFeedbackRecords,
  buildPredictionWeightMetrics,
  buildTradeMemoryMarketContext,
} from "../market-intelligence/prediction-feedback-adapter.js";

const TIMESTAMP = "2026-08-02T12:00:00Z";

function features(score = 80, volatility = 20) {
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

function feedback(score = 80, volatility = 20) {
  const featureSet = features(score, volatility);
  const predictions = predictMultipleHorizons(featureSet, { atrPercent: 2 });

  return buildPredictionFeedbackRecords({
    symbol: "7203.T",
    companyName: "Example",
    predictionPrice: 3000,
    featureSet,
    predictions,
    technicalFeatures: {
      schemaVersion: 1,
      values: { rsi: 55 },
      conditions: [],
    },
    marketRegime: "BULL",
  });
}

test("Feedback adapter creates five existing-schema prediction records", () => {
  const records = feedback();

  assert.equal(records.length, 5);
  assert.deepEqual(
    records.map((record) => record.period),
    [1, 3, 5, 10, 20],
  );
  assert.equal(records[0].source, "market-intelligence-v1");
  assert.equal(records[0].executionAllowed, false);
  assert.equal(records[0].decision.purpose, "forecast_evaluation");
  assert.equal(records[0].features.schemaVersion, 2);
  assert.equal(records[0].features.values.rsi, 55);
  assert.equal(records[0].features.marketIntelligence.values.marketScore, 80);
  assert.equal(records[0].factorScores.news, 80);
  assert.equal(records[0].factorScores.sentiment, 80);
});

test("Record ids are stable for symbol, timestamp and horizon", () => {
  const first = feedback();
  const second = feedback();

  assert.deepEqual(
    first.map((record) => record.id),
    second.map((record) => record.id),
  );
  assert.equal(new Set(first.map((record) => record.id)).size, 5);
});

test("Feedback records link to the exact point-in-time market snapshot", () => {
  const featureSet = features();
  const predictions = predictMultipleHorizons(featureSet, { atrPercent: 2 });
  const snapshot = createHistoricalMarketSnapshot({
    symbol: "7203.T",
    asOf: TIMESTAMP,
    capturedAt: TIMESTAMP,
    features: featureSet,
    predictions,
  });
  const records = buildPredictionFeedbackRecords({
    symbol: "7203.T",
    predictionPrice: 3000,
    featureSet,
    predictions,
    historicalSnapshot: snapshot,
  });

  assert.equal(records[0].marketIntelligenceSnapshot.id, snapshot.id);
  assert.equal(
    records[0].marketIntelligenceSnapshot.contentFingerprint,
    snapshot.contentFingerprint,
  );
  assert.equal(
    buildTradeMemoryMarketContext(records[0]).historicalSnapshot.id,
    snapshot.id,
  );

  const mismatched = {
    ...createHistoricalMarketSnapshotReference(snapshot),
    asOf: "2026-08-02T11:00:00Z",
  };

  assert.throws(
    () =>
      buildPredictionFeedbackRecords({
        symbol: "7203.T",
        predictionPrice: 3000,
        featureSet,
        predictions,
        historicalSnapshot: mismatched,
      }),
    /timestamp does not match/,
  );
});

test("Unavailable predictions are skipped instead of becoming zero scores", () => {
  const featureSet = createPredictionFeatureSet({
    details: {},
    timestamp: TIMESTAMP,
  });
  const records = buildPredictionFeedbackRecords({
    symbol: "7203.T",
    predictionPrice: 3000,
    featureSet,
    predictions: predictMultipleHorizons(featureSet),
  });

  assert.deepEqual(records, []);
});

test("Resolved feedback builds generic Weight Optimizer metrics", () => {
  const bullish = feedback()[0];
  const bearish = feedback(20, 80)[0];
  const metrics = buildPredictionWeightMetrics([
    {
      ...bullish,
      status: "resolved",
      actualLabel: "上昇",
      actualReturn: 5,
    },
    {
      ...bearish,
      status: "resolved",
      actualLabel: "下落",
      actualReturn: -4,
    },
  ]);

  assert.equal(metrics.sampleSize, 2);
  assert.equal(metrics.metrics.marketScore.winRate, 100);
  assert.equal(metrics.metrics.marketScore.averageReturnPercent, 4.5);
  assert.equal(metrics.metrics.volatility.winRate, 100);
  assert.equal(metrics.futureInformationIncluded, false);

  const optimization = optimizeWeights({
    currentWeights: { marketScore: 1 },
    learningResult: metrics,
  });

  assert.ok(
    optimization.suggestions.find(
      (suggestion) => suggestion.indicator === "marketScore",
    ).suggestedWeight > 1,
  );
});

test("Feedback records flow into Learning Dataset without future labels", () => {
  const record = {
    ...feedback()[0],
    status: "resolved",
    resolvedAt: "2026-08-03T12:00:00Z",
    actualLabel: "上昇",
    actualReturn: 3,
    hit: true,
  };
  const dataset = buildMachineLearningDataset([record]);

  assert.equal(dataset.rows[0].features.marketIntelligence.marketScore, 80);
  assert.equal(
    dataset.rows[0].audit.marketIntelligenceFeatureVersion,
    "market-intelligence-features-v1",
  );
  assert.equal(dataset.rows[0].audit.futureInformationIncluded, false);
});

test("Feedback records resolve through the existing accuracy evaluator", () => {
  const record = feedback()[0];
  const start = Number(record.analysisTime);
  const result = resolvePredictions([record], "7203.T", [
    { time: start, close: 3000 },
    { time: start + 86_400, close: 3100 },
  ]);

  assert.equal(result.changed, true);
  assert.equal(result.records[0].status, "resolved");
  assert.equal(result.records[0].actualLabel, "上昇");
  assert.equal(result.records[0].hit, true);
});

test("Trade Memory context is read-only metadata and inputs validate", () => {
  const context = buildTradeMemoryMarketContext(feedback()[0]);

  assert.equal(context.values.compositeAI, 80);
  assert.equal(context.prediction.horizon, 1);
  assert.equal(context.executionAllowed, false);
  assert.throws(
    () =>
      buildPredictionFeedbackRecords({
        symbol: "",
        predictionPrice: 3000,
        featureSet: features(),
      }),
    /symbol is required/,
  );
  assert.throws(
    () =>
      buildPredictionFeedbackRecords({
        symbol: "7203.T",
        predictionPrice: 0,
        featureSet: features(),
      }),
    /price must be positive/,
  );
});
