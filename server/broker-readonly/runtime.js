const BROKER_RUNTIME_VERSION = "0.1.0";

function createRuntime() {
  return {
    version: BROKER_RUNTIME_VERSION,
    startedAt: new Date().toISOString(),
    status: "ready",
    readOnly: true,
    liveTradingEnabled: false,
    orderSubmissionAvailable: false,
  };
}

module.exports = {
  BROKER_RUNTIME_VERSION,
  createRuntime,
};