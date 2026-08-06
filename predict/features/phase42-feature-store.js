import { stableStringify } from "../data/phase41-data-lake.js";

const PHASE42_SAFETY = Object.freeze({
  mode: "FEATURE_STORE_ONLY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  automaticCandidateCreationAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const FEATURE_SCHEMA_VERSION = 1;

function fnv1a(value) {
  let hash = 0x811c9dc5;
  for (const char of String(value)) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function normalizeDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new TypeError("sessionDate is invalid");
  return date.toISOString().slice(0, 10);
}

function normalizeUpdatedAt(value) {
  const date = new Date(value ?? Date.now());
  if (Number.isNaN(date.getTime())) throw new TypeError("updatedAt is invalid");
  return date.toISOString();
}

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeFeatureMap(features = {}) {
  if (!features || typeof features !== "object" || Array.isArray(features)) {
    throw new TypeError("features must be an object");
  }
  return Object.fromEntries(
    Object.entries(features)
      .map(([name, value]) => [String(name).trim(), finiteOrNull(value)])
      .filter(([name]) => name),
  );
}

export function createFeatureRecord(input = {}) {
  const symbol = String(input.symbol ?? "").trim().toUpperCase();
  if (!symbol) throw new TypeError("symbol is required");
  const sessionDate = normalizeDate(input.sessionDate ?? input.date ?? input.time);
  const featureSetId = String(input.featureSetId ?? "core-v1").trim();
  if (!featureSetId) throw new TypeError("featureSetId is required");

  const normalized = {
    schemaVersion: FEATURE_SCHEMA_VERSION,
    featureSetId,
    symbol,
    sessionDate,
    sourceShardId: String(input.sourceShardId ?? "").trim() || null,
    sourceChecksum: String(input.sourceChecksum ?? "").trim() || null,
    generatedAt: normalizeUpdatedAt(input.generatedAt),
    features: normalizeFeatureMap(input.features),
  };

  normalized.featureKey = `${featureSetId}:${symbol}:${sessionDate}`;
  normalized.contentHash = fnv1a(stableStringify(normalized));
  return Object.freeze(normalized);
}

export function createFeatureStoreShard({ records = [], shardId = null } = {}) {
  if (!Array.isArray(records)) throw new TypeError("records must be an array");
  const normalized = records.map(createFeatureRecord).sort((a, b) => a.featureKey.localeCompare(b.featureKey));
  const byKey = new Map();
  const duplicateKeys = [];

  for (const record of normalized) {
    if (byKey.has(record.featureKey)) duplicateKeys.push(record.featureKey);
    const current = byKey.get(record.featureKey);
    if (!current || Date.parse(record.generatedAt) >= Date.parse(current.generatedAt)) {
      byKey.set(record.featureKey, record);
    }
  }

  const rows = [...byKey.values()].sort((a, b) => a.featureKey.localeCompare(b.featureKey));
  const checksum = fnv1a(stableStringify(rows));

  return Object.freeze({
    schemaVersion: FEATURE_SCHEMA_VERSION,
    shardId: shardId || `phase42-${checksum}`,
    immutable: true,
    recordCount: rows.length,
    duplicateKeys: Object.freeze([...new Set(duplicateKeys)]),
    records: Object.freeze(rows),
    checksum,
    safety: { ...PHASE42_SAFETY },
  });
}

export function auditFeatureStoreShard(shard, options = {}) {
  const blockers = [];
  const warnings = [];
  const minimumFeatures = Math.max(1, Number(options.minimumFeatures ?? 1));
  const maximumMissingRate = Math.max(0, Number(options.maximumMissingRate ?? 0.1));
  const records = shard?.records ?? [];

  if (!shard?.immutable) blockers.push("FEATURE_SHARD_NOT_IMMUTABLE");
  if (!Array.isArray(records) || records.length === 0) blockers.push("FEATURE_STORE_EMPTY");
  if ((shard?.duplicateKeys ?? []).length) blockers.push("DUPLICATE_FEATURE_KEYS");

  let totalFeatures = 0;
  let missingFeatures = 0;
  for (const record of records) {
    const entries = Object.entries(record.features ?? {});
    if (entries.length < minimumFeatures) blockers.push(`INSUFFICIENT_FEATURES:${record.featureKey}`);
    totalFeatures += entries.length;
    missingFeatures += entries.filter(([, value]) => !Number.isFinite(value)).length;
    if (!record.sourceShardId) warnings.push(`SOURCE_SHARD_MISSING:${record.featureKey}`);
    if (!record.sourceChecksum) warnings.push(`SOURCE_CHECKSUM_MISSING:${record.featureKey}`);
  }

  const missingRate = totalFeatures ? missingFeatures / totalFeatures : 1;
  if (missingRate > maximumMissingRate) blockers.push("FEATURE_MISSING_RATE_EXCEEDED");

  return {
    status: blockers.length ? "BLOCKED" : warnings.length ? "WARNING" : "VALID",
    canUseForTraining: blockers.length === 0,
    recordCount: records.length,
    totalFeatures,
    missingFeatures,
    missingRate,
    blockers: [...new Set(blockers)],
    warnings: [...new Set(warnings)],
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE42_SAFETY },
  };
}

export function buildFeatureStoreManifest({ shards = [], generatedAt = new Date().toISOString() } = {}) {
  const entries = shards.map((shard) => ({
    shardId: shard.shardId,
    checksum: shard.checksum,
    recordCount: shard.recordCount,
    immutable: shard.immutable === true,
  })).sort((a, b) => a.shardId.localeCompare(b.shardId));
  const blockers = [];
  if (entries.some((entry) => !entry.immutable)) blockers.push("MUTABLE_FEATURE_SHARD");
  if (new Set(entries.map((entry) => entry.shardId)).size !== entries.length) blockers.push("DUPLICATE_FEATURE_SHARD_ID");

  return Object.freeze({
    schemaVersion: FEATURE_SCHEMA_VERSION,
    status: blockers.length ? "BLOCKED" : "READY",
    generatedAt: normalizeUpdatedAt(generatedAt),
    shardCount: entries.length,
    totalRecords: entries.reduce((sum, entry) => sum + entry.recordCount, 0),
    entries: Object.freeze(entries),
    blockers: Object.freeze(blockers),
    manifestHash: fnv1a(stableStringify(entries)),
    safety: { ...PHASE42_SAFETY },
  });
}

export function validateFeatureStoreManifest(manifest, shards = []) {
  const shardMap = new Map(shards.map((shard) => [shard.shardId, shard]));
  const blockers = [...(manifest?.blockers ?? [])];
  for (const entry of manifest?.entries ?? []) {
    const shard = shardMap.get(entry.shardId);
    if (!shard) {
      blockers.push(`MISSING_FEATURE_SHARD:${entry.shardId}`);
      continue;
    }
    if (shard.checksum !== entry.checksum) blockers.push(`FEATURE_CHECKSUM_MISMATCH:${entry.shardId}`);
    if (shard.recordCount !== entry.recordCount) blockers.push(`FEATURE_COUNT_MISMATCH:${entry.shardId}`);
  }
  return {
    status: blockers.length ? "BLOCKED" : "VALID",
    canUseForTraining: blockers.length === 0,
    blockers: [...new Set(blockers)],
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE42_SAFETY },
  };
}

export { PHASE42_SAFETY, FEATURE_SCHEMA_VERSION };
