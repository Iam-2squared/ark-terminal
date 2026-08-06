import test from "node:test";
import assert from "node:assert/strict";

import {
  PHASE43_SAFETY,
  createModelVersion,
  createModelRegistry,
  evaluateTrainingRun,
  compareChampionAndCandidate,
  createRollbackPlan,
  createModelGovernanceDashboard,
} from "../models/phase43-model-registry.js";

const baseModel = {
  modelId: "ark-core",
  version: "1.0.0",
  status: "EXPERIMENT",
  algorithm: "gradient-boosting",
  featureSetId: "core-v1",
  featureManifestHash: "feature123",
  datasetChecksum: "dataset123",
  artifactChecksum: "artifact123",
  trainingWindow: { start: "2024-01-01", end: "2024-12-31" },
  validationWindow: { start: "2025-01-01", end: "2025-06-30" },
  testWindow: { start: "2025-07-01", end: "2025-12-31" },
  metrics: {
    winRate: 0.56,
    averageReturn: 0.012,
    medianReturn: 0.008,
    profitFactor: 1.35,
    maxDrawdown: 0.14,
    sharpeRatio: 1.1,
    sampleCount: 420,
    confidenceLow: 0.002,
    confidenceHigh: 0.021,
  },
  createdAt: "2026-08-06T12:00:00.000Z",
};

test("creates deterministic immutable model versions", () => {
  const first = createModelVersion(baseModel);
  const second = createModelVersion(baseModel);
  assert.equal(first.modelKey, "ark-core:1.0.0");
  assert.equal(first.registryHash, second.registryHash);
  assert.equal(Object.isFrozen(first), true);
});

test("blocks duplicate model keys and multiple champions", () => {
  const registry = createModelRegistry({
    models: [
      { ...baseModel, status: "CHAMPION" },
      { ...baseModel, status: "CHAMPION" },
      { ...baseModel, version: "1.1.0", status: "CHAMPION" },
    ],
  });
  assert.equal(registry.status, "BLOCKED");
  assert.ok(registry.blockers.includes("DUPLICATE_MODEL_KEYS"));
  assert.ok(registry.blockers.includes("MULTIPLE_CHAMPIONS"));
});

test("passes a training run only for human review", () => {
  const evaluation = evaluateTrainingRun({ model: baseModel });
  assert.equal(evaluation.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(evaluation.canRegisterAsCandidate, true);
  assert.equal(evaluation.automaticPromotionAllowed, false);
  assert.equal(evaluation.productionUpdateAllowed, false);
});

test("fails closed on missing integrity metadata and poor metrics", () => {
  const evaluation = evaluateTrainingRun({
    model: {
      ...baseModel,
      featureManifestHash: null,
      datasetChecksum: null,
      artifactChecksum: null,
      metrics: { ...baseModel.metrics, sampleCount: 10, profitFactor: 0.8, maxDrawdown: 0.5 },
    },
  });
  assert.equal(evaluation.status, "BLOCKED");
  assert.ok(evaluation.blockers.includes("FEATURE_MANIFEST_HASH_MISSING"));
  assert.ok(evaluation.blockers.includes("DATASET_CHECKSUM_MISSING"));
  assert.ok(evaluation.blockers.includes("MODEL_ARTIFACT_CHECKSUM_MISSING"));
  assert.ok(evaluation.blockers.includes("INSUFFICIENT_SAMPLE_COUNT"));
  assert.ok(evaluation.blockers.includes("PROFIT_FACTOR_BELOW_GATE"));
  assert.ok(evaluation.blockers.includes("MAX_DRAWDOWN_EXCEEDED"));
});

test("compares champion and candidate without automatic promotion", () => {
  const result = compareChampionAndCandidate({
    champion: { ...baseModel, status: "CHAMPION" },
    candidate: {
      ...baseModel,
      version: "1.1.0",
      status: "CANDIDATE",
      metrics: { ...baseModel.metrics, profitFactor: 1.5, averageReturn: 0.018, maxDrawdown: 0.13 },
    },
    gates: { requiredProfitFactorDelta: 0.05, requiredAverageReturnDelta: 0.002, allowedDrawdownIncrease: 0 },
  });
  assert.equal(result.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(result.recommendation, "REVIEW_CANDIDATE");
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.humanApprovalRequired, true);
});

test("creates rollback plans without execution", () => {
  const registry = createModelRegistry({ models: [{ ...baseModel, status: "CHAMPION" }] });
  const plan = createRollbackPlan({ registry, targetModelKey: "ark-core:1.0.0", reason: "metric regression" });
  assert.equal(plan.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(plan.executeAutomatically, false);
  assert.equal(plan.productionUpdateAllowed, false);
});

test("builds a consolidated governance dashboard", () => {
  const champion = { ...baseModel, status: "CHAMPION" };
  const candidate = { ...baseModel, version: "1.1.0", status: "CANDIDATE" };
  const registry = createModelRegistry({ models: [champion, candidate] });
  const evaluation = evaluateTrainingRun({ model: candidate });
  const comparison = compareChampionAndCandidate({ champion, candidate });
  const dashboard = createModelGovernanceDashboard({ registry, trainingEvaluations: [evaluation], comparisons: [comparison] });
  assert.equal(dashboard.modelCount, 2);
  assert.equal(dashboard.championModelKey, "ark-core:1.0.0");
  assert.deepEqual(dashboard.candidateModelKeys, ["ark-core:1.1.0"]);
  assert.equal(dashboard.automaticPromotionAllowed, false);
});

test("keeps all broker and production mutations disabled", () => {
  assert.equal(PHASE43_SAFETY.mode, "MODEL_REGISTRY_REVIEW_ONLY");
  assert.equal(PHASE43_SAFETY.brokerWriteAllowed, false);
  assert.equal(PHASE43_SAFETY.liveTradingAllowed, false);
  assert.equal(PHASE43_SAFETY.orderCreationAllowed, false);
  assert.equal(PHASE43_SAFETY.orderTransmissionAllowed, false);
  assert.equal(PHASE43_SAFETY.orderCancellationAllowed, false);
  assert.equal(PHASE43_SAFETY.orderModificationAllowed, false);
  assert.equal(PHASE43_SAFETY.excelOrderWriteAllowed, false);
  assert.equal(PHASE43_SAFETY.orderTriggerWriteAllowed, false);
  assert.equal(PHASE43_SAFETY.automaticCandidatePromotionAllowed, false);
  assert.equal(PHASE43_SAFETY.automaticProductionUpdateAllowed, false);
  assert.equal(PHASE43_SAFETY.humanApprovalRequired, true);
});