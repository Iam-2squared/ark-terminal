import test from "node:test";
import assert from "node:assert/strict";

import {
  PHASE44_SAFETY,
  createValidationCandidate,
  evaluateOverfitting,
  rankValidationCandidates,
  compareChampionCandidate,
  buildSelectionDashboard,
} from "../models/phase44-model-selection.js";

const champion = {
  modelId: "ark-core",
  version: "1.0.0",
  featureSetId: "core-v1",
  datasetHash: "dataset-a",
  artifactHash: "artifact-a",
  metrics: { winRate: 0.58, averageReturn: 0.012, profitFactor: 1.45, maxDrawdown: -0.12, sharpe: 1.1, sampleCount: 400 },
  walkForward: { folds: 5, successfulFolds: 4, stabilityScore: 0.72 },
};

const candidate = {
  ...champion,
  version: "1.1.0",
  artifactHash: "artifact-b",
  metrics: { winRate: 0.61, averageReturn: 0.015, profitFactor: 1.7, maxDrawdown: -0.1, sharpe: 1.35, sampleCount: 420 },
  walkForward: { folds: 6, successfulFolds: 5, stabilityScore: 0.8 },
};

test("creates deterministic candidate records", () => {
  const first = createValidationCandidate({ ...candidate, createdAt: "2026-08-06T00:00:00.000Z" });
  const second = createValidationCandidate({ ...candidate, createdAt: "2026-08-06T00:00:00.000Z" });
  assert.equal(first.candidateKey, "ark-core:1.1.0");
  assert.equal(first.contentHash, second.contentHash);
  assert.equal(Object.isFrozen(first), true);
});

test("blocks unstable or undersampled candidates", () => {
  const record = createValidationCandidate({
    ...candidate,
    metrics: { ...candidate.metrics, sampleCount: 20 },
    walkForward: { folds: 1, successfulFolds: 1, stabilityScore: 0.2 },
  });
  const result = evaluateOverfitting(record);
  assert.equal(result.status, "BLOCKED");
  assert.ok(result.blockers.includes("INSUFFICIENT_WALK_FORWARD_FOLDS"));
  assert.ok(result.blockers.includes("UNSTABLE_WALK_FORWARD_RESULTS"));
  assert.ok(result.blockers.includes("INSUFFICIENT_SAMPLE_COUNT"));
});

test("ranks valid candidates without automatic promotion", () => {
  const ranking = rankValidationCandidates({ candidates: [champion, candidate], champion });
  assert.equal(ranking.recommendedCandidateKey, "ark-core:1.1.0");
  assert.equal(ranking.ranked[0].candidate.candidateKey, "ark-core:1.1.0");
  assert.equal(ranking.promotionAllowed, false);
  assert.equal(ranking.productionUpdateAllowed, false);
});

test("recommends review when candidate improves champion", () => {
  const comparison = compareChampionCandidate(champion, candidate, { minimumProfitFactorGain: 0.1 });
  assert.equal(comparison.status, "REVIEW_PROMOTION");
  assert.equal(comparison.automaticPromotion, false);
  assert.equal(comparison.humanApprovalRequired, true);
});

test("blocks mismatched lineage", () => {
  const comparison = compareChampionCandidate(champion, { ...candidate, featureSetId: "other-v1" });
  assert.equal(comparison.status, "BLOCKED");
  assert.ok(comparison.blockers.includes("FEATURE_SET_MISMATCH"));
});

test("builds fail-closed human-review dashboard", () => {
  const ranking = rankValidationCandidates({ candidates: [candidate], champion });
  const comparison = compareChampionCandidate(champion, candidate);
  const dashboard = buildSelectionDashboard({ ranking, comparison });
  assert.equal(dashboard.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(dashboard.automaticPromotion, false);
  assert.equal(dashboard.productionUpdateAllowed, false);
});

test("keeps trading and production writes disabled", () => {
  assert.equal(PHASE44_SAFETY.brokerWriteAllowed, false);
  assert.equal(PHASE44_SAFETY.liveTradingAllowed, false);
  assert.equal(PHASE44_SAFETY.orderCreationAllowed, false);
  assert.equal(PHASE44_SAFETY.orderTransmissionAllowed, false);
  assert.equal(PHASE44_SAFETY.orderCancellationAllowed, false);
  assert.equal(PHASE44_SAFETY.orderModificationAllowed, false);
  assert.equal(PHASE44_SAFETY.excelOrderWriteAllowed, false);
  assert.equal(PHASE44_SAFETY.orderTriggerWriteAllowed, false);
  assert.equal(PHASE44_SAFETY.automaticPromotionAllowed, false);
  assert.equal(PHASE44_SAFETY.productionUpdateAllowed, false);
  assert.equal(PHASE44_SAFETY.automaticRollbackAllowed, false);
  assert.equal(PHASE44_SAFETY.humanApprovalRequired, true);
});
