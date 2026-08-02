function analyzeMarketBreadth({
  advancing = 0,
  declining = 0,
  unchanged = 0,
} = {}) {
  const up =
    Math.max(
      0,
      Number(advancing) || 0,
    );

  const down =
    Math.max(
      0,
      Number(declining) || 0,
    );

  const flat =
    Math.max(
      0,
      Number(unchanged) || 0,
    );

  const total =
    up +
    down +
    flat;

  const advanceDeclineRatio =
    down > 0
      ? up / down
      : up > 0
        ? Infinity
        : 0;

  const strengthPercent =
    total > 0
      ? (
          (up - down) /
          total
        ) * 100
      : 0;

  return {
    advancing:
      up,

    declining:
      down,

    unchanged:
      flat,

    total,

    advanceDeclineRatio,
    strengthPercent,

    condition:
      strengthPercent >= 20
        ? "strong"
        : strengthPercent <= -20
          ? "weak"
          : "neutral",
  };
}

module.exports = {
  analyzeMarketBreadth,
};