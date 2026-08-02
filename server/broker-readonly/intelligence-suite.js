const {
  buildRecommendation,
} = require("./recommendation");

const {
  evaluateBrokerGuard,
} = require("./guard");

const {
  evaluateBrokerRisk,
} = require("./risk");

const {
  diagnoseBroker,
} = require("./diagnostics");

const {
  detectBrokerAnomalies,
} = require("./anomaly-detector");

const {
  buildBrokerExplanation,
} = require("./explanation");

function analyzeBrokerIntelligence(
  metrics = {},
) {
  const recommendation =
    buildRecommendation(
      metrics,
    );

  const guard =
    evaluateBrokerGuard(
      metrics,
    );

  const risk =
    evaluateBrokerRisk(
      metrics,
    );

  const diagnostics =
    diagnoseBroker(
      metrics,
    );

  const anomalies =
    detectBrokerAnomalies(
      metrics,
    );

  const explanation =
    buildBrokerExplanation({
      score:
        recommendation.score,

      grade:
        recommendation.grade,

      action:
        recommendation.action,

      risk,

      anomalies,
    });

  return {
    version:
      "broker-intelligence-suite-v1",

    recommendation,
    guard,
    risk,
    diagnostics,
    anomalies,
    explanation,

    safeForReadOnly:
      guard.passed &&
      risk.level !==
        "critical",

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  analyzeBrokerIntelligence,
};