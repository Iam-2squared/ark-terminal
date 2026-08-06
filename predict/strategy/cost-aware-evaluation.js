export const COST_AWARE_EVALUATION_VERSION = "phase24-cost-aware-evaluation-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = 0) => finite(value) ? Number(value) : fallback;

export function evaluateCostAwareStrategy(rows = [], options = {}) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");
  const defaultFeePercent = number(options.feePercent, 0.1);
  const defaultSlippagePercent = number(options.slippagePercent, 0.15);
  const eligible = rows.filter((row) => finite(row.grossReturn ?? row.returnPercent ?? row.actualReturn));

  const trades = eligible.map((row) => {
    const grossReturn = number(row.grossReturn ?? row.returnPercent ?? row.actualReturn);
    const feePercent = number(row.feePercent, defaultFeePercent);
    const slippagePercent = number(row.slippagePercent, defaultSlippagePercent);
    const delayCostPercent = number(row.delayCostPercent, 0);
    const netReturn = grossReturn - feePercent - slippagePercent - delayCostPercent;
    return { grossReturn, feePercent, slippagePercent, delayCostPercent, netReturn };
  });

  const positive = trades.filter((trade) => trade.netReturn > 0).reduce((sum, trade) => sum + trade.netReturn, 0);
  const negative = Math.abs(trades.filter((trade) => trade.netReturn < 0).reduce((sum, trade) => sum + trade.netReturn, 0));
  const netReturns = trades.map((trade) => trade.netReturn);
  const grossReturns = trades.map((trade) => trade.grossReturn);
  const average = (values) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

  return {
    version: COST_AWARE_EVALUATION_VERSION,
    sampleCount: trades.length,
    grossAverageReturn: average(grossReturns),
    netAverageReturn: average(netReturns),
    profitFactor: negative > 0 ? positive / negative : positive > 0 ? Infinity : null,
    winRate: trades.length ? trades.filter((trade) => trade.netReturn > 0).length / trades.length : null,
    totalFees: trades.reduce((sum, trade) => sum + trade.feePercent, 0),
    totalSlippage: trades.reduce((sum, trade) => sum + trade.slippagePercent, 0),
    totalDelayCost: trades.reduce((sum, trade) => sum + trade.delayCostPercent, 0),
    trades,
    safety: {
      evaluationOnly: true,
      executionAllowed: false,
      brokerWriteAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
    },
  };
}

export default evaluateCostAwareStrategy;
