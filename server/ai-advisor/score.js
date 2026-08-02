function clamp(value) {
  return Math.max(
    0,
    Math.min(
      100,
      Number(value) || 0
    )
  );
}

function calculateAdvisorScore(input = {}) {
  const aiScore =
    clamp(
      input.ai?.score?.score
    );

  const marketScore =
    clamp(
      input.market?.globalScore?.score ??
      input.market?.score ??
      50
    );

  const portfolioScore =
    clamp(
      input.portfolio?.score?.score ??
      input.portfolio?.score ??
      50
    );

  const brokerScore =
    clamp(
      input.broker?.score?.score ??
      input.broker?.score ??
      100
    );

  const score =
    Math.round(
      aiScore * 0.4 +
      marketScore * 0.25 +
      portfolioScore * 0.2 +
      brokerScore * 0.15
    );

  return {
    score,

    grade:
      score >= 85 ? "A" :
      score >= 70 ? "B" :
      score >= 55 ? "C" :
      score >= 40 ? "D" :
      "E",
  };
}

module.exports = {
  calculateAdvisorScore,
};