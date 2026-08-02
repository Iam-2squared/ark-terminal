const {
  calculatePortfolioScore,
} = require("./score");

function buildPortfolioRecommendation(
  holdings = [],
) {
  const result =
    calculatePortfolioScore(
      holdings,
    );

  let action =
    "HOLD";

  if (
    result.risk.level ===
    "critical"
  ) {
    action =
      "REVIEW_IMMEDIATELY";
  }
  else if (
    result.risk.level ===
    "high"
  ) {
    action =
      "REDUCE_CONCENTRATION";
  }
  else if (
    result.risk.level ===
    "moderate"
  ) {
    action =
      "MONITOR";
  }

  return {
    action,
    score:
      result.score,

    grade:
      result.grade,

    reasons:
      result.risk
        .factors,

    simulationOnly:
      true,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  buildPortfolioRecommendation,
};