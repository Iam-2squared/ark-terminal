export const DISCOVERY_RANKING_ADAPTER_V2 = "discovery-ranking-adapter-v2";

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, finite(value)));
}

function riskAdjustment(entry) {
  const level = finite(entry.riskLevel, 2);
  if (level <= 1) return 3;
  if (level >= 3) return -6;
  return 0;
}

function confidenceAdjustment(entry) {
  const confidence = clamp(entry.confidence, 0, 100);
  return (confidence - 50) * 0.08;
}

function marketRegimeAdjustment(entry, context = {}) {
  const regime = String(context.marketRegime ?? entry.marketRegime ?? "neutral").toLowerCase();
  const direction = String(entry.direction ?? "neutral").toLowerCase();

  if (["bull", "bullish", "risk_on"].includes(regime)) {
    return direction.includes("up") || direction.includes("bull") ? 4 : -1;
  }
  if (["bear", "bearish", "risk_off"].includes(regime)) {
    return direction.includes("down") || direction.includes("bear") ? 3 : -5;
  }
  return 0;
}

function sectorAdjustment(entry, context = {}) {
  const sectorScores = context.sectorScores ?? {};
  const raw = sectorScores[entry.sector];
  if (!Number.isFinite(Number(raw))) return 0;
  return clamp(Number(raw), -10, 10);
}

export function rankDiscoveryEntry(entry = {}, context = {}) {
  const baseScore = finite(entry.discoveryScore ?? entry.aiScore, 0);
  const adjustments = {
    confidence: Number(confidenceAdjustment(entry).toFixed(2)),
    risk: Number(riskAdjustment(entry).toFixed(2)),
    marketRegime: Number(marketRegimeAdjustment(entry, context).toFixed(2)),
    sector: Number(sectorAdjustment(entry, context).toFixed(2)),
  };
  const compositeScore = clamp(
    baseScore +
      adjustments.confidence +
      adjustments.risk +
      adjustments.marketRegime +
      adjustments.sector,
  );

  const reasons = [
    `Base ${baseScore.toFixed(1)}`,
    `Confidence ${adjustments.confidence >= 0 ? "+" : ""}${adjustments.confidence.toFixed(1)}`,
    `Risk ${adjustments.risk >= 0 ? "+" : ""}${adjustments.risk.toFixed(1)}`,
    `Market ${adjustments.marketRegime >= 0 ? "+" : ""}${adjustments.marketRegime.toFixed(1)}`,
    `Sector ${adjustments.sector >= 0 ? "+" : ""}${adjustments.sector.toFixed(1)}`,
  ];

  return {
    ...entry,
    compositeScore: Number(compositeScore.toFixed(2)),
    rankingScore: Number(compositeScore.toFixed(2)),
    rankingAdjustments: adjustments,
    rankingReasons: reasons,
    rankingVersion: DISCOVERY_RANKING_ADAPTER_V2,
  };
}

export function rankDiscoveryEntries(entries = [], context = {}) {
  return (Array.isArray(entries) ? entries : [])
    .map((entry) => rankDiscoveryEntry(entry, context))
    .sort((first, second) => {
      const scoreDifference = second.rankingScore - first.rankingScore;
      if (scoreDifference !== 0) return scoreDifference;
      return String(first.symbol ?? "").localeCompare(String(second.symbol ?? ""));
    });
}
