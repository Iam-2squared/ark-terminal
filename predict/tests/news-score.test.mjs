import test from "node:test";
import assert from "node:assert/strict";

import {
  calculateNewsItemScore,
  calculateNewsRecencyWeight,
  calculateNewsScore,
} from "../market-intelligence/news-score.js";

const NOW = Date.parse("2026-08-02T12:00:00Z");

function report(score, confidence = 100, coverage = 100) {
  return { score, confidence, coverage };
}

test("Item score combines sentiment, surprise and inverted risk", () => {
  const result = calculateNewsItemScore({
    sentiment: report(80),
    surprise: report(80),
    risk: report(20),
  });

  assert.equal(result.score, 80);
  assert.equal(result.confidence, 100);
  assert.equal(result.sentiment, "BULLISH");
});

test("Missing surprise is excluded and remaining weights renormalize", () => {
  const result = calculateNewsItemScore({
    sentiment: report(70),
    surprise: report(null, 0, 0),
    risk: report(0),
  });

  assert.equal(result.score, 79.23);
  assert.equal(result.components[1].available, false);
  assert.equal(result.confidence, 65);
});

test("Missing risk is not treated as safe", () => {
  const result = calculateNewsItemScore({
    sentiment: report(60),
    risk: report(null, 0, 0),
  });

  assert.equal(result.score, 60);
  assert.equal(result.components[2].available, false);
});

test("Recent high-importance news outweighs old news", () => {
  const result = calculateNewsScore(
    [
      {
        id: "recent",
        publishedAt: "2026-08-02T11:00:00Z",
        importance: 90,
        scoreReport: report(90),
      },
      {
        id: "old",
        publishedAt: "2026-07-20T12:00:00Z",
        importance: 90,
        scoreReport: report(10),
      },
    ],
    { now: () => NOW },
  );

  assert.ok(result.score > 80);
  assert.equal(result.analyzedCount, 2);
});

test("Unknown timestamp has an explicit half-weight fallback", () => {
  assert.equal(
    calculateNewsRecencyWeight(null, { now: () => NOW }),
    0.5,
  );
});

test("Empty news score is unknown and clock contracts are validated", () => {
  const empty = calculateNewsScore([], { now: () => NOW });

  assert.equal(empty.score, null);
  assert.equal(empty.confidence, 0);
  assert.equal(empty.sentiment, "UNKNOWN");
  assert.throws(
    () => calculateNewsScore([], { now: NOW }),
    /clock must be a function/,
  );
});
