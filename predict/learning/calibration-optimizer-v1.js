export const CALIBRATION_OPTIMIZER_V1 = "calibration-optimizer-v1";

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function summarize(records = [], threshold = 50) {
  const trades = records.filter((row) => String(row.action).toUpperCase() !== "NO_TRADE" && finite(row.score ?? row.confidence) >= threshold);
  const noTradeCount = records.length - trades.length;
  const wins = trades.filter((row) => finite(row.return) > 0);
  const grossProfit = wins.reduce((sum, row) => sum + finite(row.return), 0);
  const grossLoss = Math.abs(trades.filter((row) => finite(row.return) < 0).reduce((sum, row) => sum + finite(row.return), 0));
  return {
    threshold,
    sampleSize: records.length,
    tradeCount: trades.length,
    noTradeRate: records.length ? noTradeCount / records.length : 0,
    winRate: trades.length ? wins.length / trades.length : 0,
    expectedValue: trades.length ? trades.reduce((sum, row) => sum + finite(row.return), 0) / trades.length : 0,
    profitFactor: grossLoss ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0,
  };
}

function group(records, key) {
  const grouped = new Map();
  for (const row of records) {
    const name = row?.[key] ?? "UNKNOWN";
    if (!grouped.has(name)) grouped.set(name, []);
    grouped.get(name).push(row);
  }
  return [...grouped.entries()].map(([name, rows]) => ({ name, sampleSize: rows.length }));
}

export function optimizeCalibration({
  records = [],
  production = { buyThreshold: 60, sellThreshold: 60, confidenceThreshold: 50 },
  thresholdCandidates = [40, 50, 60, 70, 80],
  targetNoTradeRate = { min: 0.2, max: 0.8 },
} = {}) {
  const candidates = thresholdCandidates
    .map((threshold) => summarize(records, finite(threshold, 50)))
    .map((metrics) => ({
      ...metrics,
      acceptableNoTradeRate: metrics.noTradeRate >= targetNoTradeRate.min && metrics.noTradeRate <= targetNoTradeRate.max,
      objective: metrics.expectedValue * Math.sqrt(Math.max(1, metrics.tradeCount)),
    }))
    .sort((a, b) => b.objective - a.objective);

  const best = candidates.find((candidate) => candidate.acceptableNoTradeRate) ?? candidates[0] ?? null;
  const candidateConfig = best
    ? {
        confidenceThreshold: best.threshold,
        buyThreshold: best.threshold,
        sellThreshold: best.threshold,
      }
    : { ...production };

  return {
    version: CALIBRATION_OPTIMIZER_V1,
    generatedAt: new Date().toISOString(),
    status: records.length ? "REVIEW_REQUIRED" : "INSUFFICIENT_DATA",
    production: { ...production },
    candidate: candidateConfig,
    candidates,
    confidenceCalibration: candidates.map(({ threshold, winRate, expectedValue, sampleSize }) => ({ threshold, winRate, expectedValue, sampleSize })),
    sectorCoverage: group(records, "sector"),
    regimeCoverage: group(records, "marketRegime"),
    drift: {
      detected: best ? Math.abs(best.threshold - finite(production.confidenceThreshold, 50)) >= 20 : false,
      thresholdDelta: best ? best.threshold - finite(production.confidenceThreshold, 50) : 0,
    },
    comparison: {
      thresholdDelta: best ? best.threshold - finite(production.confidenceThreshold, 50) : 0,
      reviewRecommended: Boolean(best && best.tradeCount >= 30),
    },
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  };
}

export default optimizeCalibration;
