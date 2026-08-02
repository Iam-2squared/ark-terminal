import test from "node:test";
import assert from "node:assert/strict";

import {
  NEWS_ITEM_STATUS,
  NEWS_SOURCE_TYPES,
  createNewsItem,
} from "../market-intelligence/news-data-model.js";
import {
  NEWS_EVENT_CATEGORIES,
  classifyNewsEvent,
} from "../market-intelligence/news-event-classifier.js";

function item(title, overrides = {}) {
  return createNewsItem({
    id: `item-${title || "empty"}`,
    title,
    publishedAt: "2026-08-02",
    source: "TDnet",
    confidence: 90,
    status: NEWS_ITEM_STATUS.AVAILABLE,
    ...overrides,
  });
}

test("Earnings source type is classified even with a generic title", () => {
  const result = classifyNewsEvent(
    item("2026年3月期資料", { type: NEWS_SOURCE_TYPES.EARNINGS }),
  );

  assert.equal(result.category, NEWS_EVENT_CATEGORIES.EARNINGS);
  assert.equal(result.available, true);
  assert.ok(result.confidence > 60);
});

test("Guidance has priority over a general earnings signal", () => {
  const result = classifyNewsEvent(
    item("決算発表および業績予想の上方修正"),
  );

  assert.equal(result.category, NEWS_EVENT_CATEGORIES.GUIDANCE);
  assert.ok(result.secondaryCategories.includes(NEWS_EVENT_CATEGORIES.EARNINGS));
});

test("Classifier reports M&A and partnership signals separately", () => {
  const result = classifyNewsEvent(item("買収に向けた業務提携を発表"));

  assert.equal(result.category, NEWS_EVENT_CATEGORIES.MERGER_ACQUISITION);
  assert.ok(
    result.secondaryCategories.includes(NEWS_EVENT_CATEGORIES.PARTNERSHIP),
  );
});

test("Unmatched content is OTHER rather than a fabricated event", () => {
  const result = classifyNewsEvent(item("定時株主総会のお知らせ"));

  assert.equal(result.category, NEWS_EVENT_CATEGORIES.OTHER);
  assert.equal(result.available, false);
});

test("Unavailable records cannot create an event", () => {
  const result = classifyNewsEvent(
    item("決算", {
      confidence: 0,
      status: NEWS_ITEM_STATUS.UNAVAILABLE,
    }),
  );

  assert.equal(result.available, false);
  assert.equal(result.confidence, 0);
});
