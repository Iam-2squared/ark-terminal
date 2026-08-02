const {
  analyzeBrokerIntelligence,
} = require("./intelligence-suite");

const {
  calculateBrokerConfidence,
} = require("./confidence");

const {
  analyzeBrokerTrend,
} = require("./trend-analyzer");

const {
  evaluateReadonlyBrokerPolicy,
} = require("./policy");

function createBrokerIntelligenceReport({
  metrics = {},
  history = [],
} = {}) {
  const intelligence =
    analyzeBrokerIntelligence(
      metrics,
    );

  const trend =
    analyzeBrokerTrend(
      history,
    );

  const confidence =
    calculateBrokerConfidence({
      sampleCount:
        history.length,

      anomalyCount:
        intelligence
          .anomalies
          .count,

      connected:
        metrics.connected ===
        true,

      authenticated:
        metrics.authenticated ===
        true,
    });

  const policy =
    evaluateReadonlyBrokerPolicy({
      diagnostics:
        intelligence
          .diagnostics,

      confidence,

      trend,
    });

  return {
    version:
      "broker-intelligence-report-v1",

    generatedAt:
      new Date()
        .toISOString(),

    intelligence,
    trend,
    confidence,
    policy,

    readOnly:
      true,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  createBrokerIntelligenceReport,
};