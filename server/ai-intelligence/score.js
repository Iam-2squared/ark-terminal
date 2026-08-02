function calculateAiScore(input = {}) {
  const score = Math.round(
    input.technicalScore * 0.25 +
    input.fundamentalScore * 0.15 +
    input.marketScore * 0.2 +
    input.newsScore * 0.1 +
    input.portfolioFit * 0.15 +
    input.liquidityScore * 0.15
  );

  return {
    score,
    grade:
      score >= 85 ? "A" :
      score >= 70 ? "B" :
      score >= 55 ? "C" :
      score >= 40 ? "D" : "E",
  };
}

module.exports = {
  calculateAiScore,
};