const {
  buildRecommendation,
} = require("./recommendation");

function decideBrokerState(
  metrics = {},
) {
  const recommendation =
    buildRecommendation(
      metrics,
    );

  const allowed =
    recommendation.action !==
    "BLOCK";

  return {
    allowed,
    mode:
      allowed
        ? "read-only"
        : "blocked",

    action:
      recommendation.action,

    score:
      recommendation.score,

    grade:
      recommendation.grade,

    reason:
      allowed
        ? "Broker connection quality is acceptable for read-only access."
        : "Broker connection quality is below the safe threshold.",

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  decideBrokerState,
};