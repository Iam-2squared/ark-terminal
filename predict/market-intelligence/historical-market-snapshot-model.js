import {
  normalizeHistoricalMarketSnapshotInput,
} from "./historical-market-snapshot-normalizer.js";

export const HISTORICAL_MARKET_SNAPSHOT_SCHEMA_VERSION = 1;
export const HISTORICAL_MARKET_SNAPSHOT_VERSION =
  "historical-market-snapshot-v1";

function canonicalStringify(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return `[${value.map(canonicalStringify).join(",")}]`;
  }

  return `{${Object.keys(value)
    .sort()
    .map(
      (key) =>
        `${JSON.stringify(key)}:${canonicalStringify(value[key])}`,
    )
    .join(",")}}`;
}

function fnv1a32(value) {
  let hash = 0x811c9dc5;

  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }

  return (hash >>> 0).toString(16).padStart(8, "0");
}

function deepFreeze(value, seen = new WeakSet()) {
  if (!value || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);

  for (const item of Object.values(value)) deepFreeze(item, seen);

  return Object.freeze(value);
}

function snapshotContent(normalized) {
  return {
    schemaVersion: HISTORICAL_MARKET_SNAPSHOT_SCHEMA_VERSION,
    version: HISTORICAL_MARKET_SNAPSHOT_VERSION,
    symbol: normalized.symbol,
    asOf: normalized.asOf,
    status: normalized.status,
    confidence: normalized.confidence,
    coverage: normalized.coverage,
    reports: normalized.reports,
    features: normalized.features,
    predictions: normalized.predictions,
    lineage: normalized.lineage,
    versions: normalized.versions,
    metadata: normalized.metadata,
    retentionPolicy: normalized.retentionPolicy,
    executionAllowed: false,
  };
}

function snapshotId(normalized) {
  return [
    "market-intelligence-snapshot",
    normalized.symbol,
    Date.parse(normalized.asOf),
  ].join(":");
}

function contentFingerprint(content) {
  return `fnv1a32:${fnv1a32(canonicalStringify(content))}`;
}

function assertRestoredIdentity(input, snapshot) {
  if (input.id !== undefined && input.id !== snapshot.id) {
    throw new RangeError("Historical snapshot id does not match its content.");
  }

  if (
    input.contentFingerprint !== undefined &&
    input.contentFingerprint !== snapshot.contentFingerprint
  ) {
    throw new RangeError(
      "Historical snapshot fingerprint does not match its content.",
    );
  }

  if (
    input.schemaVersion !== undefined &&
    Number(input.schemaVersion) !== HISTORICAL_MARKET_SNAPSHOT_SCHEMA_VERSION
  ) {
    throw new RangeError("Historical snapshot schema version is unsupported.");
  }

  if (
    input.version !== undefined &&
    input.version !== HISTORICAL_MARKET_SNAPSHOT_VERSION
  ) {
    throw new RangeError("Historical snapshot version is unsupported.");
  }
}

export function createHistoricalMarketSnapshot(input = {}, options = {}) {
  const normalized = normalizeHistoricalMarketSnapshotInput(input, options);
  const content = snapshotContent(normalized);
  const snapshot = {
    ...content,
    id: snapshotId(normalized),
    capturedAt: normalized.capturedAt,
    contentFingerprint: contentFingerprint(content),
  };

  assertRestoredIdentity(input, snapshot);
  return deepFreeze(snapshot);
}

export function restoreHistoricalMarketSnapshot(input = {}) {
  return createHistoricalMarketSnapshot(input, {
    now: () => input.capturedAt,
  });
}

export function isHistoricalMarketSnapshot(value) {
  if (
    !value ||
    typeof value !== "object" ||
    value.schemaVersion !== HISTORICAL_MARKET_SNAPSHOT_SCHEMA_VERSION ||
    value.version !== HISTORICAL_MARKET_SNAPSHOT_VERSION
  ) {
    return false;
  }

  try {
    restoreHistoricalMarketSnapshot(value);
    return true;
  } catch {
    return false;
  }
}

export function createHistoricalMarketSnapshotReference(snapshot) {
  const restored = restoreHistoricalMarketSnapshot(snapshot);

  return deepFreeze({
    id: restored.id,
    schemaVersion: restored.schemaVersion,
    version: restored.version,
    symbol: restored.symbol,
    asOf: restored.asOf,
    contentFingerprint: restored.contentFingerprint,
    executionAllowed: false,
  });
}

export const HistoricalMarketSnapshotModelInternals = Object.freeze({
  canonicalStringify,
  fnv1a32,
  deepFreeze,
  snapshotContent,
  snapshotId,
  contentFingerprint,
  assertRestoredIdentity,
});

export default createHistoricalMarketSnapshot;
