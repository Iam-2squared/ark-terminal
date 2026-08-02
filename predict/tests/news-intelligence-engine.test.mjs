import test from "node:test";
import assert from "node:assert/strict";

import { NewsIntelligenceEngine } from "../market-intelligence/news-intelligence-engine.js";
import { NewsSummaryService } from "../market-intelligence/news-summary-service.js";

const NOW = Date.parse("2026-08-02T12:00:00Z");

test("News Intelligence composes all Bundle 4 stages without mutation", async () => {
  const input = {
    earnings: [
      {
        id: "earnings-1",
        title: "最高益、EPSは市場予想を上回る",
        summary: "四半期決算を発表しました。",
        publishedAt: "2026-08-02T10:00:00Z",
        source: "TDnet",
        symbol: "7203.T",
        actual: 120,
        consensus: 100,
        metric: "EPS",
        importance: 90,
        confidence: 95,
      },
    ],
    disclosures: [
      {
        id: "risk-1",
        title: "情報漏えいの影響は軽微",
        publishedAt: "2026-08-02T09:00:00Z",
        source: "TDnet",
        symbol: "7203.T",
        importance: 80,
        confidence: 90,
      },
    ],
  };
  const original = structuredClone(input);
  const engine = new NewsIntelligenceEngine({ now: () => NOW });
  const result = await engine.analyze(input);

  assert.equal(result.timestamp, "2026-08-02T12:00:00.000Z");
  assert.equal(result.status, "ready");
  assert.equal(result.items.length, 2);
  assert.equal(result.items[0].event.category, "EARNINGS");
  assert.equal(result.items[0].surprise.label, "POSITIVE");
  assert.equal(result.items[0].generatedSummary.method, "source");
  assert.ok(result.risk.eventCount >= 1);
  assert.ok(Number.isFinite(result.score));
  assert.deepEqual(input, original);
});

test("AI summarizer can be injected without coupling the engine to a provider", async () => {
  const engine = new NewsIntelligenceEngine({
    now: () => NOW,
    summaryService: new NewsSummaryService({
      summarizer: async () => ({ text: "要約結果", confidence: 88 }),
    }),
  });
  const result = await engine.analyze([
    {
      title: "新製品を発売",
      publishedAt: "2026-08-02T11:00:00Z",
      source: "Company",
    },
  ]);

  assert.equal(result.items[0].generatedSummary.text, "要約結果");
  assert.equal(result.items[0].generatedSummary.method, "ai");
});

test("No usable source items produces an unavailable report", async () => {
  const engine = new NewsIntelligenceEngine({ now: () => NOW });
  const result = await engine.analyze([]);

  assert.equal(result.status, "unavailable");
  assert.equal(result.score, null);
  assert.equal(result.confidence, 0);
  assert.equal(result.risk.severity, "UNKNOWN");
});

test("Timestamp and dependency contracts fail early", async () => {
  assert.throws(
    () => new NewsIntelligenceEngine({ now: NOW }),
    /clock must be a function/,
  );
  assert.throws(
    () => new NewsIntelligenceEngine({ sentimentEngine: {} }),
    /sentiment engine is invalid/,
  );

  const engine = new NewsIntelligenceEngine({ now: () => NOW });
  await assert.rejects(
    () => engine.analyze([], { timestamp: "invalid" }),
    /timestamp is invalid/,
  );
});
