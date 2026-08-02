const {
  calculatePositionWeights,
} = require("./position-weights");

const {
  calculateSectorExposure,
} = require("./sector-exposure");

function analyzeConcentration(
  holdings = [],
) {
  const positions =
    calculatePositionWeights(
      holdings,
    );

  const sectors =
    calculateSectorExposure(
      holdings,
    );

  const sortedPositions =
    positions.positions
      .slice()
      .sort(
        (left, right) =>
          right.weightPercent -
          left.weightPercent,
      );

  const topPosition =
    sortedPositions[0] ||
    null;

  const topSector =
    sectors.sectors[0] ||
    null;

  const topThreeWeightPercent =
    sortedPositions
      .slice(0, 3)
      .reduce(
        (total, position) =>
          total +
          position.weightPercent,
        0,
      );

  return {
    topPosition,
    topSector,
    topThreeWeightPercent,

    positionConcentrated:
      (
        topPosition
          ?.weightPercent ||
        0
      ) >= 40,

    sectorConcentrated:
      (
        topSector
          ?.weightPercent ||
        0
      ) >= 50,
  };
}

module.exports = {
  analyzeConcentration,
};