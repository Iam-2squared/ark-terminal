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

function evaluateMarketSentiment({
  breadthScore = 0,
  momentumScore = 0,
  volumeScore = 0,
  newsScore = 0,
} = {}) {
  const score =
    clamp(
      Math.round(
        (
          Number(breadthScore) *
          0.35
        ) +
        (
          Number(momentumScore) *
          0.3
        ) +
        (
          Number(volumeScore) *
          0.2
        ) +
        (
          Number(newsScore) *
          0.15
        ),
      ),
      -100,
      100,
    );

  return {
    score,

    label:
      score >= 40
        ? "bullish"
        : score <= -40
          ? "bearish"
          : score >= 15
            ? "slightly_bullish"
            : score <= -15
              ? "slightly_bearish"
              : "neutral",

    extreme:
      Math.abs(score) >= 75,
  };
}

module.exports = {
  evaluateMarketSentiment,
};