export const SHADOW_FILL_FEASIBILITY_VERSION = "phase26-shadow-fill-feasibility-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = null) => finite(value) ? Number(value) : fallback;

export function assessShadowFillFeasibility(input = {}, options = {}) {
  const quantity = Math.max(0, Math.floor(number(input.quantity, 0)));
  const spreadPercent = number(input.spreadPercent);
  const dailyVolume = number(input.dailyVolume ?? input.volume);
  const availableAtPrice = number(input.availableAtPrice ?? input.visibleLiquidity);
  const maxParticipationRate = number(options.maxParticipationRate, 0.01);
  const maxSpreadPercent = number(options.maxSpreadPercent, 1.5);
  const blockers = [];

  if (!(quantity > 0)) blockers.push("QUANTITY_INVALID");
  if (!(dailyVolume > 0)) blockers.push("DAILY_VOLUME_MISSING");
  if (!(availableAtPrice >= 0)) blockers.push("VISIBLE_LIQUIDITY_MISSING");
  if (!(spreadPercent >= 0)) blockers.push("SPREAD_MISSING");
  if (spreadPercent > maxSpreadPercent) blockers.push("SPREAD_TOO_WIDE");

  const participationRate = dailyVolume > 0 ? quantity / dailyVolume : null;
  if (participationRate !== null && participationRate > maxParticipationRate) blockers.push("PARTICIPATION_TOO_HIGH");

  const estimatedFillRatio = quantity > 0 && availableAtPrice !== null
    ? Math.min(1, Math.max(0, availableAtPrice / quantity))
    : 0;
  if (estimatedFillRatio < 1) blockers.push("INSUFFICIENT_VISIBLE_LIQUIDITY");

  return {
    version: SHADOW_FILL_FEASIBILITY_VERSION,
    status: blockers.length ? "BLOCKED" : "FEASIBLE",
    blockers,
    metrics: {
      quantity,
      spreadPercent,
      dailyVolume,
      availableAtPrice,
      participationRate,
      estimatedFillRatio,
      expectedDelayMs: number(input.expectedDelayMs, 0),
    },
    thresholds: { maxParticipationRate, maxSpreadPercent },
    safety: {
      mode: "SHADOW_ONLY",
      executionAllowed: false,
      brokerWriteAllowed: false,
      orderCreationAllowed: false,
      liveTradingAllowed: false,
    },
  };
}

export default assessShadowFillFeasibility;
