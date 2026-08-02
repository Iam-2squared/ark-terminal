import { resolvePredictions } from "../backtest/engine.js";
import {
  createHistoricalMarketSnapshotReference,
  restoreHistoricalMarketSnapshot,
} from "./historical-market-snapshot-model.js";
import {
  buildHistoricalMarketOutcomeTimeline,
  normalizeHistoricalOutcomeTimestamp,
} from "./historical-market-outcome-normalizer.js";
import { buildPredictionFeedbackRecords } from "./prediction-feedback-adapter.js";

export const HISTORICAL_MARKET_ACCURACY_VERSION =
  "historical-market-accuracy-v1";

function stringOrFallback(value, fallback = null) {
  const normalized = String(value ?? "").trim();
  return normalized || fallback;
}

function resolveMarketRegime(snapshot) {
  const value =
    snapshot.metadata?.marketRegime ??
    snapshot.reports?.marketSnapshot?.regime?.regime ??
    snapshot.reports?.marketSnapshot?.regime;

  return typeof value === "string" ? value : "未取得";
}

function baseReport(snapshot, timeline, evaluatedAt) {
  return {
    version: HISTORICAL_MARKET_ACCURACY_VERSION,
    snapshot: createHistoricalMarketSnapshotReference(snapshot),
    symbol: snapshot.symbol,
    asOf: snapshot.asOf,
    evaluatedAt,
    anchor: timeline.anchor
      ? {
          timestamp: snapshot.asOf,
          price: timeline.anchor.close,
          source: timeline.anchor.source,
        }
      : null,
    availableFutureSessions: timeline.availableFutureSessions,
    futureInformationIncluded: false,
    executionAllowed: false,
  };
}

function unavailableReport(snapshot, timeline, evaluatedAt, reason) {
  return {
    ...baseReport(snapshot, timeline, evaluatedAt),
    status: "unavailable",
    reason,
    inputPredictionCount: snapshot.predictions.length,
    recordCount: 0,
    resolvedCount: 0,
    pendingCount: 0,
    records: [],
  };
}

function historicalAudit(record, snapshot, timeline) {
  return {
    version: HISTORICAL_MARKET_ACCURACY_VERSION,
    snapshotId: snapshot.id,
    snapshotFingerprint: snapshot.contentFingerprint,
    featureTimestamp: snapshot.asOf,
    anchorTimestamp: snapshot.asOf,
    anchorPriceSource: timeline.anchor?.source ?? null,
    availableFutureSessions: timeline.availableFutureSessions,
    requiredFutureSessions: Number(record.period),
    outcomeTimestamp: record.resolvedAt ?? null,
    futureInformationIncluded: false,
  };
}

export function evaluateHistoricalMarketSnapshot({
  snapshot: suppliedSnapshot,
  history = [],
  predictionPrice = null,
  companyName = null,
  industry = null,
  market = null,
  evaluatedAt = Date.now(),
} = {}) {
  const snapshot = restoreHistoricalMarketSnapshot(suppliedSnapshot);
  const normalizedEvaluatedAt = normalizeHistoricalOutcomeTimestamp(
    evaluatedAt,
    "Historical accuracy evaluation timestamp",
  );
  const timeline = buildHistoricalMarketOutcomeTimeline({
    snapshot,
    history,
    predictionPrice,
    availableAt: normalizedEvaluatedAt,
  });

  if (!timeline.anchor) {
    return unavailableReport(
      snapshot,
      timeline,
      normalizedEvaluatedAt,
      "prediction_price_unavailable",
    );
  }

  const pending = buildPredictionFeedbackRecords({
    symbol: snapshot.symbol,
    companyName:
      stringOrFallback(companyName) ??
      stringOrFallback(snapshot.metadata?.companyName),
    industry:
      stringOrFallback(industry) ??
      stringOrFallback(snapshot.metadata?.industry),
    predictionPrice: timeline.anchor.close,
    featureSet: snapshot.features,
    predictions: snapshot.predictions,
    technicalFeatures: snapshot.metadata?.technicalFeatures ?? {},
    existingFactorScores: snapshot.metadata?.factorScores ?? {},
    marketRegime: resolveMarketRegime(snapshot),
    market:
      stringOrFallback(market) ??
      stringOrFallback(snapshot.metadata?.market, "未取得"),
    analysisTime: Date.parse(snapshot.asOf) / 1000,
    historicalSnapshot: snapshot,
  });

  if (pending.length === 0) {
    return unavailableReport(
      snapshot,
      timeline,
      normalizedEvaluatedAt,
      "evaluable_predictions_unavailable",
    );
  }

  const resolved = resolvePredictions(
    pending,
    snapshot.symbol,
    timeline.candles,
  ).records.map((record) => ({
    ...record,
    historicalAccuracyAudit: historicalAudit(record, snapshot, timeline),
    executionAllowed: false,
  }));
  const resolvedCount = resolved.filter(
    (record) => record.status === "resolved",
  ).length;
  const pendingCount = resolved.length - resolvedCount;
  const status =
    resolvedCount === resolved.length
      ? "resolved"
      : resolvedCount > 0
        ? "partial"
        : "pending";

  return {
    ...baseReport(snapshot, timeline, normalizedEvaluatedAt),
    status,
    reason: pendingCount > 0 ? "awaiting_future_sessions" : null,
    inputPredictionCount: snapshot.predictions.length,
    recordCount: resolved.length,
    resolvedCount,
    pendingCount,
    records: resolved,
  };
}

export const HistoricalMarketAccuracyEngineInternals = Object.freeze({
  stringOrFallback,
  resolveMarketRegime,
  baseReport,
  unavailableReport,
  historicalAudit,
});

export default evaluateHistoricalMarketSnapshot;
