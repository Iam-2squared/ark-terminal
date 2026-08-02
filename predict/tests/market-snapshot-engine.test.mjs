import test from "node:test";
import assert from "node:assert/strict";

import {
  MARKET_DATA_DEFINITIONS,
  MARKET_DATA_STATUS,
  createMarketDataPoint,
} from "../market-intelligence/market-data-model.js";
import {
  MarketSnapshotEngine,
  buildMarketSnapshot,
  createMarketSnapshot,
} from "../market-intelligence/market-snapshot-engine.js";

const TIMESTAMP = "2026-08-01T00:00:00.000Z";
const NOW = Date.parse("2026-08-02T03:04:05.000Z");

function point(symbol, changePercent = 1, price = 100) {
  return createMarketDataPoint({
    symbol,
    price,
    change: (price * changePercent) / 100,
    changePercent,
    timestamp: TIMESTAMP,
    source: "test-provider",
    confidence: 90,
  });
}

function completeMarketData() {
  return MARKET_DATA_DEFINITIONS.map(({ symbol }) =>
    point(symbol, symbol === "VIX" ? -5 : 1, symbol === "VIX" ? 18 : 100),
  );
}

test("Market snapshot follows the required top-level contract", () => {
  const snapshot = buildMarketSnapshot(completeMarketData(), {
    now: () => NOW,
  });

  assert.deepEqual(Object.keys(snapshot), [
    "indexes",
    "macro",
    "regime",
    "score",
    "timestamp",
  ]);
  assert.equal(snapshot.timestamp, "2026-08-02T03:04:05.000Z");
  assert.equal(typeof snapshot.score, "number");
  assert.equal(snapshot.indexes.availableCount, 8);
  assert.equal(snapshot.macro.availableCount, 7);
  assert.equal(snapshot.macro.vixLevel, 18);
});

test("Snapshot accepts Map and service-style data collections", () => {
  const points = completeMarketData();
  const asMap = new Map(points.map((item) => [item.symbol, item]));
  const mapSnapshot = buildMarketSnapshot(asMap, { now: () => NOW });
  const responseSnapshot = buildMarketSnapshot({ data: points }, { now: () => NOW });

  assert.deepEqual(mapSnapshot, responseSnapshot);
});

test("A failed VIX source does not erase otherwise available snapshot data", () => {
  const points = completeMarketData().filter((item) => item.symbol !== "VIX");
  points.push(
    createMarketDataPoint({
      symbol: "VIX",
      status: MARKET_DATA_STATUS.ERROR,
      source: "test-provider",
    }),
  );
  const snapshot = buildMarketSnapshot(points, { now: () => NOW });

  assert.equal(typeof snapshot.score, "number");
  assert.equal(snapshot.macro.vixLevel, null);
  assert.equal(snapshot.macro.riskLevel, "UNKNOWN");
  assert.ok(snapshot.macro.coverage < 100);
});

test("Invalid collection and clock contracts fail fast", () => {
  assert.throws(() => buildMarketSnapshot({ points: [] }), /array, Map/);
  assert.throws(
    () => buildMarketSnapshot([], { now: () => "invalid" }),
    /invalid timestamp/,
  );
  assert.throws(
    () => new MarketSnapshotEngine({ marketDataService: {} }),
    /getAll/,
  );
  assert.throws(
    () => new MarketSnapshotEngine({ now: NOW }),
    /clock must be a function/,
  );
});

test("Snapshot engine can analyze supplied data without a provider", async () => {
  const snapshot = await createMarketSnapshot({
    marketData: completeMarketData(),
    now: () => NOW,
  });

  assert.equal(snapshot.timestamp, "2026-08-02T03:04:05.000Z");
  assert.equal(snapshot.indexes.coverage, 100);
});

test("Snapshot engine accepts an explicit point-in-time timestamp", () => {
  const engine = new MarketSnapshotEngine({ now: () => NOW });
  const snapshot = engine.analyze(completeMarketData(), {
    timestamp: "2026-08-02T01:00:00Z",
  });

  assert.equal(snapshot.timestamp, "2026-08-02T01:00:00.000Z");
});

test("Snapshot engine loads Bundle 1 data with refresh and abort options", async () => {
  const calls = [];
  const controller = new AbortController();
  const service = {
    async getAll(options) {
      calls.push(options);
      return completeMarketData();
    },
  };
  const engine = new MarketSnapshotEngine({
    marketDataService: service,
    now: () => NOW,
  });
  const snapshot = await engine.run({
    forceRefresh: true,
    signal: controller.signal,
  });

  assert.deepEqual(calls, [
    { forceRefresh: true, signal: controller.signal },
  ]);
  assert.equal(snapshot.indexes.availableCount, 8);
});

test("Snapshot engine requires a service only when it must load data", async () => {
  const engine = new MarketSnapshotEngine({ now: () => NOW });

  await assert.rejects(engine.run(), /service is required/);
  assert.equal(engine.analyze([]).score, null);
});
