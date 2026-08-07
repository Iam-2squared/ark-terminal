import test from "node:test";
import assert from "node:assert/strict";
import { downloadHistoricalSeries, downloadHistoricalUniverse } from "../data/phase50-historical-downloader.js";

function payloadFromRows(rows) {
  return {
    chart: {
      result: [{
        timestamp: rows.map((row) => row.timestamp),
        indicators: {
          quote: [{
            open: rows.map((row) => row.open),
            high: rows.map((row) => row.high),
            low: rows.map((row) => row.low),
            close: rows.map((row) => row.close),
            volume: rows.map((row) => row.volume),
          }],
          adjclose: [{ adjclose: rows.map((row) => row.adjustedClose ?? row.close) }],
        },
      }],
    },
  };
}

test("one sub-0.1-percent Yahoo range-drift row is quarantined with audit", async () => {
  const payload = payloadFromRows([
    {
      timestamp: 1652745600,
      open: 19106.666015625,
      high: 19333.333984375,
      low: 18853.333984375,
      close: 19346.666015625,
      adjustedClose: 17528.361328125,
      volume: 2355300,
    },
    {
      timestamp: 1652832000,
      open: 19713.333984375,
      high: 20043.333984375,
      low: 19653.333984375,
      close: 19900,
      adjustedClose: 18029.69140625,
      volume: 4083900,
    },
  ]);
  const fetchImpl = async () => ({ ok: true, status: 200, json: async () => payload });
  const result = await downloadHistoricalSeries({
    symbol: "8035.T",
    start: "2022-05-17",
    end: "2022-05-19",
    fetchImpl,
  });
  assert.equal(result.records.length, 1);
  assert.equal(result.quarantined.length, 1);
  assert.equal(result.quarantined[0].sessionDate, "2022-05-17");
  assert.equal(result.warnings[0].code, "QUARANTINED_RANGE_DRIFT");
});

test("more than one minor inconsistent row remains fail-closed", async () => {
  const payload = payloadFromRows([
    { timestamp: 1652745600, open: 100, high: 101, low: 99, close: 101.05, volume: 1000 },
    { timestamp: 1652832000, open: 100, high: 101, low: 99, close: 101.05, volume: 1000 },
  ]);
  const fetchImpl = async () => ({ ok: true, status: 200, json: async () => payload });
  await assert.rejects(
    () => downloadHistoricalUniverse({
      instruments: [{ symbol: "8035.T", outputSymbol: "8035.T", kind: "OHLCV", currency: "JPY" }],
      start: "2022-05-17",
      end: "2022-05-19",
      fetchImpl,
    }),
    (error) => {
      assert.equal(error.message, "HISTORICAL_UNIVERSE_DOWNLOAD_BLOCKED");
      assert.equal(error.failures[0].blockers.length, 2);
      return true;
    },
  );
});

test("single material range error remains fail-closed", async () => {
  const payload = payloadFromRows([
    { timestamp: 1652745600, open: 100, high: 101, low: 99, close: 103, volume: 1000 },
  ]);
  const fetchImpl = async () => ({ ok: true, status: 200, json: async () => payload });
  await assert.rejects(
    () => downloadHistoricalSeries({ symbol: "8035.T", start: "2022-05-17", end: "2022-05-18", fetchImpl }),
    /DOWNLOADED_DATA_BLOCKED/,
  );
});
