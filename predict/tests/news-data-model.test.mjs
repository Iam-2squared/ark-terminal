import test from "node:test";
import assert from "node:assert/strict";

import {
  NEWS_ITEM_STATUS,
  NEWS_METRIC_DIRECTIONS,
  NEWS_SOURCE_TYPES,
  createNewsItem,
  isUsableNewsItem,
} from "../market-intelligence/news-data-model.js";

function item(overrides = {}) {
  return createNewsItem({
    id: "news-1",
    type: NEWS_SOURCE_TYPES.EARNINGS,
    title: "決算発表",
    publishedAt: 1_785_628_800,
    source: "TDnet",
    status: NEWS_ITEM_STATUS.AVAILABLE,
    confidence: 120,
    importance: -5,
    metrics: [
      {
        name: "EPS",
        actual: "120",
        consensus: 100,
        direction: NEWS_METRIC_DIRECTIONS.HIGHER_IS_BETTER,
      },
    ],
    tags: ["earnings", "earnings"],
    ...overrides,
  });
}

test("News data model creates the immutable shared contract", () => {
  const result = item();

  assert.equal(result.publishedAt, "2026-08-02T00:00:00.000Z");
  assert.equal(result.confidence, 100);
  assert.equal(result.importance, 0);
  assert.equal(result.metrics[0].actual, 120);
  assert.deepEqual(result.tags, ["earnings"]);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.metrics), true);
  assert.equal(Object.isFrozen(result.metrics[0]), true);
});

test("News data model rejects invalid identities and enums", () => {
  assert.throws(() => createNewsItem(), /id is required/);
  assert.throws(
    () => item({ type: "social-media" }),
    /Unknown news source type/,
  );
  assert.throws(
    () => item({ status: "pending" }),
    /Unknown news item status/,
  );
});

test("Usable items require text, positive confidence and a usable status", () => {
  assert.equal(isUsableNewsItem(item()), true);
  assert.equal(isUsableNewsItem(item({ confidence: 0 })), false);
  assert.equal(
    isUsableNewsItem(
      item({
        title: "",
        summary: "",
        body: "",
      }),
    ),
    false,
  );
  assert.equal(
    isUsableNewsItem(item({ status: NEWS_ITEM_STATUS.ERROR })),
    false,
  );
});

test("Invalid timestamps and metric numbers stay null", () => {
  const result = item({
    publishedAt: "invalid",
    metrics: [{ name: "EPS", actual: "n/a", consensus: "" }],
  });

  assert.equal(result.publishedAt, null);
  assert.equal(result.metrics[0].actual, null);
  assert.equal(result.metrics[0].consensus, null);
});
