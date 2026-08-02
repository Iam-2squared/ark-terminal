const {
  normalizeAiInput,
} = require("./normalize");

const {
  buildEvidence,
} = require("./evidence");

const {
  calculateAiScore,
} = require("./score");

const {
  calculateAiRisk,
} = require("./risk");

const {
  calculateAiConfidence,
} = require("./confidence");

const {
  evaluateAiPolicy,
} = require("./policy");

const {
  createAiDecision,
} = require("./decision");

const {
  createAiExplanation,
} = require("./explanation");

const {
  createAiScenarios,
} = require("./scenario");

function analyzeWithAi(input = {}) {
  const normalized =
    normalizeAiInput(input);

  const evidence =
    buildEvidence(normalized);

  const score =
    calculateAiScore(normalized);

  const risk =
    calculateAiRisk(normalized);

  const confidence =
    calculateAiConfidence(
      normalized,
      evidence
    );

  const policy =
    evaluateAiPolicy({
      input: normalized,
      risk,
      confidence,
    });

  const decision =
    createAiDecision({
      score,
      risk,
      confidence,
      policy,
    });

  const explanation =
    createAiExplanation({
      score,
      risk,
      confidence,
      evidence,
      decision,
    });

  const scenarios =
    createAiScenarios({
      score,
      risk,
    });

  return {
    version: "ai-intelligence-v1",
    generatedAt: new Date().toISOString(),
    symbol: normalized.symbol,
    score,
    risk,
    confidence,
    evidence,
    policy,
    decision,
    explanation,
    scenarios,
    liveTradingAllowed: false,
    orderSubmissionAllowed: false,
  };
}

module.exports = {
  analyzeWithAi,
};