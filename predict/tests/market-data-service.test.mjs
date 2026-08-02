import test from "node:test";
import assert from "node:assert/strict";

import {
  MARKET_DATA_DEFINITIONS,
  MARKET_DATA_STATUS,
} from "../market-intelligence/market-data-model.js";
import {
  MarketDataService,
  createMarketDataService,
} from "../market-intelligence/market-data-service.js";

const NOW = Date.parse("2026-08-02T00:00:00.000Z");
const PREVIOUS = Date.parse("2026-07-30T00:00:00.000Z") / 1000;
const LATEST = Date.parse("2026-07-31T00:00:00.000Z") / 1000;

function history(price = 101) {
  return {
    provider: "test-provider",
    candles: [
      { time: PREVIOUS, close: 100 },
      { time: LATEST, close: price },
    ],
  };
}

test("Market data service caches normalized results", async () => {
  let calls = 0;
  const service = new MarketDataService({
    provider: {
      fetch: async () => {
        calls += 1;
        return history();
      },
    },
    now: () => NOW,
  });

  const first = await service.get("NIKKEI225");
  const second = await service.get("^N225");

  assert.equal(first, second);
  assert.equal(calls, 1);
  assert.equal(first.status, MARKET_DATA_STATUS.AVAILABLE);
});

test("Force refresh bypasses cache", async () => {
  let calls = 0;
  const service = new MarketDataService({
    provider: {
      fetch: async () => history(100 + ++calls),
    },
    now: () => NOW,
  });

  const first = await service.get("VIX");
  const refreshed = await service.get("VIX", { forceRefresh: true });

  assert.equal(calls, 2);
  assert.notEqual(first.price, refreshed.price);
});

test("Concurrent requests for one symbol share one provider call", async () => {
  let calls = 0;
  let release;
  const raw = new Promise((resolve) => {
    release = resolve;
  });
  const service = new MarketDataService({
    provider: {
      fetch: async () => {
        calls += 1;
        return raw;
      },
    },
    now: () => NOW,
  });

  const first = service.get("NASDAQ");
  const second = service.get("NASDAQ");
  release(history());

  const [firstResult, secondResult] = await Promise.all([first, second]);
  assert.equal(calls, 1);
  assert.equal(firstResult, secondResult);
});

test("Provider failure is isolated as an error data point", async () => {
  let calls = 0;
  const service = new MarketDataService({
    provider: {
      fetch: async () => {
        calls += 1;
        throw new Error("upstream unavailable");
      },
    },
    now: () => NOW,
  });

  const first = await service.get("SOX");
  const cached = await service.get("SOX");

  assert.equal(first.status, MARKET_DATA_STATUS.ERROR);
  assert.equal(first.price, null);
  assert.equal(first.confidence, 0);
  assert.equal(cached, first);
  assert.equal(calls, 1);
});

test("throwOnError retries a cached safe error and rejects", async () => {
  let calls = 0;
  const service = new MarketDataService({
    provider: {
      fetch: async () => {
        calls += 1;
        throw new Error("upstream unavailable");
      },
    },
    now: () => NOW,
  });

  assert.equal((await service.get("SOX")).status, MARKET_DATA_STATUS.ERROR);
  await assert.rejects(
    service.get("SOX", { throwOnError: true }),
    /upstream unavailable/,
  );
  assert.equal(calls, 2);
});

test("getAll returns every registered series even when one fails", async () => {
  const service = new MarketDataService({
    provider: {
      fetch: async (definition) => {
        if (definition.symbol === "VIX") {
          throw new Error("VIX unavailable");
        }

        return history();
      },
    },
    now: () => NOW,
  });

  const results = await service.getAll();

  assert.equal(results.length, MARKET_DATA_DEFINITIONS.length);
  assert.equal(results.find((item) => item.symbol === "VIX").status, "error");
  assert.equal(
    results.filter((item) => item.status === "available").length,
    MARKET_DATA_DEFINITIONS.length - 1,
  );
});

test("getMany normalizes aliases and removes duplicates", async () => {
  let calls = 0;
  const service = new MarketDataService({
    provider: {
      fetch: async () => {
        calls += 1;
        return history();
      },
    },
    now: () => NOW,
  });

  const results = await service.getMany(["SP500", "^GSPC", "BTC", "BITCOIN"]);

  assert.deepEqual(
    results.map((item) => item.symbol),
    ["SP500", "BITCOIN"],
  );
  assert.equal(calls, 2);
});

test("Abort errors are rethrown and never cached", async () => {
  const abortError = new Error("aborted");
  abortError.name = "AbortError";
  const service = new MarketDataService({
    provider: {
      fetch: async () => {
        throw abortError;
      },
    },
    now: () => NOW,
  });

  await assert.rejects(service.get("USDJPY"), { name: "AbortError" });
  assert.equal(service.cache.size(), 0);
});

test("Service factory wires the existing fetchHistory dependency", async () => {
  const calls = [];
  const service = createMarketDataService({
    fetchHistory: async (symbol, options) => {
      calls.push({ symbol, options });
      return history();
    },
    now: () => NOW,
  });

  const point = await service.get("ETHEREUM");

  assert.equal(point.symbol, "ETHEREUM");
  assert.equal(calls[0].symbol, "ETH-USD");
  assert.equal(calls[0].options.range, "6mo");
  assert.equal(calls[0].options.interval, "1d");
});
