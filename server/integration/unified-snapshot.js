function createUnifiedSnapshot({
  broker = {},
  portfolio = {},
  market = {},
} = {}) {
  return {
    generatedAt:
      new Date().toISOString(),

    broker:
      structuredClone(broker),

    portfolio:
      structuredClone(portfolio),

    market:
      structuredClone(market),

    readOnly:
      true,

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  createUnifiedSnapshot,
};