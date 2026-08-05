export const HISTORICAL_VALIDATION_V1 = "historical-validation-v1";

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function groupBy(records, key) {
  const groups = new Map();
  for (const record of records) {
    const value = record?.[key] ?? "UNKNOWN";
    if (!groups.has(value)) groups.set(value, []);
    groups.get(value).push(record);
  }
  return groups;
}

function summarize(records = []) {
  const trades = records.filter((record) => record.action !== "NO_TRADE");
  const wins = trades.filter((record) => finite(record.return) > 0);
  const losses = trades.filter((record) => finite(record.return) < 0);
  const grossProfit = wins.reduce((sum, record) => sum + finite(record.return), 0);
  const grossLoss = Math.abs(losses.reduce((sum, record) => sum + finite(record.return), 0));
  const noTrade = records.filter((record) => record.action === "NO_TRADE").length;
  const avgReturn = trades.length ? trades.reduce((sum, record) => sum + finite(record.return), 0) / trades.length : 0;
  const buy = trades.filter((record) => record.action === "BUY");
  const sell = trades.filter((record) => record.action === "SELL");

  return {
    sampleSize: records.length,
    tradeCount: trades.length,
    noTradeCount: noTrade,
    noTradeRate: records.length ? noTrade / records.length : 0,
    winRate: trades.length ? wins.length / trades.length : 0,
    buyWinRate: buy.length ? buy.filter((record) => finite(record.return) > 0).length / buy.length : 0,
    sellWinRate: sell.length ? sell.filter((record) => finite(record.return) > 0).length / sell.length : 0,
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0,
    expectedValue: avgReturn,
  };
}

function rankedBreakdown(records, key) {
  return [...groupBy(records, key).entries()]
    .map(([name, rows]) => ({ name, ...summarize(rows) }))
    .sort((a, b) => b.expectedValue - a.expectedValue);
}

export function runHistoricalValidation({ records = [], metadata = {} } = {}) {
  const valid = records.filter((record) => record && record.timestamp && record.symbol && record.action);
  const duplicateKeys = new Set();
  const seen = new Set();
  for (const record of valid) {
    const key = `${record.symbol}|${record.timestamp}|${record.action}`;
    if (seen.has(key)) duplicateKeys.add(key);
    seen.add(key);
  }

  const futureLeakDetected = valid.some((record) => {
    const signalAt = Date.parse(record.signalAt ?? record.timestamp);
    const outcomeAt = Date.parse(record.outcomeAt ?? record.timestamp);
    return Number.isFinite(signalAt) && Number.isFinite(outcomeAt) && signalAt > outcomeAt;
  });

  const overall = summarize(valid);
  const bySymbol = rankedBreakdown(valid, "symbol");
  const bySector = rankedBreakdown(valid, "sector");
  const byRegime = rankedBreakdown(valid, "marketRegime");
  const confidenceBuckets = rankedBreakdown(
    valid.map((record) => ({
      ...record,
      confidenceBucket: `${Math.floor(finite(record.confidence) / 10) * 10}-${Math.floor(finite(record.confidence) / 10) * 10 + 9}`,
    })),
    "confidenceBucket",
  );

  const blockers = [
    ...(valid.length === 0 ? ["NO_VALID_RECORDS"] : []),
    ...(futureLeakDetected ? ["FUTURE_LEAK_DETECTED"] : []),
    ...(duplicateKeys.size ? ["DUPLICATE_RECORDS"] : []),
  ];

  return {
    version: HISTORICAL_VALIDATION_V1,
    generatedAt: new Date().toISOString(),
    status: blockers.length ? "BLOCKED" : "READY",
    metadata,
    overall,
    bySymbol,
    bySector,
    byRegime,
    confidenceCalibration: confidenceBuckets,
    bestSymbols: bySymbol.slice(0, 10),
    worstSymbols: [...bySymbol].reverse().slice(0, 10),
    worstSectors: [...bySector].reverse().slice(0, 10),
    dataQuality: {
      inputCount: records.length,
      validCount: valid.length,
      duplicateCount: duplicateKeys.size,
      futureLeakDetected,
    },
    blockers,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  };
}

export default runHistoricalValidation;
