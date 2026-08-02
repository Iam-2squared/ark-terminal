import assert from "node:assert/strict";
import test from "node:test";

import { evaluateHistoricalMarketSnapshot } from "../market-intelligence/historical-market-accuracy-engine.js";
import {
  createHistoricalAccuracyHistory,
  createHistoricalAccuracySnapshot,
  historicalAccuracyEvaluationTime,
} from "./historical-market-accuracy-fixture.mjs";

test("Historical snapshot resolves all five horizons through existing records", () => {
  const snapshot = createHistoricalAccuracySnapshot();
  const history = createHistoricalAccuracyHistory();
  const original = structuredClone(history);
  const result = evaluateHistoricalMarketSnapshot({
    snapshot,
    history,
    evaluatedAt: historicalAccuracyEvaluationTime(),
  });

  assert.equal(result.status, "resolved");
  assert.equal(result.recordCount, 5);
  assert.equal(result.resolvedCount, 5);
  assert.deepEqual(
    result.records.map((record) => record.period),
    [1, 3, 5, 10, 20],
  );
  assert.ok(result.records.every((record) => record.status === "resolved"));
  assert.ok(result.records.every((record) => record.executionAllowed === false));
  assert.equal(
    result.records[0].marketIntelligenceSnapshot.id,
    snapshot.id,
  );
  assert.equal(
    result.records[0].historicalAccuracyAudit.futureInformationIncluded,
    false,
  );
  assert.deepEqual(history, original);
});

test("Insufficient future sessions remain pending instead of being scored", () => {
  const snapshot = createHistoricalAccuracySnapshot();
  const result = evaluateHistoricalMarketSnapshot({
    snapshot,
    history: createHistoricalAccuracyHistory(),
    evaluatedAt: historicalAccuracyEvaluationTime(4),
  });

  assert.equal(result.status, "partial");
  assert.equal(result.resolvedCount, 2);
  assert.equal(result.pendingCount, 3);
  assert.deepEqual(
    result.records
      .filter((record) => record.status === "resolved")
      .map((record) => record.period),
    [1, 3],
  );
  assert.equal(result.reason, "awaiting_future_sessions");
});

test("Missing prediction-time price is unavailable without history inference", () => {
  const snapshot = createHistoricalAccuracySnapshot({
    includePredictionPrice: false,
  });
  const start = Date.parse(snapshot.asOf) / 1000;
  const result = evaluateHistoricalMarketSnapshot({
    snapshot,
    history: [
      { time: start - 86_400, close: 99 },
      ...createHistoricalAccuracyHistory(),
    ],
    evaluatedAt: historicalAccuracyEvaluationTime(),
  });

  assert.equal(result.status, "unavailable");
  assert.equal(result.reason, "prediction_price_unavailable");
  assert.equal(result.recordCount, 0);
});
