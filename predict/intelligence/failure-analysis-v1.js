export const FAILURE_ANALYSIS_V1 = "failure-analysis-v1";

const RULES = [
  ["LOW_VOLUME", (record) => Number(record?.technical?.volumeRatio ?? record?.volumeRatio) > 0 && Number(record?.technical?.volumeRatio ?? record?.volumeRatio) < 1],
  ["RSI_OVERHEATED", (record) => Number(record?.technical?.rsi ?? record?.rsi) >= 70],
  ["RSI_OVERSOLD_SELL", (record) => String(record?.action).toUpperCase() === "SELL" && Number(record?.technical?.rsi ?? record?.rsi) <= 30],
  ["HIGH_VOLATILITY", (record) => Number(record?.risk?.atrPercent ?? record?.atrPercent) >= 5],
  ["MARKET_HEADWIND", (record) => ["bear", "bearish", "risk_off"].includes(String(record?.marketRegime ?? record?.marketIntelligence?.regime ?? "").toLowerCase()) && String(record?.action).toUpperCase() === "BUY"],
  ["EVENT_RISK", (record) => Boolean(record?.eventRisk ?? record?.marketIntelligence?.eventRisk)],
  ["LOW_CONFIDENCE", (record) => Number(record?.confidence ?? record?.predictionConfidence) < 60],
];

function isLoss(record) {
  const status = String(record?.status ?? record?.outcome ?? "").toUpperCase();
  const result = Number(record?.pnl ?? record?.returnPercent ?? record?.actualReturnPercent);
  return status === "LOSS" || (Number.isFinite(result) && result < 0);
}

export function analyzeFailuresV1(records = []) {
  const losses = (Array.isArray(records) ? records : []).filter(isLoss);
  const counts = new Map();
  const analyzed = losses.map((record) => {
    const reasons = RULES.filter(([, predicate]) => predicate(record)).map(([id]) => id);
    if (!reasons.length) reasons.push("UNCLASSIFIED");
    for (const reason of reasons) counts.set(reason, (counts.get(reason) ?? 0) + 1);
    return { id: record?.id ?? null, symbol: record?.symbol ?? "UNKNOWN", reasons };
  });

  const ranking = [...counts.entries()]
    .map(([reason, count]) => ({ reason, count, ratio: losses.length ? count / losses.length : 0 }))
    .sort((a, b) => b.count - a.count || a.reason.localeCompare(b.reason));

  const suggestions = ranking.slice(0, 5).map((item) => ({
    reason: item.reason,
    action: `REVIEW_WEIGHT_OR_GATE:${item.reason}`,
    requiresWalkForward: true,
    humanApprovalRequired: true,
  }));

  return {
    version: FAILURE_ANALYSIS_V1,
    sampleSize: Array.isArray(records) ? records.length : 0,
    lossCount: losses.length,
    analyzed,
    ranking,
    suggestions,
    automaticProductionUpdateAllowed: false,
  };
}

export default analyzeFailuresV1;
