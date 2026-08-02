const {
  evaluatePortfolioRisk,
} = require("./risk");

function calculatePortfolioScore(
  holdings = [],
) {
  const risk =
    evaluatePortfolioRisk(
      holdings,
    );

  const score =
    Math.max(
      0,
      100 -
      risk.score,
    );

  return {
    score,

    grade:
      score >= 90
        ? "A"
        : score >= 80
          ? "B"
          : score >= 70
            ? "C"
            : score >= 60
              ? "D"
              : "E",

    risk,
  };
}

module.exports = {
  calculatePortfolioScore,
};