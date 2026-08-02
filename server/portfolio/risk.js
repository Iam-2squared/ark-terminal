const {
  analyzePortfolio,
} = require("./analyzer");

function evaluatePortfolioRisk(
  holdings = [],
) {
  const analysis =
    analyzePortfolio(
      holdings,
    );

  let score = 0;
  const factors = [];

  if (
    analysis.metrics
      .positionCount ===
    0
  ) {
    factors.push(
      "empty_portfolio",
    );
  }

  if (
    analysis
      .largestWeightPercent >=
    60
  ) {
    score += 50;

    factors.push(
      "extreme_concentration",
    );
  }
  else if (
    analysis
      .largestWeightPercent >=
    40
  ) {
    score += 30;

    factors.push(
      "high_concentration",
    );
  }

  if (
    analysis.metrics
      .returnPercent <=
    -20
  ) {
    score += 40;

    factors.push(
      "large_unrealized_loss",
    );
  }
  else if (
    analysis.metrics
      .returnPercent <=
    -10
  ) {
    score += 20;

    factors.push(
      "unrealized_loss",
    );
  }

  score =
    Math.min(
      100,
      score,
    );

  return {
    score,

    level:
      score >= 70
        ? "critical"
        : score >= 40
          ? "high"
          : score >= 20
            ? "moderate"
            : "low",

    factors,
    analysis,
  };
}

module.exports = {
  evaluatePortfolioRisk,
};