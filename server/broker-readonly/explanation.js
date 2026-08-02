function buildBrokerExplanation({
  score,
  grade,
  action,
  risk,
  anomalies,
} = {}) {
  const reasons = [];

  if (
    Number(score) >= 90
  ) {
    reasons.push(
      "Broker health score is excellent.",
    );
  }
  else if (
    Number(score) >= 75
  ) {
    reasons.push(
      "Broker health score is acceptable but should be monitored.",
    );
  }
  else {
    reasons.push(
      "Broker health score is below the preferred threshold.",
    );
  }

  if (
    risk?.factors?.length
  ) {
    reasons.push(
      `Risk factors: ${risk.factors.join(", ")}.`,
    );
  }

  if (
    anomalies?.count > 0
  ) {
    reasons.push(
      `${anomalies.count} broker anomaly or anomalies detected.`,
    );
  }

  return {
    summary:
      `Broker grade ${grade || "-"}, action ${action || "UNKNOWN"}.`,

    reasons,

    readOnlyNotice:
      "This evaluation never enables order submission.",
  };
}

module.exports = {
  buildBrokerExplanation,
};