import {
  explainMovingAverages,
  explainRsi,
  explainMacd,
  explainBollinger,
  explainVolume,
  explainAdx,
  explainAtr,
  explainStochastic,
  explainVwap,
} from "./explanations.js";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number(value) || 0));
}

function formatPercent(value, digits = 1) {
  return finite(value) ? `${Number(value).toFixed(digits)}%` : null;
}

function trendStrength(indicators) {
  const { movingAverages, macd, adx, priceChangePercent } = indicators;
  const trendScore = [];

  if (
    movingAverages &&
    finite(movingAverages.ma5) &&
    finite(movingAverages.ma25) &&
    finite(movingAverages.ma75) &&
    finite(movingAverages.ma200)
  ) {
    trendScore.push(
      movingAverages.ma5 > movingAverages.ma25 &&
        movingAverages.ma25 > movingAverages.ma75 &&
        movingAverages.ma75 > movingAverages.ma200
        ? 2
        : 0,
    );
  }

  if (macd && finite(macd.histogram)) {
    trendScore.push(macd.histogram > 0 ? 1 : 0);
  }

  if (adx && finite(adx.value)) {
    trendScore.push(adx.value >= 25 ? 1 : 0);
  }

  if (finite(priceChangePercent)) {
    trendScore.push(priceChangePercent >= 0 ? 1 : 0);
  }

  return trendScore.reduce((sum, value) => sum + value, 0);
}

function hasBullishMovingAverageAlignment(indicators) {
  const { movingAverages } = indicators;

  return (
    movingAverages &&
    finite(movingAverages.ma5) &&
    finite(movingAverages.ma25) &&
    finite(movingAverages.ma75) &&
    finite(movingAverages.ma200) &&
    indicators.currentPrice > movingAverages.ma5 &&
    movingAverages.ma5 > movingAverages.ma25 &&
    movingAverages.ma25 > movingAverages.ma75 &&
    movingAverages.ma75 > movingAverages.ma200
  );
}

function hasMacdBullishSignal(indicators) {
  const { macd } = indicators;

  if (!macd || !finite(macd.value) || !finite(macd.signal)) {
    return false;
  }

  return (
    finite(macd.previousValue) &&
    finite(macd.previousSignal) &&
    macd.previousValue <= macd.previousSignal &&
    macd.value > macd.signal
  );
}

function hasMacdBearishSignal(indicators) {
  const { macd } = indicators;

  if (!macd || !finite(macd.value) || !finite(macd.signal)) {
    return false;
  }

  return (
    finite(macd.previousValue) &&
    finite(macd.previousSignal) &&
    macd.previousValue >= macd.previousSignal &&
    macd.value < macd.signal
  );
}

function isAboveVwap(indicators) {
  return (
    indicators.vwap !== null &&
    finite(indicators.currentPrice) &&
    finite(indicators.vwap) &&
    indicators.currentPrice >= indicators.vwap
  );
}

function isBelowVwap(indicators) {
  return (
    indicators.vwap !== null &&
    finite(indicators.currentPrice) &&
    finite(indicators.vwap) &&
    indicators.currentPrice < indicators.vwap
  );
}

function isAtUpperBollinger(indicators) {
  return (
    indicators.bollingerBands &&
    finite(indicators.bollingerBands.percentB) &&
    indicators.bollingerBands.percentB > 0.85
  );
}

function isAtLowerBollinger(indicators) {
  return (
    indicators.bollingerBands &&
    finite(indicators.bollingerBands.percentB) &&
    indicators.bollingerBands.percentB < 0.25
  );
}

function isOverheatedRsi(indicators) {
  return finite(indicators.rsi) && indicators.rsi >= 70;
}

function isOversoldRsi(indicators) {
  return finite(indicators.rsi) && indicators.rsi <= 30;
}

function isVolatileAtr(indicators) {
  return indicators.atr && finite(indicators.atr.percent) && indicators.atr.percent >= 5;
}

function isStrongTrend(indicators) {
  return indicators.adx && finite(indicators.adx.value) && indicators.adx.value >= 25;
}

function collectBuyFactors(state) {
  const { indicators, analysis } = state;
  const factors = [];

  if (hasBullishMovingAverageAlignment(indicators)) {
    factors.push(
      "移動平均線が上向きの並びを示しており、中期的な上昇トレンドが優勢です。",
    );
  }

  if (hasMacdBullishSignal(indicators)) {
    factors.push("MACDのゴールデンクロスが確認され、上昇モメンタムが強まっています。");
  }

  if (isAboveVwap(indicators)) {
    factors.push("株価が20日VWAPの上にあり、需給面で買い優勢です。");
  }

  if (indicators.volume && finite(indicators.volume.ratio) && indicators.volume.ratio > 1.1) {
    factors.push("出来高が20日平均を上回り、買い圧力を伴った値動きです。");
  }

  if (finite(indicators.rsi) && indicators.rsi >= 40 && indicators.rsi <= 60) {
    factors.push("RSIは中立圏にあり、過熱感が少なく上昇余地があります。");
  }

  if (isAtLowerBollinger(indicators)) {
    factors.push("株価がボリンジャーバンドの下限付近にあり、反発の可能性があります。");
  }

  if (analysis && finite(analysis.discoveryScore)) {
    factors.push(`Discoveryスコアは${Math.round(analysis.discoveryScore)}点で、銘柄評価の裏付けがあります。`);
  }

  if (!factors.length) {
    factors.push("現時点で明確な買い要因は限定的ですが、複数の指標を併せて確認すると良いでしょう。");
  }

  return factors.slice(0, 5);
}

function collectRiskFactors(indicators) {
  const factors = [];

  if (isOverheatedRsi(indicators)) {
    factors.push("RSIが70以上で、短期的な買われ過ぎによる反落リスクがあります。");
  }

  if (isAtUpperBollinger(indicators)) {
    factors.push("株価がボリンジャーバンドの上限付近で、短期的な調整が入りやすい状況です。");
  }

  if (isVolatileAtr(indicators)) {
    factors.push("ATRが大きく、値動きが荒いため損切り幅やリスク管理が重要です。");
  }

  if (indicators.volume && finite(indicators.volume.ratio) && indicators.volume.ratio < 0.85) {
    factors.push("出来高が20日平均を下回り、値動きに勢いが乏しい可能性があります。");
  }

  if (!isStrongTrend(indicators)) {
    factors.push("ADXが低く、トレンドの強さに一貫性が見られません。");
  }

  if (!factors.length) {
    factors.push("現時点で大きなリスク要因は見られませんが、指標の変動に注意を払ってください。");
  }

  return factors.slice(0, 5);
}

function deriveStance(score) {
  if (score >= 70) {
    return "強気";
  }

  if (score >= 60) {
    return "やや強気";
  }

  if (score >= 45) {
    return "中立";
  }

  if (score >= 35) {
    return "やや弱気";
  }

  return "弱気";
}

function deriveOverallScore(state) {
  const base = clamp(state.analysis?.totalScore || 0);
  const bonus = clamp(trendStrength(state.indicators) * 8, 0, 20);
  const score = clamp(Math.round(base * 0.85 + bonus * 0.15));

  return score;
}

function deriveConfidence(state) {
  const score = clamp(state.prediction?.confidence?.score || 0);
  const label = state.prediction?.confidence?.label || "中";
  const qualityScore = clamp(state.quality?.qualityScore || 0);

  return {
    score,
    label,
    method:
      "予測信頼度は指標一致度と履歴品質、過去実績の安定性を参考に算出しています。",
    explanation: `信頼度は${score}点で、データ品質は${qualityScore}点です。`,
  };
}

function deriveOutlook(state) {
  const { indicators } = state;
  const shortTerm = [];
  const midTerm = [];

  if (hasBullishMovingAverageAlignment(indicators) && hasMacdBullishSignal(indicators)) {
    shortTerm.push("短期的には上昇バイアスが継続しやすい状況です。");
  } else if (hasMacdBearishSignal(indicators)) {
    shortTerm.push("短期的には調整圧力が強く、戻り売りに注意が必要です。");
  } else {
    shortTerm.push("短期的には方向感が定まりにくく、節目の突破が重要です。");
  }

  if (isStrongTrend(indicators) && !isOverheatedRsi(indicators)) {
    midTerm.push("中期的にはトレンドの持続が期待できます。25日線を維持できれば優勢です。");
  } else if (isAtUpperBollinger(indicators) || isOverheatedRsi(indicators)) {
    midTerm.push("中期的には過熱感から調整局面になる可能性が高いです。");
  } else {
    midTerm.push("中期的には様子見が妥当で、明確なトレンドの確認が必要です。");
  }

  return {
    shortTerm: shortTerm.join(" "),
    midTerm: midTerm.join(" "),
  };
}

function deriveTradeSuggestions(state) {
  const { indicators } = state;
  const entry = [];
  const stopLoss = [];
  const takeProfit = [];

  if (isBelowVwap(indicators)) {
    entry.push("VWAP付近までの押し目で反発を確認してからエントリーを検討してください。");
  } else if (hasBullishMovingAverageAlignment(indicators)) {
    entry.push("上昇トレンド継続を前提に、押し目や安値切り上げを待ってからの買いが望ましいです。");
  } else {
    entry.push("明確な買いサインが出るまで様子見し、リスク管理を優先してください。");
  }

  if (indicators.atr && finite(indicators.atr.percent)) {
    const distance = Math.min(Math.max(indicators.atr.percent * 1.2, 1), 15);
    stopLoss.push(
      `ストップロスはATRの約${formatPercent(distance)}下、直近安値を目安に設定してください。`,
    );
  } else {
    stopLoss.push("ATRデータが不足しているため、直近のサポートラインや安値を参考に損切り水準を設定してください。");
  }

  if (indicators.atr && finite(indicators.atr.percent)) {
    const target = Math.min(Math.max(indicators.atr.percent * 1.8, 2), 25);
    takeProfit.push(
      `初期利食いはATRの約${formatPercent(target)}上を目安にし、次にボリンジャーバンド上限や52週高値付近を目標にしてください。`,
    );
  } else {
    takeProfit.push("ATRが利用できないため、直近のレジスタンスや高値を目安に利食いを検討してください。");
  }

  return {
    entrySuggestion: entry.join(" "),
    stopLossSuggestion: stopLoss.join(" "),
    takeProfitSuggestion: takeProfit.join(" "),
  };
}

export function createAiAnalysis(state) {
  if (!state || !state.analysis || !state.indicators || !state.prediction) {
    throw new Error("AI分析に必要な状態情報が不足しています。");
  }

  const overallAiScore = deriveOverallScore(state);
  const stance = deriveStance(overallAiScore);
  const confidence = deriveConfidence(state);
  const outlook = deriveOutlook(state);
  const suggestions = deriveTradeSuggestions(state);
  const buyFactors = collectBuyFactors(state);
  const riskFactors = collectRiskFactors(state);

  const discoveryMessage =
    finite(state.analysis.discoveryScore) &&
    state.analysis.discoveryScore !== state.analysis.totalScore
      ? `Discoveryスコアは${Math.round(state.analysis.discoveryScore)}点です。`
      : "";

  const overallAssessment =
    `AIスコアは${overallAiScore}点で、${stance}の傾向です。` +
    `短期的には${outlook.shortTerm}中期的には${outlook.midTerm}` +
    (discoveryMessage ? ` ${discoveryMessage}` : "");

  return {
    overallAiScore,
    stance,
    overallAssessment,
    overallSummary: overallAssessment,
    confidence,
    buyFactors,
    riskFactors,
    shortTermOutlook: outlook.shortTerm,
    midTermOutlook: outlook.midTerm,
    entrySuggestion: suggestions.entrySuggestion,
    stopLossSuggestion: suggestions.stopLossSuggestion,
    takeProfitSuggestion: suggestions.takeProfitSuggestion,
  };
}

export const AiAnalysisInternals = {
  finite,
  clamp,
  createAiAnalysis,
  deriveOverallScore,
  deriveConfidence,
  deriveOutlook,
  deriveTradeSuggestions,
};
