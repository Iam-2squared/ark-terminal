import test from "node:test";
import assert from "node:assert/strict";

import {
  NEWS_ITEM_STATUS,
  createNewsItem,
} from "../market-intelligence/news-data-model.js";
import {
  analyzeNewsItemSentiment,
  analyzeNewsSentiment,
} from "../market-intelligence/news-sentiment-engine.js";

function item(id, title, overrides = {}) {
  return createNewsItem({
    id,
    title,
    source: "Wire",
    publishedAt: "2026-08-02T00:00:00Z",
    status: NEWS_ITEM_STATUS.AVAILABLE,
    confidence: 80,
    importance: 50,
    ...overrides,
  });
}

test("News sentiment reuses the existing bilingual context lexicon", () => {
  const positive = analyzeNewsItemSentiment(
    item("positive", "最高益で増益、提携も発表"),
  );
  const negative = analyzeNewsItemSentiment(
    item("negative", "下方修正と赤字、訴訟を発表"),
  );

  assert.equal(positive.label, "POSITIVE");
  assert.equal(negative.label, "NEGATIVE");
  assert.equal(positive.method, "existing-context-lexicon-v1");
  assert.ok(positive.positiveSignals >= 2);
  assert.ok(negative.negativeSignals >= 2);
});

test("No lexicon match stays neutral with deliberately low confidence", () => {
  const result = analyzeNewsItemSentiment(item("neutral", "定時株主総会のお知らせ"));

  assert.equal(result.score, 50);
  assert.equal(result.label, "NEUTRAL");
  assert.equal(result.confidence, 20);
});

test("Aggregate sentiment excludes unavailable items without inventing a score", () => {
  const result = analyzeNewsSentiment([
    item("positive", "record profit and strong growth"),
    item("missing", "", {
      confidence: 0,
      status: NEWS_ITEM_STATUS.UNAVAILABLE,
    }),
  ]);

  assert.equal(result.analyzedCount, 1);
  assert.equal(result.requestedCount, 2);
  assert.equal(result.label, "POSITIVE");
  assert.ok(result.confidence < 80);
});

test("Empty sentiment input is explicitly unknown", () => {
  const result = analyzeNewsSentiment([]);

  assert.equal(result.score, null);
  assert.equal(result.confidence, 0);
  assert.equal(result.label, "UNKNOWN");
});
