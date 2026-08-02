function finite(
  value,
) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(
      Number(value),
    )
  );
}

function numberOrZero(
  value,
) {
  return finite(value)
    ? Number(value)
    : 0;
}

function evaluateBrokerRisk(
  metrics = {},
) {
  const latency =
    numberOrZero(
      metrics.latency,
    );

  const errors =
    numberOrZero(
      metrics.errors,
    );

  const uptime =
    finite(
      metrics.uptime,
    )
      ? Number(
          metrics.uptime,
        )
      : 100;

  let score = 0;
  const factors = [];

  if (latency > 1000) {
    score += 35;
    factors.push(
      "high_latency",
    );
  }
  else if (latency > 500) {
    score += 20;
    factors.push(
      "elevated_latency",
    );
  }

  if (errors >= 5) {
    score += 40;
    factors.push(
      "frequent_errors",
    );
  }
  else if (errors > 0) {
    score += errors * 5;
    factors.push(
      "errors_detected",
    );
  }

  if (uptime < 95) {
    score += 30;
    factors.push(
      "low_uptime",
    );
  }
  else if (uptime < 99) {
    score += 10;
    factors.push(
      "reduced_uptime",
    );
  }

  score =
    Math.max(
      0,
      Math.min(
        100,
        Math.round(score),
      ),
    );

  return {
    score,

    level:
      score >= 70
        ? "critical"
        : score >= 40
          ? "high"
          : score >= 20
            ? "moderate"
            : "low",

    factors,
  };
}

module.exports = {
  evaluateBrokerRisk,
};