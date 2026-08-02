import test from "node:test";
import assert from "node:assert/strict";

import {
  NEWS_ITEM_STATUS,
  NEWS_METRIC_DIRECTIONS,
  NEWS_SOURCE_TYPES,
} from "../market-intelligence/news-data-model.js";
import {
  normalizeNewsCollection,
  normalizeNewsItem,
} from "../market-intelligence/news-data-normalizer.js";

test("Normalizer accepts news, IR, TDnet and earnings collections", () => {
  const result = normalizeNewsCollection({
    news: [
      {
        headline: "市場ニュース",
        pubDate: "2026-08-02T01:00:00Z",
        publisher: { name: "Wire" },
      },
    ],
    ir: [
      {
        title: "新製品IR",
        date: "2026-08-02T02:00:00Z",
        source: "Company",
      },
    ],
    disclosures: [
      {
        title: "適時開示",
        timestamp: "2026-08-02T03:00:00Z",
        source: "TDnet",
      },
    ],
    earnings: [
      {
        title: "決算短信",
        publishedAt: "2026-08-02T04:00:00Z",
        source: "TDnet",
      },
    ],
  });

  assert.deepEqual(
    result.map((item) => item.type),
    [
      NEWS_SOURCE_TYPES.EARNINGS,
      NEWS_SOURCE_TYPES.TDNET,
      NEWS_SOURCE_TYPES.IR,
      NEWS_SOURCE_TYPES.NEWS,
    ],
  );
});

test("Normalizer maps provider aliases and numeric surprise fields", () => {
  const result = normalizeNewsItem({
    sourceType: "financial-results",
    headline: "Quarterly results",
    pubDate: 1_785_628_800,
    provider: "Example",
    ticker: "7203.T",
    metric: "operating profit",
    actual: "120",
    estimate: "100",
    prior: 90,
    metricDirection: "higher",
  });

  assert.equal(result.type, NEWS_SOURCE_TYPES.EARNINGS);
  assert.equal(result.symbol, "7203.T");
  assert.equal(result.metrics[0].actual, 120);
  assert.equal(result.metrics[0].consensus, 100);
  assert.equal(
    result.metrics[0].direction,
    NEWS_METRIC_DIRECTIONS.HIGHER_IS_BETTER,
  );
  assert.equal(result.status, NEWS_ITEM_STATUS.AVAILABLE);
});

test("Deterministic ids and URL deduplication are stable", () => {
  const raw = {
    title: "同じ記事",
    publishedAt: "2026-08-02T00:00:00Z",
    source: "Wire",
    url: "https://example.test/article",
  };
  const first = normalizeNewsItem(raw);
  const second = normalizeNewsItem(raw);
  const collection = normalizeNewsCollection([
    { ...raw, confidence: 40 },
    { ...raw, confidence: 90 },
  ]);

  assert.equal(first.id, second.id);
  assert.equal(collection.length, 1);
  assert.equal(collection[0].confidence, 85);
});

test("Incomplete records are partial and textless records are unavailable", () => {
  const partial = normalizeNewsItem({ title: "速報" });
  const unavailable = normalizeNewsItem({ source: "Wire" });

  assert.equal(partial.status, NEWS_ITEM_STATUS.PARTIAL);
  assert.ok(partial.confidence > 0);
  assert.equal(unavailable.status, NEWS_ITEM_STATUS.UNAVAILABLE);
  assert.equal(unavailable.confidence, 0);
});

test("Normalization never mutates provider payloads", () => {
  const input = {
    earnings: [
      {
        title: "決算",
        date: "2026-08-02",
        source: "TDnet",
        metrics: [{ name: "EPS", actual: 10, consensus: 9 }],
      },
    ],
  };
  const original = structuredClone(input);

  normalizeNewsCollection(input);

  assert.deepEqual(input, original);
});
