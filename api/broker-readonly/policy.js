function evaluateReadonlyBrokerPolicy({
  diagnostics,
  confidence,
  trend,
} = {}) {
  const reasons = [];

  if (
    diagnostics?.severity ===
    "critical"
  ) {
    reasons.push(
      "critical_diagnostics",
    );
  }

  if (
    confidence
      ?.sufficientEvidence !==
    true
  ) {
    reasons.push(
      "insufficient_evidence",
    );
  }

  if (
    trend?.deteriorating ===
    true
  ) {
    reasons.push(
      "deteriorating_trend",
    );
  }

  const allowed =
    !reasons.includes(
      "critical_diagnostics",
    );

  return {
    allowed,

    mode:
      allowed
        ? "read-only"
        : "blocked",

    reasons,

    submitOrder:
      false,

    cancelOrder:
      false,

    replaceOrder:
      false,

    liveTrading:
      false,
  };
}

module.exports = {
  evaluateReadonlyBrokerPolicy,
};