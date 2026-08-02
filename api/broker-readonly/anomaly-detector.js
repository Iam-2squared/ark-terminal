function detectBrokerAnomalies(
  metrics = {},
) {
  const anomalies = [];

  const latency =
    Number(
      metrics.latency,
    );

  const errors =
    Number(
      metrics.errors,
    );

  const uptime =
    Number(
      metrics.uptime,
    );

  if (
    Number.isFinite(latency) &&
    latency > 1500
  ) {
    anomalies.push({
      code:
        "LATENCY_SPIKE",

      severity:
        "high",

      value:
        latency,
    });
  }

  if (
    Number.isFinite(errors) &&
    errors >= 10
  ) {
    anomalies.push({
      code:
        "ERROR_BURST",

      severity:
        "critical",

      value:
        errors,
    });
  }

  if (
    Number.isFinite(uptime) &&
    uptime < 95
  ) {
    anomalies.push({
      code:
        "AVAILABILITY_DROP",

      severity:
        "critical",

      value:
        uptime,
    });
  }

  if (
    metrics.connected ===
    false
  ) {
    anomalies.push({
      code:
        "DISCONNECTED",

      severity:
        "critical",

      value:
        false,
    });
  }

  return {
    detected:
      anomalies.length > 0,

    count:
      anomalies.length,

    anomalies,
  };
}

module.exports = {
  detectBrokerAnomalies,
};