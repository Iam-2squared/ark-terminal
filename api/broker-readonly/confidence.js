function clamp(
  value,
  minimum,
  maximum,
) {
  return Math.max(
    minimum,
    Math.min(
      maximum,
      value,
    ),
  );
}

function calculateBrokerConfidence({
  sampleCount = 0,
  anomalyCount = 0,
  connected = false,
  authenticated = false,
} = {}) {
  let score = 20;

  score +=
    Math.min(
      Number(sampleCount) || 0,
      50,
    );

  if (connected) {
    score += 15;
  }

  if (authenticated) {
    score += 15;
  }

  score -=
    Math.min(
      (
        Number(anomalyCount) ||
        0
      ) * 10,
      50,
    );

  score =
    clamp(
      Math.round(score),
      0,
      100,
    );

  return {
    score,

    level:
      score >= 80
        ? "high"
        : score >= 50
          ? "medium"
          : "low",

    sufficientEvidence:
      score >= 50,
  };
}

module.exports = {
  calculateBrokerConfidence,
};