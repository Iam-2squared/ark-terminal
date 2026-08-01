import {
  DataQualityError,
  validateHistoryData,
  validateIndicatorCalculations,
} from "../predict/analysis/data-quality.js";
import { calculateIndicators } from "../predict/analysis/indicators.js";
import { createPredictionOutput } from "../predict/analysis/prediction-output.js";
import { scoreAnalysis } from "../predict/analysis/scoring.js";
import { DEFAULT_WEIGHTS } from "../predict/config.js";

function finite(value) {
  if (value === null || value === undefined || value === "") {
    return false;
  }

  return Number.isFinite(Number(value));
}

function riskFromAtr(atrPercent) {
  if (!finite(atrPercent)) {
    return {
      label: "不明",
      level: null,
    };
  }

  if (Number(atrPercent) <= 2) {
    return {
      label: "低",
      level: 1,
    };
  }

  if (Number(atrPercent) <= 4) {
    return {
      label: "中",
      level: 2,
    };
  }

  return {
    label: "高",
    level: 3,
  };
}

function topReasons(analysis, maximum = 3) {
  return analysis.factors
    .filter((factor) => factor.available)
    .sort(
      (first, second) =>
        Math.abs(second.score - 50) * second.weight -
        Math.abs(first.score - 50) * first.weight,
    )
    .slice(0, maximum)
    .map((factor) => factor.reason);
}

function factorScore(analysis, key, fallback = 50) {
  return (
    analysis.factors.find((factor) => factor.key === key)?.score ?? fallback
  );
}

function calculateDiscoveryScore({ analysis, confidence, volumeRatio }) {
  const trend = factorScore(analysis, "movingAverages");
  const rsi = factorScore(analysis, "rsi");
  const macd = factorScore(analysis, "macd");
  const vwap = factorScore(analysis, "vwap");
  const volume = factorScore(analysis, "volume");
  const low52Week = factorScore(analysis, "low52Week");
  const bollinger = factorScore(analysis, "bollingerBands");

  const confidenceBonus = Number(confidence) >= 70 ? 2 : 0;
  const volumeBoost = Number(volumeRatio) >= 1.5
    ? 6
    : Number(volumeRatio) >= 1.2
      ? 4
      : Number(volumeRatio) >= 1.0
        ? 2
        : 0;

  const weighted =
    trend * 0.24 +
    rsi * 0.16 +
    macd * 0.12 +
    vwap * 0.16 +
    volume * 0.14 +
    low52Week * 0.10 +
    bollinger * 0.08;

  return Math.min(
    100,
    Math.max(0, Math.round(weighted / 1 + confidenceBonus + volumeBoost)),
  );
}

function verifiedQuality(history) {
  let quality = validateHistoryData(history);

  if (!quality.canScore) {
    throw new DataQualityError(quality);
  }

  const indicators = calculateIndicators(quality.candles, {
    qualityReport: quality,
  });
  const calculation = validateIndicatorCalculations(
    indicators,
    quality.candles,
  );

  quality = {
    ...quality,
    canScore: quality.canScore && calculation.canScore,
    status: calculation.canScore ? quality.status : "failed",
    issues: [...quality.issues, ...calculation.blockingIssues],
    blockingIssues: [
      ...quality.blockingIssues,
      ...calculation.blockingIssues,
    ],
    calculationValidation: calculation,
  };

  if (!quality.canScore) {
    throw new DataQualityError(quality);
  }

  return {
    quality,
    indicators,
  };
}

export function buildScreenerEntry({
  history,
  metadata = {},
  weights = DEFAULT_WEIGHTS,
  period = 5,
  scannedAt = new Date().toISOString(),
}) {
  const { quality, indicators } = verifiedQuality(history);
  const analysis = scoreAnalysis({
    indicators,
    context: {},
    weights,
  });
  const prediction = createPredictionOutput({
    analysis,
    indicators,
    quality,
    period,
    records: [],
    symbol: history.symbol,
  });
  const risk = riskFromAtr(indicators.atr?.percent);
  const currentPrice = Number(indicators.currentPrice);
  const lotSize = finite(metadata.lotSize) ? Number(metadata.lotSize) : 100;
  const marketCap = finite(metadata.marketCap)
    ? Number(metadata.marketCap)
    : finite(history.meta?.marketCap)
      ? Number(history.meta.marketCap)
      : null;

  const discoveryScore = calculateDiscoveryScore({
    analysis,
    confidence: prediction.confidence.score,
    volumeRatio: indicators.volume?.ratio,
  });

  return {
    symbol: history.symbol,
    code: metadata.code || String(history.symbol).replace(/\.T$/, ""),
    name: metadata.name || history.meta?.shortName || history.symbol,
    market: metadata.market || "未分類",
    sector: metadata.sector || "未分類",
    themes: Array.isArray(metadata.themes) ? metadata.themes : [],
    lotSize,
    currentPrice,
    purchaseAmount: currentPrice * lotSize,
    currency: history.meta?.currency || "JPY",
    dailyChangePercent: indicators.priceChangePercent,
    marketCap,
    volume: indicators.volume?.current ?? null,
    volumeRatio: indicators.volume?.ratio ?? null,
    aiScore: analysis.totalScore,
    discoveryScore,
    technicalScore: analysis.technicalScore,
    direction: prediction.direction,
    confidence: prediction.confidence.score,
    confidenceLabel: prediction.confidence.label,
    expectedMove: prediction.expectedMoveRange?.amplitude ?? null,
    expectedMoveRange: prediction.expectedMoveRange,
    downsideRisk: prediction.downsideRisk,
    risk: risk.label,
    riskLevel: risk.level,
    atrPercent: indicators.atr?.percent ?? null,
    qualityScore: quality.qualityScore,
    dataCoverage: analysis.dataCoverage,
    reasons: topReasons(analysis),
    scannedAt,
    status: "analyzed",
    source: history.provider || "yahoo-finance",
  };
}

export function buildBlockedEntry({
  symbol,
  metadata = {},
  error,
  scannedAt = new Date().toISOString(),
}) {
  return {
    symbol,
    code: metadata.code || String(symbol).replace(/\.T$/, ""),
    name: metadata.name || symbol,
    market: metadata.market || "未分類",
    sector: metadata.sector || "未分類",
    themes: Array.isArray(metadata.themes) ? metadata.themes : [],
    lotSize: finite(metadata.lotSize) ? Number(metadata.lotSize) : 100,
    marketCap: finite(metadata.marketCap)
      ? Number(metadata.marketCap)
      : null,
    aiScore: null,
    confidence: null,
    status: error instanceof DataQualityError ? "blocked" : "failed",
    error: error?.message || "分析データを取得できませんでした。",
    scannedAt,
  };
}

export const ScreenerEngineInternals = {
  riskFromAtr,
  topReasons,
};
