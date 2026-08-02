import assert from "node:assert/strict";
import test from "node:test";

import { evaluateModelPromotionCandidate } from "../learning/model-promotion-gate.js";

function rows(count, prefix) {
  return Array.from({ length: count }, (_, index) => ({
    id: `${prefix}-${index}`,
    audit: { futureInformationIncluded: false },
  }));
}

function feedback({
  training = 36,
  validation = 12,
  finalTest = 12,
  updated = true,
  futureInformationIncluded = false,
} = {}) {
  const partitions = {
    training: rows(training, "training"),
    validation: rows(validation, "validation"),
    test: rows(finalTest, "test"),
  };
  return {
    id: "feedback-1",
    generatedAt: "2026-08-03T00:00:00.000Z",
    learningDataset: {
      rows: Object.values(partitions).flat(),
      partitions,
    },
    weightCandidate: {
      updated,
      applied: false,
      weights: { rsi: 10 },
    },
    audit: {
      futureInformationIncluded,
      activeWeightsChanged: false,
    },
  };
}

test("Sufficient chronological evidence creates a validation candidate", () => {
  const gate = evaluateModelPromotionCandidate(feedback());

  assert.equal(gate.eligible, true);
  assert.equal(gate.status, "eligible_for_validation");
  assert.deepEqual(gate.candidate.weights, { rsi: 10 });
  assert.equal(gate.promotionAllowed, false);
  assert.equal(gate.requiresBacktestValidation, true);
  assert.equal(gate.requiresHumanApproval, true);
  assert.equal(gate.executionAllowed, false);
});

test("Small validation or final-test partitions block candidacy", () => {
  const gate = evaluateModelPromotionCandidate(
    feedback({ training: 50, validation: 5, finalTest: 5 }),
  );

  assert.equal(gate.eligible, false);
  assert.equal(gate.candidate, null);
  assert.equal(gate.checks.totalSamples, true);
  assert.equal(gate.checks.validationSamples, false);
  assert.equal(gate.checks.testSamples, false);
});

test("Future leakage blocks candidacy regardless of sample size", () => {
  const gate = evaluateModelPromotionCandidate(
    feedback({ futureInformationIncluded: true }),
  );

  assert.equal(gate.eligible, false);
  assert.equal(gate.checks.noFutureInformation, false);
  assert.match(gate.reasons.join(" "), /未来情報/);
});

test("Unchanged optimizer output is not a promotion candidate", () => {
  const gate = evaluateModelPromotionCandidate(feedback({ updated: false }));
  assert.equal(gate.eligible, false);
  assert.equal(gate.checks.candidateReady, false);
});
