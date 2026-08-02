// Part263 B27 Portfolio Scenario Simulator

function simulateScenario(portfolio = {}) {
  return {
    portfolio,
    simulatedAt: new Date().toISOString(),
  };
}

module.exports = {
    simulateScenario,
};
