function createAiScenarios({
  score = {},
  risk = {},
} = {}) {
  return {
    bullish: {
      condition:
        "Score improves while risk remains controlled.",
      bias:
        score.score >= 65 ? "supported" : "conditional",
    },

    base: {
      condition:
        "Current evidence and market conditions continue.",
      bias:
        score.score >= 55 ? "positive" : "neutral",
    },

    bearish: {
      condition:
        "Risk rises or supporting evidence deteriorates.",
      bias:
        risk.score >= 55 ? "elevated" : "conditional",
    },
  };
}

module.exports = {
  createAiScenarios,
};