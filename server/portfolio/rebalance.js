const {
  analyzeConcentration,
} = require("./concentration");

const {
  calculateDiversificationScore,
} = require("./diversification");

function buildRebalanceSuggestions(
  holdings = [],
) {
  const concentration =
    analyzeConcentration(
      holdings,
    );

  const diversification =
    calculateDiversificationScore(
      holdings,
    );

  const suggestions = [];

  if (
    concentration
      .positionConcentrated
  ) {
    suggestions.push({
      type:
        "REDUCE_POSITION_CONCENTRATION",

      symbol:
        concentration
          .topPosition
          ?.symbol ||
        null,

      currentWeightPercent:
        concentration
          .topPosition
          ?.weightPercent ||
        0,

      targetMaximumPercent:
        35,
    });
  }

  if (
    concentration
      .sectorConcentrated
  ) {
    suggestions.push({
      type:
        "REDUCE_SECTOR_CONCENTRATION",

      sector:
        concentration
          .topSector
          ?.sector ||
        null,

      currentWeightPercent:
        concentration
          .topSector
          ?.weightPercent ||
        0,

      targetMaximumPercent:
        45,
    });
  }

  if (
    diversification.score <
    50
  ) {
    suggestions.push({
      type:
        "INCREASE_DIVERSIFICATION",

      currentScore:
        diversification.score,

      targetScore:
        65,
    });
  }

  return {
    required:
      suggestions.length > 0,

    suggestions,

    simulationOnly:
      true,

    automaticExecution:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  buildRebalanceSuggestions,
};