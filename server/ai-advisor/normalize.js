function objectOrEmpty(value) {
  return value && typeof value === "object"
    ? value
    : {};
}

function normalizeAdvisorInput(input = {}) {
  return {
    symbol:
      typeof input.symbol === "string"
        ? input.symbol.trim().toUpperCase()
        : "",

    ai:
      objectOrEmpty(input.ai),

    market:
      objectOrEmpty(input.market),

    portfolio:
      objectOrEmpty(input.portfolio),

    broker:
      objectOrEmpty(input.broker),

    requestedAt:
      input.requestedAt ||
      new Date().toISOString(),

    humanApproval:
      input.humanApproval === true,
  };
}

module.exports = {
  normalizeAdvisorInput,
};