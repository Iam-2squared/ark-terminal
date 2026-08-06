import test from "node:test";
import assert from "node:assert/strict";

import {
  buildDataLakeManifest,
  createDataLakeShard,
  mergeDailyDataLake,
  validateDataLakeManifest,
} from "../data/phase41-data-lake.js";

function row(overrides = {}) {
  return {
    kind: "OHLCV",
    symbol: "7203.T",
    sessionDate: "2026-08-05",
    source: "fixture",
    updatedAt: "2026-08-06T00:00:00Z",
    open: 2500,
    high: 2550,
    low: 2480,
    close: 2530,
    adjustedClose: 2530,
    volume: 1000000,
    ...overrides,
  };
}

test("creates immutable deterministic shard with symbol-session dedupe", () => {
  const shard = createDataLakeShard({
    records: [
      row(),
      row({ updatedAt: "2026-08-06T01:00:00Z", close: 2540, adjustedClose: 2540 }),
    ],
  });

  assert.equal(shard.immutable, true);
  assert.equal(shard.recordCount, 1);
  assert.deepEqual(shard.duplicateKeys, ["OHLCV:7203.T:2026-08-05"]);
  assert.equal(shard.records[0].close, 2540);
  assert.equal(shard.safety.brokerWriteAllowed, false);
  assert.equal(shard.safety.liveTradingAllowed, false);
});

test("daily merge ignores stale revisions and accepts newer values", () => {
  const existingShard = createDataLakeShard({ records: [row()] });
  const result = mergeDailyDataLake({
    existingShard,
    incomingRecords: [
      row({ updatedAt: "2026-08-05T23:00:00Z", close: 1, adjustedClose: 1 }),
      row({
        symbol: "6758.T",
        sessionDate: "2026-08-05",
        updatedAt: "2026-08-06T01:00:00Z",
      }),
    ],
  });

  assert.equal(result.status, "MERGED");
  assert.deepEqual(result.ignoredStaleKeys, ["OHLCV:7203.T:2026-08-05"]);
  assert.deepEqual(result.insertedKeys, ["OHLCV:6758.T:2026-08-05"]);
  assert.equal(result.shard.recordCount, 2);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
});

test("supports index and macro series contracts", () => {
  const shard = createDataLakeShard({
    records: [
      {
        kind: "INDEX",
        symbol: "NIKKEI225",
        sessionDate: "2026-08-05",
        updatedAt: "2026-08-06T00:00:00Z",
        value: 40000,
        source: "fixture",
      },
      {
        kind: "MACRO",
        symbol: "USDJPY",
        sessionDate: "2026-08-05",
        updatedAt: "2026-08-06T00:00:00Z",
        value: 150.5,
        source: "fixture",
      },
    ],
  });

  assert.equal(shard.recordCount, 2);
  assert.deepEqual(shard.records.map((item) => item.kind), ["INDEX", "MACRO"]);
});

test("manifest validation blocks missing or tampered shards", () => {
  const shard = createDataLakeShard({ records: [row()] });
  const manifest = buildDataLakeManifest({ shards: [shard] });

  const valid = validateDataLakeManifest(manifest, [shard]);
  assert.equal(valid.status, "VALID");
  assert.equal(valid.canUseForBacktest, true);

  const missing = validateDataLakeManifest(manifest, []);
  assert.equal(missing.status, "BLOCKED");
  assert.match(missing.blockers[0], /^MISSING_SHARD:/);
});
