const {
  createIntegrationRuntime,
} = require("./runtime");

const {
  createUnifiedSnapshot,
} = require("./unified-snapshot");

const {
  createUnifiedDecision,
} = require("./unified-decision");

function runIntegration({
  broker = {},
  portfolio = {},
  market = {},
} = {}) {
  const runtime =
    createIntegrationRuntime();

  const snapshot =
    createUnifiedSnapshot({
      broker,
      portfolio,
      market,
    });

  const decision =
    createUnifiedDecision({
      brokerRisk:
        broker.risk ||
        "low",

      portfolioRisk:
        portfolio.risk ||
        "low",

      brokerConnected:
        broker.connected !==
        false,
    });

  return {
    runtime,
    snapshot,
    decision,

    generatedAt:
      new Date().toISOString(),

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  runIntegration,
};