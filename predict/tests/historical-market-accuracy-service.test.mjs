import assert from "node:assert/strict";
import test from "node:test";

import { HistoricalMarketAccuracyService } from "../market-intelligence/historical-market-accuracy-service.js";
import {
  createHistoricalAccuracyHistory,
  createHistoricalAccuracySnapshot,
  historicalAccuracyEvaluationTime,
} from "./historical-market-accuracy-fixture.mjs";

test("Batch service deduplicates snapshots and isolates corrupt entries", () => {
  const snapshot = createHistoricalAccuracySnapshot();
  const evaluatedAt = historicalAccuracyEvaluationTime();
  const service = new HistoricalMarketAccuracyService({
    now: () => Date.parse(evaluatedAt),
  });
  const result = service.evaluateBatch({
    snapshots: [snapshot, snapshot, { id: "corrupt" }],
    histories: new Map([[snapshot.symbol, createHistoricalAccuracyHistory()]]),
  });

  assert.equal(result.status, "partial");
  assert.equal(result.reports.length, 1);
  assert.equal(result.errors.length, 1);
  assert.equal(result.records.length, 5);
  assert.equal(result.resolvedRecords.length, 5);
  assert.equal(result.executionAllowed, false);
});

test("Batch price resolver supports snapshots created before price capture", () => {
  const snapshot = createHistoricalAccuracySnapshot({
    symbol: "6758.T",
    includePredictionPrice: false,
  });
  const evaluatedAt = historicalAccuracyEvaluationTime();
  const service = new HistoricalMarketAccuracyService({
    now: () => Date.parse(evaluatedAt),
  });
  const result = service.evaluateBatch({
    snapshots: [snapshot],
    histories: {
      "6758.T": createHistoricalAccuracyHistory({ symbol: "6758.T" }),
    },
    prices: new Map([[snapshot.id, 100]]),
  });

  assert.equal(result.status, "ready");
  assert.equal(result.resolvedRecords.length, 5);
  assert.equal(result.reports[0].anchor.source, "explicit");
});

test("Service validates dependencies and exposes safe single evaluation", () => {
  assert.throws(
    () => new HistoricalMarketAccuracyService({ evaluator: null }),
    /evaluator must be a function/,
  );
  assert.throws(
    () => new HistoricalMarketAccuracyService({ composer: {} }),
    /composer must be a function/,
  );
  assert.throws(
    () => new HistoricalMarketAccuracyService({ now: 1 }),
    /clock must be a function/,
  );

  const service = new HistoricalMarketAccuracyService();
  const result = service.evaluateSnapshotSafely({ snapshot: {} });

  assert.equal(result.report, null);
  assert.match(result.error.message, /symbol is required|feature set is required/);
});
