export const FEATURE_INTELLIGENCE_V1 = "feature-intelligence-v1";

function finite(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function mean(values = []) {
  const valid = values.map((value) => finite(value)).filter((value) => value !== null);
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : null;
}

function stdDev(values = []) {
  const avg = mean(values);
  if (avg === null) return null;
  const valid = values.map((value) => finite(value)).filter((value) => value !== null);
  return Math.sqrt(valid.reduce((sum, value) => sum + (value - avg) ** 2, 0) / valid.length);
}

function correlation(left = [], right = []) {
  const pairs = left.map((value, index) => [finite(value), finite(right[index])])
    .filter(([a, b]) => a !== null && b !== null);
  if (pairs.length < 2) return null;
  const xs = pairs.map(([a]) => a);
  const ys = pairs.map(([, b]) => b);
  const xMean = mean(xs);
  const yMean = mean(ys);
  const numerator = pairs.reduce((sum, [x, y]) => sum + (x - xMean) * (y - yMean), 0);
  const denominator = Math.sqrt(
    pairs.reduce((sum, [x]) => sum + (x - xMean) ** 2, 0) *
    pairs.reduce((sum, [, y]) => sum + (y - yMean) ** 2, 0),
  );
  return denominator ? numerator / denominator : null;
}

function volumeProfile(rows = [], bucketSize = 10) {
  const buckets = new Map();
  for (const row of rows) {
    const price = finite(row?.price ?? row?.close);
    const volume = finite(row?.volume, 0);
    if (price === null || volume <= 0) continue;
    const bucket = Math.floor(price / bucketSize) * bucketSize;
    buckets.set(bucket, (buckets.get(bucket) ?? 0) + volume);
  }
  return [...buckets.entries()]
    .map(([price, volume]) => ({ price, volume }))
    .sort((a, b) => b.volume - a.volume);
}

export function buildFeatureIntelligence({
  candles = [],
  benchmarkReturns = [],
  sectorReturns = {},
  breadth = {},
  macro = {},
  asOf = null,
} = {}) {
  const returns = candles.map((row, index) => {
    if (index === 0) return null;
    const previous = finite(candles[index - 1]?.close);
    const current = finite(row?.close);
    return previous && current !== null ? (current - previous) / previous : null;
  }).filter((value) => value !== null);
  const volatility = stdDev(returns);
  const profile = volumeProfile(candles);
  const correlations = {
    benchmark: correlation(returns, benchmarkReturns),
    sectors: Object.fromEntries(Object.entries(sectorReturns).map(([name, values]) => [name, correlation(returns, values)])),
  };
  const advancers = finite(breadth.advancers, 0);
  const decliners = finite(breadth.decliners, 0);
  const breadthRatio = decliners > 0 ? advancers / decliners : advancers > 0 ? Infinity : 0;
  const rotation = Object.entries(sectorReturns)
    .map(([sector, values]) => ({ sector, return: mean(values) ?? 0 }))
    .sort((a, b) => b.return - a.return);
  const invalidRows = candles.filter((row) => finite(row?.close) === null || finite(row?.volume) === null).length;
  const futureLeakDetected = asOf
    ? candles.some((row) => row?.timestamp && Date.parse(row.timestamp) > Date.parse(asOf))
    : false;

  return {
    version: FEATURE_INTELLIGENCE_V1,
    generatedAt: new Date().toISOString(),
    status: futureLeakDetected ? "BLOCKED" : invalidRows ? "DEGRADED" : "READY",
    features: {
      volatility,
      volatilityRegime: volatility === null ? "UNKNOWN" : volatility >= 0.03 ? "HIGH" : volatility >= 0.015 ? "NORMAL" : "LOW",
      volumeProfile: profile,
      pointOfControl: profile[0] ?? null,
      marketBreadth: { advancers, decliners, ratio: breadthRatio },
      sectorRotation: rotation,
      correlations,
      macro: { ...macro },
    },
    quality: {
      sampleSize: candles.length,
      invalidRows,
      futureLeakDetected,
    },
    productionUpdateAllowed: false,
  };
}

export default buildFeatureIntelligence;
