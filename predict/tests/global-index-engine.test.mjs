import test from "node:test";
import assert from "node:assert/strict";

import { createMarketDataPoint } from "../market-intelligence/market-data-model.js";
import {
  GLOBAL_INDEX_CONFIGURATION,
  GlobalIndexEngine,
  analyzeGlobalIndexes,
} from "../market-intelligence/global-index-engine.js";

const TIMESTAMP = "2026-08-01T00:00:00.000Z";

function point(symbol, changePercent, confidence = 100) {
  return createMarketDataPoint({
    symbol,
    price: 100,
    change: changePercent,
    changePercent,
    timestamp: TIMESTAMP,
    source: "test-provider",
    confidence,
  });
}

function allIndexes(changePercent = 1) {
  return GLOBAL_INDEX_CONFIGURATION.map(({ symbol }) =>
    point(symbol, changePercent),
  );
}

test("Global index engine covers all eight required indexes", () => {
  const report = analyzeGlobalIndexes(allIndexes());

  assert.equal(report.availableCount, 8);
  assert.equal(report.requestedCount, 8);
  assert.equal(report.coverage, 100);
  assert.equal(report.confidence, 100);
  assert.ok(report.score > 65);
  assert.equal(report.items.length, 8);
});

test("Japanese and US regions are scored independently", () => {
  const points = GLOBAL_INDEX_CONFIGURATION.map(({ symbol, region }) =>
    point(symbol, region === "JP" ? -2 : 2),
  );
  const report = analyzeGlobalIndexes(points);

  assert.ok(report.regions.JP.score < 20);
  assert.ok(report.regions.US.score > 80);
  assert.equal(report.regions.JP.availableCount, 4);
  assert.equal(report.regions.US.availableCount, 4);
});

test("Leaders and laggards are sorted by daily change", () => {
  const changes = [1, -2, 4, 0.5, -4, 3, 2, -1];
  const points = GLOBAL_INDEX_CONFIGURATION.map(({ symbol }, index) =>
    point(symbol, changes[index]),
  );
  const report = analyzeGlobalIndexes(points);

  assert.deepEqual(
    report.leaders.map((item) => item.changePercent),
    [4, 3, 2],
  );
  assert.deepEqual(
    report.laggards.map((item) => item.changePercent),
    [-4, -2, -1],
  );
});

test("Missing indexes reduce coverage without injecting neutral scores", () => {
  const report = analyzeGlobalIndexes([point("NIKKEI225", 2)]);

  assert.equal(report.score, 100);
  assert.ok(report.coverage < 20);
  assert.equal(report.availableCount, 1);
  assert.equal(report.leaders.length, 1);
});

test("No index data produces an explicit unavailable report", () => {
  const report = analyzeGlobalIndexes();

  assert.equal(report.score, null);
  assert.equal(report.confidence, 0);
  assert.equal(report.coverage, 0);
  assert.deepEqual(report.leaders, []);
  assert.deepEqual(report.laggards, []);
});

test("GlobalIndexEngine exposes the same stateless analysis contract", () => {
  const engine = new GlobalIndexEngine();
  assert.deepEqual(engine.analyze(allIndexes()), analyzeGlobalIndexes(allIndexes()));
});
