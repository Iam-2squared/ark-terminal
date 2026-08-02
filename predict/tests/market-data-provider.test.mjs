import test from "node:test";
import assert from "node:assert/strict";

import {
  CompositeMarketDataProvider,
  MarketDataProvider,
  MarketDataProviderError,
  createHistoryMarketDataProvider,
} from "../market-intelligence/market-data-provider.js";

test("History provider reuses the existing history API contract", async () => {
  const calls = [];
  const signal = new AbortController().signal;
  const provider = createHistoryMarketDataProvider({
    fetchHistory: async (symbol, options) => {
      calls.push({ symbol, options });
      return { provider: "yahoo-finance", candles: [] };
    },
  });

  const raw = await provider.fetch("NIKKEI225", { signal });

  assert.deepEqual(calls, [
    {
      symbol: "^N225",
      options: {
        range: "6mo",
        interval: "1d",
        signal,
      },
    },
  ]);
  assert.equal(raw.requestedSymbol, "NIKKEI225");
  assert.equal(raw.providerSymbol, "^N225");
});

test("Provider rejects unsupported series with structured metadata", async () => {
  const provider = new MarketDataProvider({
    name: "unsupported",
    supports: () => false,
    fetcher: async () => ({}),
  });

  await assert.rejects(
    provider.fetch("VIX"),
    (error) =>
      error instanceof MarketDataProviderError &&
      error.symbol === "VIX" &&
      error.provider === "unsupported",
  );
});

test("Composite provider falls back in declared order", async () => {
  const first = new MarketDataProvider({
    name: "first",
    fetcher: async () => {
      throw new Error("temporary failure");
    },
  });
  const second = new MarketDataProvider({
    name: "second",
    fetcher: async (definition) => ({ price: 10, symbol: definition.symbol }),
  });
  const provider = new CompositeMarketDataProvider([first, second]);

  assert.deepEqual(await provider.fetch("GOLD"), {
    price: 10,
    symbol: "GOLD",
  });
});

test("Abort stops provider fallback immediately", async () => {
  let fallbackCalls = 0;
  const abortError = new Error("aborted");
  abortError.name = "AbortError";
  const first = new MarketDataProvider({
    name: "first",
    fetcher: async () => {
      throw abortError;
    },
  });
  const second = new MarketDataProvider({
    name: "second",
    fetcher: async () => {
      fallbackCalls += 1;
      return {};
    },
  });
  const provider = new CompositeMarketDataProvider([first, second]);

  await assert.rejects(provider.fetch("WTI"), { name: "AbortError" });
  assert.equal(fallbackCalls, 0);
});
