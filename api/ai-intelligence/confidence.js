function calculateAiConfidence(input = {}, evidence = {}) {
  const evidenceCount =
    evidence.positive.length +
    evidence.negative.length;

  const agreementBonus =
    evidence.agreement === "mixed"
      ? 0
      : Math.min(15, evidenceCount * 3);

  const score = Math.min(
    100,
    Math.round(
      input.dataQuality * 0.5 +
      input.freshness * 0.35 +
      agreementBonus
    )
  );

  return {
    score,
    level:
      score >= 80 ? "high" :
      score >= 55 ? "medium" : "low",
  };
}

module.exports = {
  calculateAiConfidence,
};