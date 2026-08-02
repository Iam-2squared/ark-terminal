// Part263 B2 Portfolio Session

function createPortfolioSession() {
  return {
    id: Date.now().toString(),
    createdAt: new Date().toISOString(),
    active: true,
    simulationOnly: true,
    holdings: [],
  };
}

module.exports = {
  createPortfolioSession,
};
