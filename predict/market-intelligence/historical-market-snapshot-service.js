import {
  createHistoricalMarketSnapshot,
  createHistoricalMarketSnapshotReference,
} from "./historical-market-snapshot-model.js";
import {
  HistoricalMarketSnapshotRepository,
  resolveHistoricalMarketSnapshotStorage,
} from "./historical-market-snapshot-repository.js";

export const HISTORICAL_MARKET_SNAPSHOT_CAPTURE_VERSION =
  "historical-market-snapshot-capture-v1";

function errorDetails(error) {
  return {
    name: error?.name ?? "Error",
    message: error?.message ?? String(error),
  };
}

function captureReport({ snapshot, inserted, retained = true }) {
  return {
    version: HISTORICAL_MARKET_SNAPSHOT_CAPTURE_VERSION,
    status: inserted
      ? "captured"
      : retained
        ? "duplicate"
        : "outside_retention_window",
    inserted,
    retained,
    reference: createHistoricalMarketSnapshotReference(snapshot),
    snapshot,
    error: null,
    executionAllowed: false,
  };
}

function captureErrorReport(error) {
  return {
    version: HISTORICAL_MARKET_SNAPSHOT_CAPTURE_VERSION,
    status: "error",
    inserted: false,
    retained: false,
    reference: null,
    snapshot: null,
    error: errorDetails(error),
    executionAllowed: false,
  };
}

function validateRepository(repository) {
  if (!repository) return null;

  for (const method of [
    "append",
    "get",
    "list",
    "latest",
    "findAtOrBefore",
    "count",
    "clear",
    "export",
  ]) {
    if (typeof repository[method] !== "function") {
      throw new TypeError("Historical snapshot repository is invalid.");
    }
  }

  return repository;
}

export class HistoricalMarketSnapshotService {
  constructor({ repository = null, now = Date.now } = {}) {
    if (typeof now !== "function") {
      throw new TypeError("Historical snapshot service clock must be a function.");
    }

    this.repository =
      validateRepository(repository) ??
      new HistoricalMarketSnapshotRepository();
    this.now = now;
  }

  capture(input = {}) {
    const snapshot = createHistoricalMarketSnapshot(input, { now: this.now });
    return captureReport(this.repository.append(snapshot));
  }

  captureSafely(input = {}) {
    try {
      return this.capture(input);
    } catch (error) {
      return captureErrorReport(error);
    }
  }

  get(id) {
    return this.repository.get(id);
  }

  list(filters = {}) {
    return this.repository.list(filters);
  }

  latest(symbol = null) {
    return this.repository.latest(symbol);
  }

  findAtOrBefore(query = {}) {
    return this.repository.findAtOrBefore(query);
  }

  count(filters = {}) {
    return this.repository.count(filters);
  }

  clear(filters = {}) {
    return this.repository.clear(filters);
  }

  export() {
    return this.repository.export();
  }
}

export function createHistoricalMarketSnapshotService({
  storage = resolveHistoricalMarketSnapshotStorage(),
  key,
  limit,
  now = Date.now,
} = {}) {
  return new HistoricalMarketSnapshotService({
    repository: new HistoricalMarketSnapshotRepository({
      storage,
      key,
      limit,
    }),
    now,
  });
}

export const historicalMarketSnapshotService =
  createHistoricalMarketSnapshotService();

export const HistoricalMarketSnapshotServiceInternals = Object.freeze({
  errorDetails,
  captureReport,
  captureErrorReport,
  validateRepository,
});

export default HistoricalMarketSnapshotService;
