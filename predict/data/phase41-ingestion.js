import {
  PHASE41_SAFETY,
  buildDataLakeManifest,
  createDataLakeShard,
  mergeDailyDataLake,
  validateDataLakeManifest,
} from "./phase41-data-lake.js";

const PROVIDERS = new Set(["GENERIC", "CSV", "JSON", "MARKETSPEED_RSS"]);

function text(value) {
  return String(value ?? "").trim();
}

function providerName(value) {
  const normalized = text(value || "GENERIC").toUpperCase();
  if (!PROVIDERS.has(normalized)) throw new TypeError(`unsupported provider: ${normalized}`);
  return normalized;
}

function inferKind(row, fallback = "OHLCV") {
  const explicit = text(row?.kind || fallback).toUpperCase();
  return explicit || "OHLCV";
}

export function adaptProviderRows({ provider = "GENERIC", rows = [], metadata = {} } = {}) {
  const normalizedProvider = providerName(provider);
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");

  const records = rows.map((row, index) => {
    if (!row || typeof row !== "object") throw new TypeError(`row ${index} must be an object`);
    const kind = inferKind(row, metadata.kind);
    const symbol = text(row.symbol ?? row.ticker ?? row.seriesId ?? metadata.symbol).toUpperCase();
    const sessionDate = row.sessionDate ?? row.date ?? row.Date ?? row.time ?? row.timestamp;
    const updatedAt = row.updatedAt ?? metadata.updatedAt ?? new Date().toISOString();
    const source = text(row.source ?? metadata.source ?? normalizedProvider) || normalizedProvider;

    if (kind === "OHLCV") {
      return {
        kind,
        symbol,
        sessionDate,
        updatedAt,
        source,
        currency: row.currency ?? metadata.currency ?? "JPY",
        open: row.open ?? row.Open,
        high: row.high ?? row.High,
        low: row.low ?? row.Low,
        close: row.close ?? row.Close,
        adjustedClose: row.adjustedClose ?? row.adjClose ?? row["Adj Close"],
        volume: row.volume ?? row.Volume,
      };
    }

    return {
      kind,
      symbol,
      sessionDate,
      updatedAt,
      source,
      currency: row.currency ?? metadata.currency ?? "JPY",
      value: row.value ?? row.close ?? row.Close,
    };
  });

  return {
    provider: normalizedProvider,
    recordCount: records.length,
    records,
    safety: { ...PHASE41_SAFETY },
  };
}

export function buildPhase41IngestionPlan({ existingShard = null, batches = [] } = {}) {
  if (!Array.isArray(batches)) throw new TypeError("batches must be an array");
  const accepted = [];
  const rejected = [];

  for (let index = 0; index < batches.length; index += 1) {
    try {
      const adapted = adaptProviderRows(batches[index]);
      accepted.push(...adapted.records);
    } catch (error) {
      rejected.push({ index, error: String(error?.message || error) });
    }
  }

  const merged = mergeDailyDataLake({
    existingShard: existingShard || createDataLakeShard({ records: [] }),
    incomingRecords: accepted,
  });
  const manifest = buildDataLakeManifest({ shards: [merged.shard] });
  const integrity = validateDataLakeManifest(manifest, [merged.shard]);

  return {
    status: rejected.length || integrity.status !== "VALID" ? "REVIEW_REQUIRED" : "READY_TO_PERSIST",
    merged,
    manifest,
    integrity,
    rejected,
    acceptedRecordCount: accepted.length,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE41_SAFETY },
  };
}

export function createPhase41Checkpoint({ plan, runId, generatedAt = new Date().toISOString() } = {}) {
  if (!plan?.merged?.shard) throw new TypeError("plan is required");
  return Object.freeze({
    schemaVersion: 1,
    runId: text(runId) || `phase41-${Date.now()}`,
    generatedAt: new Date(generatedAt).toISOString(),
    shardId: plan.merged.shard.shardId,
    checksum: plan.merged.shard.checksum,
    recordCount: plan.merged.shard.recordCount,
    insertedCount: plan.merged.insertedKeys.length,
    updatedCount: plan.merged.updatedKeys.length,
    staleIgnoredCount: plan.merged.ignoredStaleKeys.length,
    rejectedCount: plan.rejected.length,
    completed: plan.integrity.status === "VALID",
    safety: { ...PHASE41_SAFETY },
  });
}
