const MARKET_RUNTIME_VERSION = "1.0.0";

function createMarketRuntime() {
  return {
    version:
      MARKET_RUNTIME_VERSION,

    startedAt:
      new Date().toISOString(),

    status:
      "ready",

    analysisOnly:
      true,

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  MARKET_RUNTIME_VERSION,
  createMarketRuntime,
};