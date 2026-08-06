export const PAPER_SHADOW_DIFF_VERSION = "phase26-paper-shadow-diff-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = null) => finite(value) ? Number(value) : fallback;

export function comparePaperAndShadow(input = {}, options = {}) {
  const paperPrice = number(input.paperPrice);
  const shadowPrice = number(input.shadowPrice);
  const paperFillRatio = number(input.paperFillRatio, 1);
  const shadowFillRatio = number(input.shadowFillRatio, 0);
  const paperDelayMs = number(input.paperDelayMs, 0);
  const shadowDelayMs = number(input.shadowDelayMs, 0);
  const maxPriceDifferencePercent = number(options.maxPriceDifferencePercent, 1);
  const minFillRatio = number(options.minFillRatio, 0.9);
  const maxDelayDifferenceMs = number(options.maxDelayDifferenceMs, 1500);

  const blockers = [];
  if (!(paperPrice > 0)) blockers.push("PAPER_PRICE_INVALID");
  if (!(shadowPrice > 0)) blockers.push("SHADOW_PRICE_INVALID");

  const priceDifferencePercent = paperPrice > 0 && shadowPrice > 0
    ? Math.abs(shadowPrice - paperPrice) / paperPrice * 100
    : null;
  const fillRatioDifference = shadowFillRatio - paperFillRatio;
  const delayDifferenceMs = shadowDelayMs - paperDelayMs;

  if (priceDifferencePercent !== null && priceDifferencePercent > maxPriceDifferencePercent) blockers.push("PRICE_DIFFERENCE_TOO_LARGE");
  if (shadowFillRatio < minFillRatio) blockers.push("SHADOW_FILL_RATIO_TOO_LOW");
  if (delayDifferenceMs > maxDelayDifferenceMs) blockers.push("SHADOW_DELAY_TOO_HIGH");

  return {
    version: PAPER_SHADOW_DIFF_VERSION,
    status: blockers.length ? "BLOCKED" : "WITHIN_TOLERANCE",
    blockers,
    metrics: {
      paperPrice,
      shadowPrice,
      priceDifferencePercent,
      paperFillRatio,
      shadowFillRatio,
      fillRatioDifference,
      paperDelayMs,
      shadowDelayMs,
      delayDifferenceMs,
    },
    thresholds: { maxPriceDifferencePercent, minFillRatio, maxDelayDifferenceMs },
    safety: {
      mode: "SHADOW_ONLY",
      executionAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
      productionUpdateAllowed: false,
    },
  };
}

export default comparePaperAndShadow;
