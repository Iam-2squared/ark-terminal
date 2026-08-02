function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.max(minimum, Math.min(maximum, finite(value)));
}

function normalizeAiInput(input = {}) {
  return {
    symbol:
      typeof input.symbol === "string"
        ? input.symbol.trim().toUpperCase()
        : "",

    technicalScore: clamp(input.technicalScore),
    fundamentalScore: clamp(input.fundamentalScore),
    marketScore: clamp(input.marketScore),
    newsScore: clamp(input.newsScore),
    portfolioFit: clamp(input.portfolioFit),
    liquidityScore: clamp(input.liquidityScore),
    dataQuality: clamp(input.dataQuality),
    freshness: clamp(input.freshness),

    volatilityRisk: clamp(input.volatilityRisk),
    drawdownRisk: clamp(input.drawdownRisk),
    eventRisk: clamp(input.eventRisk),
    concentrationRisk: clamp(input.concentrationRisk),

    brokerConnected: input.brokerConnected !== false,
    marketConnected: input.marketConnected !== false,
  };
}

module.exports = {
  finite,
  clamp,
  normalizeAiInput,
};