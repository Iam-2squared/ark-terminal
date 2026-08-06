const SHADOW_SAFETY = Object.freeze({
  mode: "SHADOW_ONLY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  humanReviewRequired: true,
});

function finiteNumber(value, fallback = null) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function normalizeSignal(value) {
  const signal = String(value ?? "NO_TRADE").trim().toUpperCase();
  return ["BUY", "SELL", "HOLD", "NO_TRADE"].includes(signal) ? signal : "NO_TRADE";
}

function normalizeSymbol(value) {
  const symbol = String(value ?? "").trim().toUpperCase();
  if (!symbol) throw new TypeError("symbol is required");
  return /^\d+$/.test(symbol) ? `${symbol}.T` : symbol;
}

function hashText(value) {
  let hash = 2166136261;
  for (const char of String(value)) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function createShadowPrediction(input, options = {}) {
  if (!input || typeof input !== "object") throw new TypeError("prediction input is required");
  const symbol = normalizeSymbol(input.symbol);
  const signal = normalizeSignal(input.signal);
  const entryPrice = finiteNumber(input.entryPrice, null);
  const stopLoss = finiteNumber(input.stopLoss, null);
  const takeProfit = finiteNumber(input.takeProfit, null);
  const confidence = finiteNumber(input.confidence, null);
  const expectedHoldingDays = Math.max(1, Math.trunc(finiteNumber(input.expectedHoldingDays, 5)));
  if (["BUY", "SELL"].includes(signal) && !(entryPrice > 0)) {
    throw new TypeError("BUY/SELL shadow prediction requires a positive entryPrice");
  }
  const createdAt = options.now ?? new Date().toISOString();
  const predictionId = options.predictionId ?? `shadow-${createdAt}-${symbol}-${hashText(JSON.stringify({ symbol, signal, entryPrice, confidence }))}`;
  return {
    predictionId,
    createdAt,
    frozenAt: createdAt,
    symbol,
    signal,
    entryPrice,
    stopLoss,
    takeProfit,
    confidence,
    marketRegime: String(input.marketRegime ?? "UNKNOWN").toUpperCase(),
    expectedHoldingDays,
    rationale: Array.isArray(input.rationale) ? [...input.rationale] : [],
    modelId: input.modelId ?? null,
    featureSnapshotId: input.featureSnapshotId ?? null,
    status: signal === "NO_TRADE" ? "NO_TRADE_RECORDED" : "PENDING_EVALUATION",
    immutable: true,
    safety: { ...SHADOW_SAFETY },
  };
}

export function evaluateShadowPrediction(prediction, marketOutcome, costs = {}) {
  if (!prediction || typeof prediction !== "object") throw new TypeError("prediction is required");
  if (!marketOutcome || typeof marketOutcome !== "object") throw new TypeError("marketOutcome is required");
  if (prediction.status === "NO_TRADE_RECORDED") {
    return {
      predictionId: prediction.predictionId,
      status: "NO_TRADE_CONFIRMED",
      directionCorrect: null,
      grossReturn: 0,
      netReturn: 0,
      grossPnl: 0,
      netPnl: 0,
      costs: 0,
      safety: { ...SHADOW_SAFETY },
    };
  }
  const exitPrice = finiteNumber(marketOutcome.exitPrice, null);
  if (!(exitPrice > 0)) throw new TypeError("marketOutcome.exitPrice must be positive");
  const quantity = Math.max(1, Math.trunc(finiteNumber(marketOutcome.quantity, 1)));
  const sideMultiplier = prediction.signal === "SELL" ? -1 : 1;
  const grossReturn = sideMultiplier * ((exitPrice - prediction.entryPrice) / prediction.entryPrice);
  const commission = Math.max(0, finiteNumber(costs.commission, 0));
  const slippage = Math.max(0, finiteNumber(costs.slippage, 0));
  const delayCost = Math.max(0, finiteNumber(costs.delayCost, 0));
  const totalCosts = commission + slippage + delayCost;
  const grossPnl = sideMultiplier * (exitPrice - prediction.entryPrice) * quantity;
  const netPnl = grossPnl - totalCosts;
  const notional = prediction.entryPrice * quantity;
  const netReturn = notional > 0 ? netPnl / notional : 0;
  return {
    predictionId: prediction.predictionId,
    evaluatedAt: marketOutcome.evaluatedAt ?? new Date().toISOString(),
    status: "EVALUATED",
    symbol: prediction.symbol,
    signal: prediction.signal,
    entryPrice: prediction.entryPrice,
    exitPrice,
    quantity,
    directionCorrect: grossReturn > 0,
    grossReturn,
    netReturn,
    grossPnl,
    netPnl,
    costs: totalCosts,
    holdingDays: Math.max(0, Math.trunc(finiteNumber(marketOutcome.holdingDays, prediction.expectedHoldingDays))),
    marketRegime: prediction.marketRegime,
    safety: { ...SHADOW_SAFETY },
  };
}

export function buildShadowDailyLog({ date, predictions = [], evaluations = [] } = {}) {
  const byId = new Map(evaluations.map((item) => [item.predictionId, item]));
  const rows = predictions.map((prediction) => ({
    predictionId: prediction.predictionId,
    symbol: prediction.symbol,
    signal: prediction.signal,
    confidence: prediction.confidence,
    marketRegime: prediction.marketRegime,
    predictionStatus: prediction.status,
    evaluation: byId.get(prediction.predictionId) ?? null,
  }));
  const settled = rows.filter((row) => row.evaluation?.status === "EVALUATED");
  const totalNetPnl = settled.reduce((sum, row) => sum + row.evaluation.netPnl, 0);
  const wins = settled.filter((row) => row.evaluation.directionCorrect).length;
  return {
    date: date ?? new Date().toISOString().slice(0, 10),
    predictionCount: predictions.length,
    evaluatedCount: settled.length,
    pendingCount: predictions.filter((item) => item.status === "PENDING_EVALUATION" && !byId.has(item.predictionId)).length,
    noTradeCount: predictions.filter((item) => item.status === "NO_TRADE_RECORDED").length,
    wins,
    losses: settled.length - wins,
    winRate: settled.length ? wins / settled.length : null,
    totalNetPnl,
    averageNetReturn: settled.length ? settled.reduce((sum, row) => sum + row.evaluation.netReturn, 0) / settled.length : null,
    rows,
    audit: {
      generatedAt: new Date().toISOString(),
      checksum: hashText(JSON.stringify(rows)),
      immutableInputs: true,
    },
    safety: { ...SHADOW_SAFETY },
  };
}

export function runShadowForwardOperations({ candidates = [], outcomesBySymbol = {}, costsBySymbol = {}, now } = {}) {
  const predictions = candidates.map((candidate, index) => createShadowPrediction(candidate, {
    now: now ?? new Date().toISOString(),
    predictionId: `shadow-${index + 1}-${normalizeSymbol(candidate.symbol)}-${hashText(JSON.stringify(candidate))}`,
  }));
  const evaluations = predictions.flatMap((prediction) => {
    const outcome = outcomesBySymbol[prediction.symbol];
    if (!outcome || prediction.status !== "PENDING_EVALUATION") return [];
    return [evaluateShadowPrediction(prediction, outcome, costsBySymbol[prediction.symbol] ?? {})];
  });
  const dailyLog = buildShadowDailyLog({ date: (now ?? new Date().toISOString()).slice(0, 10), predictions, evaluations });
  return {
    status: "SHADOW_RUN_COMPLETE",
    predictions,
    evaluations,
    dailyLog,
    brokerWrites: 0,
    liveOrders: 0,
    excelOrderWrites: 0,
    orderTriggerChanges: 0,
    safety: { ...SHADOW_SAFETY },
  };
}

export { SHADOW_SAFETY };
