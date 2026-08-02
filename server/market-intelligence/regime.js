function classifyMarketRegime({
  trendScore = 0,
  sentimentScore = 0,
  breadthScore = 0,
  volatilityRegime = "low",
} = {}) {
  const composite =
    (
      Number(trendScore) *
      0.45
    ) +
    (
      Number(sentimentScore) *
      0.3
    ) +
    (
      Number(breadthScore) *
      0.25
    );

  const highVolatility =
    [
      "high",
      "extreme",
    ].includes(
      volatilityRegime,
    );

  let regime =
    "sideways";

  if (
    highVolatility &&
    composite <= -20
  ) {
    regime =
      "risk_off";
  }
  else if (
    highVolatility &&
    composite >= 20
  ) {
    regime =
      "volatile_bull";
  }
  else if (
    composite >= 35
  ) {
    regime =
      "bull";
  }
  else if (
    composite <= -35
  ) {
    regime =
      "bear";
  }

  return {
    compositeScore:
      composite,

    regime,

    highVolatility,

    riskOn:
      [
        "bull",
        "volatile_bull",
      ].includes(
        regime,
      ),
  };
}

module.exports = {
  classifyMarketRegime,
};