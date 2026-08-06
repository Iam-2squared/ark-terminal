const PHASE41_SAFETY = Object.freeze({
  mode: "DATA_LAKE_ONLY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
});

const ALLOWED_KINDS = new Set(["OHLCV", "INDEX", "MACRO"]);

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }
  if (value && typeof value === "object") {
    const keys = Object.keys(value).sort();
    return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function fnv1a(value) {
  let hash = 0x811c9dc5;
  for (const char of String(value)) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function normalizeDate(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) throw new TypeError("sessionDate is invalid");
  return parsed.toISOString().slice(0, 10);
}

function normalizeUpdatedAt(value) {
  const parsed = new Date(value ?? Date.now());
  if (Number.isNaN(parsed.getTime())) throw new TypeError("updatedAt is invalid");
  return parsed.toISOString();
}

function finiteOrNull(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeRecord(record = {}) {
  const kind = String(record.kind ?? "OHLCV").trim().toUpperCase();
  if (!ALLOWED_KINDS.has(kind)) throw new TypeError(`unsupported kind: ${kind}`);

  const symbol = String(record.symbol ?? record.seriesId ?? "").trim().toUpperCase();
  if (!symbol) throw new TypeError("symbol is required");

  const normalized = {
    kind,
    symbol,
    sessionDate: normalizeDate(record.sessionDate ?? record.date ?? record.time),
    source: String(record.source ?? "UNKNOWN").trim() || "UNKNOWN",
    updatedAt: normalizeUpdatedAt(record.updatedAt),
    currency: String(record.currency ?? "JPY").trim().toUpperCase(),
  };

  if (kind === "OHLCV") {
    Object.assign(normalized, {
      open: finiteOrNull(record.open),
      high: finiteOrNull(record.high),
      low: finiteOrNull(record.low),
      close: finiteOrNull(record.close),
      adjustedClose: finiteOrNull(record.adjustedClose ?? record.adjClose),
      volume: finiteOrNull(record.volume),
    });
  } else {
    normalized.value = finiteOrNull(record.value ?? record.close);
  }

  normalized.recordKey = `${kind}:${symbol}:${normalized.sessionDate}`;
  normalized.contentHash = fnv1a(stableStringify(normalized));
  return Object.freeze(normalized);
}

export function createDataLakeShard({ records = [], shardId = null } = {}) {
  if (!Array.isArray(records)) throw new TypeError("records must be an array");
  const normalized = records.map(normalizeRecord).sort((a, b) => a.recordKey.localeCompare(b.recordKey));
  const byKey = new Map();
  const duplicates = [];

  for (const record of normalized) {
    if (byKey.has(record.recordKey)) duplicates.push(record.recordKey);
    const current = byKey.get(record.recordKey);
    if (!current || Date.parse(record.updatedAt) >= Date.parse(current.updatedAt)) {
      byKey.set(record.recordKey, record);
    }
  }

  const rows = [...byKey.values()].sort((a, b) => a.recordKey.localeCompare(b.recordKey));
  const checksum = fnv1a(stableStringify(rows));

  return Object.freeze({
    shardId: shardId || `phase41-${checksum}`,
    schemaVersion: 1,
    immutable: true,
    recordCount: rows.length,
    duplicateKeys: [...new Set(duplicates)],
    records: Object.freeze(rows),
    checksum,
    safety: { ...PHASE41_SAFETY },
  });
}

export function mergeDailyDataLake({ existingShard, incomingRecords = [] } = {}) {
  const existing = existingShard?.records ?? [];
  const incoming = incomingRecords.map(normalizeRecord);
  const byKey = new Map(existing.map((record) => [record.recordKey, record]));
  const ignoredStaleKeys = [];
  const insertedKeys = [];
  const updatedKeys = [];

  for (const record of incoming) {
    const current = byKey.get(record.recordKey);
    if (!current) {
      byKey.set(record.recordKey, record);
      insertedKeys.push(record.recordKey);
      continue;
    }
    if (Date.parse(record.updatedAt) < Date.parse(current.updatedAt)) {
      ignoredStaleKeys.push(record.recordKey);
      continue;
    }
    if (record.contentHash !== current.contentHash) updatedKeys.push(record.recordKey);
    byKey.set(record.recordKey, record);
  }

  const shard = createDataLakeShard({
    records: [...byKey.values()],
  });

  return {
    status: "MERGED",
    shard,
    insertedKeys,
    updatedKeys,
    ignoredStaleKeys,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE41_SAFETY },
  };
}

export function buildDataLakeManifest({ shards = [], generatedAt = new Date().toISOString() } = {}) {
  const entries = shards.map((shard) => ({
    shardId: shard.shardId,
    checksum: shard.checksum,
    recordCount: shard.recordCount,
    immutable: shard.immutable === true,
  })).sort((a, b) => a.shardId.localeCompare(b.shardId));

  const blockers = [];
  if (entries.some((entry) => !entry.immutable)) blockers.push("MUTABLE_SHARD_REJECTED");
  if (new Set(entries.map((entry) => entry.shardId)).size !== entries.length) blockers.push("DUPLICATE_SHARD_ID");

  return Object.freeze({
    status: blockers.length ? "BLOCKED" : "READY",
    schemaVersion: 1,
    generatedAt: normalizeUpdatedAt(generatedAt),
    shardCount: entries.length,
    totalRecords: entries.reduce((sum, entry) => sum + entry.recordCount, 0),
    entries: Object.freeze(entries),
    blockers: Object.freeze(blockers),
    manifestHash: fnv1a(stableStringify(entries)),
    safety: { ...PHASE41_SAFETY },
  });
}

export function validateDataLakeManifest(manifest, shards = []) {
  const shardMap = new Map(shards.map((shard) => [shard.shardId, shard]));
  const blockers = [...(manifest?.blockers ?? [])];

  for (const entry of manifest?.entries ?? []) {
    const shard = shardMap.get(entry.shardId);
    if (!shard) {
      blockers.push(`MISSING_SHARD:${entry.shardId}`);
      continue;
    }
    if (shard.checksum !== entry.checksum) blockers.push(`CHECKSUM_MISMATCH:${entry.shardId}`);
    if (shard.recordCount !== entry.recordCount) blockers.push(`COUNT_MISMATCH:${entry.shardId}`);
  }

  return {
    status: blockers.length ? "BLOCKED" : "VALID",
    canUseForBacktest: blockers.length === 0,
    blockers: [...new Set(blockers)],
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE41_SAFETY },
  };
}

export { PHASE41_SAFETY, normalizeRecord, stableStringify };
