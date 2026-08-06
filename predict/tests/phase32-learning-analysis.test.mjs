import test from "node:test";
import assert from "node:assert/strict";

import {
  classifyPhase32Failures,
  analyzePhase32Weaknesses,
  analyzePhase32ConfidenceCalibration,
  buildPhase32ImprovementProposals,
  runPhase32LearningAnalysis,
} from "../learning/phase32-learning-analysis.js";

const rows = [
  { id: "a", symbol: "7203.T", sector: "AUTO", regime: "BULL", signal: "BUY", confidence: 0.9, actualReturn: -0.03, netReturn: -0.035 },
  { id: "b", symbol: "7203.T", sector: "AUTO", regime: "BULL", signal: "BUY", confidence: 0.85, actualReturn: -0.02, netReturn: -0.025 },
  { id: "c", symbol: "7203.T", sector: "AUTO", regime: "BULL", signal: "BUY", confidence: 0.8, actualReturn: 0.01, netReturn: 0.005 },
  { id: "d", symbol: "6758.T", sector: "TECH", regime: "RANGE", signal: "SELL", confidence: 0.6, actualReturn: -0.02, netReturn: 0.015 },
  { id: "e", symbol: "6758.T", sector: "TECH", regime: "RANGE", signal: "NO_TRADE", confidence: 0.4, actualReturn: 0.03, netReturn: 0 },
  { id: "f", symbol: "6758.T", sector: "TECH", regime: "RANGE", signal: "BUY", confidence: 0.55, actualReturn: 0.02, netReturn: 0.015 },
];

test("classifies direction, loss, high-confidence and missed-upside failures", () => {
  const classified = classifyPhase32Failures(rows, { lossThreshold: 0.02, highConfidence: 0.75 });
  assert.ok(classified[0].failureReasons.includes("DIRECTION_MISS"));
  assert.ok(classified[0].failureReasons.includes("LOSS_THRESHOLD_BREACH"));
  assert.ok(classified[0].failureReasons.includes("HIGH_CONFIDENCE_FAILURE"));
  assert.ok(classified[4].failureReasons.includes("MISSED_UPSIDE"));
});

test("aggregates weaknesses by regime, symbol and sector", () => {
  const classified = classifyPhase32Failures(rows);
  const report = analyzePhase32Weaknesses(classified, { minSamples: 2 });
  assert.equal(report.status, "WEAKNESSES_FOUND");
  assert.ok(report.flagged.some((item) => item.dimension === "REGIME" && item.name === "BULL"));
  assert.equal(report.safety.productionUpdateAllowed, false);
});

test("detects confidence overstatement", () => {
  const classified = classifyPhase32Failures(rows);
  const report = analyzePhase32ConfidenceCalibration(classified);
  assert.equal(report.overconfidenceDetected, true);
  assert.ok(report.bins.some((item) => item.overconfident));
});

test("improvement proposals are review-only", () => {
  const classified = classifyPhase32Failures(rows);
  const weaknessReport = analyzePhase32Weaknesses(classified, { minSamples: 2 });
  const calibrationReport = analyzePhase32ConfidenceCalibration(classified);
  const review = buildPhase32ImprovementProposals({ classifiedRows: classified, weaknessReport, calibrationReport });
  assert.equal(review.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(review.automaticCandidateCreationAllowed, false);
  assert.equal(review.automaticPromotionAllowed, false);
  assert.equal(review.productionUpdateAllowed, false);
  assert.equal(review.brokerWrites, 0);
  assert.equal(review.liveOrders, 0);
  assert.ok(review.proposals.every((item) => item.candidatePatchCreated === false));
});

test("full runner stays learning-analysis-only", () => {
  const result = runPhase32LearningAnalysis({ rows, options: { minSamples: 2 } });
  assert.equal(result.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(result.safety.mode, "LEARNING_ANALYSIS_ONLY");
  assert.equal(result.automaticCandidateCreationAllowed, false);
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
});
