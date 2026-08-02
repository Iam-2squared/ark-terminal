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

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number(value)));
}

function scoreMovingAverageAlignment(indicators) {
  const { currentPrice } = indicators;
  const ma = indicators.movingAverages || {};
  const values = [currentPrice, ma.ma5, ma.ma25, ma.ma75, ma.ma200];

  if (values.some((value) => !finite(value))) {
    return 50;
  }

  const alignmentCount = [
    currentPrice > ma.ma5,
    ma.ma5 > ma.ma25,
    ma.ma25 > ma.ma75,
    ma.ma75 > ma.ma200,
  ].filter(Boolean).length;

  const alignmentScore = (alignmentCount / 4) * 100;
  const slope = finite(ma.ma5) && finite(ma.ma25)
    ? (ma.ma5 - ma.ma25) / Math.max(1, Math.abs(ma.ma25))
    : 0;
  const slopeScore = clamp(50 + slope * 140, 25, 95);

  const crossedUp =
    finite(ma.previousMa5) &&
    finite(ma.previousMa25) &&
    ma.previousMa5 <= ma.previousMa25 &&
    ma.ma5 > ma.ma25;
  const crossedDown =
    finite(ma.previousMa5) &&
    finite(ma.previousMa25) &&
    ma.previousMa5 >= ma.previousMa25 &&
    ma.ma5 < ma.ma25;

  const crossBonus = crossedUp ? 6 : crossedDown ? -6 : 0;

  return clamp(alignmentScore * 0.72 + slopeScore * 0.28 + crossBonus, 25, 97);
}

function scoreRsiPosition(rsi) {
  if (!finite(rsi)) {
    return 50;
  }

  if (rsi <= 30) {
    return clamp(40 + (rsi / 30) * 15, 40, 55);
  }

  if (rsi <= 45) {
    return clamp(55 + ((rsi - 30) / 15) * 15, 55, 70);
  }

  if (rsi <= 60) {
    return clamp(70 + ((rsi - 45) / 15) * 10, 70, 80);
  }

  if (rsi <= 70) {
    return clamp(80 - ((rsi - 60) / 10) * 15, 65, 80);
  }

  if (rsi <= 80) {
    return clamp(65 - ((rsi - 70) / 10) * 25, 40, 65);
  }

  return 40;
}

function scoreMacdStrength(macd) {
  if (!macd || !finite(macd.value) || !finite(macd.signal) || !finite(macd.histogram)) {
    return 50;
  }

  const hist = clamp(macd.histogram, -5, 5);
  const base = clamp(50 + hist * 7, 25, 90);

  const crossedUp =
    finite(macd.previousValue) &&
    finite(macd.previousSignal) &&
    macd.previousValue <= macd.previousSignal &&
    macd.value > macd.signal;
  const crossedDown =
    finite(macd.previousValue) &&
    finite(macd.previousSignal) &&
    macd.previousValue >= macd.previousSignal &&
    macd.value < macd.signal;

  return clamp(base + (crossedUp ? 8 : crossedDown ? -8 : 0), 25, 92);
}

function scoreVwapDistance(indicators) {
  if (!finite(indicators.vwap) || !finite(indicators.currentPrice)) {
    return 50;
  }

  const diff = (indicators.currentPrice - indicators.vwap) / Math.max(1, indicators.vwap);
  return clamp(50 + diff * 160, 20, 95);
}

function scoreVolumeRatio(ratio, priceChangePercent) {
  if (!finite(ratio)) {
    return 50;
  }

  const normalized = clamp((ratio - 0.6) / 1.9, 0, 1);
  const base = 40 + normalized * 40;
  const directionBonus = finite(priceChangePercent)
    ? priceChangePercent >= 0
      ? 8
      : -4
    : 0;

  return clamp(base + directionBonus, 25, 92);
}

function score52WeekPosition(indicators) {
  const low = indicators.distanceFrom52WeekLow;
  const high = indicators.distanceFrom52WeekHigh;

  const lowScore = finite(low)
    ? clamp(60 + Math.min(100, low) * 0.2, 60, 90)
    : 50;
  const highScore = finite(high)
    ? clamp(82 - Math.min(100, Math.max(-50, high)) * 0.35, 40, 90)
    : 50;

  return clamp(lowScore * 0.55 + highScore * 0.45, 40, 90);
}

function scoreRisk(atrPercent) {
  if (!finite(atrPercent)) {
    return 55;
  }

  return clamp(85 - atrPercent * 6.5, 25, 85);
}

function scoreConfidence(confidence) {
  if (!finite(confidence)) {
    return 50;
  }

  return clamp(30 + Number(confidence) * 0.65, 30, 95);
}

function scoreQuality(quality) {
  if (!quality || !finite(quality.qualityScore)) {
    return 50;
  }

  return clamp(30 + quality.qualityScore * 0.45, 30, 95);
}

function calculateDiscoveryScore({ analysis, indicators, confidence, quality }) {
  const trendScore = scoreMovingAverageAlignment(indicators);
  const rsiScore = scoreRsiPosition(indicators.rsi);
  const macdScore = scoreMacdStrength(indicators.macd);
  const vwapScore = scoreVwapDistance(indicators);
  const volumeScore = scoreVolumeRatio(indicators.volume?.ratio, indicators.priceChangePercent);
  const positionScore = score52WeekPosition(indicators);
  const riskScore = scoreRisk(indicators.atr?.percent);
  const confidenceScore = scoreConfidence(confidence);
  const qualityScore = scoreQuality(quality);

  const baselineScore = finite(analysis?.totalScore)
    ? Number(analysis.totalScore)
    : 60;

  const weighted =
    baselineScore * 0.48 +
    trendScore * 0.14 +
    rsiScore * 0.09 +
    macdScore * 0.08 +
    vwapScore * 0.06 +
    volumeScore * 0.08 +
    positionScore * 0.07 +
    riskScore * 0.04 +
    confidenceScore * 0.03 +
    qualityScore * 0.01;

  return Number(clamp(weighted, 0, 100).toFixed(2));
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
    indicators,
    confidence: prediction.confidence.score,
    quality,
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
