import test from "node:test";
import assert from "node:assert/strict";

import { ExecutionLearningPipelineV1 } from "../learning/execution-learning-pipeline-v1.js";

test("learning pipeline requires walk-forward and human approval before production", () => {
  const pipeline = new ExecutionLearningPipelineV1({
    productionModel: { version: "prod-1" },
    candidateBuilder: ({ records }) => ({
      id: "candidate-1",
      model: { version: "candidate-1", learnedFrom: records.length },
    }),
    walkForwardEvaluator: ({ candidate }) => ({
      passed: candidate.datasetSize >= 2,
      profitFactor: 1.4,
      sharpe: 1.1,
      maxDrawdownPercent: 12,
    }),
  });

  const candidate = pipeline.createCandidate({
    records: [
      { action: "BUY", status: "WIN" },
      { action: "SELL", status: "LOSS" },
      { action: "BUY", status: "PENDING" },
      { action: "NO_TRADE", status: "WIN" },
    ],
  });

  assert.equal(candidate.datasetSize, 2);
  assert.throws(() => pipeline.promoteApprovedCandidate(candidate.id));

  const evaluated = pipeline.evaluateCandidate(candidate.id);
  assert.equal(evaluated.status, "AWAITING_APPROVAL");
  assert.throws(() => pipeline.approveCandidate(candidate.id, {}));

  const approved = pipeline.approveCandidate(candidate.id, { approvedBy: "human-owner" });
  assert.equal(approved.status, "APPROVED");

  const production = pipeline.promoteApprovedCandidate(candidate.id);
  assert.equal(production.version, "candidate-1");
  assert.equal(production.promotedFromCandidateId, candidate.id);
  assert.equal(pipeline.getState().autoPromotionAllowed, false);
});

test("learning pipeline rejects empty closed-trade datasets", () => {
  const pipeline = new ExecutionLearningPipelineV1({
    candidateBuilder: () => ({ id: "x" }),
    walkForwardEvaluator: () => ({ passed: true }),
  });

  assert.throws(() => pipeline.createCandidate({
    records: [{ action: "BUY", status: "PENDING" }],
  }));
});
