const {
  decideBrokerState,
} = require("./decision");

function evaluateBrokerGuard(
  metrics = {},
) {
  const decision =
    decideBrokerState(
      metrics,
    );

  const reasons = [];

  if (!decision.allowed) {
    reasons.push(
      "broker_quality_blocked",
    );
  }

  if (
    metrics.connected ===
    false
  ) {
    reasons.push(
      "broker_disconnected",
    );
  }

  if (
    metrics.authenticated ===
    false
  ) {
    reasons.push(
      "broker_not_authenticated",
    );
  }

  const passed =
    decision.allowed &&
    metrics.connected !== false &&
    metrics.authenticated !== false;

  return {
    passed,
    reasons,

    mode:
      "read-only",

    transmitted:
      false,

    decision,
  };
}

module.exports = {
  evaluateBrokerGuard,
};