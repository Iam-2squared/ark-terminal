import test from "node:test";
import assert from "node:assert/strict";

import {
  normalizeMarketObservation,
  normalizeMarketObservations,
  resolveExpectedObservationCount,
  resolveLatestObservationTimestamp,
  summarizeObservationCoverage,
} from "../market-intelligence/market-observation-normalizer.js";

test("Market observation normalizer builds the shared immutable contract", () => {
  const observation = normalizeMarketObservation({
    symbol: "7203.t",
    industry: "輸送用機器",
    changePercent: "1.25",
    volume: 200,
    avgVolume: 100,
    turnover: 3000,
    avgTurnover: 2000,
    aboveMa20: 1,
    aboveMa50: "false",
    newHigh: true,
    newLow: false,
    timestamp: "2026-08-02T00:00:00Z",
    source: "test",
    confidence: 95.4,
  });

  assert.equal(observation.symbol, "7203.T");
  assert.equal(observation.sector, "輸送用機器");
  assert.equal(observation.changePercent, 1.25);
  assert.equal(observation.volumeRatio, 2);
  assert.equal(observation.turnoverRatio, 1.5);
  assert.equal(observation.aboveMa20, true);
  assert.equal(observation.aboveMa50, false);
  assert.equal(observation.confidence, 95);
  assert.equal(observation.timestamp, "2026-08-02T00:00:00.000Z");
  assert.ok(Object.isFrozen(observation));
});

test("Explicit activity ratios override derived values", () => {
  const observation = normalizeMarketObservation({
    symbol: "A",
    volume: 200,
    averageVolume: 100,
    volumeRatio: 1.25,
    turnover: 300,
    averageTurnover: 100,
    turnoverRatio: 0.8,
  });

  assert.equal(observation.volumeRatio, 1.25);
  assert.equal(observation.turnoverRatio, 0.8);
});

test("Invalid optional values remain missing instead of becoming zero", () => {
  const observation = normalizeMarketObservation({
    symbol: "A",
    changePercent: "invalid",
    volume: -1,
    averageVolume: 0,
    aboveMa20: "unknown",
    timestamp: "invalid",
    confidence: 150,
  });

  assert.equal(observation.changePercent, null);
  assert.equal(observation.volume, null);
  assert.equal(observation.averageVolume, null);
  assert.equal(observation.volumeRatio, null);
  assert.equal(observation.aboveMa20, null);
  assert.equal(observation.timestamp, null);
  assert.equal(observation.confidence, 100);
});

test("Observation collections deduplicate canonical symbols using latest data", () => {
  const observations = normalizeMarketObservations([
    { symbol: "abc", changePercent: 1 },
    { symbol: "ABC", changePercent: 2 },
    { symbol: "xyz", changePercent: -1 },
  ]);

  assert.equal(observations.length, 2);
  assert.equal(observations[0].symbol, "ABC");
  assert.equal(observations[0].changePercent, 2);
});

test("Required observation contracts fail fast", () => {
  assert.throws(() => normalizeMarketObservation(null), /must be an object/);
  assert.throws(() => normalizeMarketObservation({}), /symbol is required/);
  assert.throws(() => normalizeMarketObservations({}), /must be an array/);
});

test("Expected count cannot hide observed or missing constituents", () => {
  const observations = normalizeMarketObservations([
    { symbol: "A" },
    { symbol: "B" },
  ]);

  assert.equal(resolveExpectedObservationCount(observations, 1), 2);
  assert.equal(resolveExpectedObservationCount(observations, 4.9), 4);
  assert.equal(resolveExpectedObservationCount(observations), 2);
});

test("Coverage excludes missing fields and zero-confidence observations", () => {
  const observations = normalizeMarketObservations([
    { symbol: "A", changePercent: 1, confidence: 80 },
    { symbol: "B", changePercent: -1, confidence: 0 },
    { symbol: "C", confidence: 100 },
  ]);
  const summary = summarizeObservationCoverage(
    observations,
    (item) => item.changePercent !== null,
    { expectedCount: 4 },
  );

  assert.equal(summary.availableCount, 1);
  assert.equal(summary.requestedCount, 4);
  assert.equal(summary.coverage, 25);
  assert.equal(summary.sourceConfidence, 80);
  assert.equal(summary.confidence, 20);
});

test("Latest observation timestamp is preserved for downstream snapshots", () => {
  const observations = normalizeMarketObservations([
    { symbol: "A", timestamp: "2026-08-01T00:00:00Z" },
    { symbol: "B", timestamp: "2026-08-02T00:00:00Z" },
    { symbol: "C" },
  ]);

  assert.equal(
    resolveLatestObservationTimestamp(observations),
    "2026-08-02T00:00:00.000Z",
  );
  assert.equal(resolveLatestObservationTimestamp([]), null);
});
