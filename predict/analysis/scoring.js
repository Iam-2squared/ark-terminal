import {
  explain52WeekHigh,
  explain52WeekLow,
  explainAdx,
  explainAtr,
  explainBollinger,
  explainMacd,
  explainMovingAverages,
  explainRsi,
  explainStochastic,
  explainVolume,
  explainVwap,
} from "./explanations.js";
import { scoreContextFactors } from "./context-scoring.js";

function finite(value) {
  return Number.isFinite(Number(value));
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number(value)));
}

function verdict(score) {
  if (score >= 75) {
    return "強気";
  }

  if (score >= 60) {
    return "やや強気";
  }

  if (score >= 45) {
    return "中立";
  }

  if (score >= 30) {
    return "やや弱気";
  }

  return "弱気";
}

function factor({
  key,
  label,
  category,
  weight,
  score,
  reason,
  available = true,
}) {
  const normalizedScore = available ? Math.round(clamp(score)) : null;

  return {
    key,
    label,
    category,
    weight: Number(weight) || 0,
    score: normalizedScore,
    contribution: available
      ? (normalizedScore * (Number(weight) || 0)) / 100
      : 0,
    verdict: available ? verdict(normalizedScore) : "データなし",
    reason: available
      ? reason
      : reason || `${label}のデータを取得できませんでした。`,
    available,
  };
}

function unavailable(key, label, category, weight, reason) {
  return factor({
    key,
    label,
    category,
    weight,
    score: 0,
    reason,
    available: false,
  });
}

function scoreMovingAverages(indicators, weight) {
  const { currentPrice } = indicators;

  const { ma5, ma25, ma75, ma200 } = indicators.movingAverages || {};

  const values = [currentPrice, ma5, ma25, ma75, ma200];

  if (values.some((value) => !finite(value))) {
    return unavailable(
      "movingAverages",
      "移動平均線",
      "technical",
      weight,
      "5日・25日・75日・200日移動平均線の計算に必要な履歴が不足しています。",
    );
  }

  const comparisons = [
    currentPrice > ma5,
    ma5 > ma25,
    ma25 > ma75,
    ma75 > ma200,
  ];

  let score = (comparisons.filter(Boolean).length / comparisons.length) * 100;

  const crossedUp =
    finite(indicators.movingAverages.previousMa5) &&
    finite(indicators.movingAverages.previousMa25) &&
    indicators.movingAverages.previousMa5 <=
      indicators.movingAverages.previousMa25 &&
    ma5 > ma25;

  if (crossedUp) {
    score += 10;
  }

  return factor({
    key: "movingAverages",
    label: "移動平均線（5・25・75・200日）",
    category: "technical",
    weight,
    score,
    reason: explainMovingAverages({
      currentPrice,
      ma5,
      ma25,
      ma75,
      ma200,
    }),
  });
}

function scoreRsi(indicators, weight) {
  const rsi = indicators.rsi;

  if (!finite(rsi)) {
    return unavailable("rsi", "RSI", "technical", weight);
  }

  let score;

  if (rsi >= 80) {
    score = 20;
  } else if (rsi >= 70) {
    score = 38;
  } else if (rsi >= 55) {
    score = 72;
  } else if (rsi >= 45) {
    score = 58;
  } else if (rsi >= 30) {
    score = 45;
  } else if (rsi >= 20) {
    score = 55;
  } else {
    score = 35;
  }

  return factor({
    key: "rsi",
    label: "RSI（14日）",
    category: "technical",
    weight,
    score,
    reason: explainRsi(rsi),
  });
}

function scoreMacd(indicators, weight) {
  const macd = indicators.macd;

  if (!macd || !finite(macd.value) || !finite(macd.signal)) {
    return unavailable("macd", "MACD", "technical", weight);
  }

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

  const score = crossedUp
    ? 92
    : crossedDown
      ? 18
      : macd.histogram >= 0
        ? 72
        : 32;

  return factor({
    key: "macd",
    label: "MACD",
    category: "technical",
    weight,
    score,
    reason: explainMacd(macd),
  });
}

function scoreBollinger(indicators, weight) {
  const bands = indicators.bollingerBands;

  if (!bands || !finite(bands.percentB)) {
    return unavailable(
      "bollingerBands",
      "ボリンジャーバンド",
      "technical",
      weight,
    );
  }

  let score;

  if (bands.percentB > 1.1) {
    score = 30;
  } else if (bands.percentB > 0.75) {
    score = 72;
  } else if (bands.percentB >= 0.35) {
    score = 58;
  } else if (bands.percentB >= 0) {
    score = 42;
  } else {
    score = 38;
  }

  return factor({
    key: "bollingerBands",
    label: "ボリンジャーバンド",
    category: "technical",
    weight,
    score,
    reason: explainBollinger(bands),
  });
}

function scoreVolume(indicators, weight) {
  const volume = indicators.volume;

  if (
    !volume ||
    !finite(volume.ratio) ||
    !finite(indicators.priceChangePercent)
  ) {
    return unavailable("volume", "出来高増減", "technical", weight);
  }

  const rising = indicators.priceChangePercent >= 0;

  let score = 50;

  if (volume.ratio >= 1.5) {
    score = rising ? 88 : 20;
  } else if (volume.ratio >= 1.1) {
    score = rising ? 70 : 35;
  } else if (volume.ratio <= 0.6) {
    score = 45;
  }

  return factor({
    key: "volume",
    label: "出来高増減",
    category: "technical",
    weight,
    score,
    reason: explainVolume(volume, indicators.priceChangePercent),
  });
}

function scoreAdx(indicators, weight) {
  const adx = indicators.adx;

  if (!adx || !finite(adx.value)) {
    return unavailable("adx", "ADX", "technical", weight);
  }

  const upward = adx.plusDi >= adx.minusDi;

  const score = adx.value >= 25 ? (upward ? 78 : 24) : upward ? 57 : 43;

  return factor({
    key: "adx",
    label: "ADX（14日）",
    category: "technical",
    weight,
    score,
    reason: explainAdx(adx),
  });
}

function scoreAtr(indicators, weight) {
  const atr = indicators.atr;

  if (!atr || !finite(atr.percent)) {
    return unavailable("atr", "ATR", "technical", weight);
  }

  const score =
    atr.percent <= 2 ? 68 : atr.percent <= 4 ? 58 : atr.percent <= 7 ? 40 : 24;

  return factor({
    key: "atr",
    label: "ATR（14日）",
    category: "technical",
    weight,
    score,
    reason: explainAtr(atr),
  });
}

function scoreStochastic(indicators, weight) {
  const stochastic = indicators.stochastic;

  if (!stochastic || !finite(stochastic.k) || !finite(stochastic.d)) {
    return unavailable("stochastic", "ストキャスティクス", "technical", weight);
  }

  let score;

  if (stochastic.k <= 20 && stochastic.k > stochastic.d) {
    score = 76;
  } else if (stochastic.k >= 80) {
    score = 32;
  } else {
    score = stochastic.k >= stochastic.d ? 65 : 40;
  }

  return factor({
    key: "stochastic",
    label: "ストキャスティクス",
    category: "technical",
    weight,
    score,
    reason: explainStochastic(stochastic),
  });
}

function scoreVwap(indicators, weight) {
  if (!finite(indicators.vwap) || !finite(indicators.currentPrice)) {
    return unavailable("vwap", "VWAP", "technical", weight);
  }

  const score = indicators.currentPrice >= indicators.vwap ? 70 : 35;

  return factor({
    key: "vwap",
    label: "VWAP（20日）",
    category: "technical",
    weight,
    score,
    reason: explainVwap(indicators.currentPrice, indicators.vwap),
  });
}

function score52WeekHigh(indicators, weight) {
  const distance = indicators.distanceFrom52WeekHigh;

  if (!finite(distance)) {
    return unavailable("high52Week", "52週高値との差", "technical", weight);
  }

  const score =
    distance >= -3 ? 78 : distance >= -10 ? 68 : distance >= -25 ? 48 : 30;

  return factor({
    key: "high52Week",
    label: "52週高値との差",
    category: "technical",
    weight,
    score,
    reason: explain52WeekHigh(distance),
  });
}

function score52WeekLow(indicators, weight) {
  const distance = indicators.distanceFrom52WeekLow;

  if (!finite(distance)) {
    return unavailable("low52Week", "52週安値との差", "technical", weight);
  }

  const score =
    distance >= 50 ? 72 : distance >= 20 ? 62 : distance >= 5 ? 45 : 25;

  return factor({
    key: "low52Week",
    label: "52週安値との差",
    category: "technical",
    weight,
    score,
    reason: explain52WeekLow(distance),
  });
}

export function getOverallResult(totalScore) {
  if (totalScore >= 75) {
    return {
      label: "強気",
      className: "strongBullish",
    };
  }

  if (totalScore >= 60) {
    return {
      label: "やや強気",
      className: "bullish",
    };
  }

  if (totalScore >= 45) {
    return {
      label: "中立",
      className: "neutral",
    };
  }

  if (totalScore >= 30) {
    return {
      label: "やや弱気",
      className: "bearish",
    };
  }

  return {
    label: "弱気",
    className: "strongBearish",
  };
}

export function scoreAnalysis({ indicators, context = {}, weights }) {
  const factors = [
    scoreMovingAverages(indicators, weights.movingAverages),
    scoreRsi(indicators, weights.rsi),
    scoreMacd(indicators, weights.macd),
    scoreBollinger(indicators, weights.bollingerBands),
    scoreVolume(indicators, weights.volume),
    scoreAdx(indicators, weights.adx),
    scoreAtr(indicators, weights.atr),
    scoreStochastic(indicators, weights.stochastic),
    scoreVwap(indicators, weights.vwap),
    score52WeekHigh(indicators, weights.high52Week),
    score52WeekLow(indicators, weights.low52Week),
    ...scoreContextFactors(context, weights),
  ];

  const totalWeight = Object.values(weights).reduce(
    (sum, value) => sum + Number(value),
    0,
  );

  const availableFactors = factors.filter((item) => item.available);

  const availableWeight = availableFactors.reduce(
    (sum, item) => sum + item.weight,
    0,
  );

  const weightedTotal = availableFactors.reduce(
    (sum, item) => sum + item.contribution,
    0,
  );

  const totalScore =
    availableWeight > 0
      ? Math.round((weightedTotal / availableWeight) * 100)
      : 50;

  const technicalFactors = availableFactors.filter(
    (item) => item.category === "technical",
  );

  const technicalWeight = technicalFactors.reduce(
    (sum, item) => sum + item.weight,
    0,
  );

  const technicalScore =
    technicalWeight > 0
      ? Math.round(
          (technicalFactors.reduce((sum, item) => sum + item.contribution, 0) /
            technicalWeight) *
            100,
        )
      : null;

  return {
    totalScore,
    technicalScore,
    dataCoverage:
      totalWeight > 0 ? Math.round((availableWeight / totalWeight) * 100) : 0,
    availableCount: availableFactors.length,
    totalCount: factors.length,
    availableWeight,
    totalWeight,
    factors,
    result: getOverallResult(totalScore),
  };
}

export const ScoringInternals = {
  verdict,
};
