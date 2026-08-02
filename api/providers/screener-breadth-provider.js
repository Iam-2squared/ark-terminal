const DEFAULT_MAXIMUM_AGE_MS = 5 * 24 * 60 * 60 * 1000;
const FULL_FRESHNESS_MS = 2 * 24 * 60 * 60 * 1000;

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number(value) || 0));
}

function isoOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function resolveNow(now) {
  const value = typeof now === "function" ? now() : now;
  const timestamp = new Date(value).getTime();

  if (!Number.isFinite(timestamp)) {
    throw new TypeError("Screener breadth clock is invalid.");
  }

  return timestamp;
}

function freshnessConfidence(generatedAt, now, maximumAgeMs) {
  const generated = Date.parse(generatedAt);

  if (!Number.isFinite(generated)) return 50;

  const age = Math.max(0, now - generated);

  if (age <= FULL_FRESHNESS_MS) return 100;
  if (age <= maximumAgeMs) return 75;
  return 50;
}

function observationConfidence(entry, freshness) {
  const quality =
    finiteOrNull(entry.qualityScore) ??
    finiteOrNull(entry.dataCoverage) ??
    70;

  return Math.round(clamp(quality) * (freshness / 100));
}

function normalizeObservation(entry, meta, freshness) {
  if (!entry || entry.status !== "analyzed") return null;

  const symbol = String(entry.symbol || "").trim().toUpperCase();
  const changePercent = finiteOrNull(entry.dailyChangePercent);

  if (!symbol || changePercent === null) return null;

  return {
    symbol,
    sector: String(entry.sector || "").trim() || null,
    changePercent,
    volume: finiteOrNull(entry.volume),
    averageVolume: null,
    volumeRatio: finiteOrNull(entry.volumeRatio),
    turnover: null,
    turnoverRatio: null,
    aboveMa20: null,
    aboveMa50: null,
    newHigh: null,
    newLow: null,
    timestamp: isoOrNull(entry.scannedAt) || isoOrNull(meta.generatedAt),
    source: `ark-screener:${entry.source || meta.provider || "unknown"}`,
    confidence: observationConfidence(entry, freshness),
  };
}

function latestTimestamp(observations, fallback = null) {
  const timestamps = observations
    .map((item) => Date.parse(item.timestamp))
    .filter(Number.isFinite);

  return timestamps.length
    ? new Date(Math.max(...timestamps)).toISOString()
    : fallback;
}

export function createScreenerBreadthPayload(
  snapshot = {},
  {
    now = Date.now,
    maximumAgeMs = DEFAULT_MAXIMUM_AGE_MS,
  } = {},
) {
  const meta = snapshot?.meta || {};
  const generatedAt = isoOrNull(meta.generatedAt);
  const currentTime = resolveNow(now);
  const ageLimit = Math.max(1, Number(maximumAgeMs) || DEFAULT_MAXIMUM_AGE_MS);
  const freshness = freshnessConfidence(generatedAt, currentTime, ageLimit);
  const observationsBySymbol = new Map();

  for (const entry of Array.isArray(snapshot?.entries) ? snapshot.entries : []) {
    const observation = normalizeObservation(entry, meta, freshness);

    if (observation) {
      observationsBySymbol.set(observation.symbol, observation);
    }
  }

  const observations = [...observationsBySymbol.values()];
  const requestedCount = Math.max(
    observations.length,
    Math.floor(
      finiteOrNull(meta.universeCount) ??
        finiteOrNull(meta.analyzedCount) ??
        observations.length,
    ),
  );
  const coverage = requestedCount
    ? Math.round((observations.length / requestedCount) * 1_000) / 10
    : 0;
  const age = generatedAt
    ? Math.max(0, currentTime - Date.parse(generatedAt))
    : null;
  const status = !observations.length
    ? "unavailable"
    : age === null
      ? "partial"
      : age > ageLimit
        ? "stale"
        : "available";

  return {
    observations,
    expectedObservationCount: requestedCount,
    availableCount: observations.length,
    coverage,
    timestamp: latestTimestamp(observations, generatedAt),
    generatedAt,
    source: `ark-screener:${meta.provider || "unknown"}`,
    sourceBranch: meta.delivery?.sourceBranch || null,
    status,
    freshnessConfidence: freshness,
    executionAllowed: false,
    errors: [],
  };
}

export const ScreenerBreadthProviderInternals = Object.freeze({
  DEFAULT_MAXIMUM_AGE_MS,
  FULL_FRESHNESS_MS,
  finiteOrNull,
  isoOrNull,
  resolveNow,
  freshnessConfidence,
  observationConfidence,
  normalizeObservation,
  latestTimestamp,
});
