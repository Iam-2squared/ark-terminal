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

function fetchFor(payload) {
  return async () => ({ ok: true, status: 200, json: async () => payload });
}

test("legacy sub-0.11 Yahoo drift is normalized before quarantine", async () => {
  const payload = payloadFromRows([{
    timestamp: 1652745600,
    open: 738,
    high: 739.2999877929688,
    low: 717.2000122070312,
    close: 717.0999755859375,
    adjustedClose: 623.1179809570312,
    volume: 64714400,
  }]);

  const result = await downloadHistoricalSeries({
    symbol: "8306.T",
    start: "2022-05-17",
    end: "2022-05-18",
    fetchImpl: fetchFor(payload),
  });

  assert.equal(result.records.length, 1);
  assert.equal(result.quarantined.length, 0);
  assert.equal(result.records[0].low, result.records[0].close);
  assert.equal(result.warnings[0].code, "MINOR_RANGE_ADJUSTMENT");
});

test("one isolated residual sub-0.1-percent Yahoo row is quarantined with audit", async () => {
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

  const result = await downloadHistoricalSeries({
    symbol: "8035.T",
    start: "2022-05-17",
    end: "2022-05-19",
    fetchImpl: fetchFor(payload),
  });

  assert.equal(result.records.length, 1);
  assert.equal(result.records[0].sessionDate, "2022-05-18");
  assert.equal(result.quarantined.length, 1);
  assert.equal(result.quarantined[0].code, "QUARANTINED_RANGE_DRIFT");
  assert.equal(result.quarantined[0].sessionDate, "2022-05-17");
  assert.equal(result.quarantined[0].originalRecord.close, 19346.666015625);
  assert.equal(result.warnings.some((warning) => warning.code === "QUARANTINED_RANGE_DRIFT"), true);
});

test("two residual minor Yahoo violations remain fail-closed", async () => {
  const payload = payloadFromRows([
    { timestamp: 1652745600, open: 999, high: 1000, low: 998, close: 1000.5, volume: 1000 },
    { timestamp: 1652832000, open: 999, high: 1000, low: 998, close: 1000.5, volume: 1000 },
  ]);

  await assert.rejects(
    () => downloadHistoricalUniverse({
      instruments: [{ symbol: "8035.T", outputSymbol: "8035.T", kind: "OHLCV", currency: "JPY" }],
      start: "2022-05-17",
      end: "2022-05-19",
      fetchImpl: fetchFor(payload),
    }),
    (error) => {
      assert.equal(error.message, "HISTORICAL_UNIVERSE_DOWNLOAD_BLOCKED");
      assert.equal(error.failures.length, 1);
      assert.equal(error.failures[0].blockers.filter((blocker) => blocker.code === "CLOSE_OUTSIDE_RANGE").length, 2);
      return true;
    },
  );
});

test("one material Yahoo violation remains fail-closed", async () => {
  const payload = payloadFromRows([
    { timestamp: 1652745600, open: 999, high: 1000, low: 998, close: 1002, volume: 1000 },
  ]);

  await assert.rejects(
    () => downloadHistoricalSeries({
      symbol: "8035.T",
      start: "2022-05-17",
      end: "2022-05-18",
      fetchImpl: fetchFor(payload),
    }),
    (error) => {
      assert.equal(error.message, "DOWNLOADED_DATA_BLOCKED");
      assert.equal(error.inspection.blockers[0].code, "CLOSE_OUTSIDE_RANGE");
      return true;
    },
  );
});