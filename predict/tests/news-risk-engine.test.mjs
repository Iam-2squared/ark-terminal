import test from "node:test";
import assert from "node:assert/strict";

import {
  NEWS_ITEM_STATUS,
  createNewsItem,
} from "../market-intelligence/news-data-model.js";
import {
  NEWS_RISK_CATEGORIES,
  detectNewsRisk,
} from "../market-intelligence/news-risk-engine.js";

function item(title, overrides = {}) {
  return createNewsItem({
    id: "risk-item",
    title,
    publishedAt: "2026-08-02",
    source: "Wire",
    status: NEWS_ITEM_STATUS.AVAILABLE,
    confidence: 80,
    ...overrides,
  });
}

test("Financial distress is surfaced as a high risk event", () => {
  const result = detectNewsRisk(item("Going concern and default warning"));

  assert.equal(result.severity, "HIGH");
  assert.equal(
    result.findings[0].category,
    NEWS_RISK_CATEGORIES.FINANCIAL_DISTRESS,
  );
});

test("Independent risk findings combine without exceeding 100", () => {
  const result = detectNewsRisk(
    item("Accounting irregularity investigation and public offering dilution"),
  );

  assert.ok(result.score > 80);
  assert.ok(result.score <= 100);
  assert.equal(result.findings.length, 2);
});

test("Explicit mitigation lowers but does not erase detected risk", () => {
  const unresolved = detectNewsRisk(item("Data breach reported"));
  const resolved = detectNewsRisk(item("Data breach resolved and restored"));

  assert.equal(resolved.mitigated, true);
  assert.ok(resolved.score < unresolved.score);
  assert.ok(resolved.score > 0);
});

test("Analyzed text with no risk signal receives a zero risk score", () => {
  const result = detectNewsRisk(item("New product launch announced"));

  assert.equal(result.score, 0);
  assert.equal(result.severity, "NONE");
  assert.ok(result.confidence > 0);
});

test("Unavailable text does not imply zero risk", () => {
  const result = detectNewsRisk(
    item("", {
      confidence: 0,
      status: NEWS_ITEM_STATUS.UNAVAILABLE,
    }),
  );

  assert.equal(result.score, null);
  assert.equal(result.severity, "UNKNOWN");
});
