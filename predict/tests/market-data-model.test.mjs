import test from "node:test";
import assert from "node:assert/strict";

import {
  MARKET_DATA_DEFINITIONS,
  MARKET_DATA_STATUS,
  createMarketDataPoint,
  getMarketDataDefinition,
  isMarketDataPoint,
  listMarketDataDefinitions,
} from "../market-intelligence/market-data-model.js";

test("Market Data Core registers all 15 required series", () => {
  assert.equal(MARKET_DATA_DEFINITIONS.length, 15);
  assert.deepEqual(
    MARKET_DATA_DEFINITIONS.map((definition) => definition.symbol),
    [
      "NIKKEI225",
      "TOPIX",
      "JPX400",
      "GROWTH250",
      "NASDAQ",
      "SP500",
      "SOX",
      "RUSSELL2000",
      "VIX",
      "USDJPY",
      "US10Y",
      "WTI",
      "GOLD",
      "BITCOIN",
      "ETHEREUM",
    ],
  );
  assert.ok(Object.isFrozen(MARKET_DATA_DEFINITIONS));
  assert.notEqual(listMarketDataDefinitions(), MARKET_DATA_DEFINITIONS);
});

test("Market symbols and provider aliases resolve to one definition", () => {
  assert.equal(getMarketDataDefinition("S&P500").symbol, "SP500");
  assert.equal(getMarketDataDefinition("^GSPC").symbol, "SP500");
  assert.equal(getMarketDataDefinition("btc-usd").symbol, "BITCOIN");
  assert.equal(getMarketDataDefinition("unknown"), null);
});

test("Japanese index proxies are explicit and lower confidence", () => {
  const nikkei = getMarketDataDefinition("NIKKEI225");

  for (const symbol of ["TOPIX", "JPX400", "GROWTH250"]) {
    const definition = getMarketDataDefinition(symbol);
    assert.equal(definition.isProxy, true);
    assert.match(definition.source, /proxy/);
    assert.ok(definition.confidence < nikkei.confidence);
  }
});

test("Market data points follow the shared immutable contract", () => {
  const point = createMarketDataPoint({
    symbol: "^N225",
    price: "41000.5",
    change: 125.5,
    changePercent: 0.31,
    timestamp: "2026-08-01T06:00:00.000Z",
    source: "yahoo-finance",
    status: MARKET_DATA_STATUS.AVAILABLE,
    confidence: 95.4,
  });

  assert.deepEqual(Object.keys(point), [
    "symbol",
    "price",
    "change",
    "changePercent",
    "timestamp",
    "source",
    "status",
    "confidence",
  ]);
  assert.equal(point.symbol, "NIKKEI225");
  assert.equal(point.price, 41000.5);
  assert.equal(point.confidence, 95);
  assert.equal(isMarketDataPoint(point), true);
  assert.ok(Object.isFrozen(point));
});

test("Unavailable points cannot expose an invalid price as available", () => {
  const point = createMarketDataPoint({
    symbol: "VIX",
    price: Number.NaN,
    status: MARKET_DATA_STATUS.AVAILABLE,
    confidence: 80,
  });

  assert.equal(point.price, null);
  assert.equal(point.status, MARKET_DATA_STATUS.UNAVAILABLE);
  assert.equal(isMarketDataPoint(point), true);
});

test("Error points never leak a stale price or confidence", () => {
  const point = createMarketDataPoint({
    symbol: "VIX",
    price: 20,
    change: 2,
    changePercent: 10,
    timestamp: 1_785_628_800,
    status: MARKET_DATA_STATUS.ERROR,
    confidence: 95,
  });

  assert.equal(point.price, null);
  assert.equal(point.change, null);
  assert.equal(point.changePercent, null);
  assert.equal(point.confidence, 0);
  assert.equal(point.timestamp, "2026-08-02T00:00:00.000Z");
  assert.equal(isMarketDataPoint(point), true);
});
