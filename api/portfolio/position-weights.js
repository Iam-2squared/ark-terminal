function numberOrZero(value) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : 0;
}

function calculatePositionWeights(
  holdings = [],
) {
  const positions =
    (Array.isArray(holdings)
      ? holdings
      : [])
      .map((holding) => {
        const quantity =
          numberOrZero(
            holding.quantity,
          );

        const currentPrice =
          numberOrZero(
            holding.currentPrice,
          );

        return {
          symbol:
            String(
              holding.symbol ||
              "",
            ),

          sector:
            String(
              holding.sector ||
              "Unknown",
            ),

          marketValue:
            quantity *
            currentPrice,
        };
      });

  const totalMarketValue =
    positions.reduce(
      (total, position) =>
        total +
        position.marketValue,
      0,
    );

  return {
    totalMarketValue,

    positions:
      positions.map(
        (position) => ({
          ...position,

          weightPercent:
            totalMarketValue > 0
              ? (
                  position.marketValue /
                  totalMarketValue
                ) * 100
              : 0,
        }),
      ),
  };
}

module.exports = {
  calculatePositionWeights,
};