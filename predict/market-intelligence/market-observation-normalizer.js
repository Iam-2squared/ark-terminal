function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function nonNegativeOrNull(value) {
  const number = finiteOrNull(value);
  return number !== null && number >= 0 ? number : null;
}

function positiveOrNull(value) {
  const number = finiteOrNull(value);
  return number !== null && number > 0 ? number : null;
}

function booleanOrNull(value) {
  if (value === true || value === false) return value;
  if (value === 1 || value === "1" || value === "true") return true;
  if (value === 0 || value === "0" || value === "false") return false;
  return null;
}

function timestampOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const numeric = finiteOrNull(value);
  const timestamp =
    numeric !== null && numeric < 1_000_000_000_000
      ? numeric * 1000
      : value;
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function clampConfidence(value) {
  const number = finiteOrNull(value);
  return Math.round(Math.min(100, Math.max(0, number ?? 100)));
}

function ratioOrDerived(ratio, value, average) {
  const direct = nonNegativeOrNull(ratio);

  if (direct !== null) {
    return direct;
  }

  if (value === null || average === null) {
    return null;
  }

  return Math.round((value / average) * 1_000_000) / 1_000_000;
}

function normalizedText(value, fallback = null) {
  const text = String(value ?? "").trim();
  return text || fallback;
}

export function normalizeMarketObservation(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("Market observation must be an object.");
  }

  const symbol = normalizedText(input.symbol)?.toUpperCase();

  if (!symbol) {
    throw new TypeError("Market observation symbol is required.");
  }

  const volume = nonNegativeOrNull(input.volume);
  const averageVolume = positiveOrNull(
    input.averageVolume ?? input.avgVolume,
  );
  const turnover = nonNegativeOrNull(input.turnover);
  const averageTurnover = positiveOrNull(
    input.averageTurnover ?? input.avgTurnover,
  );

  return Object.freeze({
    symbol,
    sector: normalizedText(input.sector ?? input.industry),
    changePercent: finiteOrNull(input.changePercent),
    volume,
    averageVolume,
    volumeRatio: ratioOrDerived(input.volumeRatio, volume, averageVolume),
    turnover,
    averageTurnover,
    turnoverRatio: ratioOrDerived(
      input.turnoverRatio,
      turnover,
      averageTurnover,
    ),
    aboveMa20: booleanOrNull(input.aboveMa20),
    aboveMa50: booleanOrNull(input.aboveMa50),
    newHigh: booleanOrNull(input.newHigh),
    newLow: booleanOrNull(input.newLow),
    timestamp: timestampOrNull(input.timestamp),
    source: normalizedText(input.source, "unknown"),
    confidence: clampConfidence(input.confidence),
  });
}

export function normalizeMarketObservations(inputs = []) {
  if (!Array.isArray(inputs)) {
    throw new TypeError("Market observations must be an array.");
  }

  const observations = new Map();

  for (const input of inputs) {
    const observation = normalizeMarketObservation(input);
    observations.set(observation.symbol, observation);
  }

  return [...observations.values()];
}

export function resolveExpectedObservationCount(
  observations,
  expectedCount = null,
) {
  const actualCount = Array.isArray(observations) ? observations.length : 0;
  const requested = finiteOrNull(expectedCount);

  if (requested === null || requested < 0) {
    return actualCount;
  }

  return Math.max(actualCount, Math.floor(requested));
}

export function resolveLatestObservationTimestamp(observations) {
  if (!Array.isArray(observations)) {
    throw new TypeError("Normalized market observations must be an array.");
  }

  const timestamps = observations
    .map((observation) => Date.parse(observation?.timestamp))
    .filter(Number.isFinite);

  return timestamps.length
    ? new Date(Math.max(...timestamps)).toISOString()
    : null;
}

export function summarizeObservationCoverage(
  observations,
  predicate = () => true,
  { expectedCount = null } = {},
) {
  if (!Array.isArray(observations)) {
    throw new TypeError("Normalized market observations must be an array.");
  }

  if (typeof predicate !== "function") {
    throw new TypeError("Market observation predicate must be a function.");
  }

  const requestedCount = resolveExpectedObservationCount(
    observations,
    expectedCount,
  );
  const items = observations.filter(
    (observation) => observation.confidence > 0 && predicate(observation),
  );
  const availableCount = items.length;
  const coverage =
    requestedCount > 0 ? (availableCount / requestedCount) * 100 : 0;
  const sourceConfidence =
    availableCount > 0
      ? items.reduce((total, item) => total + item.confidence, 0) /
        availableCount
      : 0;

  return {
    items,
    availableCount,
    requestedCount,
    coverage: Math.round(coverage * 10) / 10,
    sourceConfidence: Math.round(sourceConfidence * 10) / 10,
    confidence:
      Math.round(sourceConfidence * (coverage / 100) * 10) / 10,
  };
}

export const MarketObservationNormalizerInternals = Object.freeze({
  finiteOrNull,
  booleanOrNull,
  timestampOrNull,
  ratioOrDerived,
});

export default normalizeMarketObservations;
