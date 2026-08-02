const {
  calculatePortfolioMetrics,
} = require("./metrics");

function analyzePortfolio(
  holdings = [],
) {
  const metrics =
    calculatePortfolioMetrics(
      holdings,
    );

  const largestPosition =
    metrics.positions
      .slice()
      .sort(
        (
          left,
          right,
        ) =>
          right.marketValue -
          left.marketValue,
      )[0] ||
    null;

  const largestWeightPercent =
    largestPosition &&
    metrics.totalMarketValue > 0
      ? (
          largestPosition
            .marketValue /
          metrics
            .totalMarketValue
        ) * 100
      : 0;

  return {
    metrics,
    largestPosition,
    largestWeightPercent,

    concentrated:
      largestWeightPercent >=
      40,

    profitable:
      metrics
        .totalProfitLoss >
      0,
  };
}

module.exports = {
  analyzePortfolio,
};