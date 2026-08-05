export const DAILY_PREDICTION_RUN_V1 = "daily-prediction-run-v1";

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, Number(value) || 0));
}

function classify(score, buyThreshold, sellThreshold) {
  if (score >= buyThreshold) return "BUY";
  if (score <= sellThreshold) return "SELL";
  return "NO_TRADE";
}

export function runDailyPredictionV1({
  universe = [],
  market = {},
  buyThreshold = 65,
  sellThreshold = 35,
  asOf = new Date().toISOString(),
} = {}) {
  const predictions = universe.map((item) => {
    const technical = clamp(item.technicalScore ?? item.score ?? 50);
    const news = clamp(item.newsScore ?? 50);
    const earnings = clamp(item.earningsScore ?? 50);
    const marketScore = clamp(((Number(market?.riskScore ?? 0) + 1) / 2) * 100);
    const aiScore = clamp(technical * 0.5 + news * 0.2 + earnings * 0.2 + marketScore * 0.1);
    const disagreement = Math.max(technical, news, earnings, marketScore) - Math.min(technical, news, earnings, marketScore);
    const confidence = clamp(100 - disagreement);
    return {
      symbol: item.symbol ?? null,
      generatedAt: asOf,
      action: classify(aiScore, buyThreshold, sellThreshold),
      aiScore,
      confidence,
      components: { technical, news, earnings, market: marketScore },
      requiresHumanApproval: true,
      brokerExecutionAllowed: false,
    };
  });

  return {
    version: DAILY_PREDICTION_RUN_V1,
    generatedAt: asOf,
    status: predictions.length ? "READY" : "BLOCKED",
    thresholds: { buy: buyThreshold, sell: sellThreshold },
    predictions,
    summary: {
      total: predictions.length,
      buy: predictions.filter((row) => row.action === "BUY").length,
      sell: predictions.filter((row) => row.action === "SELL").length,
      noTrade: predictions.filter((row) => row.action === "NO_TRADE").length,
    },
    predictionHistory: predictions.map((row) => ({ ...row })),
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    brokerExecutionAllowed: false,
  };
}

export default runDailyPredictionV1;
