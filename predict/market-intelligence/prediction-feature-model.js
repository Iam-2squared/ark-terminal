export const PREDICTION_FEATURE_SCHEMA_VERSION = 1;
export const PREDICTION_FEATURE_VERSION = "market-intelligence-features-v1";

export const PREDICTION_FEATURE_KEYS = Object.freeze([
  "marketScore",
  "breadth",
  "liquidity",
  "volatility",
  "macro",
  "newsScore",
  "sectorStrength",
  "momentum",
  "fearGreed",
  "compositeAI",
]);

export const PREDICTION_FEATURE_POLARITIES = Object.freeze({
  marketScore: "supportive",
  breadth: "supportive",
  liquidity: "supportive",
  volatility: "risk",
  macro: "supportive",
  newsScore: "supportive",
  sectorStrength: "supportive",
  momentum: "supportive",
  fearGreed: "supportive",
  compositeAI: "supportive",
});

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number(value)));
}

function isoTimestamp(value, label = "Prediction feature timestamp") {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    throw new TypeError(`${label} is invalid.`);
  }

  return date.toISOString();
}

function normalizeFeatureDetail(key, detail = {}) {
  const score = finiteOrNull(detail?.score);
  const confidence =
    score === null ? 0 : clamp(finiteOrNull(detail?.confidence) ?? 0);
  const coverage =
    score === null ? 0 : clamp(finiteOrNull(detail?.coverage) ?? 100);

  return Object.freeze({
    key,
    score:
      score === null ? null : Math.round(clamp(score) * 100) / 100,
    confidence: Math.round(confidence * 10) / 10,
    coverage: Math.round(coverage * 10) / 10,
    available: score !== null && confidence > 0,
    polarity: PREDICTION_FEATURE_POLARITIES[key],
    source: String(detail?.source || "unknown"),
    sourceTimestamp: detail?.sourceTimestamp
      ? isoTimestamp(detail.sourceTimestamp, `${key} source timestamp`)
      : null,
  });
}

function featureSetStatus(values, coverage) {
  if (values.compositeAI === null) return "unavailable";
  if (coverage < 70) return "partial";
  return "ready";
}

export function createPredictionFeatureSet({
  details = {},
  confidence = 0,
  coverage = 0,
  timestamp,
} = {}) {
  const normalizedDetails = Object.freeze(
    Object.fromEntries(
      PREDICTION_FEATURE_KEYS.map((key) => [
        key,
        normalizeFeatureDetail(key, details[key]),
      ]),
    ),
  );
  const values = Object.freeze(
    Object.fromEntries(
      PREDICTION_FEATURE_KEYS.map((key) => [
        key,
        normalizedDetails[key].score,
      ]),
    ),
  );
  const availability = Object.freeze(
    Object.fromEntries(
      PREDICTION_FEATURE_KEYS.map((key) => [
        key,
        normalizedDetails[key].available,
      ]),
    ),
  );
  const normalizedCoverage = Math.round(clamp(coverage) * 10) / 10;

  return Object.freeze({
    schemaVersion: PREDICTION_FEATURE_SCHEMA_VERSION,
    version: PREDICTION_FEATURE_VERSION,
    ...values,
    values,
    details: normalizedDetails,
    availability,
    availableCount: Object.values(availability).filter(Boolean).length,
    requestedCount: PREDICTION_FEATURE_KEYS.length,
    confidence: Math.round(clamp(confidence) * 10) / 10,
    coverage: normalizedCoverage,
    timestamp: isoTimestamp(timestamp),
    status: featureSetStatus(values, normalizedCoverage),
    isProbability: false,
  });
}

export const PredictionFeatureModelInternals = Object.freeze({
  finiteOrNull,
  clamp,
  normalizeFeatureDetail,
});

export default createPredictionFeatureSet;
