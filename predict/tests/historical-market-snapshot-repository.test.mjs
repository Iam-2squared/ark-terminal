import assert from "node:assert/strict";
import test from "node:test";

import {
  createHistoricalMarketSnapshot,
} from "../market-intelligence/historical-market-snapshot-model.js";
import {
  DEFAULT_HISTORICAL_MARKET_SNAPSHOT_STORAGE_KEY,
  HistoricalMarketSnapshotRepository,
  readHistoricalMarketSnapshotArchive,
} from "../market-intelligence/historical-market-snapshot-repository.js";

function createStorage() {
  const values = new Map();

  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    removeItem(key) {
      values.delete(key);
    },
    values,
  };
}

function snapshot({
  symbol = "7203.T",
  timestamp = "2026-08-02T12:00:00Z",
  score = 80,
} = {}) {
  return createHistoricalMarketSnapshot({
    symbol,
    asOf: timestamp,
    capturedAt: timestamp,
    features: {
      version: "market-intelligence-features-v1",
      timestamp,
      status: "ready",
      confidence: 90,
      coverage: 100,
      values: { marketScore: score },
      details: {},
    },
    predictions: [],
  });
}

test("Repository is append-only and duplicate captures are idempotent", () => {
  const repository = new HistoricalMarketSnapshotRepository();
  const first = snapshot();

  assert.equal(repository.append(first).inserted, true);
  assert.equal(repository.append(first).inserted, false);
  assert.equal(repository.count(), 1);
  assert.throws(
    () => repository.append(snapshot({ score: 20 })),
    /cannot be rewritten/,
  );
  assert.equal(
    repository.get(first.id).contentFingerprint,
    first.contentFingerprint,
  );
});

test("Repository finds the newest snapshot at or before a target time", () => {
  const repository = new HistoricalMarketSnapshotRepository({ limit: 10 });
  repository.append(
    snapshot({ timestamp: "2026-08-01T10:00:00Z", score: 60 }),
  );
  repository.append(
    snapshot({ timestamp: "2026-08-02T10:00:00Z", score: 70 }),
  );
  repository.append(
    snapshot({ timestamp: "2026-08-03T10:00:00Z", score: 80 }),
  );

  const found = repository.findAtOrBefore({
    symbol: "7203.t",
    timestamp: "2026-08-02T12:00:00Z",
  });

  assert.equal(found.asOf, "2026-08-02T10:00:00.000Z");
  assert.equal(
    repository.findAtOrBefore({
      symbol: "7203.T",
      timestamp: "2026-08-02T12:00:00Z",
      maximumAgeMs: 60 * 60 * 1000,
    }),
    null,
  );
  assert.equal(repository.latest("7203.T").features.values.marketScore, 80);
});

test("Repository limit prunes oldest records and filters without mutation", () => {
  const repository = new HistoricalMarketSnapshotRepository({ limit: 2 });
  repository.append(snapshot({ timestamp: "2026-08-01T00:00:00Z" }));
  repository.append(snapshot({ timestamp: "2026-08-02T00:00:00Z" }));
  repository.append(snapshot({ timestamp: "2026-08-03T00:00:00Z" }));

  const listed = repository.list({
    from: "2026-08-02T00:00:00Z",
    to: "2026-08-03T00:00:00Z",
  });

  assert.deepEqual(
    listed.map((item) => item.asOf),
    ["2026-08-03T00:00:00.000Z", "2026-08-02T00:00:00.000Z"],
  );
  assert.equal(repository.count(), 2);
  listed.length = 0;
  assert.equal(repository.count(), 2);

  const outside = repository.append(
    snapshot({ timestamp: "2026-07-01T00:00:00Z" }),
  );
  assert.equal(outside.inserted, false);
  assert.equal(outside.retained, false);
  assert.equal(repository.count(), 2);
});

test("Valid persisted snapshots survive corrupt archive entries", () => {
  const storage = createStorage();
  const valid = snapshot();
  storage.setItem(
    DEFAULT_HISTORICAL_MARKET_SNAPSHOT_STORAGE_KEY,
    JSON.stringify([valid, { id: "corrupt" }]),
  );

  const archive = readHistoricalMarketSnapshotArchive({ storage });
  const repository = new HistoricalMarketSnapshotRepository({ storage });

  assert.equal(archive.length, 1);
  assert.equal(repository.count(), 1);
  repository.clear();
  assert.equal(repository.count(), 0);
  assert.equal(
    storage.getItem(DEFAULT_HISTORICAL_MARKET_SNAPSHOT_STORAGE_KEY),
    null,
  );
});
