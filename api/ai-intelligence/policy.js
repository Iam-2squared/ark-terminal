function evaluateAiPolicy({
  input = {},
  risk = {},
  confidence = {},
} = {}) {
  const reasons = [];

  if (!input.brokerConnected) {
    reasons.push("broker_disconnected");
  }

  if (!input.marketConnected) {
    reasons.push("market_data_disconnected");
  }

  if (risk.level === "critical") {
    reasons.push("critical_risk");
  }

  if (confidence.level === "low") {
    reasons.push("low_confidence");
  }

  return {
    analysisAllowed:
      !reasons.includes("market_data_disconnected"),

    recommendationAllowed:
      reasons.length === 0,

    reasons,

    liveTradingAllowed: false,
    orderSubmissionAllowed: false,
    humanApprovalRequired: true,
  };
}

module.exports = {
  evaluateAiPolicy,
};