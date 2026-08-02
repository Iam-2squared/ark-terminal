function createAdvisorExplanation({
  score = {},
  confidence = {},
  conflicts = {},
  safety = {},
  recommendation = {},
} = {}) {
  return {
    summary:
      `Recommendation ${recommendation.recommendation}; ` +
      `score ${score.score}; ` +
      `confidence ${confidence.level}.`,

    conflicts:
      conflicts.conflicts || [],

    safetyReasons:
      safety.reasons || [],

    disclaimer:
      "This result is advisory only and cannot submit orders.",
  };
}

module.exports = {
  createAdvisorExplanation,
};