export const MODEL_VERSION = "ark-evaluation-v3";

export const EVALUATION_POLICY = Object.freeze({
  minimumConfidenceScore: 60,
  minimumDataQualityScore: 80,
  atrLabelMultiplier: 1,
  labelMethod: "ATR×√期間",
});

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function roundTripCostPercent(costs = {}) {
  return (
    ((Number(costs.commissionBpsPerSide) || 0) +
      (Number(costs.slippageBpsPerSide) || 0)) *
    2 *
    0.01
  );
}

export function deriveEvaluationThreshold({
  atrPercent,
  period,
  multiplier = EVALUATION_POLICY.atrLabelMultiplier,
}) {
  if (!finite(atrPercent) || Number(atrPercent) <= 0) {
    return null;
  }

  const horizon = Math.max(1, Number(period) || 1);

  return (
    Math.abs(Number(atrPercent)) *
    Math.sqrt(horizon) *
    Math.max(0.1, Number(multiplier) || 1)
  );
}

export function classifyActualReturn({ actualReturn, threshold }) {
  if (!finite(actualReturn) || !finite(threshold) || Number(threshold) <= 0) {
    return "判定不能";
  }

  if (Number(actualReturn) >= Number(threshold)) {
    return "上昇";
  }

  if (Number(actualReturn) <= -Number(threshold)) {
    return "下落";
  }

  return "中立";
}

export function deriveTradeDecision({
  direction,
  confidenceScore,
  dataQualityScore,
  policy = EVALUATION_POLICY,
}) {
  const resolvedPolicy = {
    ...EVALUATION_POLICY,
    ...(policy || {}),
  };
  const reasons = [];

  if (direction === "中立") {
    reasons.push("方向スコアが中立圏です。");
  }

  if (!finite(confidenceScore)) {
    reasons.push("信頼度を算出できません。");
  } else if (
    Number(confidenceScore) < resolvedPolicy.minimumConfidenceScore
  ) {
    reasons.push(
      `信頼度が${resolvedPolicy.minimumConfidenceScore}未満です。`,
    );
  }

  if (!finite(dataQualityScore)) {
    reasons.push("データ品質を確認できません。");
  } else if (
    Number(dataQualityScore) < resolvedPolicy.minimumDataQualityScore
  ) {
    reasons.push(
      `データ品質が${resolvedPolicy.minimumDataQualityScore}未満です。`,
    );
  }

  const isActionable = reasons.length === 0;

  return {
    action: isActionable ? "採用" : "見送り",
    isActionable,
    reasons,
    modelVersion: MODEL_VERSION,
    policy: {
      ...resolvedPolicy,
    },
  };
}

export function evaluateResolvedPrediction({
  direction,
  actualReturn,
  threshold,
  decision,
  costs,
}) {
  const actualLabel = classifyActualReturn({
    actualReturn,
    threshold,
  });
  const isActionable =
    decision?.isActionable === true || decision?.action === "採用";

  if (!isActionable || direction === "中立") {
    return {
      actualLabel,
      labelThreshold: finite(threshold) ? Number(threshold) : null,
      grossStrategyReturn: 0,
      tradingCost: 0,
      strategyReturn: 0,
      hit: null,
      outcome: "見送り",
      excludedFromPerformance: true,
    };
  }

  if (actualLabel === "判定不能") {
    return {
      actualLabel,
      labelThreshold: null,
      grossStrategyReturn: null,
      tradingCost: null,
      strategyReturn: null,
      hit: null,
      outcome: "判定不能",
      excludedFromPerformance: true,
    };
  }

  const grossStrategyReturn =
    direction === "強気" ? Number(actualReturn) : -Number(actualReturn);
  const tradingCost = roundTripCostPercent(costs);
  const strategyReturn = grossStrategyReturn - tradingCost;
  const hit =
    direction === "強気"
      ? actualLabel === "上昇"
      : actualLabel === "下落";

  return {
    actualLabel,
    labelThreshold: Number(threshold),
    grossStrategyReturn,
    tradingCost,
    strategyReturn,
    hit,
    outcome: hit ? "的中" : "外れ",
    excludedFromPerformance: false,
  };
}

export const EvaluationPolicyInternals = {
  finite,
  roundTripCostPercent,
};
