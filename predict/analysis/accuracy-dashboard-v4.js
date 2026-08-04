import { auditTradeMemoryAccuracy } from "./trade-memory-accuracy-v1.js";

export const ACCURACY_DASHBOARD_V4_VERSION = "accuracy-dashboard-v4";

function finiteOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function buildAccuracyDashboardV4({
  tradeMemoryRecords = [],
  performance = {},
} = {}) {
  const result = auditTradeMemoryAccuracy(tradeMemoryRecords);
  const audit = result.audit;
  const trade = audit.tradePerformance;
  const buy = audit.byAction.BUY;
  const sell = audit.byAction.SELL;

  return {
    version: ACCURACY_DASHBOARD_V4_VERSION,
    generatedAt: new Date().toISOString(),
    sample: {
      evaluations: audit.counts.all,
      trades: audit.counts.trade,
      resolvedTrades: trade.resolved,
      pending: audit.counts.pending,
      noTrade: audit.counts.noTrade,
      insufficient: audit.warnings.includes("INSUFFICIENT_TRADE_SAMPLE"),
    },
    metrics: {
      predictionAccuracy: audit.predictionAccuracy.winRate,
      tradeWinRate: trade.winRate,
      buyWinRate: buy.winRate,
      sellWinRate: sell.winRate,
      profitFactor: trade.profitFactor,
      sharpe: finiteOrNull(performance.sharpe ?? performance.sharpeRatio),
      maxDrawdownPercent: finiteOrNull(
        performance.maxDrawdownPercent ?? performance.maximumDrawdownPercent,
      ),
      averageReturnPercent: trade.averageReturnPercent,
    },
    reverseStrategy: audit.reverseStrategy,
    warnings: [...audit.warnings],
    definitions: { ...audit.definitions },
    source: result,
  };
}

export default buildAccuracyDashboardV4;
