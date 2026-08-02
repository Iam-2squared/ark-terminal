const AI_INTELLIGENCE_VERSION = "1.0.0";

function createAiRuntime() {
  return {
    version: AI_INTELLIGENCE_VERSION,
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
  AI_INTELLIGENCE_VERSION,
  createAiRuntime,
};