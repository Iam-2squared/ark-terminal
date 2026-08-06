export const FAILURE_REVIEW_V3_VERSION = "phase25-failure-review-v3";

const finite = (value) => Number.isFinite(Number(value));
const normalize = (value, fallback = "UNKNOWN") => String(value ?? fallback).trim().toUpperCase() || fallback;

export function buildFailureReviewV3(rows = []) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");

  const failures = rows
    .filter((row) => normalize(row.status) === "RESOLVED")
    .filter((row) => finite(row.netReturn) && Number(row.netReturn) < 0)
    .map((row) => {
      const confidence = finite(row.confidence) ? Number(row.confidence) : null;
      const actualDirection = normalize(row.actualDirection ?? (Number(row.netReturn) >= 0 ? "UP" : "DOWN"));
      const predictedDirection = normalize(row.predictedDirection ?? row.signal);
      const confidenceGap = confidence === null ? null : Math.max(0, confidence - 0.5);
      const hypotheses = [];
      if (confidence !== null && confidence >= 0.75) hypotheses.push("OVERCONFIDENT_SIGNAL");
      if (normalize(row.marketRegime) === "UNKNOWN") hypotheses.push("REGIME_CONTEXT_MISSING");
      if (finite(row.slippagePercent) && Number(row.slippagePercent) >= 0.5) hypotheses.push("HIGH_SLIPPAGE");
      if (finite(row.holdingPeriod) && Number(row.holdingPeriod) <= 1) hypotheses.push("HOLDING_PERIOD_TOO_SHORT");
      if (!row.newsFeatures) hypotheses.push("NEWS_CONTEXT_MISSING");
      if (!row.technicalFeatures) hypotheses.push("TECHNICAL_CONTEXT_MISSING");
      if (predictedDirection === actualDirection) hypotheses.push("DIRECTION_RIGHT_BUT_COST_OR_TIMING_FAILED");

      return {
        id: row.id ?? null,
        symbol: normalize(row.symbol),
        marketRegime: normalize(row.marketRegime),
        predictedDirection,
        actualDirection,
        confidence,
        confidenceGap,
        holdingPeriod: finite(row.holdingPeriod) ? Number(row.holdingPeriod) : null,
        grossReturn: finite(row.grossReturn) ? Number(row.grossReturn) : null,
        netReturn: Number(row.netReturn),
        feePercent: finite(row.feePercent) ? Number(row.feePercent) : 0,
        slippagePercent: finite(row.slippagePercent) ? Number(row.slippagePercent) : 0,
        newsFeatures: row.newsFeatures ?? null,
        technicalFeatures: row.technicalFeatures ?? null,
        hypotheses,
      };
    });

  const hypothesisCounts = new Map();
  for (const failure of failures) {
    for (const hypothesis of failure.hypotheses) {
      hypothesisCounts.set(hypothesis, (hypothesisCounts.get(hypothesis) ?? 0) + 1);
    }
  }

  return {
    version: FAILURE_REVIEW_V3_VERSION,
    failureCount: failures.length,
    failures,
    topHypotheses: [...hypothesisCounts.entries()]
      .map(([hypothesis, count]) => ({ hypothesis, count }))
      .sort((a, b) => b.count - a.count || a.hypothesis.localeCompare(b.hypothesis)),
    safety: {
      advisoryOnly: true,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
    },
  };
}

export default buildFailureReviewV3;
