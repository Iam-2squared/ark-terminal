function classifyVolatilityRegime({
  atrPercent = 0,
  realizedVolatility = 0,
  volatilityIndex = 0,
} = {}) {
  const atr =
    Math.max(
      0,
      Number(atrPercent) || 0,
    );

  const realized =
    Math.max(
      0,
      Number(realizedVolatility) || 0,
    );

  const index =
    Math.max(
      0,
      Number(volatilityIndex) || 0,
    );

  const score =
    (
      atr *
      8
    ) +
    (
      realized *
      0.8
    ) +
    (
      index *
      1.2
    );

  return {
    score,

    regime:
      score >= 70
        ? "extreme"
        : score >= 45
          ? "high"
          : score >= 25
            ? "moderate"
            : "low",

    riskElevated:
      score >= 45,
  };
}

module.exports = {
  classifyVolatilityRegime,
};