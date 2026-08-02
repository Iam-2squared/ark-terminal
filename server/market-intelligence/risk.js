function evaluateMarketRisk({
  regime = "sideways",
  volatilityRegime = "low",
  sentimentScore = 0,
  breadthScore = 0,
} = {}) {
  let score = 0;
  const factors = [];

  if (
    regime ===
    "risk_off"
  ) {
    score += 45;

    factors.push(
      "risk_off_regime",
    );
  }

  if (
    volatilityRegime ===
    "extreme"
  ) {
    score += 40;

    factors.push(
      "extreme_volatility",
    );
  }
  else if (
    volatilityRegime ===
    "high"
  ) {
    score += 25;

    factors.push(
      "high_volatility",
    );
  }

  if (
    Number(sentimentScore) <=
    -50
  ) {
    score += 20;

    factors.push(
      "bearish_sentiment",
    );
  }

  if (
    Number(breadthScore) <=
    -30
  ) {
    score += 20;

    factors.push(
      "weak_market_breadth",
    );
  }

  score =
    Math.min(
      100,
      score,
    );

  return {
    score,

    level:
      score >= 75
        ? "critical"
        : score >= 50
          ? "high"
          : score >= 25
            ? "moderate"
            : "low",

    factors,
  };
}

module.exports = {
  evaluateMarketRisk,
};