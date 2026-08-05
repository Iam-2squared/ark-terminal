export const NEWS_EARNINGS_INTELLIGENCE_V1 = "news-earnings-intelligence-v1";

function finite(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function pctDelta(actual, reference) {
  const a = finite(actual);
  const r = finite(reference);
  return a === null || r === null || r === 0 ? null : (a - r) / Math.abs(r);
}

function classifyNews(item = {}) {
  const text = `${item.title ?? ""} ${item.summary ?? ""}`.toLowerCase();
  const categories = [];
  if (/earnings|決算|guidance|業績/.test(text)) categories.push("EARNINGS");
  if (/contract|受注|partnership|提携/.test(text)) categories.push("BUSINESS");
  if (/lawsuit|訴訟|investigation|調査/.test(text)) categories.push("LEGAL");
  if (/offering|増資|dilution|希薄化/.test(text)) categories.push("FINANCING");
  if (/product|launch|発売|承認/.test(text)) categories.push("PRODUCT");
  return categories.length ? categories : ["GENERAL"];
}

function sentimentScore(item = {}) {
  if (finite(item.sentiment) !== null) return Math.max(-1, Math.min(1, finite(item.sentiment)));
  const text = `${item.title ?? ""} ${item.summary ?? ""}`.toLowerCase();
  const positive = (text.match(/beat|上方修正|増益|最高益|approval|承認|受注/g) ?? []).length;
  const negative = (text.match(/miss|下方修正|減益|赤字|lawsuit|訴訟|希薄化/g) ?? []).length;
  const total = positive + negative;
  return total ? (positive - negative) / total : 0;
}

export function analyzeNewsAndEarnings({ earnings = {}, news = [], asOf = null } = {}) {
  const metrics = {
    revenueVsPrior: pctDelta(earnings.revenue, earnings.priorRevenue),
    revenueVsConsensus: pctDelta(earnings.revenue, earnings.consensusRevenue),
    operatingProfitVsPrior: pctDelta(earnings.operatingProfit, earnings.priorOperatingProfit),
    operatingProfitVsConsensus: pctDelta(earnings.operatingProfit, earnings.consensusOperatingProfit),
    guidanceVsPrior: pctDelta(earnings.guidance, earnings.priorGuidance),
  };
  const guidanceDirection = metrics.guidanceVsPrior === null
    ? "UNKNOWN"
    : metrics.guidanceVsPrior > 0.02 ? "RAISED" : metrics.guidanceVsPrior < -0.02 ? "LOWERED" : "UNCHANGED";
  const events = news.map((item) => {
    const sentiment = sentimentScore(item);
    const ageHours = asOf && item.publishedAt
      ? Math.max(0, (Date.parse(asOf) - Date.parse(item.publishedAt)) / 3_600_000)
      : null;
    const recency = ageHours === null ? 0.5 : Math.max(0, 1 - ageHours / 168);
    const sourceWeight = finite(item.sourceWeight, 1) ?? 1;
    const importance = Math.min(100, Math.round((Math.abs(sentiment) * 60 + recency * 40) * sourceWeight));
    return {
      id: item.id ?? null,
      title: item.title ?? null,
      publishedAt: item.publishedAt ?? null,
      categories: classifyNews(item),
      sentiment,
      importance,
      expectedImpactWindow: importance >= 75 ? "1-5D" : importance >= 45 ? "1-3D" : "INTRADAY",
    };
  }).sort((a, b) => b.importance - a.importance);
  const aggregateSentiment = events.length
    ? events.reduce((sum, event) => sum + event.sentiment * Math.max(1, event.importance), 0) /
      events.reduce((sum, event) => sum + Math.max(1, event.importance), 0)
    : 0;
  const futureLeakDetected = asOf
    ? news.some((item) => item.publishedAt && Date.parse(item.publishedAt) > Date.parse(asOf))
    : false;
  const earningsScore = Object.values(metrics)
    .filter((value) => value !== null)
    .reduce((sum, value) => sum + Math.max(-1, Math.min(1, value)), 0);

  return {
    version: NEWS_EARNINGS_INTELLIGENCE_V1,
    generatedAt: new Date().toISOString(),
    status: futureLeakDetected ? "BLOCKED" : "READY",
    earnings: {
      summary: metrics,
      guidanceDirection,
      score: earningsScore,
    },
    news: {
      sentiment: aggregateSentiment,
      events,
      topEvents: events.slice(0, 10),
    },
    integratedSignal: {
      score: Math.max(-100, Math.min(100, earningsScore * 20 + aggregateSentiment * 40)),
      confidence: Math.min(100, events.length * 10 + Object.values(metrics).filter((value) => value !== null).length * 15),
    },
    quality: {
      futureLeakDetected,
      newsCount: news.length,
      earningsMetricCount: Object.values(metrics).filter((value) => value !== null).length,
    },
    advisoryOnly: true,
    brokerExecutionAllowed: false,
  };
}

export default analyzeNewsAndEarnings;
