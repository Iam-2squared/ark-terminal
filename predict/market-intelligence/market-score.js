import {
  MARKET_DATA_STATUS,
  getMarketDataDefinition,
} from "./market-data-model.js";

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, value));
}

function round(value, digits = 2) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function isUsablePoint(point) {
  return Boolean(
    point &&
      (point.status === MARKET_DATA_STATUS.AVAILABLE ||
        point.status === MARKET_DATA_STATUS.STALE) &&
      finiteOrNull(point.price) !== null &&
      finiteOrNull(point.changePercent) !== null,
  );
}

function normalizeConfiguration(configuration) {
  if (Array.isArray(configuration)) {
    return configuration;
  }

  return Object.entries(configuration || {}).map(([symbol, options]) => ({
    symbol,
    ...(options || {}),
  }));
}

function indexPoints(points) {
  const indexed = new Map();

  for (const point of Array.isArray(points) ? points : []) {
    const definition = getMarketDataDefinition(point?.symbol);

    if (definition) {
      indexed.set(definition.symbol, point);
    }
  }

  return indexed;
}

export function scoreDirectionalChange(
  changePercent,
  { scale = 2, invert = false } = {},
) {
  const change = finiteOrNull(changePercent);
  const normalizedScale = Math.abs(finiteOrNull(scale) ?? 2);

  if (change === null || normalizedScale === 0) {
    return null;
  }

  const directional = clamp(change / normalizedScale, -1, 1);
  const rawScore = 50 + directional * 50;
  return round(invert ? 100 - rawScore : rawScore);
}

export function scoreMarketSeries(points, configuration) {
  const entries = normalizeConfiguration(configuration);
  const data = indexPoints(points);
  const requestedWeight = entries.reduce(
    (total, entry) => total + Math.max(0, finiteOrNull(entry.weight) ?? 1),
    0,
  );
  let availableWeight = 0;
  let effectiveWeight = 0;
  let weightedScore = 0;
  let weightedConfidence = 0;
  let availableCount = 0;

  const items = entries.map((entry) => {
    const definition = getMarketDataDefinition(entry.symbol);

    if (!definition) {
      throw new RangeError(`Unknown market score symbol: ${entry.symbol}`);
    }

    const point = data.get(definition.symbol) ?? null;
    const weight = Math.max(0, finiteOrNull(entry.weight) ?? 1);
    const available = isUsablePoint(point);

    if (!available) {
      return {
        symbol: definition.symbol,
        price: finiteOrNull(point?.price),
        score: null,
        weight,
        effectiveWeight: 0,
        changePercent: finiteOrNull(point?.changePercent),
        confidence: finiteOrNull(point?.confidence) ?? 0,
        status: point?.status ?? MARKET_DATA_STATUS.UNAVAILABLE,
        available: false,
      };
    }

    const confidence = clamp(finiteOrNull(point.confidence) ?? 0);
    const score = scoreDirectionalChange(point.changePercent, entry);
    const resolvedEffectiveWeight = weight * (confidence / 100);

    availableCount += 1;
    availableWeight += weight;
    effectiveWeight += resolvedEffectiveWeight;
    weightedScore += score * resolvedEffectiveWeight;
    weightedConfidence += confidence * weight;

    return {
      symbol: definition.symbol,
      price: Number(point.price),
      score,
      weight,
      effectiveWeight: round(resolvedEffectiveWeight, 4),
      changePercent: Number(point.changePercent),
      confidence,
      status: point.status,
      available: true,
    };
  });

  const coverage =
    requestedWeight > 0 ? (availableWeight / requestedWeight) * 100 : 0;
  const sourceConfidence =
    availableWeight > 0 ? weightedConfidence / availableWeight : 0;

  return {
    score: effectiveWeight > 0 ? round(weightedScore / effectiveWeight) : null,
    confidence: round(sourceConfidence * (coverage / 100), 1),
    coverage: round(coverage, 1),
    availableCount,
    requestedCount: entries.length,
    items,
  };
}

export function calculateCompositeMarketScore({
  indexes,
  macro,
  indexWeight = 70,
  macroWeight = 30,
} = {}) {
  const normalizedIndexWeight = Math.max(
    0,
    finiteOrNull(indexWeight) ?? 70,
  );
  const normalizedMacroWeight = Math.max(
    0,
    finiteOrNull(macroWeight) ?? 30,
  );
  return calculateWeightedScore([
    { key: "indexes", report: indexes, weight: normalizedIndexWeight },
    { key: "macro", report: macro, weight: normalizedMacroWeight },
  ]);
}

export function calculateWeightedScore(components = []) {
  if (!Array.isArray(components)) {
    throw new TypeError("Weighted score components must be an array.");
  }

  const configured = components.map((component, index) => ({
    key: String(component?.key ?? index),
    report: component?.report ?? component,
    weight: Math.max(0, finiteOrNull(component?.weight) ?? 1),
  }));
  const requestedWeight = configured.reduce(
    (total, component) => total + component.weight,
    0,
  );
  let availableWeight = 0;
  let effectiveWeight = 0;
  let weightedScore = 0;
  let weightedConfidence = 0;
  let weightedCoverage = 0;

  const resolvedComponents = configured.map(({ key, report, weight }) => {
    const rawScore = finiteOrNull(report?.score);
    const score = rawScore === null ? null : clamp(rawScore);
    const confidence = clamp(finiteOrNull(report?.confidence) ?? 0);
    const available = score !== null && confidence > 0 && weight > 0;
    const coverage = available
      ? clamp(finiteOrNull(report?.coverage) ?? 100)
      : 0;
    const resolvedEffectiveWeight = available
      ? weight * (confidence / 100)
      : 0;

    if (available) {
      availableWeight += weight;
      effectiveWeight += resolvedEffectiveWeight;
      weightedScore += score * resolvedEffectiveWeight;
      weightedConfidence += confidence * weight;
      weightedCoverage += coverage * weight;
    }

    return {
      key,
      score,
      confidence,
      coverage,
      weight,
      effectiveWeight: round(resolvedEffectiveWeight, 4),
      available,
    };
  });

  const coverage =
    requestedWeight > 0 ? (availableWeight / requestedWeight) * 100 : 0;
  const sourceConfidence =
    availableWeight > 0 ? weightedConfidence / availableWeight : 0;
  const dataCoverage =
    requestedWeight > 0 ? weightedCoverage / requestedWeight : 0;

  return {
    score: effectiveWeight > 0 ? round(weightedScore / effectiveWeight) : null,
    confidence: round(sourceConfidence * (coverage / 100), 1),
    coverage: round(dataCoverage, 1),
    components: resolvedComponents,
  };
}

export function scoreToSentiment(score) {
  const value = finiteOrNull(score);

  if (value === null) return "UNKNOWN";
  if (value >= 65) return "BULLISH";
  if (value <= 35) return "BEARISH";
  return "NEUTRAL";
}

export const MarketScoreInternals = Object.freeze({
  finiteOrNull,
  isUsablePoint,
  indexPoints,
});

export default calculateCompositeMarketScore;
