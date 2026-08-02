import { STORAGE_KEYS } from "../config.js";
import {
  restoreHistoricalMarketSnapshot,
} from "./historical-market-snapshot-model.js";
import {
  HistoricalMarketSnapshotNormalizerInternals,
} from "./historical-market-snapshot-normalizer.js";

export const DEFAULT_HISTORICAL_MARKET_SNAPSHOT_STORAGE_KEY =
  STORAGE_KEYS.marketIntelligenceSnapshots;
export const DEFAULT_HISTORICAL_MARKET_SNAPSHOT_LIMIT = 365;

const { normalizeSymbol, timestampMilliseconds } =
  HistoricalMarketSnapshotNormalizerInternals;

function normalizeLimit(value, fallback = DEFAULT_HISTORICAL_MARKET_SNAPSHOT_LIMIT) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0
    ? Math.floor(number)
    : fallback;
}

function validateStorage(storage) {
  if (storage === null || storage === undefined) return null;

  for (const method of ["getItem", "setItem", "removeItem"]) {
    if (typeof storage[method] !== "function") {
      throw new TypeError(
        "Historical snapshot storage must expose getItem(), setItem(), and removeItem().",
      );
    }
  }

  return storage;
}

export function resolveHistoricalMarketSnapshotStorage() {
  try {
    return validateStorage(globalThis.localStorage ?? null);
  } catch {
    return null;
  }
}

function newestFirst(first, second) {
  return Date.parse(second.asOf) - Date.parse(first.asOf) ||
    second.id.localeCompare(first.id);
}

function restoreArchive(records) {
  const restored = [];
  const identities = new Map();

  for (const record of Array.isArray(records) ? records : []) {
    try {
      const snapshot = restoreHistoricalMarketSnapshot(record);
      const fingerprint = identities.get(snapshot.id);

      if (fingerprint && fingerprint !== snapshot.contentFingerprint) continue;
      if (!fingerprint) restored.push(snapshot);
      identities.set(snapshot.id, snapshot.contentFingerprint);
    } catch {
      // Corrupt or unsupported records are isolated from the valid archive.
    }
  }

  return restored.sort(newestFirst);
}

export function readHistoricalMarketSnapshotArchive({
  storage = null,
  key = DEFAULT_HISTORICAL_MARKET_SNAPSHOT_STORAGE_KEY,
} = {}) {
  const resolvedStorage = validateStorage(storage);
  if (!resolvedStorage) return [];

  try {
    const raw = resolvedStorage.getItem(key);
    return raw ? restoreArchive(JSON.parse(raw)) : [];
  } catch {
    return [];
  }
}

function writeArchive(storage, key, snapshots) {
  if (!storage) return;
  storage.setItem(key, JSON.stringify(snapshots));
}

function normalizeOptionalTimestamp(value, label) {
  if (value === null || value === undefined || value === "") return null;
  return timestampMilliseconds(value, label);
}

function normalizeQueryLimit(value) {
  if (value === null || value === undefined) return null;
  const number = Number(value);

  if (!Number.isFinite(number) || number < 0) {
    throw new TypeError("Historical snapshot query limit must be non-negative.");
  }

  return Math.floor(number);
}

function filterSnapshots(snapshots, {
  symbol = null,
  status = null,
  from = null,
  to = null,
  limit = null,
} = {}) {
  const normalizedSymbol = symbol ? normalizeSymbol(symbol) : null;
  const normalizedStatus = status
    ? String(status).trim().toLowerCase()
    : null;
  const fromTime = normalizeOptionalTimestamp(from, "Historical snapshot from");
  const toTime = normalizeOptionalTimestamp(to, "Historical snapshot to");
  const queryLimit = normalizeQueryLimit(limit);

  if (fromTime !== null && toTime !== null && fromTime > toTime) {
    throw new RangeError("Historical snapshot from cannot be later than to.");
  }

  const filtered = snapshots.filter((snapshot) => {
    const asOf = Date.parse(snapshot.asOf);
    return (
      (!normalizedSymbol || snapshot.symbol === normalizedSymbol) &&
      (!normalizedStatus || snapshot.status === normalizedStatus) &&
      (fromTime === null || asOf >= fromTime) &&
      (toTime === null || asOf <= toTime)
    );
  });

  return queryLimit === null
    ? filtered
    : filtered.slice(0, queryLimit);
}

export class HistoricalMarketSnapshotRepository {
  constructor({
    storage = null,
    key = DEFAULT_HISTORICAL_MARKET_SNAPSHOT_STORAGE_KEY,
    limit = DEFAULT_HISTORICAL_MARKET_SNAPSHOT_LIMIT,
  } = {}) {
    this.storage = validateStorage(storage);
    this.key = String(key || DEFAULT_HISTORICAL_MARKET_SNAPSHOT_STORAGE_KEY);
    this.limit = normalizeLimit(limit);
    this.snapshots = readHistoricalMarketSnapshotArchive({
      storage: this.storage,
      key: this.key,
    }).slice(0, this.limit);
  }

  append(value) {
    const snapshot = restoreHistoricalMarketSnapshot(value);
    const existing = this.snapshots.find((item) => item.id === snapshot.id);

    if (existing) {
      if (existing.contentFingerprint !== snapshot.contentFingerprint) {
        throw new RangeError(
          "Historical snapshot conflict: an existing point-in-time record cannot be rewritten.",
        );
      }

      return { snapshot: existing, inserted: false, retained: true };
    }

    const next = [...this.snapshots, snapshot]
      .sort(newestFirst)
      .slice(0, this.limit);
    const retained = next.some((item) => item.id === snapshot.id);

    if (!retained) {
      return { snapshot, inserted: false, retained: false };
    }

    writeArchive(this.storage, this.key, next);
    this.snapshots = next;

    return { snapshot, inserted: true, retained: true };
  }

  get(id) {
    return this.snapshots.find((snapshot) => snapshot.id === id) ?? null;
  }

  list(filters = {}) {
    return [...filterSnapshots(this.snapshots, filters)];
  }

  latest(symbol = null) {
    return this.list({ symbol, limit: 1 })[0] ?? null;
  }

  findAtOrBefore({ symbol, timestamp, maximumAgeMs = null } = {}) {
    const normalizedSymbol = normalizeSymbol(symbol);
    const target = timestampMilliseconds(
      timestamp,
      "Historical snapshot lookup timestamp",
    );
    const maximumAge =
      maximumAgeMs === null || maximumAgeMs === undefined
        ? null
        : Number(maximumAgeMs);

    if (
      maximumAge !== null &&
      (!Number.isFinite(maximumAge) || maximumAge < 0)
    ) {
      throw new TypeError("Historical snapshot maximum age must be non-negative.");
    }

    const snapshot = this.snapshots.find(
      (item) =>
        item.symbol === normalizedSymbol && Date.parse(item.asOf) <= target,
    );

    if (!snapshot) return null;
    if (maximumAge !== null && target - Date.parse(snapshot.asOf) > maximumAge) {
      return null;
    }

    return snapshot;
  }

  count(filters = {}) {
    return this.list(filters).length;
  }

  clear({ symbol = null } = {}) {
    if (!symbol) {
      if (this.storage) this.storage.removeItem(this.key);
      this.snapshots = [];
      return 0;
    }

    const normalizedSymbol = normalizeSymbol(symbol);
    const next = this.snapshots.filter(
      (snapshot) => snapshot.symbol !== normalizedSymbol,
    );
    writeArchive(this.storage, this.key, next);
    this.snapshots = next;
    return next.length;
  }

  export() {
    return JSON.stringify(this.snapshots, null, 2);
  }
}

export const HistoricalMarketSnapshotRepositoryInternals = Object.freeze({
  normalizeLimit,
  validateStorage,
  newestFirst,
  restoreArchive,
  writeArchive,
  normalizeOptionalTimestamp,
  normalizeQueryLimit,
  filterSnapshots,
});

export default HistoricalMarketSnapshotRepository;
