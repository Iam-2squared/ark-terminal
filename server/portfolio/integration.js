const {
  createPortfolioRuntime,
} = require("./runtime");

const {
  createPortfolioSession,
} = require("./session");

function initializePortfolio() {
  return {
    runtime:
      createPortfolioRuntime(),

    session:
      createPortfolioSession(),

    simulationOnly:
      true,

    liveTradingAllowed:
      false,
  };
}

module.exports = {
  initializePortfolio,
};