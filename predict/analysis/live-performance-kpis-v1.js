export const LIVE_PERFORMANCE_KPIS_VERSION = "live-performance-kpis-v1";

function finite(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function numberOrNull(value) {
  return finite(value) ? Number(value) : null;
}

function readGrossReturn(row) {
  return numberOrNull(row?.grossReturn ?? row?.strategyReturn ?? row?.actualReturn ?? row?.returnPercent);
}

function readFees(row) {
  return numberOrNull(row?.fees ?? row?.commission ?? row?.transactionCost) ?? 0;
}

function readSlippage(row) {
  return numberOrNull(row?.slippage ?? row?.slippageCost) ?? 0;
}

function readNetReturn(row) {
  const explicit = numberOrNull(row?.netReturn ?? row?.costAdjustedReturn ?? row?.pnlPercent);
  if (explicit !== null) return explicit;
  const gross = readGrossReturn(row);
  if (gross === null) return null;
  return gross - readFees(row) - readSlippage(row);
}

function maxDrawdown(returns) {
  let equity = 0;
  let peak = 0;
  let maximum = 0;
  for (const value of returns) {
    equity += value;
    peak = Math.max(peak, equity);
    maximum = Math.max(maximum, peak - equity);
  }
  return maximum;
}

function profitFactor(returns) {
  const gains = returns.filter((value) => value > 0).reduce((sum, value) => sum + value, 0);
  const losses = Math.abs(returns.filter((value) => value < 0).reduce((sum, value) => sum + value, 0));
  if (losses === 0) return gains > 0 ? Infinity : null;
  return gains / losses;
}

function average(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

export function buildLivePerformanceKpisV1({ rows = [], options = {} } = {}) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");

  const trades = rows
    .map((row) => ({
      grossReturn: readGrossReturn(row),
      netReturn: readNetReturn(row),
      fees: readFees(row),
      slippage: readSlippage(row),
      exposure: numberOrNull(row?.exposure),
      turnover: numberOrNull(row?.turnover),
      directionHit: typeof row?.directionHit === "boolean" ? row.directionHit : null,
    }))
    .filter((row) => row.netReturn !== null);

  const netReturns = trades.map((row) => row.netReturn);
  const grossReturns = trades.map((row) => row.grossReturn).filter((value) => value !== null);
  const wins = netReturns.filter((value) => value > 0);
  const losses = netReturns.filter((value) => value < 0);
  const directional = trades.filter((row) => row.directionHit !== null);

  return {
    version: LIVE_PERFORMANCE_KPIS_VERSION,
    generatedAt: options.generatedAt ?? new Date().toISOString(),
    sampleCount: trades.length,
    predictionAccuracy: directional.length
      ? directional.filter((row) => row.directionHit).length / directional.length
      : null,
    tradeWinRate: trades.length ? wins.length / trades.length : null,
    grossReturn: grossReturns.reduce((sum, value) => sum + value, 0),
    netReturn: netReturns.reduce((sum, value) => sum + value, 0),
    averageReturn: average(netReturns),
    expectancy: average(netReturns),
    payoffRatio: losses.length && wins.length
      ? average(wins) / Math.abs(average(losses))
      : null,
    profitFactor: profitFactor(netReturns),
    maximumDrawdown: maxDrawdown(netReturns),
    transactionCost: trades.reduce((sum, row) => sum + row.fees, 0),
    slippage: trades.reduce((sum, row) => sum + row.slippage, 0),
    exposure: average(trades.map((row) => row.exposure).filter((value) => value !== null)),
    turnover: trades.reduce((sum, row) => sum + (row.turnover ?? 0), 0),
    safety: {
      executionAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
    },
  };
}

export const LivePerformanceKpisInternals = Object.freeze({
  readGrossReturn,
  readNetReturn,
  readFees,
  readSlippage,
  profitFactor,
  maxDrawdown,
});

export default buildLivePerformanceKpisV1;
