import test from "node:test";
import assert from "node:assert/strict";

import {
  PHASE42_SAFETY,
  createFeatureRecord,
  createFeatureStoreShard,
  auditFeatureStoreShard,
  buildFeatureStoreManifest,
  validateFeatureStoreManifest,
} from "../features/phase42-feature-store.js";

const baseRecord = {
  featureSetId: "core-v1",
  symbol: "7203.T",
  sessionDate: "2026-08-05",
  sourceShardId: "phase41-demo",
  sourceChecksum: "abc123",
  generatedAt: "2026-08-06T12:00:00.000Z",
  features: {
    close: 2585,
    return1d: 0.0058,
    volumeRatio20: 1.12,
  },
};

test("creates immutable feature records with deterministic keys", () => {
  const first = createFeatureRecord(baseRecord);
  const second = createFeatureRecord(baseRecord);
  assert.equal(first.featureKey, "core-v1:7203.T:2026-08-05");
  assert.equal(first.contentHash, second.contentHash);
  assert.equal(Object.isFrozen(first), true);
});

test("deduplicates feature records by newest generatedAt", () => {
  const shard = createFeatureStoreShard({
    records: [
      baseRecord,
      {
        ...baseRecord,
        generatedAt: "2026-08-06T13:00:00.000Z",
        features: { ...baseRecord.features, close: 2600 },
      },
    ],
  });
  assert.equal(shard.recordCount, 1);
  assert.deepEqual(shard.duplicateKeys, ["core-v1:7203.T:2026-08-05"]);
  assert.equal(shard.records[0].features.close, 2600);
});

test("blocks duplicate feature keys and excessive missing values", () => {
  const shard = createFeatureStoreShard({
    records: [
      baseRecord,
      {
        ...baseRecord,
        generatedAt: "2026-08-06T14:00:00.000Z",
        features: { close: null, return1d: null },
      },
    ],
  });
  const audit = auditFeatureStoreShard(shard, { maximumMissingRate: 0.1 });
  assert.equal(audit.status, "BLOCKED");
  assert.equal(audit.canUseForTraining, false);
  assert.ok(audit.blockers.includes("DUPLICATE_FEATURE_KEYS"));
  assert.ok(audit.blockers.includes("FEATURE_MISSING_RATE_EXCEEDED"));
});

test("validates manifest integrity", () => {
  const shard = createFeatureStoreShard({ records: [baseRecord] });
  const manifest = buildFeatureStoreManifest({ shards: [shard] });
  const validation = validateFeatureStoreManifest(manifest, [shard]);
  assert.equal(validation.status, "VALID");
  assert.equal(validation.canUseForTraining, true);
});

test("fails closed on manifest checksum mismatch", () => {
  const shard = createFeatureStoreShard({ records: [baseRecord] });
  const manifest = buildFeatureStoreManifest({ shards: [shard] });
  const tampered = { ...shard, checksum: "deadbeef" };
  const validation = validateFeatureStoreManifest(manifest, [tampered]);
  assert.equal(validation.status, "BLOCKED");
  assert.ok(validation.blockers.some((item) => item.startsWith("FEATURE_CHECKSUM_MISMATCH:")));
});

test("keeps all trading and broker writes disabled", () => {
  assert.equal(PHASE42_SAFETY.mode, "FEATURE_STORE_ONLY");
  assert.equal(PHASE42_SAFETY.brokerWriteAllowed, false);
  assert.equal(PHASE42_SAFETY.liveTradingAllowed, false);
  assert.equal(PHASE42_SAFETY.orderCreationAllowed, false);
  assert.equal(PHASE42_SAFETY.orderTransmissionAllowed, false);
  assert.equal(PHASE42_SAFETY.orderCancellationAllowed, false);
  assert.equal(PHASE42_SAFETY.orderModificationAllowed, false);
  assert.equal(PHASE42_SAFETY.excelOrderWriteAllowed, false);
  assert.equal(PHASE42_SAFETY.orderTriggerWriteAllowed, false);
  assert.equal(PHASE42_SAFETY.automaticPromotionAllowed, false);
  assert.equal(PHASE42_SAFETY.productionUpdateAllowed, false);
});
