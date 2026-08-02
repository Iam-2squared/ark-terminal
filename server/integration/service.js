const {
  runIntegration,
} = require("./orchestrator");

const {
  createIntegrationHistory,
} = require("./history");

function createIntegrationService() {
  const history =
    createIntegrationHistory();

  function analyze(input = {}) {
    const result =
      runIntegration(input);

    history.add(result);

    return result;
  }

  function getHistory() {
    return history.list();
  }

  function getLatest() {
    return history.latest();
  }

  return {
    analyze,
    getHistory,
    getLatest,
  };
}

module.exports = {
  createIntegrationService,
};