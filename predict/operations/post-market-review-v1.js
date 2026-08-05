export const POST_MARKET_REVIEW_V1 = "post-market-review-v1";

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function buildPostMarketReviewV1({
  predictions = [],
  outcomes = [],
  previousAccuracy = null,
  driftThreshold = 0.1,
  asOf = new Date().toISOString(),
} = {}) {
  const outcomeMap = new Map(outcomes.map((row) => [row.symbol, row]));
  const evaluated = predictions.map((prediction) => {
    const outcome = outcomeMap.get(prediction.symbol);
    const actualReturn = finite(outcome?.return, null);
    const action = String(prediction.action ?? "NO_TRADE").toUpperCase();
    let correct = null;
    if (actualReturn !== null) {
      if (action === "BUY") correct = actualReturn > 0;
      else if (action === "SELL") correct = actualReturn < 0;
      else correct = Math.abs(actualReturn) < 0.01;
    }
    return {
      symbol: prediction.symbol ?? null,
      action,
      confidence: finite(prediction.confidence),
      aiScore: finite(prediction.aiScore),
      actualReturn,
      correct,
    };
  });
  const labeled = evaluated.filter((row) => row.correct !== null);
  const accuracy = labeled.length ? labeled.filter((row) => row.correct).length / labeled.length : 0;
  const byAction = ["BUY", "SELL", "NO_TRADE"].map((action) => {
    const rows = labeled.filter((row) => row.action === action);
    return {
      action,
      sampleSize: rows.length,
      accuracy: rows.length ? rows.filter((row) => row.correct).length / rows.length : 0,
    };
  });
  const weakSegments = byAction.filter((row) => row.sampleSize > 0 && row.accuracy < 0.5);
  const drift = previousAccuracy === null ? 0 : accuracy - finite(previousAccuracy);
  const driftDetected = previousAccuracy !== null && Math.abs(drift) >= driftThreshold;
  const suggestions = [];
  if (weakSegments.length) suggestions.push("REVIEW_ACTION_THRESHOLDS");
  if (driftDetected) suggestions.push("RECHECK_FEATURES_AND_MARKET_REGIME");
  if (!labeled.length) suggestions.push("WAIT_FOR_MORE_OUTCOMES");

  return {
    version: POST_MARKET_REVIEW_V1,
    generatedAt: asOf,
    status: labeled.length ? "READY" : "DEGRADED",
    overall: { sampleSize: labeled.length, accuracy },
    byAction,
    weakSegments,
    drift: { previousAccuracy, currentAccuracy: accuracy, delta: drift, detected: driftDetected },
    improvementSuggestions: suggestions,
    evaluated,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  };
}

export default buildPostMarketReviewV1;
