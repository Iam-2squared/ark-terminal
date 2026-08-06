export const LIQUIDITY_GATE_VERSION = "phase24-liquidity-gate-v1";

const finite = (value) => Number.isFinite(Number(value));

export function evaluateLiquidity(row = {}, options = {}) {
  const minVolume = finite(options.minVolume) ? Number(options.minVolume) : 100000;
  const minTurnover = finite(options.minTurnover) ? Number(options.minTurnover) : 10000000;
  const maxSpreadPercent = finite(options.maxSpreadPercent) ? Number(options.maxSpreadPercent) : 1.5;
  const minPrice = finite(options.minPrice) ? Number(options.minPrice) : 50;

  const price = finite(row.price ?? row.close) ? Number(row.price ?? row.close) : null;
  const volume = finite(row.volume) ? Number(row.volume) : null;
  const turnover = finite(row.turnover ?? row.tradedValue)
    ? Number(row.turnover ?? row.tradedValue)
    : price !== null && volume !== null
      ? price * volume
      : null;
  const spreadPercent = finite(row.spreadPercent) ? Number(row.spreadPercent) : null;

  const blockers = [];
  if (price === null || price < minPrice) blockers.push("PRICE_TOO_LOW_OR_MISSING");
  if (volume === null || volume < minVolume) blockers.push("VOLUME_TOO_LOW_OR_MISSING");
  if (turnover === null || turnover < minTurnover) blockers.push("TURNOVER_TOO_LOW_OR_MISSING");
  if (spreadPercent === null || spreadPercent > maxSpreadPercent) blockers.push("SPREAD_TOO_WIDE_OR_MISSING");

  return {
    version: LIQUIDITY_GATE_VERSION,
    status: blockers.length ? "BLOCKED" : "PASS",
    blockers,
    metrics: { price, volume, turnover, spreadPercent },
    thresholds: { minPrice, minVolume, minTurnover, maxSpreadPercent },
    safety: {
      executionAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
    },
  };
}

export default evaluateLiquidity;
