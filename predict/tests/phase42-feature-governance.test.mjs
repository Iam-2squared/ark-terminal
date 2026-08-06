import test from "node:test";
import assert from "node:assert/strict";

import {
  createFeatureStoreShard,
  buildFeatureStoreManifest,
} from "../features/phase42-feature-store.js";
import {
  PHASE42_GOVERNANCE_SAFETY,
  analyzeFeatureDrift,
  evaluateFeatureLineage,
  buildFeatureGovernanceDashboard,
} from "../features/phase42-feature-governance.js";

const records = [
  {
    featureSetId: "core-v1",
    symbol: "7203.T",
    sessionDate: "2026-08-04",
    sourceShardId: "phase41-a",
    sourceChecksum: "checksum-a",
    generatedAt: "2026-08-05T12:00:00.000Z",
    features: { close: 2500, return1d: 0.01 },
  },
  {
    featureSetId: "core-v1",
    symbol: "7203.T",
    sessionDate: "2026-08-05",
    sourceShardId: "phase41-b",
    sourceChecksum: "checksum-b",
    generatedAt: "2026-08-06T12:00:00.000Z",
    features: { close: 2525, return1d: 0.008 },
  },
];

test("reports stable feature means inside the review threshold", () => {
  const drift = analyzeFeatureDrift({
    baselineRecords: records,
    currentRecords: records.map((record) => ({
      ...record,
      features: { ...record.features, close: record.features.close * 1.01 },
    })),
  });
  assert.equal(drift.status, "STABLE");
  assert.equal(drift.canAutoApplyChanges, false);
  assert.ok(drift.features.every((feature) => feature.status === "STABLE"));
});

test("surfaces drift for human review without changing models", () => {
  const drift = analyzeFeatureDrift({
    baselineRecords: records,
    currentRecords: records.map((record) => ({
      ...record,
      features: { ...record.features, close: record.features.close * 2 },
    })),
    thresholds: { maximumMeanShift: 0.25 },
  });
  assert.equal(drift.status, "REVIEW");
  assert.ok(drift.warnings.includes("FEATURE_DRIFT_REVIEW:close"));
  assert.equal(drift.canAutoApplyChanges, false);
});

test("fails closed when drift input is incomplete", () => {
  const drift = analyzeFeatureDrift({ baselineRecords: records, currentRecords: [] });
  assert.equal(drift.status, "BLOCKED");
  assert.ok(drift.blockers.includes("CURRENT_FEATURES_MISSING"));
});

test("validates feature lineage against the manifest", () => {
  const shard = createFeatureStoreShard({ records });
  const manifest = buildFeatureStoreManifest({ shards: [shard] });
  const lineage = evaluateFeatureLineage({ manifest, shards: [shard] });
  assert.equal(lineage.status, "VALID");
  assert.equal(lineage.canUseForTrainingReview, true);
});

test("blocks records with missing source lineage", () => {
  const shard = createFeatureStoreShard({
    records: [{ ...records[0], sourceShardId: null, sourceChecksum: null }],
  });
  const manifest = buildFeatureStoreManifest({ shards: [shard] });
  const lineage = evaluateFeatureLineage({ manifest, shards: [shard] });
  assert.equal(lineage.status, "BLOCKED");
  assert.ok(lineage.blockers.some((item) => item.startsWith("SOURCE_SHARD_MISSING:")));
  assert.ok(lineage.blockers.some((item) => item.startsWith("SOURCE_CHECKSUM_MISSING:")));
});

test("builds a read-only dashboard with a human review gate", () => {
  const shard = createFeatureStoreShard({ records });
  const manifest = buildFeatureStoreManifest({ shards: [shard] });
  const dashboard = buildFeatureGovernanceDashboard({
    manifest,
    shards: [shard],
    baselineRecords: records,
    currentRecords: records,
  });
  assert.equal(dashboard.state, "READY_FOR_HUMAN_REVIEW");
  assert.equal(dashboard.canCreateOrders, false);
  assert.equal(dashboard.canTransmitOrders, false);
  assert.equal(dashboard.canPromoteAutomatically, false);
  assert.equal(dashboard.canUpdateProduction, false);
  assert.equal(dashboard.brokerWrites, 0);
  assert.equal(dashboard.liveOrders, 0);
});

test("keeps every broker and trading capability disabled", () => {
  assert.equal(PHASE42_GOVERNANCE_SAFETY.mode, "FEATURE_GOVERNANCE_REVIEW_ONLY");
  assert.equal(PHASE42_GOVERNANCE_SAFETY.brokerWriteAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.liveTradingAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.orderCreationAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.orderTransmissionAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.orderCancellationAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.orderModificationAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.excelOrderWriteAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.orderTriggerWriteAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.automaticCandidateCreationAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.automaticPromotionAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.productionUpdateAllowed, false);
  assert.equal(PHASE42_GOVERNANCE_SAFETY.humanApprovalRequired, true);
});
