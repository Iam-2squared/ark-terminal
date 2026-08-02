import test from "node:test";
import assert from "node:assert/strict";

import {
  MARKET_DATA_STATUS,
  createMarketDataPoint,
} from "../market-intelligence/market-data-model.js";
import {
  calculateCompositeMarketScore,
  scoreDirectionalChange,
  scoreMarketSeries,
  scoreToSentiment,
} from "../market-intelligence/market-score.js";

const TIMESTAMP = "2026-08-01T00:00:00.000Z";

function point(
  symbol,
  { price = 100, changePercent = 0, confidence = 100, status } = {},
) {
  return createMarketDataPoint({
    symbol,
    price,
    change: (price * changePercent) / 100,
    changePercent,
    timestamp: TIMESTAMP,
    source: "test-provider",
    status,
    confidence,
  });
}

test("Directional score clamps daily changes to a 0-100 scale", () => {
  assert.equal(scoreDirectionalChange(2, { scale: 2 }), 100);
  assert.equal(scoreDirectionalChange(-2, { scale: 2 }), 0);
  assert.equal(scoreDirectionalChange(8, { scale: 2 }), 100);
  assert.equal(scoreDirectionalChange(-1, { scale: 2, invert: true }), 75);
  assert.equal(scoreDirectionalChange(null), null);
});

test("Market series scoring uses source confidence as an effective weight", () => {
  const report = scoreMarketSeries(
    [
      point("NIKKEI225", { changePercent: 2 }),
      point("NASDAQ", { changePercent: -2, confidence: 50 }),
    ],
    [
      { symbol: "NIKKEI225", scale: 2 },
      { symbol: "NASDAQ", scale: 2 },
    ],
  );

  assert.equal(report.score, 66.67);
  assert.equal(report.confidence, 75);
  assert.equal(report.coverage, 100);
  assert.equal(report.availableCount, 2);
  assert.equal(report.items[0].price, 100);
});

test("Missing series are excluded instead of being scored as neutral", () => {
  const report = scoreMarketSeries(
    [point("NIKKEI225", { changePercent: 2 })],
    [
      { symbol: "NIKKEI225", scale: 2 },
      { symbol: "NASDAQ", scale: 2 },
    ],
  );

  assert.equal(report.score, 100);
  assert.equal(report.coverage, 50);
  assert.equal(report.confidence, 50);
  assert.equal(report.items[1].available, false);
  assert.equal(report.items[1].status, MARKET_DATA_STATUS.UNAVAILABLE);
});

test("Error and zero-confidence points cannot influence a series score", () => {
  const error = createMarketDataPoint({
    symbol: "NIKKEI225",
    status: MARKET_DATA_STATUS.ERROR,
  });
  const zeroConfidence = point("NASDAQ", {
    changePercent: 2,
    confidence: 0,
  });
  const report = scoreMarketSeries([error, zeroConfidence], [
    { symbol: "NIKKEI225" },
    { symbol: "NASDAQ" },
  ]);

  assert.equal(report.score, null);
  assert.equal(report.confidence, 0);
  assert.equal(report.coverage, 50);
});

test("Composite score re-normalizes when a component is unavailable", () => {
  const report = calculateCompositeMarketScore({
    indexes: { score: 80, confidence: 80 },
    macro: { score: null, confidence: 0 },
  });

  assert.equal(report.score, 80);
  assert.equal(report.coverage, 70);
  assert.equal(report.confidence, 56);
  assert.deepEqual(
    report.components.map((component) => component.available),
    [true, false],
  );
});

test("Composite score accepts numeric weight strings and safe fallbacks", () => {
  const report = calculateCompositeMarketScore({
    indexes: { score: 100, confidence: 100 },
    macro: { score: 0, confidence: 100 },
    indexWeight: "60",
    macroWeight: "40",
  });
  const fallback = calculateCompositeMarketScore({
    indexes: { score: 100, confidence: 100 },
    macro: { score: 0, confidence: 100 },
    indexWeight: "invalid",
  });

  assert.equal(report.score, 60);
  assert.equal(fallback.score, 70);
});

test("Market sentiment thresholds are deterministic", () => {
  assert.equal(scoreToSentiment(65), "BULLISH");
  assert.equal(scoreToSentiment(35), "BEARISH");
  assert.equal(scoreToSentiment(50), "NEUTRAL");
  assert.equal(scoreToSentiment(undefined), "UNKNOWN");
});

test("Unknown score symbols fail fast", () => {
  assert.throws(
    () => scoreMarketSeries([], [{ symbol: "UNKNOWN" }]),
    /Unknown market score symbol/,
  );
});
