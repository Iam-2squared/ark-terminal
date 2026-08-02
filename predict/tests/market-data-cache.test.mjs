import test from "node:test";
import assert from "node:assert/strict";

import { MarketDataCache } from "../market-intelligence/market-data-cache.js";

test("Market data cache uses canonical case-insensitive keys", () => {
  const cache = new MarketDataCache({ now: () => 1_000 });
  const value = { price: 100 };

  cache.set("nikkei225", value);

  assert.equal(cache.get("NIKKEI225"), value);
  assert.equal(cache.has({ symbol: "nikkei225" }), true);
});

test("Market data cache expires values at the TTL boundary", () => {
  let now = 1_000;
  const cache = new MarketDataCache({ ttlMs: 100, now: () => now });

  cache.set("VIX", { price: 20 });
  now = 1_099;
  assert.equal(cache.has("VIX"), true);
  now = 1_100;
  assert.equal(cache.get("VIX"), null);
  assert.equal(cache.size(), 0);
});

test("Per-entry TTL and prune remove only expired values", () => {
  let now = 100;
  const cache = new MarketDataCache({ ttlMs: 1_000, now: () => now });

  cache.set("VIX", 1, { ttlMs: 10 });
  cache.set("GOLD", 2);
  now = 111;

  assert.equal(cache.prune(), 1);
  assert.equal(cache.get("GOLD"), 2);
  assert.equal(cache.size(), 1);
});

test("Market data cache supports targeted deletion and clearing", () => {
  const cache = new MarketDataCache({ now: () => 0 });

  cache.set("VIX", 1);
  cache.set("GOLD", 2);
  assert.equal(cache.delete("vix"), true);
  assert.equal(cache.size(), 1);
  cache.clear();
  assert.equal(cache.size(), 0);
});

test("Market data cache rejects empty keys", () => {
  const cache = new MarketDataCache();
  assert.throws(() => cache.set("", 1), /key is required/i);
});
