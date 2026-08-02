const INTEGRATION_RUNTIME_VERSION = "1.0.0";

function createIntegrationRuntime() {
  return {
    version:
      INTEGRATION_RUNTIME_VERSION,

    startedAt:
      new Date().toISOString(),

    status:
      "ready",

    brokerReadOnly:
      true,

    portfolioSimulationOnly:
      true,

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  INTEGRATION_RUNTIME_VERSION,
  createIntegrationRuntime,
};