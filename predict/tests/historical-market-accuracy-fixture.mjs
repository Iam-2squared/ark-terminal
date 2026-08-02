import {
  PREDICTION_FEATURE_KEYS,
  createPredictionFeatureSet,
} from "../market-intelligence/prediction-feature-model.js";
import { predictMultipleHorizons } from "../market-intelligence/multi-horizon-prediction-engine.js";
import { createHistoricalMarketSnapshot } from "../market-intelligence/historical-market-snapshot-model.js";

export const HISTORICAL_ACCURACY_AS_OF = "2026-08-03T00:00:00.000Z";

export function createHistoricalAccuracyFeatureSet({
  asOf = HISTORICAL_ACCURACY_AS_OF,
  score = 80,
} = {}) {
  return createPredictionFeatureSet({
    details: Object.fromEntries(
      PREDICTION_FEATURE_KEYS.map((key) => [
        key,
        {
          score: key === "volatility" ? 20 : score,
          confidence: 100,
          coverage: 100,
          source: `fixture:${key}`,
          sourceTimestamp: asOf,
        },
      ]),
    ),
    confidence: 100,
    coverage: 100,
    timestamp: asOf,
  });
}

export function createHistoricalAccuracySnapshot({
  symbol = "7203.T",
  asOf = HISTORICAL_ACCURACY_AS_OF,
  predictionPrice = 100,
  includePredictionPrice = true,
} = {}) {
  const features = createHistoricalAccuracyFeatureSet({ asOf });
  const predictions = predictMultipleHorizons(features, { atrPercent: 2 });

  return createHistoricalMarketSnapshot({
    symbol,
    asOf,
    capturedAt: asOf,
    features,
    predictions,
    metadata: {
      ...(includePredictionPrice ? { predictionPrice } : {}),
      companyName: "Fixture Company",
      industry: "Technology",
      market: "JP",
      marketRegime: "BULL",
    },
  });
}

export function createHistoricalAccuracyHistory({
  symbol = "7203.T",
  asOf = HISTORICAL_ACCURACY_AS_OF,
  predictionPrice = 100,
  sessions = 25,
} = {}) {
  const start = Date.parse(asOf) / 1000;

  return Array.from({ length: sessions }, (_value, index) => ({
    time: start + (index + 1) * 86_400,
    close: predictionPrice + (index + 1) * 5,
    symbol,
  }));
}

export function historicalAccuracyEvaluationTime(
  sessions = 30,
  asOf = HISTORICAL_ACCURACY_AS_OF,
) {
  return new Date(Date.parse(asOf) + sessions * 86_400_000).toISOString();
}
