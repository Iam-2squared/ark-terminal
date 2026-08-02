function clamp(value) {
  return Math.max(
    0,
    Math.min(
      100,
      Number(value) || 0
    )
  );
}

function calculateAdvisorConfidence(
  input = {},
  conflicts = {}
) {
  const aiConfidence =
    clamp(
      input.ai?.confidence?.score
    );

  const marketConfidence =
    clamp(
      input.market?.confidence?.score ??
      60
    );

  const portfolioConfidence =
    clamp(
      input.portfolio?.confidence?.score ??
      60
    );

  const conflictPenalty =
    conflicts.conflicts?.length
      ? Math.min(
          30,
          conflicts.conflicts.length * 10
        )
      : 0;

  const score =
    Math.max(
      0,
      Math.round(
        aiConfidence * 0.5 +
        marketConfidence * 0.25 +
        portfolioConfidence * 0.25 -
        conflictPenalty
      )
    );

  return {
    score,

    level:
      score >= 80 ? "high" :
      score >= 55 ? "medium" :
      "low",
  };
}

module.exports = {
  calculateAdvisorConfidence,
};