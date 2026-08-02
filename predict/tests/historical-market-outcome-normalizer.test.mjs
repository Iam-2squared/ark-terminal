import assert from "node:assert/strict";
import test from "node:test";

import {
  buildHistoricalMarketOutcomeTimeline,
  normalizeHistoricalMarketOutcomeCandles,
  normalizeHistoricalOutcomeTimestamp,
  resolveHistoricalPredictionPrice,
} from "../market-intelligence/historical-market-outcome-normalizer.js";
import {
  HISTORICAL_ACCURACY_AS_OF,
  createHistoricalAccuracySnapshot,
} from "./historical-market-accuracy-fixture.mjs";

test("Outcome candles normalize aliases, order and duplicate timestamps", () => {
  const start = Date.parse(HISTORICAL_ACCURACY_AS_OF) / 1000;
  const rows = [
    { timestamp: (start + 86_400) * 1000, Close: 101, ticker: "7203.t" },
    { time: start - 86_400, close: 99, symbol: "7203.T" },
    { time: start + 86_400, adjustedClose: 102, symbol: "7203.T" },
    {
      date: new Date((start + 172_800) * 1000).toISOString(),
      price: 103,
    },
    { time: start + 86_400, close: 999, symbol: "6758.T" },
    { time: "invalid", close: 1 },
  ];
  const original = structuredClone(rows);
  const result = normalizeHistoricalMarketOutcomeCandles(rows, {
    symbol: "7203.T",
  });

  assert.deepEqual(
    result.map((row) => row.close),
    [99, 102, 103],
  );
  assert.deepEqual(rows, original);
});

test("Timeline admits only sessions after the snapshot and before cutoff", () => {
  const snapshot = createHistoricalAccuracySnapshot();
  const start = Date.parse(snapshot.asOf) / 1000;
  const history = [
    { time: start - 86_400, close: 95 },
    { time: start, close: 100 },
    { time: start + 86_400, close: 105 },
    { time: start + 172_800, close: 110 },
    { time: start + 259_200, close: 115 },
  ];
  const result = buildHistoricalMarketOutcomeTimeline({
    snapshot,
    history,
    availableAt: new Date((start + 172_800) * 1000).toISOString(),
  });

  assert.equal(result.anchor.close, 100);
  assert.equal(result.anchor.source, "snapshot_metadata");
  assert.equal(result.availableFutureSessions, 2);
  assert.equal(result.excludedAtOrBeforeSnapshot, 2);
  assert.equal(result.excludedAfterAvailability, 1);
  assert.equal(result.candles[0].time, start);
  assert.equal(result.futureInformationIncluded, false);
  assert.equal(result.executionAllowed, false);
});

test("Explicit anchor price wins and invalid prices fail fast", () => {
  const snapshot = createHistoricalAccuracySnapshot();

  assert.deepEqual(
    resolveHistoricalPredictionPrice({ snapshot, predictionPrice: 123.45 }),
    { price: 123.45, source: "explicit" },
  );
  assert.throws(
    () => resolveHistoricalPredictionPrice({ snapshot, predictionPrice: 0 }),
    /must be positive/,
  );
  assert.throws(
    () => normalizeHistoricalOutcomeTimestamp(null),
    /is required/,
  );
  assert.throws(
    () =>
      buildHistoricalMarketOutcomeTimeline({
        snapshot,
        availableAt: "2026-08-02T23:59:59Z",
      }),
    /cannot precede/,
  );
});
