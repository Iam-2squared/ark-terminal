// Part263 B30 Portfolio Forecast Engine

function forecastPortfolio(portfolio = {}) {
  return {
    portfolio,
    forecastAt: new Date().toISOString(),
  };
}

module.exports = {
    forecastPortfolio,
};
