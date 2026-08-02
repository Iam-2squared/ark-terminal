const {
  analyzeDrawdown,
} = require("./drawdown");

function average(values) {
  return values.length > 0
    ? (
        values.reduce(
          (total, value) =>
            total + value,
          0,
        ) /
        values.length
      )
    : 0;
}

function analyzePortfolioPerformance(
  returns = [],
  values = [],
) {
  const normalizedReturns =
    (Array.isArray(returns)
      ? returns
      : [])
      .map(Number)
      .filter(Number.isFinite);

  const meanReturn =
    average(
      normalizedReturns,
    );

  const variance =
    normalizedReturns.length > 1
      ? normalizedReturns.reduce(
          (total, value) =>
            total +
            Math.pow(
              value -
              meanReturn,
              2,
            ),
          0,
        ) /
        (
          normalizedReturns.length -
          1
        )
      : 0;

  const volatility =
    Math.sqrt(
      variance,
    );

  const sharpeRatio =
    volatility > 0
      ? meanReturn /
        volatility
      : 0;

  const positivePeriods =
    normalizedReturns.filter(
      (value) =>
        value > 0,
    ).length;

  return {
    sampleCount:
      normalizedReturns.length,

    meanReturn,
    volatility,
    sharpeRatio,

    positivePeriodRate:
      normalizedReturns.length > 0
        ? (
            positivePeriods /
            normalizedReturns.length
          ) * 100
        : 0,

    drawdown:
      analyzeDrawdown(
        values,
      ),
  };
}

module.exports = {
  analyzePortfolioPerformance,
};