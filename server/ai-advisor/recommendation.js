function createRecommendation({
  input = {},
  score = {},
  confidence = {},
  conflicts = {},
  safety = {},
} = {}) {
  let recommendation =
    "HOLD";

  const aiAction =
    input.ai?.decision?.action ||
    "HOLD";

  if (!safety.allowed) {
    recommendation =
      "BLOCK";
  }
  else if (
    conflicts.hasConflict
  ) {
    recommendation =
      "REVIEW";
  }
  else if (
    confidence.level === "low"
  ) {
    recommendation =
      "WAIT";
  }
  else if (
    aiAction === "WATCH_BUY" &&
    score.score >= 70
  ) {
    recommendation =
      "WATCH_BUY";
  }
  else if (
    aiAction === "WATCH_SELL"
  ) {
    recommendation =
      "WATCH_SELL";
  }

  return {
    recommendation,

    advisoryOnly:
      true,

    automaticExecution:
      false,

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,

    humanApprovalRequired:
      true,
  };
}

module.exports = {
  createRecommendation,
};