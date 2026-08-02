function buildEvidence(input = {}) {
  const positive = [];
  const negative = [];

  const checks = [
    ["technical", input.technicalScore],
    ["fundamental", input.fundamentalScore],
    ["market", input.marketScore],
    ["news", input.newsScore],
    ["portfolio_fit", input.portfolioFit],
    ["liquidity", input.liquidityScore],
  ];

  for (const [name, score] of checks) {
    if (score >= 65) {
      positive.push({
        factor: name,
        score,
      });
    } else if (score <= 35) {
      negative.push({
        factor: name,
        score,
      });
    }
  }

  return {
    positive,
    negative,
    agreement:
      positive.length > negative.length
        ? "positive"
        : negative.length > positive.length
          ? "negative"
          : "mixed",
  };
}

module.exports = {
  buildEvidence,
};