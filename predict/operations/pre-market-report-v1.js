export const PRE_MARKET_REPORT_V1 = "pre-market-report-v1";

function top(items = [], limit = 5) {
  return [...items]
    .filter(Boolean)
    .sort((a, b) => Number(b?.score ?? 0) - Number(a?.score ?? 0))
    .slice(0, limit);
}

export function buildPreMarketReportV1({
  market = {},
  sectors = [],
  news = [],
  earnings = [],
  candidates = [],
  risks = [],
  asOf = new Date().toISOString(),
} = {}) {
  const blockers = [];
  if (market?.quality?.futureLeakDetected) blockers.push("MARKET_FUTURE_LEAK");
  if (news.some((item) => item?.publishedAt && Date.parse(item.publishedAt) > Date.parse(asOf))) blockers.push("NEWS_FUTURE_LEAK");
  if (earnings.some((item) => item?.publishedAt && Date.parse(item.publishedAt) > Date.parse(asOf))) blockers.push("EARNINGS_FUTURE_LEAK");

  return {
    version: PRE_MARKET_REPORT_V1,
    generatedAt: new Date().toISOString(),
    asOf,
    status: blockers.length ? "BLOCKED" : "READY",
    market: {
      regime: market?.regime ?? "UNKNOWN",
      riskScore: Number(market?.riskScore ?? 0),
      leadingSectors: market?.leadingSectors ?? top(sectors),
      laggingSectors: market?.laggingSectors ?? [...top(sectors)].reverse(),
    },
    topCandidates: top(candidates, 10),
    importantNews: top(news, 10),
    earningsWatch: top(earnings, 10),
    risks: top(risks, 10),
    watchConditions: top(candidates, 10).map((item) => ({
      symbol: item.symbol ?? null,
      trigger: item.trigger ?? "REASSESS_ON_PRICE_OR_NEWS_CHANGE",
      score: Number(item.score ?? 0),
    })),
    blockers,
    advisoryOnly: true,
    brokerExecutionAllowed: false,
  };
}

export default buildPreMarketReportV1;
