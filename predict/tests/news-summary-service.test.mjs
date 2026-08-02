import test from "node:test";
import assert from "node:assert/strict";

import {
  NEWS_ITEM_STATUS,
  createNewsItem,
} from "../market-intelligence/news-data-model.js";
import {
  NEWS_SUMMARY_METHODS,
  NewsSummaryService,
} from "../market-intelligence/news-summary-service.js";

function item(overrides = {}) {
  return createNewsItem({
    id: "summary-item",
    title: "決算発表",
    publishedAt: "2026-08-02",
    source: "TDnet",
    status: NEWS_ITEM_STATUS.AVAILABLE,
    confidence: 80,
    ...overrides,
  });
}

test("Provider summary is preserved without claiming AI generation", async () => {
  const service = new NewsSummaryService();
  const result = await service.summarize(
    item({ summary: "会社が公開した要約です。" }),
  );

  assert.equal(result.text, "会社が公開した要約です。");
  assert.equal(result.method, NEWS_SUMMARY_METHODS.SOURCE);
});

test("Body fallback extracts at most the first two sentences", async () => {
  const service = new NewsSummaryService();
  const result = await service.summarize(
    item({ body: "第一文です。第二文です。第三文です。" }),
  );

  assert.equal(result.text, "第一文です。 第二文です。");
  assert.equal(result.method, NEWS_SUMMARY_METHODS.EXTRACTIVE);
});

test("Injected AI summarizer is isolated behind the service contract", async () => {
  const service = new NewsSummaryService({
    summarizer: async ({ title }) => ({
      text: `${title}をAI要約`,
      confidence: 91,
    }),
  });
  const result = await service.summarize(item());

  assert.equal(result.text, "決算発表をAI要約");
  assert.equal(result.method, NEWS_SUMMARY_METHODS.AI);
  assert.equal(result.confidence, 91);
});

test("AI failure falls back safely to source text", async () => {
  const service = new NewsSummaryService({
    summarizer: async () => {
      throw new Error("provider failed");
    },
  });
  const result = await service.summarize(
    item({ summary: "公開済み要約" }),
  );

  assert.equal(result.text, "公開済み要約");
  assert.equal(result.method, NEWS_SUMMARY_METHODS.SOURCE);
  assert.equal(result.fallbackReason, "ai_summary_error");
});

test("Summary length and constructor dependencies are validated", async () => {
  const service = new NewsSummaryService({ maximumLength: 80 });
  const result = await service.summarize(
    item({ summary: "長".repeat(120) }),
  );

  assert.equal(result.text.length, 80);
  assert.match(result.text, /…$/);
  assert.throws(
    () => new NewsSummaryService({ summarizer: "invalid" }),
    /must be a function or null/,
  );
});
