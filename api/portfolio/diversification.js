const {
  calculatePositionWeights,
} = require("./position-weights");

const {
  calculateSectorExposure,
} = require("./sector-exposure");

function calculateDiversificationScore(
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

  const positionHerfindahl =
    positions.positions.reduce(
      (total, position) => {
        const weight =
          position.weightPercent /
          100;

        return (
          total +
          weight * weight
        );
      },
      0,
    );

  const sectorHerfindahl =
    sectors.sectors.reduce(
      (total, sector) => {
        const weight =
          sector.weightPercent /
          100;

        return (
          total +
          weight * weight
        );
      },
      0,
    );

  const concentrationIndex =
    (
      positionHerfindahl *
      0.6
    ) +
    (
      sectorHerfindahl *
      0.4
    );

  const score =
    Math.max(
      0,
      Math.min(
        100,
        Math.round(
          (
            1 -
            concentrationIndex
          ) *
          100,
        ),
      ),
    );

  return {
    score,

    grade:
      score >= 80
        ? "A"
        : score >= 65
          ? "B"
          : score >= 50
            ? "C"
            : score >= 35
              ? "D"
              : "E",

    positionHerfindahl,
    sectorHerfindahl,
    concentrationIndex,
  };
}

module.exports = {
  calculateDiversificationScore,
};