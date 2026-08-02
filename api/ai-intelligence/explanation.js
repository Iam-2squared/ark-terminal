function createAiExplanation({
  score = {},
  risk = {},
  confidence = {},
  evidence = {},
  decision = {},
} = {}) {
  return {
    summary:
      `AI score ${score.score}, risk ${risk.level}, ` +
      `confidence ${confidence.level}, decision ${decision.action}.`,

    buyFactors:
      evidence.positive,

    sellFactors:
      evidence.negative,

    riskFactors:
      risk.factors,

    disclaimer:
      "Analysis is advisory only and does not execute orders.",
  };
}

module.exports = {
  createAiExplanation,
};