export const ACCURACY_AUDIT_V3_VERSION = "accuracy-audit-v3";

const TRADE_ACTIONS = new Set(["BUY", "SELL"]);

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function round(value, digits = 4) {
  if (!Number.isFinite(value)) return null;
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function normalizeAction(value) {
  const action = String(value ?? "NO_TRADE").trim().toUpperCase().replaceAll(" ", "_");
  if (["BUY", "SELL", "HOLD", "NO_TRADE", "BLOCK"].includes(action)) return action;
  return "NO_TRADE";
}

function normalizeStatus(value) {
  const status = String(value ?? "PENDING").trim().toUpperCase();
  if (["WIN", "LOSS", "FLAT", "PENDING", "CANCELLED"].includes(status)) return status;
  return "PENDING";
}

function normalizeRecord(record = {}) {
  const action = normalizeAction(record.action ?? record.decision ?? record.signal);
  const returnPercent = finite(record.returnPercent ?? record.actualReturnPercent ?? record.return, 0);
  let status = normalizeStatus(record.status ?? record.outcome);

  if (status === "PENDING" && record.resolved === true) {
    status = returnPercent > 0 ? "WIN" : returnPercent < 0 ? "LOSS" : "FLAT";
  }

  return {
    action,
    status,
    returnPercent,
    confidence: finite(record.confidence ?? record.confidenceScore, 0),
    symbol: String(record.symbol ?? "UNKNOWN").trim().toUpperCase(),
  };
}

function summarize(records) {
  const resolved = records.filter((record) => ["WIN", "LOSS", "FLAT"].includes(record.status));
  const wins = resolved.filter((record) => record.status === "WIN");
  const losses = resolved.filter((record) => record.status === "LOSS");
  const grossProfit = wins.reduce((sum, record) => sum + Math.max(0, record.returnPercent), 0);
  const grossLoss = Math.abs(losses.reduce((sum, record) => sum + Math.min(0, record.returnPercent), 0));

  return {
    total: records.length,
    resolved: resolved.length,
    pending: records.filter((record) => record.status === "PENDING").length,
    wins: wins.length,
    losses: losses.length,
    flats: resolved.filter((record) => record.status === "FLAT").length,
    winRate: resolved.length === 0 ? null : round((wins.length / resolved.length) * 100),
    averageReturnPercent: resolved.length === 0 ? null : round(resolved.reduce((sum, record) => sum + record.returnPercent, 0) / resolved.length),
    profitFactor: grossLoss === 0 ? (grossProfit > 0 ? "Infinity" : null) : round(grossProfit / grossLoss),
  };
}

function reverseRecord(record) {
  if (!TRADE_ACTIONS.has(record.action)) return { ...record };
  return {
    ...record,
    action: record.action === "BUY" ? "SELL" : "BUY",
    returnPercent: -record.returnPercent,
    status: record.status === "WIN" ? "LOSS" : record.status === "LOSS" ? "WIN" : record.status,
  };
}

function buildWarnings({ all, trades, predictionAccuracy, tradePerformance }) {
  const warnings = [];
  if (trades.total < 30) warnings.push("INSUFFICIENT_TRADE_SAMPLE");
  if (trades.pending > 0) warnings.push("PENDING_OUTCOMES_EXCLUDED");
  if (all.total !== trades.total) warnings.push("NO_TRADE_EXCLUDED_FROM_TRADE_WIN_RATE");
  if (predictionAccuracy.winRate !== null && tradePerformance.winRate !== null && Math.abs(predictionAccuracy.winRate - tradePerformance.winRate) >= 15) {
    warnings.push("ACCURACY_AND_TRADE_WIN_RATE_DIVERGE");
  }
  if (tradePerformance.profitFactor !== null && tradePerformance.profitFactor !== "Infinity" && tradePerformance.profitFactor < 1) {
    warnings.push("NEGATIVE_EXPECTANCY_RISK");
  }
  return warnings;
}

export function auditAccuracy(records = []) {
  const normalized = Array.isArray(records) ? records.map(normalizeRecord) : [];
  const tradeRecords = normalized.filter((record) => TRADE_ACTIONS.has(record.action));
  const noTradeRecords = normalized.filter((record) => !TRADE_ACTIONS.has(record.action));

  const predictionAccuracy = summarize(normalized);
  const tradePerformance = summarize(tradeRecords);
  const buyPerformance = summarize(tradeRecords.filter((record) => record.action === "BUY"));
  const sellPerformance = summarize(tradeRecords.filter((record) => record.action === "SELL"));
  const reversePerformance = summarize(tradeRecords.map(reverseRecord));

  return {
    version: ACCURACY_AUDIT_V3_VERSION,
    counts: {
      all: normalized.length,
      trade: tradeRecords.length,
      noTrade: noTradeRecords.length,
      pending: normalized.filter((record) => record.status === "PENDING").length,
    },
    predictionAccuracy,
    tradePerformance,
    byAction: {
      BUY: buyPerformance,
      SELL: sellPerformance,
      NO_TRADE: summarize(noTradeRecords),
    },
    reverseStrategy: {
      original: tradePerformance,
      reversed: reversePerformance,
      better: reversePerformance.averageReturnPercent !== null && tradePerformance.averageReturnPercent !== null
        ? reversePerformance.averageReturnPercent > tradePerformance.averageReturnPercent
        : null,
    },
    warnings: buildWarnings({ all: predictionAccuracy, trades: tradePerformance, predictionAccuracy, tradePerformance }),
    definitions: {
      predictionAccuracy: "All resolved predictions, including non-trade decisions.",
      tradeWinRate: "Resolved BUY/SELL trades only. NO_TRADE, HOLD, BLOCK, PENDING and CANCELLED are excluded.",
    },
  };
}

export default auditAccuracy;
