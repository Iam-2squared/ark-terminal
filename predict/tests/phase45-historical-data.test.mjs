import test from "node:test";
import assert from "node:assert/strict";
import {
  PHASE45_SAFETY,
  buildHistoricalIngestionBatch,
  createPhase45Universe,
  inspectHistoricalRecords,
  normalizeHistoricalRecord,
} from "../data/phase45-historical-data.js";

test("creates a versioned TSE universe with benchmarks", () => {
  const universe = createPhase45Universe({ equities: ["7203.T", "6758.T"] });
  assert.equal(universe.equities.length, 2);
  assert.equal(universe.benchmarks.length, 6);
  assert.equal(universe.safety.liveTradingAllowed, false);
});

test("rejects duplicate or malformed universe symbols", () => {
  assert.throws(() => createPhase45Universe({ equities: ["7203.T", "7203.T"] }), /duplicate/);
  assert.throws(() => createPhase45Universe({ equities: ["AAPL"] }), /invalid TSE symbol/);
});

test("normalizes CSV-shaped OHLCV rows", () => {
  const record = normalizeHistoricalRecord({
    symbol: "7203.T",
    Date: "2026-08-05",
    Open: "2800",
    High: "2850",
    Low: "2780",
    Close: "2830",
    "Adj Close": "2830",
    Volume: "1200000",
  });
  assert.equal(record.kind, "OHLCV");
  assert.equal(record.close, 2830);
  assert.equal(record.sessionDate, "2026-08-05");
});

test("blocks duplicate records and impossible OHLC ranges", () => {
  const rows = [
    { symbol: "7203.T", date: "2026-08-05", open: 100, high: 90, low: 95, close: 92, volume: 10 },
    { symbol: "7203.T", date: "2026-08-05", open: 100, high: 110, low: 90, close: 105, volume: 10 },
  ];
  const result = inspectHistoricalRecords(rows);
  assert.equal(result.status, "BLOCKED");
  assert.ok(result.blockers.some((item) => item.code === "LOW_ABOVE_HIGH"));
  assert.ok(result.blockers.some((item) => item.code === "DUPLICATE_RECORD"));
});

test("produces a Phase41-ready batch only when quality is valid", () => {
  const batch = buildHistoricalIngestionBatch({
    provider: "CSV",
    records: [
      { symbol: "7203.T", date: "2026-08-05", open: 100, high: 110, low: 90, close: 105, volume: 10 },
    ],
  });
  assert.equal(batch.status, "READY_FOR_PHASE41");
  assert.equal(batch.records.length, 1);
});

test("keeps every execution capability disabled", () => {
  assert.deepEqual(PHASE45_SAFETY, {
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  });
});
