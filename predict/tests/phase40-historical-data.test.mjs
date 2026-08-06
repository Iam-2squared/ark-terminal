import test from "node:test";
import assert from "node:assert/strict";

import {
  normalizeHistoricalRows,
  validateAdjustedPrices,
  auditHistoricalDataQuality,
  buildBacktestReadyCandles,
  runPhase40HistoricalDataFoundation,
} from "../backtest/phase40-historical-data.js";

function rows(count = 120) {
  const start = Date.UTC(2025, 0, 1) / 1000;
  return Array.from({ length: count }, (_, index) => ({
    symbol: "7203.T",
    time: start + index * 86400,
    open: 100 + index,
    high: 102 + index,
    low: 99 + index,
    close: 101 + index,
    adjustedClose: 101 + index,
    volume: 100000 + index,
  }));
}

test("normalizes and orders historical rows immutably", () => {
  const source = rows(3).reverse();
  const dataset = normalizeHistoricalRows({ symbol: "7203.t", rows: source, source: "fixture" });
  assert.equal(dataset.symbol, "7203.T");
  assert.equal(dataset.rows.length, 3);
  assert.ok(dataset.rows[0].time < dataset.rows[1].time);
  assert.equal(dataset.immutable, true);
  assert.equal(dataset.safety.brokerWriteAllowed, false);
});

test("validates adjusted prices and detects corporate action candidates", () => {
  const source = rows(4);
  source[2].adjustedClose = source[2].close * 0.5;
  const dataset = normalizeHistoricalRows({ symbol: "7203.T", rows: source });
  const result = validateAdjustedPrices(dataset);
  assert.equal(result.status, "WARNING");
  assert.ok(result.warnings.some((item) => item.startsWith("CORPORATE_ACTION_CANDIDATE")));
});

test("blocks duplicate dates", () => {
  const source = rows(120);
  source[10].time = source[9].time;
  const dataset = normalizeHistoricalRows({ symbol: "7203.T", rows: source });
  const audit = auditHistoricalDataQuality(dataset, { minimumRows: 100 });
  assert.equal(audit.canBacktest, false);
  assert.ok(audit.blockers.includes("DUPLICATE_TRADING_DATES"));
});

test("builds adjusted candles only after audit passes", () => {
  const dataset = normalizeHistoricalRows({ symbol: "7203.T", rows: rows(120) });
  const audit = auditHistoricalDataQuality(dataset, { minimumRows: 100 });
  const candles = buildBacktestReadyCandles(dataset, audit);
  assert.equal(candles.length, 120);
  assert.equal(candles[0].close, dataset.rows[0].adjustedClose);
  assert.equal(candles[0].adjustedCloseProvided, true);
});

test("full runner is batch-backtest ready and stays read-only", () => {
  const result = runPhase40HistoricalDataFoundation({
    symbol: "7203.T",
    rows: rows(120),
    source: "fixture",
    options: { minimumRows: 100 },
  });
  assert.equal(result.status, "READY_FOR_BATCH_BACKTEST");
  assert.equal(result.audit.canBacktest, true);
  assert.equal(result.candles.length, 120);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
  assert.equal(result.safety.liveTradingAllowed, false);
});

test("full runner blocks incomplete history", () => {
  const result = runPhase40HistoricalDataFoundation({
    symbol: "7203.T",
    rows: rows(10),
    options: { minimumRows: 100 },
  });
  assert.equal(result.status, "BLOCKED");
  assert.equal(result.candles.length, 0);
  assert.ok(result.audit.blockers.includes("INSUFFICIENT_HISTORY"));
});
