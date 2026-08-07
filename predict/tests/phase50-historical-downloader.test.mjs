import test from "node:test";
import assert from "node:assert/strict";
import {
  buildYahooChartUrl,
  normalizeYahooChartPayload,
  downloadHistoricalSeries,
  downloadHistoricalUniverse,
  PHASE50_DOWNLOADER_SAFETY,
} from "../data/phase50-historical-downloader.js";
import { buildPhase45PersistencePlan } from "../data/phase45-persistence.js";

const payload = {
  chart: {
    result: [{
      timestamp: [1722470400, 1722816000],
      indicators: {
        quote: [{
          open: [2500, 2535],
          high: [2550, 2580],
          low: [2480, 2520],
          close: [2530, 2570],
          volume: [1200000, 980000],
        }],
        adjclose: [{ adjclose: [2528, 2570] }],
      },
    }],
  },
};

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

test("buildYahooChartUrl creates a read-only chart request", () => {
  const url = buildYahooChartUrl({ symbol: "7203.T", start: "2024-01-01", end: "2024-12-31" });
  assert.match(url, /finance\/chart\/7203\.T/);
  assert.match(url, /interval=1d/);
});

test("normalizeYahooChartPayload creates Phase45 OHLCV records", () => {
  const records = normalizeYahooChartPayload(payload, { symbol: "7203.T" });
  assert.equal(records.length, 2);
  assert.equal(records[0].symbol, "7203.T");
  assert.equal(records[0].adjustedClose, 2528);
  assert.equal(records[0].kind, "OHLCV");
});

test("normalizeYahooChartPayload supports index values", () => {
  const records = normalizeYahooChartPayload(payload, {
    symbol: "^N225",
    outputSymbol: "NIKKEI225",
    kind: "INDEX",
    currency: "JPY",
  });
  assert.deepEqual(Object.keys(records[0]).sort(), ["currency", "kind", "sessionDate", "source", "symbol", "value"].sort());
  assert.equal(records[0].value, 2530);
});

test("downloadHistoricalSeries is fixture-testable without network", async () => {
  const fetchImpl = async () => ({ ok: true, status: 200, json: async () => payload });
  const result = await downloadHistoricalSeries({
    symbol: "7203.T",
    start: "2024-01-01",
    end: "2024-12-31",
    fetchImpl,
  });
  assert.equal(result.records.length, 2);
  assert.equal(result.quarantined.length, 0);
  assert.equal(result.safety.brokerWriteAllowed, false);
  assert.equal(result.safety.liveTradingAllowed, false);
});

test("Yahoo chart records pass Phase45 persistence provider validation", () => {
  const records = normalizeYahooChartPayload(payload, { symbol: "7203.T" });
  const plan = buildPhase45PersistencePlan({ records, provider: "YAHOO_CHART" });
  assert.equal(plan.status, "READY_TO_PERSIST");
  assert.equal(plan.ingestionPlan.rejected.length, 0);
  assert.equal(plan.ingestionPlan.acceptedRecordCount, 2);
});

test("minor Yahoo close-low drift is adjusted with an audit warning", async () => {
  const driftPayload = payloadFromRows([{
    timestamp: 1652745600,
    open: 738,
    high: 739.2999877929688,
    low: 717.2000122070312,
    close: 717.0999755859375,
    adjustedClose: 623.1179809570312,
    volume: 64714400,
  }]);
  const fetchImpl = async () => ({ ok: true, status: 200, json: async () => driftPayload });
  const result = await downloadHistoricalSeries({
    symbol: "8306.T",
    start: "2022-05-17",
    end: "2022-05-18",
    fetchImpl,
  });
  assert.equal(result.records.length, 1);
  assert.equal(result.quarantined.length, 0);
  assert.equal(result.records[0].low, result.records[0].close);
  assert.equal(result.warnings[0].code, "MINOR_RANGE_ADJUSTMENT");
  assert.equal(result.warnings[0].field, "close");
});

test("one residual sub-0.1-percent Yahoo range drift row is quarantined with audit", async () => {
  const driftPayload = payloadFromRows([
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
  const fetchImpl = async () => ({ ok: true, status: 200, json: async () => driftPayload });
  const result = await downloadHistoricalSeries({
    symbol: "8035.T",
    start: "2022-05-17",
    end: "2022-05-19",
    fetchImpl,
  });
  assert.equal(result.records.length, 1);
  assert.equal(result.quarantined.length, 1);
  assert.equal(result.quarantined[0].sessionDate, "2022-05-17");
  const warning = result.warnings.find((item) => item.code === "QUARANTINED_RANGE_DRIFT");
  assert.ok(warning);
  assert.equal(warning.originalRecord.close, 19346.666015625);
});

test("two residual minor Yahoo range errors remain fail closed", async () => {
  const driftPayload = payloadFromRows([
    { timestamp: 1652745600, open: 19990, high: 20000, low: 19900, close: 20010, volume: 1000 },
    { timestamp: 1652832000, open: 19990, high: 20000, low: 19900, close: 20010, volume: 1000 },
  ]);
  const fetchImpl = async () => ({ ok: true, status: 200, json: async () => driftPayload });
  await assert.rejects(
    () => downloadHistoricalUniverse({
      instruments: [{ symbol: "8035.T", outputSymbol: "8035.T", kind: "OHLCV", currency: "JPY" }],
      start: "2022-05-17",
      end: "2022-05-19",
      fetchImpl,
    }),
    (error) => {
      assert.equal(error.message, "HISTORICAL_UNIVERSE_DOWNLOAD_BLOCKED");
      assert.ok(error.failures[0].blockers.some((item) => item.code === "CLOSE_OUTSIDE_RANGE"));
      return true;
    },
  );
});

test("material Yahoo range errors still fail closed", async () => {
  const invalidPayload = payloadFromRows([{
    timestamp: 1722470400,
    open: 2600,
    high: 2550,
    low: 2480,
    close: 2530,
    volume: 1200000,
  }]);
  const fetchImpl = async () => ({ ok: true, status: 200, json: async () => invalidPayload });
  await assert.rejects(
    async () => downloadHistoricalUniverse({
      instruments: [{ symbol: "6758.T", outputSymbol: "6758.T", kind: "OHLCV", currency: "JPY" }],
      start: "2024-01-01",
      end: "2024-12-31",
      fetchImpl,
    }),
    (error) => {
      assert.equal(error.message, "HISTORICAL_UNIVERSE_DOWNLOAD_BLOCKED");
      assert.equal(error.failures[0].symbol, "6758.T");
      assert.equal(error.failures[0].message, "DOWNLOADED_DATA_BLOCKED");
      assert.equal(error.failures[0].blockers[0].code, "OPEN_OUTSIDE_RANGE");
      assert.equal(error.failures[0].recordCount, 1);
      return true;
    },
  );
});

test("invalid provider response fails closed", async () => {
  const fetchImpl = async () => ({ ok: false, status: 429, json: async () => ({}) });
  await assert.rejects(
    () => downloadHistoricalSeries({ symbol: "7203.T", start: "2024-01-01", end: "2024-12-31", fetchImpl }),
    /historical download failed: 429/,
  );
});

test("all execution writes remain disabled", () => {
  assert.equal(PHASE50_DOWNLOADER_SAFETY.brokerWriteAllowed, false);
  assert.equal(PHASE50_DOWNLOADER_SAFETY.excelOrderWriteAllowed, false);
  assert.equal(PHASE50_DOWNLOADER_SAFETY.rssOrderFunctionAllowed, false);
  assert.equal(PHASE50_DOWNLOADER_SAFETY.liveTradingAllowed, false);
  assert.equal(PHASE50_DOWNLOADER_SAFETY.networkReadOnly, true);
});
