function calculateAiRisk(input = {}) {
  const score = Math.round(
    input.volatilityRisk * 0.3 +
    input.drawdownRisk * 0.3 +
    input.eventRisk * 0.25 +
    input.concentrationRisk * 0.15
  );

  const factors = [];

  if (input.volatilityRisk >= 70) {
    factors.push("high_volatility");
  }

  if (input.drawdownRisk >= 70) {
    factors.push("drawdown_risk");
  }

  if (input.eventRisk >= 70) {
    factors.push("event_risk");
  }

  if (input.concentrationRisk >= 70) {
    factors.push("concentration_risk");
  }

  return {
    score,
    level:
      score >= 75 ? "critical" :
      score >= 55 ? "high" :
      score >= 30 ? "moderate" : "low",
    factors,
  };
}

module.exports = {
  calculateAiRisk,
};