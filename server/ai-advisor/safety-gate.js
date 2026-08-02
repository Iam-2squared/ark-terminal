function evaluateSafetyGate(input = {}) {
  const reasons = [];

  const brokerConnected =
    input.broker?.connected !== false;

  const marketConnected =
    input.market?.connected !== false;

  const aiPolicy =
    input.ai?.policy || {};

  const portfolioRisk =
    input.portfolio?.risk?.level ||
    input.portfolio?.risk ||
    "low";

  if (!brokerConnected) {
    reasons.push(
      "broker_disconnected"
    );
  }

  if (!marketConnected) {
    reasons.push(
      "market_disconnected"
    );
  }

  if (
    aiPolicy.analysisAllowed === false
  ) {
    reasons.push(
      "ai_analysis_blocked"
    );
  }

  if (
    aiPolicy.recommendationAllowed ===
    false
  ) {
    reasons.push(
      "ai_recommendation_blocked"
    );
  }

  if (
    portfolioRisk === "critical"
  ) {
    reasons.push(
      "critical_portfolio_risk"
    );
  }

  return {
    allowed:
      reasons.length === 0,

    reasons,

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,

    humanApprovalRequired:
      true,
  };
}

module.exports = {
  evaluateSafetyGate,
};