import test from "node:test";
import assert from "node:assert/strict";

import {
  MarketBreadthEngine,
  analyzeMarketBreadth,
  calculateBreadthBalanceScore,
} from "../market-intelligence/market-breadth.js";

function observation(symbol, changePercent, overrides = {}) {
  return {
    symbol,
    changePercent,
    aboveMa20: changePercent > 0,
    aboveMa50: changePercent > 0,
    newHigh: changePercent > 0,
    newLow: changePercent < 0,
    confidence: 100,
    ...overrides,
  };
}

test("Broad participation produces a maximum breadth score", () => {
  const report = analyzeMarketBreadth([
    observation("A", 1),
    observation("B", 2),
    observation("C", 0.5),
  ]);

  assert.equal(report.score, 100);
  assert.equal(report.confidence, 100);
  assert.equal(report.coverage, 100);
  assert.equal(report.advancers, 3);
  assert.equal(report.advanceDeclineRatio, null);
  assert.equal(report.newHighLow.newHighs, 3);
});

test("Balanced participation stays at a neutral breadth score", () => {
  const report = analyzeMarketBreadth([
    observation("A", 1),
    observation("B", 1),
    observation("C", -1),
    observation("D", -1),
  ]);

  assert.equal(report.score, 50);
  assert.equal(report.advancers, 2);
  assert.equal(report.decliners, 2);
  assert.equal(report.advanceDeclineRatio, 1);
  assert.equal(report.netAdvances, 0);
});

test("Daily breadth works without inventing missing auxiliary indicators", () => {
  const report = analyzeMarketBreadth([
    { symbol: "A", changePercent: 1 },
    { symbol: "B", changePercent: -1 },
  ]);

  assert.equal(report.score, 50);
  assert.equal(report.coverage, 60);
  assert.equal(report.confidence, 60);
  assert.equal(report.aboveMa20.score, null);
  assert.equal(report.newHighLow.score, null);
});

test("Expected universe size lowers breadth coverage and confidence", () => {
  const report = analyzeMarketBreadth(
    [observation("A", 1), observation("B", 1)],
    { expectedCount: 4 },
  );

  assert.equal(report.score, 100);
  assert.equal(report.coverage, 50);
  assert.equal(report.confidence, 50);
});

test("Zero-confidence rows cannot influence breadth direction", () => {
  const report = analyzeMarketBreadth([
    observation("A", 1),
    observation("B", -1, { confidence: 0 }),
  ]);

  assert.equal(report.score, 100);
  assert.equal(report.advancers, 1);
  assert.equal(report.decliners, 0);
  assert.equal(report.confidence, 50);
});

test("Empty breadth input remains explicitly unavailable", () => {
  const report = analyzeMarketBreadth();

  assert.equal(report.score, null);
  assert.equal(report.confidence, 0);
  assert.equal(report.coverage, 0);
  assert.equal(calculateBreadthBalanceScore(), null);
});

test("MarketBreadthEngine exposes the pure breadth calculation", () => {
  const inputs = [observation("A", 1), observation("B", -1)];
  const engine = new MarketBreadthEngine();

  assert.deepEqual(engine.analyze(inputs), analyzeMarketBreadth(inputs));
});

test("Breadth report carries the latest constituent timestamp", () => {
  const report = analyzeMarketBreadth([
    observation("A", 1, { timestamp: "2026-08-01T00:00:00Z" }),
    observation("B", -1, { timestamp: "2026-08-02T00:00:00Z" }),
  ]);

  assert.equal(report.timestamp, "2026-08-02T00:00:00.000Z");
});
