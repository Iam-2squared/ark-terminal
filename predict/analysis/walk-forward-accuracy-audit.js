const LABEL_POLICY_VERSION = "directional-label-policy-v2";
const JOIN_POLICY_VERSION = "symbol-session-join-v2";

function finiteNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function round(value, digits = 4) {
  const factor = 10 ** digits;
  return Math.round(finiteNumber(value) * factor) / factor;
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, finiteNumber(value)));
}

function normalizeSymbol(value) {
  return String(value ?? "").trim().toUpperCase();
}

function normalizeDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString().slice(0, 10);
}

function normalizeAction(action = "UNKNOWN") {
  const normalized = String(action ?? "")
    .trim()
    .toUpperCase()
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\s+/g, " ");

  if (["STRONG BUY", "LONG"].includes(normalized)) return "BUY";
  if (["STRONG SELL", "REDUCE", "SHORT"].includes(normalized)) return "SELL";
  if (normalized === "BUY" || normalized === "SELL") return normalized;
  if (["HOLD", "WATCH", "WAIT", "NEUTRAL"].includes(normalized)) return "HOLD";
  if (["NO TRADE", "SKIP", "PASS"].includes(normalized)) return "NO_TRADE";
  return "UNKNOWN";
}

function actionToDirection(action = "UNKNOWN") {
  const normalized = normalizeAction(action);
  if (normalized === "BUY") return "UP";
  if (normalized === "SELL") return "DOWN";
  return null;
}

function classifyReturn({ returnPercent = 0, neutralThreshold = 0.5 } = {}) {
  const value = finiteNumber(returnPercent, 0);
  const threshold = Math.max(0, finiteNumber(neutralThreshold, 0.5));
  if (value > threshold) return "UP";
  if (value < -threshold) return "DOWN";
  return "FLAT";
}

function calculateProfitFactor(returns = []) {
  const valid = returns.filter((value) => Number.isFinite(Number(value)));
  const grossProfit = valid
    .filter((value) => Number(value) > 0)
    .reduce((sum, value) => sum + Number(value), 0);
  const grossLoss = Math.abs(
    valid
      .filter((value) => Number(value) < 0)
      .reduce((sum, value) => sum + Number(value), 0),
  );

  if (grossLoss === 0) return grossProfit > 0 ? Infinity : 0;
  return round(grossProfit / grossLoss, 4);
}

function calculateMaximumDrawdown(returns = []) {
  let equity = 1;
  let peak = 1;
  let maximumDrawdown = 0;

  for (const value of returns) {
    if (!Number.isFinite(Number(value))) continue;
    equity *= 1 + Number(value) / 100;
    peak = Math.max(peak, equity);
    const drawdown = peak > 0 ? ((peak - equity) / peak) * 100 : 0;
    maximumDrawdown = Math.max(maximumDrawdown, drawdown);
  }

  return round(maximumDrawdown, 4);
}

function calculateCalibrationError(predictions = []) {
  const valid = predictions.filter(
    (item) =>
      item.accuracyEligible === true &&
      typeof item.correct === "boolean" &&
      Number.isFinite(Number(item.confidence)),
  );

  if (valid.length === 0) return null;

  const totalError = valid.reduce((sum, item) => {
    const predictedProbability = clamp(item.confidence, 0, 100) / 100;
    const actualOutcome = item.correct ? 1 : 0;
    return sum + Math.abs(predictedProbability - actualOutcome);
  }, 0);

  return round(totalError / valid.length, 4);
}

export function buildWalkForwardSeries(rows = []) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const diagnostics = {
    sourceRows: safeRows.length,
    validRowsBeforeDeduplication: 0,
    normalizedRows: 0,
    invalidRows: 0,
    duplicateRows: 0,
    invalidReasons: {
      missingSymbol: 0,
      invalidDate: 0,
      invalidClose: 0,
    },
    symbols: 0,
    perSymbol: {},
  };

  const deduplicated = new Map();

  safeRows.forEach((row, originalIndex) => {
    const symbol = normalizeSymbol(row?.symbol);
    const date = normalizeDate(row?.date ?? row?.timestamp);
    const close = finiteNumber(row?.close ?? row?.price, NaN);

    if (!symbol) {
      diagnostics.invalidRows += 1;
      diagnostics.invalidReasons.missingSymbol += 1;
      return;
    }

    if (!date) {
      diagnostics.invalidRows += 1;
      diagnostics.invalidReasons.invalidDate += 1;
      return;
    }

    if (!Number.isFinite(close) || close <= 0) {
      diagnostics.invalidRows += 1;
      diagnostics.invalidReasons.invalidClose += 1;
      return;
    }

    diagnostics.validRowsBeforeDeduplication += 1;
    const key = `${symbol}|${date}`;

    if (deduplicated.has(key)) diagnostics.duplicateRows += 1;

    deduplicated.set(key, {
      originalIndex,
      date,
      symbol,
      close,
      features: row?.features ?? row?.input ?? {},
      raw: row,
    });
  });

  const seriesBySymbol = new Map();

  for (const row of deduplicated.values()) {
    if (!seriesBySymbol.has(row.symbol)) seriesBySymbol.set(row.symbol, []);
    seriesBySymbol.get(row.symbol).push(row);
  }

  for (const [symbol, series] of seriesBySymbol.entries()) {
    series.sort((first, second) => {
      const dateOrder = new Date(first.date) - new Date(second.date);
      return dateOrder || first.originalIndex - second.originalIndex;
    });
    diagnostics.perSymbol[symbol] = series.length;
  }

  diagnostics.symbols = seriesBySymbol.size;
  diagnostics.normalizedRows = deduplicated.size;

  const normalizedRows = [...seriesBySymbol.values()]
    .flat()
    .sort((first, second) => {
      const symbolOrder = first.symbol.localeCompare(second.symbol);
      return symbolOrder || new Date(first.date) - new Date(second.date);
    });

  return {
    normalizedRows,
    seriesBySymbol,
    diagnostics,
    joinPolicy: {
      version: JOIN_POLICY_VERSION,
      key: ["symbol", "tradingDate"],
      horizonUnit: "TRADING_SESSIONS",
      duplicatePolicy: "LAST_INPUT_ROW_WINS",
      crossSymbolFallbackAllowed: false,
      calendarInterpolationAllowed: false,
    },
  };
}

export function normalizeWalkForwardRows(rows = []) {
  return buildWalkForwardSeries(rows).normalizedRows;
}

export function evaluateWalkForwardPrediction({
  prediction = {},
  entryRow = {},
  exitRow = {},
  horizon = 5,
  neutralThreshold = 0.5,
} = {}) {
  const entrySymbol = normalizeSymbol(entryRow.symbol ?? prediction.symbol);
  const exitSymbol = normalizeSymbol(exitRow.symbol);

  if (entrySymbol && exitSymbol && entrySymbol !== exitSymbol) {
    throw new Error("WALK_FORWARD_SYMBOL_MISMATCH");
  }

  const entryDate = normalizeDate(entryRow.date ?? entryRow.timestamp);
  const exitDate = normalizeDate(exitRow.date ?? exitRow.timestamp);

  if (entryDate && exitDate && new Date(exitDate) <= new Date(entryDate)) {
    throw new Error("WALK_FORWARD_EXIT_MUST_BE_AFTER_ENTRY");
  }

  const entryPrice = finiteNumber(entryRow.close ?? entryRow.price, 0);
  const exitPrice = finiteNumber(exitRow.close ?? exitRow.price, 0);

  if (entryPrice <= 0 || exitPrice <= 0) {
    throw new Error("WALK_FORWARD_PRICE_INVALID");
  }

  const returnPercent = ((exitPrice - entryPrice) / entryPrice) * 100;
  const action = normalizeAction(prediction.action ?? prediction.signal);
  const predictedDirection = actionToDirection(action);
  const actualDirection = classifyReturn({ returnPercent, neutralThreshold });
  const accuracyEligible = predictedDirection !== null;
  const correct = accuracyEligible ? predictedDirection === actualDirection : null;

  let strategyReturn = null;
  if (action === "BUY") strategyReturn = returnPercent;
  if (action === "SELL") strategyReturn = -returnPercent;

  return {
    symbol: entrySymbol || null,
    entryDate,
    exitDate,
    horizon: Math.max(1, Math.floor(finiteNumber(horizon, 5))),
    horizonUnit: "TRADING_SESSIONS",
    entryPrice: round(entryPrice, 4),
    exitPrice: round(exitPrice, 4),
    action,
    predictedDirection,
    actualDirection,
    correct,
    accuracyEligible,
    tradePerformanceEligible:
      accuracyEligible && Number.isFinite(Number(strategyReturn)),
    resolutionStatus: "RESOLVED",
    labelPolicyVersion: LABEL_POLICY_VERSION,
    score: finiteNumber(prediction.score, 50),
    confidence: finiteNumber(prediction.confidence, 0),
    returnPercent: round(returnPercent, 4),
    strategyReturn:
      strategyReturn === null ? null : round(strategyReturn, 4),
  };
}

export function summarizeWalkForwardAudit(predictions = []) {
  const source = Array.isArray(predictions) ? predictions : [];
  const eligible = source.filter(
    (item) =>
      item.accuracyEligible !== false &&
      ["BUY", "SELL"].includes(normalizeAction(item.action)) &&
      typeof item.correct === "boolean" &&
      Number.isFinite(Number(item.strategyReturn)),
  );

  const total = eligible.length;
  const correct = eligible.filter((item) => item.correct === true).length;
  const buyPredictions = eligible.filter((item) => normalizeAction(item.action) === "BUY");
  const sellPredictions = eligible.filter((item) => normalizeAction(item.action) === "SELL");
  const buyWins = buyPredictions.filter((item) => item.actualDirection === "UP").length;
  const sellWins = sellPredictions.filter((item) => item.actualDirection === "DOWN").length;
  const marketReturns = eligible.map((item) => Number(item.returnPercent));
  const strategyReturns = eligible.map((item) => Number(item.strategyReturn));

  const excluded = {
    total: source.length - total,
    hold: source.filter((item) => normalizeAction(item.action) === "HOLD").length,
    noTrade: source.filter((item) => normalizeAction(item.action) === "NO_TRADE").length,
    unknown: source.filter((item) => normalizeAction(item.action) === "UNKNOWN").length,
    unresolved: source.filter((item) => item.resolutionStatus && item.resolutionStatus !== "RESOLVED").length,
  };

  if (total === 0) {
    return {
      sourceTotal: source.length,
      total: 0,
      correct: 0,
      accuracy: 0,
      buySignals: 0,
      buyWins: 0,
      buyPrecision: 0,
      sellSignals: 0,
      sellWins: 0,
      sellPrecision: 0,
      averageReturn: 0,
      averageStrategyReturn: 0,
      profitFactor: 0,
      maximumDrawdown: 0,
      calibrationError: null,
      excluded,
      denominatorPolicy: {
        version: LABEL_POLICY_VERSION,
        includes: "Resolved BUY/SELL predictions only",
        excludes: ["HOLD", "NO_TRADE", "UNKNOWN", "UNRESOLVED"],
      },
    };
  }

  return {
    sourceTotal: source.length,
    total,
    correct,
    accuracy: round((correct / total) * 100, 2),
    buySignals: buyPredictions.length,
    buyWins,
    buyPrecision: buyPredictions.length
      ? round((buyWins / buyPredictions.length) * 100, 2)
      : 0,
    sellSignals: sellPredictions.length,
    sellWins,
    sellPrecision: sellPredictions.length
      ? round((sellWins / sellPredictions.length) * 100, 2)
      : 0,
    averageReturn: round(
      marketReturns.reduce((sum, value) => sum + value, 0) / total,
      4,
    ),
    averageStrategyReturn: round(
      strategyReturns.reduce((sum, value) => sum + value, 0) / total,
      4,
    ),
    profitFactor: calculateProfitFactor(strategyReturns),
    maximumDrawdown: calculateMaximumDrawdown(strategyReturns),
    calibrationError: calculateCalibrationError(eligible),
    excluded,
    denominatorPolicy: {
      version: LABEL_POLICY_VERSION,
      includes: "Resolved BUY/SELL predictions only",
      excludes: ["HOLD", "NO_TRADE", "UNKNOWN", "UNRESOLVED"],
    },
  };
}

export async function runWalkForwardAudit({
  rows = [],
  predictor,
  horizon = 5,
  minimumHistory = 20,
  neutralThreshold = 0.5,
  onProgress,
} = {}) {
  if (typeof predictor !== "function") {
    throw new TypeError("predictor must be a function");
  }

  const safeHorizon = Math.max(1, Math.floor(finiteNumber(horizon, 5)));
  const safeMinimumHistory = Math.max(1, Math.floor(finiteNumber(minimumHistory, 20)));
  const prepared = buildWalkForwardSeries(rows);
  const predictions = [];

  const totalPlanned = [...prepared.seriesBySymbol.values()].reduce(
    (sum, series) =>
      sum + Math.max(0, series.length - safeHorizon - safeMinimumHistory + 1),
    0,
  );

  const symbols = [...prepared.seriesBySymbol.keys()].sort();

  for (const symbol of symbols) {
    const series = prepared.seriesBySymbol.get(symbol);
    const lastEntryIndex = series.length - safeHorizon;

    for (let index = safeMinimumHistory - 1; index < lastEntryIndex; index += 1) {
      const entryRow = series[index];
      const exitRow = series[index + safeHorizon];
      const visibleHistory = series.slice(0, index + 1);

      const prediction = await predictor({
        symbol,
        date: entryRow.date,
        price: entryRow.close,
        features: entryRow.features,
        horizon: safeHorizon,
        horizonUnit: "TRADING_SESSIONS",
        history: visibleHistory.map((row) => ({
          date: row.date,
          symbol: row.symbol,
          close: row.close,
          features: row.features,
        })),
      });

      const evaluated = evaluateWalkForwardPrediction({
        prediction,
        entryRow,
        exitRow,
        horizon: safeHorizon,
        neutralThreshold,
      });

      predictions.push(evaluated);

      if (typeof onProgress === "function") {
        onProgress({
          completed: predictions.length,
          total: totalPlanned,
          latest: evaluated,
        });
      }
    }
  }

  const summary = summarizeWalkForwardAudit(predictions);

  return {
    version: "walk-forward-accuracy-audit-v2",
    generatedAt: new Date().toISOString(),
    horizon: safeHorizon,
    horizonUnit: "TRADING_SESSIONS",
    minimumHistory: safeMinimumHistory,
    neutralThreshold: finiteNumber(neutralThreshold, 0.5),
    sourceRows: prepared.diagnostics.sourceRows,
    normalizedRows: prepared.diagnostics.normalizedRows,
    futureLeakChecked: true,
    crossSymbolJoinBlocked: true,
    labelPolicy: {
      version: LABEL_POLICY_VERSION,
      target: "close-to-close directional return",
      thresholdPercent: finiteNumber(neutralThreshold, 0.5),
      directionalActions: ["BUY", "SELL"],
      nonDirectionalActions: ["HOLD", "NO_TRADE", "UNKNOWN"],
    },
    joinPolicy: prepared.joinPolicy,
    diagnostics: prepared.diagnostics,
    predictions,
    summary,
  };
}

export const WalkForwardAccuracyAuditInternals = {
  actionToDirection,
  calculateCalibrationError,
  calculateMaximumDrawdown,
  calculateProfitFactor,
  classifyReturn,
  finiteNumber,
  normalizeAction,
  normalizeDate,
  normalizeSymbol,
  round,
};
