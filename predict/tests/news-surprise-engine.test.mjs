import test from "node:test";
import assert from "node:assert/strict";

import {
  NEWS_ITEM_STATUS,
  NEWS_METRIC_DIRECTIONS,
  createNewsItem,
} from "../market-intelligence/news-data-model.js";
import { detectNewsSurprise } from "../market-intelligence/news-surprise-engine.js";

function item(overrides = {}) {
  return createNewsItem({
    id: "earnings-1",
    title: "決算発表",
    publishedAt: "2026-08-02",
    source: "TDnet",
    status: NEWS_ITEM_STATUS.AVAILABLE,
    confidence: 80,
    ...overrides,
  });
}

test("Higher-is-better metrics produce a positive numeric surprise", () => {
  const result = detectNewsSurprise(
    item({
      metrics: [
        {
          name: "EPS",
          actual: 110,
          consensus: 100,
          direction: NEWS_METRIC_DIRECTIONS.HIGHER_IS_BETTER,
        },
      ],
    }),
  );

  assert.equal(result.metrics[0].surprisePercent, 10);
  assert.equal(result.score, 75);
  assert.equal(result.label, "POSITIVE");
  assert.equal(result.method, "actual-vs-consensus-v1");
});

test("Lower costs are interpreted with lower-is-better polarity", () => {
  const result = detectNewsSurprise(
    item({
      metrics: [
        {
          name: "cost",
          actual: 8,
          consensus: 10,
          direction: NEWS_METRIC_DIRECTIONS.LOWER_IS_BETTER,
        },
      ],
    }),
  );

  assert.equal(result.metrics[0].surprisePercent, -20);
  assert.equal(result.metrics[0].directionalSurprisePercent, 20);
  assert.equal(result.score, 100);
});

test("Multiple metrics expose coverage and aggregate only classified metrics", () => {
  const result = detectNewsSurprise(
    item({
      metrics: [
        {
          name: "EPS",
          actual: 100,
          consensus: 100,
          direction: NEWS_METRIC_DIRECTIONS.HIGHER_IS_BETTER,
        },
        {
          name: "headcount",
          actual: 10,
          consensus: 8,
          direction: NEWS_METRIC_DIRECTIONS.NEUTRAL,
        },
      ],
    }),
  );

  assert.equal(result.score, 50);
  assert.equal(result.coverage, 50);
  assert.equal(result.metrics.length, 2);
});

test("Textual surprise is supported with lower confidence", () => {
  const result = detectNewsSurprise(
    item({ title: "利益が市場予想を上回る" }),
  );

  assert.equal(result.score, 70);
  assert.equal(result.method, "text-signal-v1");
  assert.equal(result.confidence, 36);
});

test("No surprise evidence remains unavailable", () => {
  const result = detectNewsSurprise(item());

  assert.equal(result.score, null);
  assert.equal(result.confidence, 0);
  assert.equal(result.label, "UNKNOWN");
});
