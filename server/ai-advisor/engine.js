const {
  normalizeAdvisorInput,
} = require("./normalize");

const {
  collectSignals,
} = require("./signals");

const {
  detectConflicts,
} = require("./conflicts");

const {
  evaluateSafetyGate,
} = require("./safety-gate");

const {
  calculateAdvisorScore,
} = require("./score");

const {
  calculateAdvisorConfidence,
} = require("./confidence");

const {
  createRecommendation,
} = require("./recommendation");

const {
  createAdvisorExplanation,
} = require("./explanation");

function runAdvisor(input = {}) {
  const normalized =
    normalizeAdvisorInput(input);

  const signals =
    collectSignals(normalized);

  const conflicts =
    detectConflicts(normalized);

  const safety =
    evaluateSafetyGate(normalized);

  const score =
    calculateAdvisorScore(normalized);

  const confidence =
    calculateAdvisorConfidence(
      normalized,
      conflicts
    );

  const recommendation =
    createRecommendation({
      input: normalized,
      score,
      confidence,
      conflicts,
      safety,
    });

  const explanation =
    createAdvisorExplanation({
      score,
      confidence,
      conflicts,
      safety,
      recommendation,
    });

  return {
    version:
      "ai-advisor-v1",

    generatedAt:
      new Date().toISOString(),

    symbol:
      normalized.symbol,

    signals,
    conflicts,
    safety,
    score,
    confidence,
    recommendation,
    explanation,

    liveTradingAllowed:
      false,

    orderSubmissionAllowed:
      false,
  };
}

module.exports = {
  runAdvisor,
};