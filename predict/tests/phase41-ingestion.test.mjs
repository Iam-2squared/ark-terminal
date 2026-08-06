import test from "node:test";
import assert from "node:assert/strict";
import {
  adaptProviderRows,
  buildPhase41IngestionPlan,
  createPhase41Checkpoint,
} from "../data/phase41-ingestion.js";
import { createDataLakeShard } from "../data/phase41-data-lake.js";

test("CSV style rows are adapted into the shared OHLCV contract", () => {
  const result = adaptProviderRows({
    provider: "CSV",
    metadata: { symbol: "7203.T", updatedAt: "2026-08-06T00:00:00Z" },
    rows: [{ Date: "2026-08-05", Open: "2500", High: "2550", Low: "2480", Close: "2530", "Adj Close": "2530", Volume: "1000" }],
  });
  assert.equal(result.records[0].symbol, "7203.T");
  assert.equal(result.records[0].close, "2530");
  assert.equal(result.safety.brokerWriteAllowed, false);
});

test("daily ingestion merges new rows and ignores stale revisions", () => {
  const existingShard = createDataLakeShard({
    records: [{
      kind: "OHLCV", symbol: "7203.T", sessionDate: "2026-08-05",
      source: "TEST", updatedAt: "2026-08-06T00:00:00Z",
      open: 1, high: 2, low: 1, close: 2, adjustedClose: 2, volume: 100,
    }],
  });
  const plan = buildPhase41IngestionPlan({
    existingShard,
    batches: [{
      provider: "JSON",
      rows: [
        { symbol: "7203.T", date: "2026-08-05", updatedAt: "2026-08-05T00:00:00Z", open: 9, high: 9, low: 9, close: 9, adjustedClose: 9, volume: 9 },
        { symbol: "7203.T", date: "2026-08-06", updatedAt: "2026-08-06T01:00:00Z", open: 2, high: 3, low: 2, close: 3, adjustedClose: 3, volume: 200 },
      ],
    }],
  });
  assert.equal(plan.integrity.status, "VALID");
  assert.equal(plan.merged.shard.recordCount, 2);
  assert.deepEqual(plan.merged.ignoredStaleKeys, ["OHLCV:7203.T:2026-08-05"]);
  assert.equal(plan.safety.liveTradingAllowed, false);
});

test("checkpoint is read-only and records ingestion counts", () => {
  const plan = buildPhase41IngestionPlan({
    batches: [{ provider: "GENERIC", rows: [{ symbol: "^N225", kind: "INDEX", date: "2026-08-05", value: 40000, updatedAt: "2026-08-06T00:00:00Z" }] }],
  });
  const checkpoint = createPhase41Checkpoint({ plan, runId: "test-run" });
  assert.equal(checkpoint.runId, "test-run");
  assert.equal(checkpoint.completed, true);
  assert.equal(checkpoint.insertedCount, 1);
  assert.equal(checkpoint.safety.orderTransmissionAllowed, false);
});
