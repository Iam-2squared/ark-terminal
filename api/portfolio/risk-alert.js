// Part263 B25 Portfolio Risk Alert Engine

function createRiskAlerts(risks = []) {
  return {
    alerts: risks,
    generatedAt: new Date().toISOString(),
  };
}

module.exports = {
    createRiskAlerts,
};
