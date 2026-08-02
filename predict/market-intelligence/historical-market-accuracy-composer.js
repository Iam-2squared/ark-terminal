import { summarizePerformance } from "../backtest/engine.js";
import { composeAccuracyDashboardData } from "../analysis/accuracy-dashboard-data-composer.js";
import { summarizeWalkForwardAudit } from "../analysis/walk-forward-accuracy-audit.js";
import { buildMachineLearningDataset } from "../learning/dataset.js";
import {
  buildPredictionWeightMetrics,
} from "./prediction-feedback-adapter.js";
import { normalizeHistoricalOutcomeTimestamp } from "./historical-market-outcome-normalizer.js";

export const HISTORICAL_MARKET_ACCURACY_COMPOSER_VERSION =
  "historical-market-accuracy-composer-v1";

function isMarketIntelligenceRecord(record) {
  return Boolean(
    record &&
      (record.source === "market-intelligence-v1" ||
        record.marketIntelligenceSnapshot),
  );
}

function timestampAtOrBefore(value, cutoff) {
  if (value === null || value === undefined || value === "") return false;

  try {
    return (
      Date.parse(normalizeHistoricalOutcomeTimestamp(value)) <=
      Date.parse(cutoff)
    );
  } catch {
    return false;
  }
}

function recordVisibleAt(record, cutoff) {
  const featureTimestamp =
    record.analysisTime ??
    record.createdAt ??
    record.marketIntelligenceSnapshot?.asOf;

  if (!timestampAtOrBefore(featureTimestamp, cutoff)) return false;
  if (record.status !== "resolved") return true;

  return timestampAtOrBefore(record.resolvedAt, cutoff);
}

function sameResolvedOutcome(first, second) {
  if (first.status !== "resolved" || second.status !== "resolved") return true;

  return (
    Number(first.actualPrice) === Number(second.actualPrice) &&
    Number(first.actualReturn) === Number(second.actualReturn) &&
    String(first.resolvedAt) === String(second.resolvedAt)
  );
}

function selectRecord(existing, candidate) {
  const existingFingerprint =
    existing.marketIntelligenceSnapshot?.contentFingerprint ?? null;
  const candidateFingerprint =
    candidate.marketIntelligenceSnapshot?.contentFingerprint ?? null;

  if (
    existingFingerprint &&
    candidateFingerprint &&
    existingFingerprint !== candidateFingerprint
  ) {
    throw new RangeError(
      "Historical accuracy record conflicts with its snapshot fingerprint.",
    );
  }

  if (!sameResolvedOutcome(existing, candidate)) {
    throw new RangeError(
      "Historical accuracy record cannot rewrite a resolved outcome.",
    );
  }

  if (existing.status === "resolved" && candidate.status !== "resolved") {
    return existing;
  }

  return candidate;
}

export function mergeHistoricalMarketAccuracyRecords(
  existingRecords = [],
  evaluationReports = [],
) {
  if (!Array.isArray(existingRecords) || !Array.isArray(evaluationReports)) {
    throw new TypeError("Historical accuracy records and reports must be arrays.");
  }

  const records = [
    ...existingRecords.filter(isMarketIntelligenceRecord),
    ...evaluationReports.flatMap((report) =>
      Array.isArray(report?.records) ? report.records : [],
    ),
  ];
  const merged = new Map();

  for (const record of records) {
    const id = String(record?.id ?? "").trim();
    if (!id) throw new TypeError("Historical accuracy record id is required.");
    const existing = merged.get(id);
    merged.set(id, existing ? selectRecord(existing, record) : record);
  }

  return [...merged.values()].sort(
    (first, second) =>
      Number(first.analysisTime) - Number(second.analysisTime) ||
      Number(first.period) - Number(second.period) ||
      String(first.id).localeCompare(String(second.id)),
  );
}

function confidenceValue(record) {
  const value = Number(record.confidence?.score ?? record.confidence);
  return Number.isFinite(value) ? value : 0;
}

function directionToAction(direction) {
  if (["強気", "上昇", "BUY"].includes(direction)) return "BUY";
  if (["弱気", "下落", "SELL"].includes(direction)) return "SELL";
  return "HOLD";
}

function actualDirection(label) {
  if (label === "上昇") return "UP";
  if (label === "下落") return "DOWN";
  return "FLAT";
}

function accuracyRow(record) {
  const action = directionToAction(record.direction);

  return {
    id: record.id,
    symbol: record.symbol,
    date: record.resolvedAt,
    timestamp: record.resolvedAt,
    signal: action,
    action,
    actual: actualDirection(record.actualLabel),
    correct: record.hit,
    confidence: confidenceValue(record),
    profit: Number(record.strategyReturn) || 0,
    return: Number(record.strategyReturn) || 0,
    period: Number(record.period),
    snapshot: record.marketIntelligenceSnapshot ?? null,
    executionAllowed: false,
  };
}

function walkForwardRow(record) {
  return {
    symbol: record.symbol,
    entryDate:
      record.marketIntelligenceSnapshot?.asOf ?? record.createdAt ?? null,
    exitDate: record.resolvedAt ?? null,
    horizon: Number(record.period),
    entryPrice: Number(record.predictionPrice),
    exitPrice: Number(record.actualPrice),
    action: directionToAction(record.direction),
    predictedDirection:
      directionToAction(record.direction) === "BUY"
        ? "UP"
        : directionToAction(record.direction) === "SELL"
          ? "DOWN"
          : "FLAT",
    actualDirection: actualDirection(record.actualLabel),
    correct: record.hit === true,
    score: Number(record.score),
    confidence: confidenceValue(record),
    returnPercent: Number(record.actualReturn),
    strategyReturn: Number(record.strategyReturn),
    snapshot: record.marketIntelligenceSnapshot ?? null,
    executionAllowed: false,
  };
}

export function composeHistoricalMarketAccuracy({
  evaluationReports = [],
  existingRecords = [],
  generatedAt = Date.now(),
} = {}) {
  if (!Array.isArray(evaluationReports) || !Array.isArray(existingRecords)) {
    throw new TypeError("Historical accuracy reports and records must be arrays.");
  }

  const normalizedGeneratedAt = normalizeHistoricalOutcomeTimestamp(
    generatedAt,
    "Historical accuracy composition timestamp",
  );
  const visibleExistingRecords = existingRecords.filter((record) =>
    recordVisibleAt(record, normalizedGeneratedAt),
  );
  const evaluationRecordCount = evaluationReports.reduce(
    (sum, report) =>
      sum + (Array.isArray(report?.records) ? report.records.length : 0),
    0,
  );
  const visibleEvaluationReports = evaluationReports.map((report) => ({
    ...report,
    records: Array.isArray(report?.records)
      ? report.records.filter((record) =>
          recordVisibleAt(record, normalizedGeneratedAt),
        )
      : [],
  }));
  const visibleEvaluationRecordCount = visibleEvaluationReports.reduce(
    (sum, report) => sum + report.records.length,
    0,
  );
  const records = mergeHistoricalMarketAccuracyRecords(
    visibleExistingRecords,
    visibleEvaluationReports,
  );
  const resolvedRecords = records.filter(
    (record) => record.status === "resolved",
  );
  const pendingRecords = records.filter(
    (record) => record.status !== "resolved",
  );
  const actionableRecords = resolvedRecords.filter(
    (record) => record.hit === true || record.hit === false,
  );
  const accuracyRows = actionableRecords.map(accuracyRow);
  const walkForwardPredictions = actionableRecords.map(walkForwardRow);
  const walkForward = {
    version: "historical-market-walk-forward-v1",
    generatedAt: normalizedGeneratedAt,
    predictions: walkForwardPredictions,
    summary: summarizeWalkForwardAudit(walkForwardPredictions),
    futureInformationIncluded: false,
    executionAllowed: false,
  };
  const dashboard = composeAccuracyDashboardData({
    rows: accuracyRows,
    walkForward,
    options: {
      generatedAt: normalizedGeneratedAt,
      source: HISTORICAL_MARKET_ACCURACY_COMPOSER_VERSION,
    },
  });
  const learningDataset = buildMachineLearningDataset(resolvedRecords, {
    generatedAt: normalizedGeneratedAt,
  });

  return {
    version: HISTORICAL_MARKET_ACCURACY_COMPOSER_VERSION,
    generatedAt: normalizedGeneratedAt,
    status:
      resolvedRecords.length > 0
        ? "ready"
        : records.length > 0
          ? "pending"
          : "empty",
    records,
    resolvedRecords,
    pendingRecords,
    accuracyRows,
    dashboard: {
      ...dashboard,
      executionAllowed: false,
    },
    walkForward,
    performance: summarizePerformance(records),
    weightMetrics: buildPredictionWeightMetrics(resolvedRecords),
    learningDataset,
    audit: {
      snapshotIds: [
        ...new Set(
          records
            .map((record) => record.marketIntelligenceSnapshot?.id)
            .filter(Boolean),
        ),
      ],
      recordCount: records.length,
      resolvedCount: resolvedRecords.length,
      pendingCount: pendingRecords.length,
      actionableCount: actionableRecords.length,
      excludedFutureRecordCount:
        existingRecords.length -
        visibleExistingRecords.length +
        evaluationRecordCount -
        visibleEvaluationRecordCount,
      futureInformationIncluded: false,
    },
    executionAllowed: false,
  };
}

export const HistoricalMarketAccuracyComposerInternals = Object.freeze({
  isMarketIntelligenceRecord,
  timestampAtOrBefore,
  recordVisibleAt,
  sameResolvedOutcome,
  selectRecord,
  confidenceValue,
  directionToAction,
  actualDirection,
  accuracyRow,
  walkForwardRow,
});

export default composeHistoricalMarketAccuracy;
