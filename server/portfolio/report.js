const {
  createPortfolioService,
} = require("./service");

const {
  calculateSectorExposure,
} = require("./sector-exposure");

const {
  analyzeConcentration,
} = require("./concentration");

const {
  calculateDiversificationScore,
} = require("./diversification");

const {
  analyzePortfolioPerformance,
} = require("./performance");

const {
  buildRebalanceSuggestions,
} = require("./rebalance");

function createPortfolioIntelligenceReport({
  holdings = [],
  returns = [],
  values = [],
} = {}) {
  const service =
    createPortfolioService();

  const baseReport =
    service.analyze(
      holdings,
    );

  return {
    version:
      "portfolio-intelligence-report-v1",

    generatedAt:
      new Date()
        .toISOString(),

    baseReport,

    sectors:
      calculateSectorExposure(
        holdings,
      ),

    concentration:
      analyzeConcentration(
        holdings,
      ),

    diversification:
      calculateDiversificationScore(
        holdings,
      ),

    performance:
      analyzePortfolioPerformance(
        returns,
        values,
      ),

    rebalance:
      buildRebalanceSuggestions(
        holdings,
      ),

    simulationOnly:
      true,

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  createPortfolioIntelligenceReport,
};