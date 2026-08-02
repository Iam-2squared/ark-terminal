import { createPredictionRecord } from "../backtest/storage.js";
import { PREDICTION_FEATURE_KEYS } from "./prediction-feature-model.js";
import {
  HISTORICAL_MARKET_SNAPSHOT_SCHEMA_VERSION,
  HISTORICAL_MARKET_SNAPSHOT_VERSION,
  createHistoricalMarketSnapshotReference,
} from "./historical-market-snapshot-model.js";

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function directionLabel(score, key) {
  const value = finiteOrNull(score);

  if (value === null) return null;
  const directional = key === "volatility" ? 100 - value : value;
  if (directional >= 55) return "上昇";
  if (directional <= 45) return "下落";
  return "中立";
}

function stableRecordId(symbol, analysisTime, horizon) {
  return [
    "market-intelligence",
    String(symbol || "unknown").toUpperCase(),
    Number(analysisTime),
    Number(horizon),
  ].join(":");
}

function normalizeAnalysisTime(value) {
  const number = finiteOrNull(value);

  if (number === null) return null;
  return number >= 1_000_000_000_000 ? number / 1000 : number;
}

function featureSnapshot(featureSet, technicalFeatures = {}) {
  return {
    schemaVersion: 2,
    capturedAt:
      normalizeAnalysisTime(technicalFeatures?.capturedAt) ??
      Date.parse(featureSet.timestamp) / 1000,
    values: {
      ...(technicalFeatures?.values || {}),
      ...featureSet.values,
    },
    conditions: Array.isArray(technicalFeatures?.conditions)
      ? [...technicalFeatures.conditions]
      : [],
    marketIntelligence: {
      schemaVersion: featureSet.schemaVersion,
      version: featureSet.version,
      capturedAt: featureSet.timestamp,
      values: { ...featureSet.values },
      availability: { ...featureSet.availability },
      confidence: featureSet.confidence,
      coverage: featureSet.coverage,
      isProbability: false,
    },
  };
}

function factorScores(featureSet, existing = {}) {
  const scores = Object.fromEntries(
    PREDICTION_FEATURE_KEYS.filter(
      (key) => finiteOrNull(featureSet.values[key]) !== null,
    ).map((key) => [key, Number(featureSet.values[key])]),
  );

  if (finiteOrNull(featureSet.values.newsScore) !== null) {
    scores.news = Number(featureSet.values.newsScore);
  }

  if (finiteOrNull(featureSet.values.fearGreed) !== null) {
    scores.sentiment = Number(featureSet.values.fearGreed);
  }

  return { ...existing, ...scores };
}

function predictionReasons(prediction) {
  return [...prediction.components]
    .filter((component) => component.available)
    .sort(
      (first, second) =>
        Math.abs(second.score - 50) * second.effectiveWeight -
        Math.abs(first.score - 50) * first.effectiveWeight,
    )
    .slice(0, 4)
    .map(
      (component) =>
        `${component.key}: ${Math.round(component.rawScore ?? component.score)}点`,
    );
}

function validateFeedbackInput({ symbol, predictionPrice, featureSet }) {
  if (!String(symbol || "").trim()) {
    throw new TypeError("Prediction feedback symbol is required.");
  }

  if (
    finiteOrNull(predictionPrice) === null ||
    Number(predictionPrice) <= 0
  ) {
    throw new TypeError("Prediction feedback price must be positive.");
  }

  if (!featureSet?.values || !featureSet?.timestamp) {
    throw new TypeError("Prediction feedback feature set is required.");
  }
}

function feedbackSnapshotReference(value, symbol, featureSet) {
  if (!value) return null;

  const supplied = value.reference ?? value.snapshot ?? value;
  const reference = supplied.features
    ? createHistoricalMarketSnapshotReference(supplied)
    : supplied;

  if (
    Number(reference?.schemaVersion) !==
      HISTORICAL_MARKET_SNAPSHOT_SCHEMA_VERSION ||
    reference?.version !== HISTORICAL_MARKET_SNAPSHOT_VERSION ||
    !String(reference?.id || "").trim() ||
    !String(reference?.contentFingerprint || "").trim() ||
    reference?.executionAllowed === true
  ) {
    throw new TypeError("Prediction feedback historical snapshot is invalid.");
  }

  if (String(reference.symbol || "").toUpperCase() !== String(symbol).toUpperCase()) {
    throw new RangeError(
      "Prediction feedback historical snapshot symbol does not match.",
    );
  }

  const snapshotTime = Date.parse(reference.asOf);
  const featureTime = Date.parse(featureSet.timestamp);

  if (
    !Number.isFinite(snapshotTime) ||
    !Number.isFinite(featureTime) ||
    snapshotTime !== featureTime
  ) {
    throw new RangeError(
      "Prediction feedback historical snapshot timestamp does not match.",
    );
  }

  return {
    id: reference.id,
    schemaVersion: reference.schemaVersion,
    version: reference.version,
    symbol: reference.symbol,
    asOf: reference.asOf,
    contentFingerprint: reference.contentFingerprint,
    executionAllowed: false,
  };
}

export function buildPredictionFeedbackRecords({
  symbol,
  companyName = null,
  industry = null,
  predictionPrice,
  featureSet,
  predictions = [],
  technicalFeatures = {},
  existingFactorScores = {},
  marketRegime = "未取得",
  market = "未取得",
  partition = null,
  analysisTime = null,
  historicalSnapshot = null,
  recordFactory = createPredictionRecord,
} = {}) {
  validateFeedbackInput({ symbol, predictionPrice, featureSet });

  if (typeof recordFactory !== "function") {
    throw new TypeError("Prediction feedback record factory must be a function.");
  }

  const resolvedAnalysisTime =
    normalizeAnalysisTime(analysisTime) ??
    Date.parse(featureSet.timestamp) / 1000;
  const snapshot = featureSnapshot(featureSet, technicalFeatures);
  const scores = factorScores(featureSet, existingFactorScores);
  const historicalSnapshotReference = feedbackSnapshotReference(
    historicalSnapshot,
    symbol,
    featureSet,
  );

  return (Array.isArray(predictions) ? predictions : [])
    .filter((prediction) => finiteOrNull(prediction?.score) !== null)
    .map((prediction) => {
      const record = recordFactory({
        symbol: String(symbol).toUpperCase(),
        companyName,
        industry,
        period: prediction.horizon,
        score: prediction.score,
        reasons: predictionReasons(prediction),
        predictionPrice,
        analysisTime: resolvedAnalysisTime,
        factorScores: scores,
        direction: prediction.direction,
        expectedMoveRange: prediction.expectedMoveRange,
        downsideRisk: prediction.downsideRisk,
        confidence: prediction.confidence,
        expectedReturn: prediction.expectedReturn,
        dataQuality: {
          status: featureSet.status,
          qualityScore: Math.min(featureSet.confidence, featureSet.coverage),
          missingRate: 100 - featureSet.coverage,
        },
        marketRegime,
        market,
        features: snapshot,
        partition,
        source: "market-intelligence-v1",
        modelVersion: prediction.modelVersion,
        evaluationPolicy: prediction.decision?.policy ?? null,
        evaluationThreshold: prediction.expectedMoveRange?.amplitude ?? null,
        decision: prediction.decision,
      });

      return {
        ...record,
        id: stableRecordId(symbol, resolvedAnalysisTime, prediction.horizon),
        createdAt: featureSet.timestamp,
        marketIntelligenceFactorScores: { ...featureSet.values },
        marketIntelligenceSnapshot: historicalSnapshotReference
          ? { ...historicalSnapshotReference }
          : null,
        executionAllowed: false,
      };
    });
}

function resolvedMarketRecords(records) {
  return (Array.isArray(records) ? records : []).filter(
    (record) =>
      record?.status === "resolved" &&
      ["上昇", "中立", "下落"].includes(record?.actualLabel) &&
      record?.features?.marketIntelligence?.values,
  );
}

export function buildPredictionWeightMetrics(records = []) {
  const eligible = resolvedMarketRecords(records);
  const metrics = Object.fromEntries(
    PREDICTION_FEATURE_KEYS.map((key) => {
      const samples = eligible
        .map((record) => ({
          record,
          predicted: directionLabel(
            record.features.marketIntelligence.values[key],
            key,
          ),
        }))
        .filter((sample) => sample.predicted && sample.predicted !== "中立");
      const correct = samples.filter(
        (sample) => sample.predicted === sample.record.actualLabel,
      ).length;
      const directionalReturns = samples
        .map((sample) => {
          const actualReturn = finiteOrNull(sample.record.actualReturn);
          if (actualReturn === null) return null;
          return sample.predicted === "上昇" ? actualReturn : -actualReturn;
        })
        .filter((value) => value !== null);
      const averageReturnPercent = directionalReturns.length
        ? directionalReturns.reduce((sum, value) => sum + value, 0) /
          directionalReturns.length
        : 0;

      return [
        key,
        {
          winRate: samples.length ? (correct / samples.length) * 100 : 50,
          averageReturnPercent,
          confidence: samples.length / (samples.length + 30),
          sampleSize: samples.length,
        },
      ];
    }),
  );

  return {
    metrics,
    sampleSize: eligible.length,
    source: "resolved-market-intelligence-predictions",
    futureInformationIncluded: false,
  };
}

export function buildTradeMemoryMarketContext(record = {}) {
  return {
    featureVersion:
      record?.features?.marketIntelligence?.version ?? null,
    values: {
      ...(record?.features?.marketIntelligence?.values || {}),
    },
    prediction: {
      horizon: finiteOrNull(record.period),
      score: finiteOrNull(record.score),
      direction: record.direction ?? null,
      confidence: finiteOrNull(record.confidence?.score ?? record.confidence),
    },
    featureTimestamp:
      record?.features?.marketIntelligence?.capturedAt ?? null,
    historicalSnapshot:
      record?.marketIntelligenceSnapshot ?? null,
    executionAllowed: false,
  };
}

export const PredictionFeedbackInternals = Object.freeze({
  directionLabel,
  stableRecordId,
  normalizeAnalysisTime,
  featureSnapshot,
  factorScores,
  predictionReasons,
  feedbackSnapshotReference,
});

export default buildPredictionFeedbackRecords;
