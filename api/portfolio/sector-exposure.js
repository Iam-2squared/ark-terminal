const {
  calculatePositionWeights,
} = require("./position-weights");

function calculateSectorExposure(
  holdings = [],
) {
  const weights =
    calculatePositionWeights(
      holdings,
    );

  const sectors = {};

  for (
    const position of
    weights.positions
  ) {
    if (!sectors[position.sector]) {
      sectors[position.sector] = {
        sector:
          position.sector,

        marketValue:
          0,

        weightPercent:
          0,

        positionCount:
          0,
      };
    }

    sectors[position.sector]
      .marketValue +=
      position.marketValue;

    sectors[position.sector]
      .weightPercent +=
      position.weightPercent;

    sectors[position.sector]
      .positionCount +=
      1;
  }

  return {
    totalMarketValue:
      weights.totalMarketValue,

    sectors:
      Object.values(sectors)
        .sort(
          (left, right) =>
            right.weightPercent -
            left.weightPercent,
        ),
  };
}

module.exports = {
  calculateSectorExposure,
};