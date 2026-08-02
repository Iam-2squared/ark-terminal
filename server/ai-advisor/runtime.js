const ADVISOR_RUNTIME_VERSION = "1.0.0";

function createAdvisorRuntime() {
  return {
    version: ADVISOR_RUNTIME_VERSION,
    startedAt: new Date().toISOString(),
    status: "ready",
    advisoryOnly: true,
    simulationOnly: true,
    liveTradingAllowed: false,
    orderSubmissionAllowed: false,
    humanApprovalRequired: true,
  };
}

module.exports = {
  ADVISOR_RUNTIME_VERSION,
  createAdvisorRuntime,
};