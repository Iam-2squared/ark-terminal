import test from "node:test";
import assert from "node:assert/strict";

import { MARKET_DATA_STATUS } from "../market-intelligence/market-data-model.js";
import {
  normalizeMarketData,
  normalizeMarketDataError,
} from "../market-intelligence/market-data-normalizer.js";

const JULY_30 = Date.parse("2026-07-30T00:00:00.000Z") / 1000;
const JULY_31 = Date.parse("2026-07-31T00:00:00.000Z") / 1000;
const AUGUST_2 = Date.parse("2026-08-02T00:00:00.000Z");

test("History payload becomes the shared market data format", () => {
  const point = normalizeMarketData(
    {
      provider: "yahoo-finance",
      candles: [
        { time: JULY_30, close: 40_000 },
        { time: JULY_31, close: 41_000 },
      ],
      sourceQuality: {
        sourceRowCount: 2,
        droppedRowCount: 0,
      },
    },
    "NIKKEI225",
    { now: AUGUST_2 },
  );

  assert.equal(point.price, 41_000);
  assert.equal(point.change, 1_000);
  assert.equal(point.changePercent, 2.5);
  assert.equal(point.timestamp, "2026-07-31T00:00:00.000Z");
  assert.equal(point.status, MARKET_DATA_STATUS.AVAILABLE);
  assert.equal(point.confidence, 95);
});

test("Quote payload uses previous close to keep change values consistent", () => {
  const point = normalizeMarketData(
    {
      price: 20,
      previousClose: 16,
      change: 999,
      changePercent: 999,
      updatedAt: "2026-08-01T12:00:00.000Z",
      provider: "test-provider",
    },
    "VIX",
    { now: AUGUST_2 },
  );

  assert.equal(point.change, 4);
  assert.equal(point.changePercent, 25);
  assert.equal(point.source, "test-provider");
});

test("Old market data is marked stale and confidence is reduced", () => {
  const point = normalizeMarketData(
    {
      price: 100,
      previousClose: 99,
      updatedAt: "2026-07-01T00:00:00.000Z",
    },
    "SP500",
    {
      now: AUGUST_2,
      staleAfterMs: 24 * 60 * 60 * 1000,
    },
  );

  assert.equal(point.status, MARKET_DATA_STATUS.STALE);
  assert.ok(point.confidence < 95);
});

test("Proxy series retain their explicit proxy source", () => {
  const point = normalizeMarketData(
    {
      price: 3_000,
      previousClose: 2_970,
      updatedAt: "2026-08-01T12:00:00.000Z",
      provider: "yahoo-finance",
    },
    "TOPIX",
    { now: AUGUST_2 },
  );

  assert.equal(point.source, "yahoo-finance-etf-proxy");
  assert.equal(point.confidence, 72);
});

test("Missing and failed payloads are explicit instead of neutral values", () => {
  const unavailable = normalizeMarketData({}, "NASDAQ", { now: AUGUST_2 });
  const failed = normalizeMarketDataError("NASDAQ", new Error("upstream"), {
    now: AUGUST_2,
  });

  assert.equal(unavailable.price, null);
  assert.equal(unavailable.status, MARKET_DATA_STATUS.UNAVAILABLE);
  assert.equal(unavailable.confidence, 0);
  assert.equal(failed.status, MARKET_DATA_STATUS.ERROR);
  assert.equal(failed.timestamp, "2026-08-02T00:00:00.000Z");
  assert.equal(failed.confidence, 0);
});
