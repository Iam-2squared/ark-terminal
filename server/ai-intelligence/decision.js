function createAiDecision({
  score = {},
  risk = {},
  confidence = {},
  policy = {},
} = {}) {
  let action = "HOLD";

  if (!policy.analysisAllowed) {
    action = "BLOCK_ANALYSIS";
  } else if (!policy.recommendationAllowed) {
    action = "REVIEW";
  } else if (
    score.score >= 75 &&
    risk.level !== "high" &&
    confidence.level === "high"
  ) {
    action = "WATCH_BUY";
  } else if (
    score.score <= 35 ||
    risk.level === "high"
  ) {
    action = "WATCH_SELL";
  }

  return {
    action,
    advisoryOnly: true,
    automaticExecution: false,
    orderSubmissionAllowed: false,
  };
}

module.exports = {
  createAiDecision,
};