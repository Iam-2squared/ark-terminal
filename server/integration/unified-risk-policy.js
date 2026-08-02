function evaluateUnifiedRiskPolicy({
  brokerRisk = "low",
  portfolioRisk = "low",
  brokerConnected = true,
} = {}) {
  const reasons = [];

  if (!brokerConnected) {
    reasons.push(
      "broker_disconnected",
    );
  }

  if (
    brokerRisk === "critical"
  ) {
    reasons.push(
      "critical_broker_risk",
    );
  }

  if (
    portfolioRisk === "critical"
  ) {
    reasons.push(
      "critical_portfolio_risk",
    );
  }

  const allowed =
    reasons.length === 0;

  return {
    allowedForAnalysis:
      allowed,

    mode:
      allowed
        ? "read-only"
        : "blocked",

    reasons,

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  evaluateUnifiedRiskPolicy,
};