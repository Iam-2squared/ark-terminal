function numberOrZero(
  value,
) {
  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : 0;
}

function calculatePortfolioMetrics(
  holdings = [],
) {
  const normalized =
    Array.isArray(holdings)
      ? holdings
      : [];

  let totalMarketValue = 0;
  let totalCost = 0;
  let totalProfitLoss = 0;

  const positions =
    normalized.map(
      (
        holding,
      ) => {
        const quantity =
          numberOrZero(
            holding.quantity,
          );

        const currentPrice =
          numberOrZero(
            holding.currentPrice,
          );

        const averagePrice =
          numberOrZero(
            holding.averagePrice,
          );

        const marketValue =
          quantity *
          currentPrice;

        const cost =
          quantity *
          averagePrice;

        const profitLoss =
          marketValue -
          cost;

        totalMarketValue +=
          marketValue;

        totalCost +=
          cost;

        totalProfitLoss +=
          profitLoss;

        return {
          symbol:
            String(
              holding.symbol ||
              "",
            ),

          quantity,
          currentPrice,
          averagePrice,
          marketValue,
          cost,
          profitLoss,
        };
      },
    );

  const returnPercent =
    totalCost > 0
      ? (
          totalProfitLoss /
          totalCost
        ) * 100
      : 0;

  return {
    positionCount:
      positions.length,

    totalMarketValue,
    totalCost,
    totalProfitLoss,
    returnPercent,
    positions,
  };
}

module.exports = {
  calculatePortfolioMetrics,
};