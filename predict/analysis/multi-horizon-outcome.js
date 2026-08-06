import { BACKTEST_COSTS } from "../config.js";

export const PHASE22_EVALUATION_HORIZONS = Object.freeze([1, 3, 5, 10, 20]);
export const MULTI_HORIZON_OUTCOME_VERSION = "phase22-multi-horizon-outcome-v1";

function finite(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function normalizeSymbol(value) {
  return String(value ?? "").trim().toUpperCase();
}

function normalizeSignal(record) {
  const value = String(record?.decision?.action ?? record?.decision ?? record?.signal ?? record?.direction ?? "")
    .trim()
    .toUpperCase();

  if (["BUY", "LONG", "強気"].includes(value)) return "BUY";
  if (["SELL", "SHORT", "弱気"].includes(value)) return "SELL";
  return "NO_TRADE";
}

function normalizeCandles(candles = []) {
  return candles
    .filter((candle) => finite(candle?.time) && finite(candle?.close) && Number(candle.close) > 0)
    .map((candle) => ({ ...candle, time: Number(candle.time), close: Number(candle.close) }))
    .sort((left, right) => left.time - right.time)
    .filter((candle, index, rows) => index === 0 || candle.time !== rows[index - 1].time);
}

function roundTripCostPercent(costs = BACKTEST_COSTS) {
  const commission = Number(costs?.commissionBpsPerSide) || 0;
  const slippage = Number(costs?.slippageBpsPerSide) || 0;
  return (commission + slippage) * 2 * 0.01;
}

function thresholdPercent(record) {
  const candidates = [record?.evaluationThreshold, record?.thresholdPercent, record?.evaluationPolicy?.threshold];
  for (const candidate of candidates) {
    if (finite(candidate)) return Math.max(0, Number(candidate));
  }
  return 0;
}

function resolveOne(record, ordered, horizon, costs) {
  const analysisTime = Number(record.analysisTime);
  const startIndex = ordered.findIndex((candle) => candle.time >= analysisTime);

  if (startIndex < 0 || startIndex + horizon >= ordered.length) return null;

  const entryPrice = finite(record.predictionPrice)
    ? Number(record.predictionPrice)
    : Number(ordered[startIndex].close);
  const target = ordered[startIndex + horizon];

  if (!finite(entryPrice) || entryPrice <= 0 || !finite(target?.close)) return null;

  const futurePrice = Number(target.close);
  const actualReturn = ((futurePrice - entryPrice) / entryPrice) * 100;
  const signal = normalizeSignal(record);
  const directionHit = signal === "BUY" ? actualReturn > 0 : signal === "SELL" ? actualReturn < 0 : null;
  const threshold = thresholdPercent(record);
  const thresholdHit = signal === "BUY"
    ? actualReturn >= threshold
    : signal === "SELL"
      ? actualReturn <= -threshold
      : null;
  const grossStrategyReturn = signal === "BUY" ? actualReturn : signal === "SELL" ? -actualReturn : 0;
  const costAdjustedReturn = signal === "NO_TRADE"
    ? 0
    : grossStrategyReturn - roundTripCostPercent(costs ?? record.costAssumptions);

  return {
    id: `${record.id ?? `${normalizeSymbol(record.symbol)}-${analysisTime}`}:h${horizon}`,
    parentPredictionId: record.id ?? null,
    symbol: normalizeSymbol(record.symbol),
    signal,
    entryPrice,
    futurePrice,
    actualReturn,
    directionHit,
    thresholdHit,
    costAdjustedReturn,
    evaluationHorizon: horizon,
    analysisTime,
    outcomeTime: target.time,
    resolvedAt: new Date(target.time * 1000).toISOString(),
    marketRegime: record.marketRegime ?? record.marketEnvironment?.regime ?? "UNKNOWN",
    industry: record.industry ?? "UNKNOWN",
    confidence: record.confidence,
    status: "resolved",
    executionAllowed: false,
    brokerWriteAllowed: false,
    source: MULTI_HORIZON_OUTCOME_VERSION,
  };
}

export function evaluatePredictionAcrossHorizons(record, candles, options = {}) {
  if (!record || typeof record !== "object") throw new TypeError("Prediction record is required.");

  const requestedSymbol = normalizeSymbol(options.symbol ?? record.symbol);
  const recordSymbol = normalizeSymbol(record.symbol);

  if (!requestedSymbol || requestedSymbol !== recordSymbol) {
    return {
      version: MULTI_HORIZON_OUTCOME_VERSION,
      outcomes: [],
      pendingHorizons: [...PHASE22_EVALUATION_HORIZONS],
      rejected: true,
      reason: "SYMBOL_MISMATCH",
      executionAllowed: false,
    };
  }

  const ordered = normalizeCandles(candles);
  const horizons = Array.isArray(options.horizons) && options.horizons.length
    ? [...new Set(options.horizons.map(Number).filter((value) => Number.isInteger(value) && value > 0))].sort((a, b) => a - b)
    : [...PHASE22_EVALUATION_HORIZONS];
  const outcomes = horizons
    .map((horizon) => resolveOne(record, ordered, horizon, options.costs))
    .filter(Boolean);
  const resolvedHorizons = new Set(outcomes.map((outcome) => outcome.evaluationHorizon));

  return {
    version: MULTI_HORIZON_OUTCOME_VERSION,
    symbol: recordSymbol,
    outcomes,
    pendingHorizons: horizons.filter((horizon) => !resolvedHorizons.has(horizon)),
    rejected: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
  };
}

export function evaluatePredictionsAcrossHorizons(records, symbol, candles, options = {}) {
  if (!Array.isArray(records)) throw new TypeError("Prediction records must be an array.");

  const normalizedSymbol = normalizeSymbol(symbol);
  const outcomes = [];
  const pending = [];

  for (const record of records) {
    if (normalizeSymbol(record?.symbol) !== normalizedSymbol) continue;
    const result = evaluatePredictionAcrossHorizons(record, candles, { ...options, symbol: normalizedSymbol });
    outcomes.push(...result.outcomes);
    if (result.pendingHorizons.length) {
      pending.push({ predictionId: record.id ?? null, horizons: result.pendingHorizons });
    }
  }

  return {
    version: MULTI_HORIZON_OUTCOME_VERSION,
    symbol: normalizedSymbol,
    outcomes,
    pending,
    executionAllowed: false,
    brokerWriteAllowed: false,
  };
}

export const MultiHorizonOutcomeInternals = Object.freeze({
  normalizeSymbol,
  normalizeSignal,
  normalizeCandles,
  roundTripCostPercent,
  thresholdPercent,
});

export default evaluatePredictionAcrossHorizons;
