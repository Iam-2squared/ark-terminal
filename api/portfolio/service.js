const {
  initializePortfolio,
} = require("./integration");

const {
  buildPortfolioRecommendation,
} = require("./recommendation");

const {
  createPortfolioHistory,
} = require("./history");

const {
  createPortfolioCache,
} = require("./cache");

function createPortfolioService() {
  const environment =
    initializePortfolio();

  const history =
    createPortfolioHistory();

  const cache =
    createPortfolioCache();

  function analyze(
    holdings = [],
  ) {
    const result =
      buildPortfolioRecommendation(
        holdings,
      );

    const report = {
      generatedAt:
        new Date()
          .toISOString(),

      environment,
      holdings:
        structuredClone(
          holdings,
        ),

      result,

      simulationOnly:
        true,

      liveTradingAllowed:
        false,

      orderSubmissionAllowed:
        false,
    };

    history.add(
      report,
    );

    cache.set(
      report,
    );

    return report;
  }

  function latest() {
    return cache.get();
  }

  function getHistory() {
    return history.list();
  }

  return {
    analyze,
    latest,
    getHistory,
  };
}

module.exports = {
  createPortfolioService,
};