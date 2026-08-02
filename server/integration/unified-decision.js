const {
  evaluateUnifiedRiskPolicy,
} = require("./unified-risk-policy");

function createUnifiedDecision(input = {}) {
  const policy =
    evaluateUnifiedRiskPolicy(input);

  let action =
    "HOLD";

  if (
    !policy.allowedForAnalysis
  ) {
    action =
      "BLOCK_ANALYSIS";
  }
  else if (
    input.portfolioRisk ===
    "high"
  ) {
    action =
      "REVIEW_PORTFOLIO";
  }
  else if (
    input.brokerRisk ===
    "high"
  ) {
    action =
      "MONITOR_BROKER";
  }

  return {
    action,
    policy,

    advisoryOnly:
      true,

    automaticExecution:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  createUnifiedDecision,
};