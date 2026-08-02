// Part263 B33 Portfolio Runtime Suite

const { createPortfolioRuntime } = require("./runtime");
const { createPortfolioSession } = require("./session");

function createPortfolioSuite() {
  return {
    runtime: createPortfolioRuntime(),
    session: createPortfolioSession(),
  };
}

module.exports = {
    createPortfolioSuite,
};
