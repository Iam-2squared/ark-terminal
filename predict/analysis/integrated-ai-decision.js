import {
  buildRecommendation,
} from "./recommendation-engine.js";

import {
  detectMarketRegime,
} from "../market-context/market-regime.js";

import {
  evaluateMacroEnvironment,
} from "../market-context/macro-engine.js";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function number(value, fallback = 0) {
  return finite(value)
    ? Number(value)
    : fallback;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      number(value),
    ),
  );
}

function round(value, digits = 2) {
  const factor = 10 ** digits;

  return (
    Math.round(
      number(value) *
      factor,
    ) / factor
  );
}

function extractTechnicalScore(state = {}) {
  return clamp(
    state?.analysis?.technicalScore ??
    state?.analysis?.totalScore ??
    state?.aiAnalysis?.overallAiScore ??
    state?.prediction?.score ??
    50,
  );
}

function extractAiScore(state = {}) {
  return clamp(
    state?.aiAnalysis?.overallAiScore ??
    state?.analysis?.totalScore ??
    state?.prediction?.confidence ??
    50,
  );
}

function extractConfidence(state = {}) {
  return clamp(
    state?.aiAnalysis?.confidence?.score ??
    state?.prediction?.confidence ??
    state?.analysis?.confidence ??
    50,
  );
}

function calculateRiskScore({
  state = {},
  portfolioPlan = {},
} = {}) {
  const indicators =
    state?.indicators ?? {};

  const atrPercent =
    number(
      indicators?.atr?.percent ??
      indicators?.atrPercent,
      2.5,
    );

  const volatilityPenalty =
    clamp(
      atrPercent * 8,
      0,
      50,
    );

  const portfolioRiskPercent =
    number(
      portfolioPlan?.risk?.riskPercent,
      0,
    );

  const portfolioPenalty =
    clamp(
      portfolioRiskPercent * 5,
      0,
      40,
    );

  const dataQuality =
    clamp(
      state?.analysis?.dataQualityScore ??
      state?.dataQualityScore ??
      75,
    );

  return clamp(
    100 -
    volatilityPenalty -
    portfolioPenalty -
    (
      100 -
      dataQuality
    ) * 0.25,
  );
}

function buildReasonList({
  technicalScore,
  macro,
  regime,
  aiScore,
  riskScore,
  confidence,
} = {}) {
  const buyFactors = [];
  const riskFactors = [];

  if (technicalScore >= 70) {
    buyFactors.push(
      `テクニカル評価が強い（${round(technicalScore)}点）`,
    );
  } else if (technicalScore < 45) {
    riskFactors.push(
      `テクニカル評価が弱い（${round(technicalScore)}点）`,
    );
  }

  if (macro.sentiment === "BULLISH") {
    buyFactors.push(
      `マクロ環境が強気（${macro.score}点）`,
    );
  } else if (macro.sentiment === "BEARISH") {
    riskFactors.push(
      `マクロ環境が弱気（${macro.score}点）`,
    );
  }

  if (regime.regime === "BULL") {
    buyFactors.push(
      "市場レジームは上昇トレンド",
    );
  }

  if (
    regime.regime === "BEAR" ||
    regime.regime === "HIGH_VOLATILITY"
  ) {
    riskFactors.push(
      `市場レジームは${regime.regime}`,
    );
  }

  if (aiScore >= 70) {
    buyFactors.push(
      `AI評価が高い（${round(aiScore)}点）`,
    );
  } else if (aiScore < 45) {
    riskFactors.push(
      `AI評価が低い（${round(aiScore)}点）`,
    );
  }

  if (riskScore < 50) {
    riskFactors.push(
      `リスク評価が低い（${round(riskScore)}点）`,
    );
  }

  if (confidence < 50) {
    riskFactors.push(
      `分析信頼度が低い（${round(confidence)}点）`,
    );
  }

  if (!buyFactors.length) {
    buyFactors.push(
      "明確な強気要因はまだ不足",
    );
  }

  if (!riskFactors.length) {
    riskFactors.push(
      "重大な警戒要因は検出されていません",
    );
  }

  return {
    buyFactors,
    riskFactors,
  };
}

export function buildIntegratedAiDecision({
  state = {},
  macroInput = {},
  marketInput = {},
  portfolioPlan = {},
} = {}) {
  const technicalScore =
    extractTechnicalScore(state);

  const aiScore =
    extractAiScore(state);

  const confidence =
    extractConfidence(state);

  const macro =
    evaluateMacroEnvironment(
      macroInput,
    );

  const regime =
    detectMarketRegime({
      trendScore:
        marketInput.trendScore ??
        technicalScore,

      volatility:
        marketInput.volatility ??
        number(
          state?.indicators?.atr?.percent,
          20,
        ),

      adx:
        marketInput.adx ??
        state?.indicators?.adx?.value ??
        state?.indicators?.adx ??
        20,

      rsi:
        marketInput.rsi ??
        state?.indicators?.rsi ??
        50,

      vix:
        marketInput.vix ??
        macroInput.vix ??
        20,
    });

  const riskScore =
    calculateRiskScore({
      state,
      portfolioPlan,
    });

  const recommendation =
    buildRecommendation({
      technicalScore,

      macroScore:
        macro.score,

      aiScore,

      riskScore,

      confidence,
    });

  const reasons =
    buildReasonList({
      technicalScore,
      macro,
      regime,
      aiScore,
      riskScore,
      confidence,
    });

  return {
    version:
      "integrated-ai-decision-v1",

    generatedAt:
      new Date().toISOString(),

    symbol:
      state?.symbol ??
      null,

    recommendation,

    technicalScore,

    aiScore,

    confidence,

    riskScore:
      round(riskScore),

    macro,

    regime,

    portfolioRisk:
      portfolioPlan?.risk ??
      null,

    buyFactors:
      reasons.buyFactors,

    riskFactors:
      reasons.riskFactors,

    summary:
      `${recommendation.action}・総合${recommendation.score}点・信頼度${confidence}点`,

    disclaimer:
      "本結果は分析支援用であり、利益や将来の値動きを保証しません。",
  };
}

export function buildIntegratedDecisionCard(
  decision = {},
) {
  return {
    action:
      decision?.recommendation?.action ??
      "HOLD",

    stars:
      decision?.recommendation?.stars ??
      3,

    score:
      decision?.recommendation?.score ??
      50,

    confidence:
      decision?.confidence ??
      0,

    expectedReturn:
      decision?.recommendation?.expectedReturn ??
      0,

    expectedRisk:
      decision?.recommendation?.expectedRisk ??
      0,

    regime:
      decision?.regime?.regime ??
      "RANGE",

    macroSentiment:
      decision?.macro?.sentiment ??
      "NEUTRAL",

    buyFactors:
      decision?.buyFactors ??
      [],

    riskFactors:
      decision?.riskFactors ??
      [],
  };
}

export const IntegratedAiDecisionInternals = {
  buildReasonList,
  calculateRiskScore,
  extractAiScore,
  extractConfidence,
  extractTechnicalScore,
};