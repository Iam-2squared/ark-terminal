const {
  analyzeMarket,
} = require("./engine");

function createMarketIntelligenceService({
  maximumHistory = 200,
} = {}) {
  const history = [];

  function analyze(
    input = {},
  ) {
    const result =
      analyzeMarket(
        input,
      );

    history.push(
      structuredClone(
        result,
      ),
    );

    while (
      history.length >
      maximumHistory
    ) {
      history.shift();
    }

    return result;
  }

  function getHistory() {
    return structuredClone(
      history,
    );
  }

  function getLatest() {
    return history.length
      ? structuredClone(
          history[
            history.length - 1
          ],
        )
      : null;
  }

  return {
    analyze,
    getHistory,
    getLatest,
  };
}

module.exports = {
  createMarketIntelligenceService,
};