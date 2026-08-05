export const NOTIFICATION_DAILY_SUMMARY_V1 = "notification-daily-summary-v1";

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function buildNotificationDailySummaryV1({
  preMarket = {},
  predictions = {},
  paperTrading = {},
  postMarket = {},
  thresholds = { confidence: 75, aiScore: 70 },
  asOf = new Date().toISOString(),
} = {}) {
  const alerts = [];
  for (const row of predictions?.predictions ?? []) {
    if (finite(row.confidence) >= finite(thresholds.confidence) && finite(row.aiScore) >= finite(thresholds.aiScore)) {
      alerts.push({ type: "HIGH_CONFIDENCE_SIGNAL", symbol: row.symbol, action: row.action, confidence: row.confidence, aiScore: row.aiScore });
    }
  }
  if (preMarket?.status === "BLOCKED") alerts.push({ type: "PRE_MARKET_BLOCKED", blockers: preMarket.blockers ?? [] });
  if (paperTrading?.killSwitch) alerts.push({ type: "PAPER_TRADING_HALTED" });
  if (postMarket?.drift?.detected) alerts.push({ type: "MODEL_DRIFT", delta: postMarket.drift.delta });
  if ((postMarket?.weakSegments ?? []).length) alerts.push({ type: "WEAK_SEGMENTS", segments: postMarket.weakSegments });

  return {
    version: NOTIFICATION_DAILY_SUMMARY_V1,
    generatedAt: asOf,
    status: "READY",
    morning: {
      marketRegime: preMarket?.market?.regime ?? "UNKNOWN",
      topCandidates: preMarket?.topCandidates ?? [],
      risks: preMarket?.risks ?? [],
    },
    evening: {
      predictions: predictions?.summary ?? { total: 0, buy: 0, sell: 0, noTrade: 0 },
      paperOrders: paperTrading?.orders?.length ?? 0,
      paperFills: paperTrading?.fills?.length ?? 0,
      accuracy: postMarket?.overall?.accuracy ?? 0,
      sampleSize: postMarket?.overall?.sampleSize ?? 0,
      improvementSuggestions: postMarket?.improvementSuggestions ?? [],
    },
    alerts,
    notificationCount: alerts.length,
    advisoryOnly: true,
    automaticPromotionAllowed: false,
    brokerExecutionAllowed: false,
    humanApprovalRequired: true,
  };
}

export default buildNotificationDailySummaryV1;
