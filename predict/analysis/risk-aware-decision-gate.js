function finiteNumber(value, fallback = 0) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      finiteNumber(value),
    ),
  );
}

function downgradeAction(action = "HOLD") {
  const normalized =
    String(action).toUpperCase();

  const map = {
    "STRONG BUY": "BUY",
    BUY: "WATCH",
    WATCH: "HOLD",
    HOLD: "HOLD",
    REDUCE: "REDUCE",
    SELL: "SELL",
  };

  return map[normalized] ?? "HOLD";
}

export function evaluateRiskAwareDecision({
  decision = {},
  portfolioRisk = {},
  limits = {},
} = {}) {
  const originalAction =
    String(
      decision.action ?? "HOLD",
    ).toUpperCase();

  const originalScore =
    clamp(
      decision.score ?? 50,
    );

  const originalConfidence =
    clamp(
      decision.confidence ?? 50,
    );

  const riskPercent =
    Math.max(
      0,
      finiteNumber(
        portfolioRisk.riskPercent,
        0,
      ),
    );

  const maximumRiskPercent =
    Math.max(
      0,
      finiteNumber(
        limits.maximumRiskPercent,
        6,
      ),
    );

  const minimumConfidence =
    clamp(
      limits.minimumConfidence ?? 55,
    );

  const minimumScore =
    clamp(
      limits.minimumScore ?? 60,
    );

  const reasons = [];

  let action =
    originalAction;

  let approved = true;

  let score =
    originalScore;

  let confidence =
    originalConfidence;

  if (
    riskPercent >
    maximumRiskPercent
  ) {
    approved = false;

    action =
      downgradeAction(
        downgradeAction(action),
      );

    score =
      clamp(
        score - 20,
      );

    confidence =
      clamp(
        confidence - 15,
      );

    reasons.push(
      "portfolio_risk_limit_exceeded",
    );
  }

  if (
    originalConfidence <
    minimumConfidence
  ) {
    approved = false;

    action =
      downgradeAction(action);

    reasons.push(
      "confidence_below_minimum",
    );
  }

  if (
    originalScore <
    minimumScore
  ) {
    approved = false;

    action =
      downgradeAction(action);

    reasons.push(
      "score_below_minimum",
    );
  }

  if (
    [
      "SELL",
      "REDUCE",
      "HOLD",
    ].includes(action)
  ) {
    approved = false;
  }

  return {
    approved,

    originalAction,

    action,

    originalScore,

    score,

    originalConfidence,

    confidence,

    riskPercent,

    maximumRiskPercent,

    reasons:
      [...new Set(reasons)],

    status:
      approved
        ? "APPROVED"
        : "BLOCKED",
  };
}

export function buildRiskAwareDecisionReport({
  decision = {},
  portfolioRisk = {},
  limits = {},
  symbol = null,
} = {}) {
  const gate =
    evaluateRiskAwareDecision({
      decision,
      portfolioRisk,
      limits,
    });

  return {
    version:
      "risk-aware-decision-gate-v1",

    generatedAt:
      new Date().toISOString(),

    symbol,

    gate,

    summary:
      gate.approved
        ? `${gate.action}・リスク条件内`
        : `${gate.action}・リスクゲートで制限`,
  };
}

export const RiskAwareDecisionGateInternals = {
  clamp,
  downgradeAction,
  finiteNumber,
};