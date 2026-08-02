const {
  normalizeMarketSnapshot,
} = require("./snapshot");

const {
  evaluateMarketSentiment,
} = require("./sentiment");

const {
  classifyVolatilityRegime,
} = require("./volatility-regime");

const {
  classifyMarketRegime,
} = require("./regime");

const {
  evaluateMarketRisk,
} = require("./risk");

function analyzeMarket(
  input = {},
) {
  const snapshot =
    normalizeMarketSnapshot(
      input,
    );

  const sentiment =
    evaluateMarketSentiment({
      breadthScore:
        input.breadthScore ||
        0,

      momentumScore:
        input.momentumScore ||
        0,

      volumeScore:
        input.volumeScore ||
        0,

      newsScore:
        input.newsScore ||
        0,
    });

  const volatility =
    classifyVolatilityRegime({
      atrPercent:
        input.atrPercent ||
        0,

      realizedVolatility:
        input.realizedVolatility ||
        0,

      volatilityIndex:
        input.volatilityIndex ||
        0,
    });

  const regime =
    classifyMarketRegime({
      trendScore:
        input.trendScore ||
        0,

      sentimentScore:
        sentiment.score,

      breadthScore:
        input.breadthScore ||
        0,

      volatilityRegime:
        volatility.regime,
    });

  const risk =
    evaluateMarketRisk({
      regime:
        regime.regime,

      volatilityRegime:
        volatility.regime,

      sentimentScore:
        sentiment.score,

      breadthScore:
        input.breadthScore ||
        0,
    });

  return {
    version:
      "market-intelligence-v1",

    generatedAt:
      new Date().toISOString(),

    snapshot,
    sentiment,
    volatility,
    regime,
    risk,

    analysisOnly:
      true,

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  analyzeMarket,
};