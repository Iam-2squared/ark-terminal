import { calculateAccuracyMetrics, normalizeAccuracyRows } from "./accuracy-metrics.js";
import { calculateConfidenceCalibration } from "./accuracy-confidence-calibration.js";
import { calculateRiskAdjustedMetrics } from "./risk-adjusted-metrics.js";

export const ACCURACY_DASHBOARD_V6_VERSION = "accuracy-dashboard-v6";
export const MARKET_REGIMES = Object.freeze([
  "BULL",
  "BEAR",
  "RANGE",
  "HIGH_VOLATILITY",
  "LOW_VOLATILITY",
]);

function finite(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function numberOrNull(value) {
  return finite(value) ? Number(value) : null;
}

function readReturn(row) {
  const candidates = [
    row?.costAdjustedReturn,
    row?.strategyReturn,
    row?.profit,
    row?.pnl,
    row?.actualReturn,
    row?.returnPercent,
  ];
  for (const candidate of candidates) {
    if (finite(candidate)) return Number(candidate);
  }
  return null;
}

function readConfidence(row) {
  const candidates = [row?.confidence?.score, row?.confidenceScore, row?.confidence, row?.probability];
  for (const candidate of candidates) {
    if (!finite(candidate)) continue;
    const value = Number(candidate);
    return Math.min(1, Math.max(0, value > 1 ? value / 100 : value));
  }
  return null;
}

function readRegime(row) {
  const value = String(row?.marketRegime ?? row?.marketEnvironment?.regime ?? row?.regime ?? "UNKNOWN")
    .trim()
    .toUpperCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");
  return MARKET_REGIMES.includes(value) ? value : "UNKNOWN";
}

function readHorizon(row) {
  const value = Number(row?.evaluationHorizon ?? row?.period ?? row?.holdingPeriod);
  return Number.isInteger(value) && value > 0 ? value : null;
}

function readIndustry(row) {
  return String(row?.industry ?? row?.sector ?? "UNKNOWN").trim() || "UNKNOWN";
}

function readSymbol(row) {
  return String(row?.symbol ?? row?.ticker ?? row?.code ?? "UNKNOWN").trim().toUpperCase() || "UNKNOWN";
}

function median(values) {
  if (!values.length) return null;
  const ordered = [...values].sort((a, b) => a - b);
  const middle = Math.floor(ordered.length / 2);
  return ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
}

function wilsonInterval(correct, total, z = 1.96) {
  if (!total) return { lower: null, upper: null, confidenceLevel: 0.95 };
  const p = correct / total;
  const z2 = z ** 2;
  const denominator = 1 + z2 / total;
  const center = (p + z2 / (2 * total)) / denominator;
  const margin = (z / denominator) * Math.sqrt((p * (1 - p) + z2 / (4 * total)) / total);
  return {
    lower: Math.max(0, center - margin),
    upper: Math.min(1, center + margin),
    confidenceLevel: 0.95,
  };
}

function enrichMetrics(rows) {
  const adapted = rows.map((row) => ({
    ...row,
    signal: row.signal ?? row.decision?.action ?? row.direction,
    profit: readReturn(row),
    correct: typeof row.directionHit === "boolean" ? row.directionHit : row.correct ?? row.hit,
    resolved: row.status === "resolved" || row.resolved === true,
  }));
  const metrics = calculateAccuracyMetrics(adapted);
  const returns = adapted.map(readReturn).filter((value) => value !== null);
  const riskAdjusted = calculateRiskAdjustedMetrics(returns);
  const confidenceInterval = wilsonInterval(metrics.correct, metrics.total);

  return {
    sampleCount: metrics.total,
    accuracy: metrics.accuracy,
    accuracyPercent: metrics.accuracyPercent,
    confidenceInterval,
    buyAccuracy: metrics.buy.winRate,
    sellAccuracy: metrics.sell.winRate,
    profitFactor: metrics.profitFactor,
    averageReturn: returns.length ? returns.reduce((sum, value) => sum + value, 0) / returns.length : null,
    medianReturn: median(returns),
    maxDrawdown: metrics.maxDrawdown,
    sharpe: numberOrNull(riskAdjusted.sharpe ?? riskAdjusted.sharpeRatio),
    tradeWinRate: metrics.trades.winRate,
    exclusions: metrics.excluded,
  };
}

function groupMetrics(rows, selector) {
  const groups = new Map();
  for (const row of rows) {
    const key = selector(row);
    if (key === null || key === undefined || key === "") continue;
    if (!groups.has(String(key))) groups.set(String(key), []);
    groups.get(String(key)).push(row);
  }
  return Object.fromEntries(
    [...groups.entries()]
      .sort(([left], [right]) => left.localeCompare(right, undefined, { numeric: true }))
      .map(([key, values]) => [key, enrichMetrics(values)]),
  );
}

function confidenceBucket(row) {
  const confidence = readConfidence(row);
  if (confidence === null) return "UNKNOWN";
  const lower = Math.min(90, Math.floor(confidence * 10) * 10);
  const upper = lower === 90 ? 100 : lower + 10;
  return `${lower}-${upper}%`;
}

export function buildAccuracyDashboardV6({ rows = [], options = {} } = {}) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");

  const normalized = normalizeAccuracyRows(rows.map((row) => ({
    ...row,
    signal: row.signal ?? row.decision?.action ?? row.direction,
    profit: readReturn(row),
    correct: typeof row.directionHit === "boolean" ? row.directionHit : row.correct ?? row.hit,
    resolved: row.status === "resolved" || row.resolved === true,
  })));
  const eligible = normalized.filter((row) => row.accuracyEligible);
  const highConfidenceThreshold = finite(options.highConfidenceThreshold)
    ? Math.min(1, Math.max(0, Number(options.highConfidenceThreshold)))
    : 0.8;
  const highConfidenceRows = eligible.filter((row) => {
    const confidence = readConfidence(row);
    return confidence !== null && confidence >= highConfidenceThreshold;
  });
  const calibration = calculateConfidenceCalibration(eligible, options.confidenceCalibration);

  return {
    version: ACCURACY_DASHBOARD_V6_VERSION,
    generatedAt: options.generatedAt ?? new Date().toISOString(),
    overall: enrichMetrics(eligible),
    buy: enrichMetrics(eligible.filter((row) => row.signal === "BUY")),
    sell: enrichMetrics(eligible.filter((row) => row.signal === "SELL")),
    highConfidence: {
      threshold: highConfidenceThreshold,
      ...enrichMetrics(highConfidenceRows),
    },
    byHorizon: groupMetrics(eligible, readHorizon),
    bySymbol: groupMetrics(eligible, readSymbol),
    byIndustry: groupMetrics(eligible, readIndustry),
    byMarketRegime: groupMetrics(eligible, readRegime),
    byConfidenceBucket: groupMetrics(eligible, confidenceBucket),
    confidenceCalibration: calibration,
    calibrationError: calibration.expectedCalibrationError,
    brierScore: calibration.brierScore,
    sample: {
      source: rows.length,
      eligible: eligible.length,
      excluded: rows.length - eligible.length,
    },
    safety: {
      executionAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
    },
  };
}

export const AccuracyDashboardV6Internals = Object.freeze({
  readReturn,
  readConfidence,
  readRegime,
  readHorizon,
  readIndustry,
  readSymbol,
  median,
  wilsonInterval,
  confidenceBucket,
  enrichMetrics,
});

export default buildAccuracyDashboardV6;
