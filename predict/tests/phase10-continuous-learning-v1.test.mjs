import test from "node:test";
import assert from "node:assert/strict";

import { ContinuousLearningOrchestratorV1 } from "../learning/continuous-learning-v1.js";

function memoryStorage() {
  const map = new Map();
  return {
    getItem: (key) => map.has(key) ? map.get(key) : null,
    setItem: (key, value) => map.set(key, String(value)),
    removeItem: (key) => map.delete(key),
  };
}

function validatedCandidate(orchestrator, version = "candidate-v1", metrics = {}) {
  const candidate = orchestrator.createCandidate({
    sourceTradeCount: 120,
    weights: { rsi: 0.4, macd: 0.6 },
    calibration: { expectedCalibrationError: 0.08 },
    drift: { driftDetected: false },
    metadata: { version },
  });
  orchestrator.recordWalkForward(candidate.id, {
    outOfSample: true,
    futureLeakChecked: true,
    passed: true,
    metrics: {
      accuracy: 62,
      winRate: 58,
      profitFactor: 1.4,
      sharpe: 1.2,
      maxDrawdown: 12,
      averageReturn: 0.8,
      ...metrics,
    },
  });
  return candidate;
}

test("Part6 creates Candidate and requires complete Walk Forward validation", () => {
  const orchestrator = new ContinuousLearningOrchestratorV1();
  const candidate = orchestrator.createCandidate({ sourceTradeCount: 50, metadata: { version: "candidate-a" } });
  orchestrator.recordWalkForward(candidate.id, {
    outOfSample: false,
    futureLeakChecked: true,
    passed: true,
    metrics: { profitFactor: 1.5, sharpe: 1.1, maxDrawdown: 10, averageReturn: 1 },
  });
  const comparison = orchestrator.compareToProduction(candidate.id);
  assert.equal(comparison.readyForReview, false);
  assert.equal(orchestrator.getCandidate(candidate.id).status, "REJECTED");
});

test("Part6 compares Candidate to Production and marks improvements ready for review", () => {
  const orchestrator = new ContinuousLearningOrchestratorV1();
  orchestrator.setProduction({
    version: "production-v1",
    metrics: { accuracy: 60, winRate: 55, profitFactor: 1.2, sharpe: 1.0, maxDrawdown: 15, averageReturn: 0.5 },
  });
  const candidate = validatedCandidate(orchestrator);
  const comparison = orchestrator.compareToProduction(candidate.id);
  assert.equal(comparison.readyForReview, true);
  assert.equal(orchestrator.getCandidate(candidate.id).status, "READY_FOR_REVIEW");
  assert.ok(comparison.deltas.profitFactor > 0);
  assert.ok(comparison.deltas.maxDrawdown > 0);
});

test("Part6 blocks automatic Production promotion and requires human approval", () => {
  const orchestrator = new ContinuousLearningOrchestratorV1();
  const candidate = validatedCandidate(orchestrator);
  orchestrator.compareToProduction(candidate.id);
  assert.throws(() => orchestrator.approveCandidate(candidate.id), /HUMAN_APPROVAL_REQUIRED/);
  const production = orchestrator.approveCandidate(candidate.id, { approvedBy: "Iam-2squared" });
  assert.equal(production.version, "candidate-v1");
  assert.equal(production.approvedBy, "Iam-2squared");
  assert.equal(production.productionUpdateAllowed, false);
});

test("Part6 rejects a Candidate that does not improve risk-adjusted metrics", () => {
  const orchestrator = new ContinuousLearningOrchestratorV1();
  orchestrator.setProduction({
    version: "production-v1",
    metrics: { profitFactor: 1.4, sharpe: 1.2, maxDrawdown: 12, averageReturn: 0.8 },
  });
  const candidate = validatedCandidate(orchestrator, "candidate-worse", {
    profitFactor: 1.1,
    sharpe: 0.7,
    maxDrawdown: 20,
    averageReturn: 0.2,
  });
  const comparison = orchestrator.compareToProduction(candidate.id);
  assert.equal(comparison.readyForReview, false);
  assert.equal(orchestrator.getCandidate(candidate.id).status, "REJECTED");
});

test("Part6 persists model history and can reload state", () => {
  const storage = memoryStorage();
  const first = new ContinuousLearningOrchestratorV1({ storage });
  const candidate = validatedCandidate(first, "candidate-persisted");
  first.compareToProduction(candidate.id);
  first.approveCandidate(candidate.id, { approvedBy: "Iam-2squared" });

  const second = new ContinuousLearningOrchestratorV1({ storage });
  const state = second.getState();
  assert.equal(state.production.version, "candidate-persisted");
  assert.ok(state.history.some((item) => item.type === "CANDIDATE_APPROVED"));
});

test("Part6 rollback also requires human approval", () => {
  const orchestrator = new ContinuousLearningOrchestratorV1();
  const first = validatedCandidate(orchestrator, "candidate-v1");
  orchestrator.compareToProduction(first.id);
  orchestrator.approveCandidate(first.id, { approvedBy: "Iam-2squared" });

  const second = validatedCandidate(orchestrator, "candidate-v2", { profitFactor: 1.6, sharpe: 1.4, maxDrawdown: 9, averageReturn: 1.1 });
  orchestrator.compareToProduction(second.id);
  orchestrator.approveCandidate(second.id, { approvedBy: "Iam-2squared" });

  assert.throws(() => orchestrator.rollback("candidate-v1"), /HUMAN_APPROVAL_REQUIRED/);
  const rolledBack = orchestrator.rollback("candidate-v1", { approvedBy: "Iam-2squared", reason: "regression detected" });
  assert.equal(rolledBack.version, "candidate-v1");
  assert.equal(rolledBack.rollbackFrom, "candidate-v2");
});
