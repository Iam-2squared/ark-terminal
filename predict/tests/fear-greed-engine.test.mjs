import test from "node:test";
import assert from "node:assert/strict";

import {
  FearGreedEngine,
  calculateFearGreed,
  classifyFearGreed,
} from "../market-intelligence/fear-greed-engine.js";

function report(score, confidence = 100, coverage = 100) {
  return { score, confidence, coverage };
}

test("Low volatility and strong participation produce extreme greed", () => {
  const result = calculateFearGreed({
    volatility: report(0),
    breadth: report(100),
    momentum: report(100),
    news: report(100),
    market: report(100),
  });

  assert.equal(result.score, 100);
  assert.equal(result.label, "EXTREME_GREED");
  assert.equal(result.isProbability, false);
});

test("High volatility and weak participation produce extreme fear", () => {
  const result = calculateFearGreed({
    volatility: report(100),
    breadth: report(0),
    momentum: report(0),
    news: report(0),
    market: report(0),
  });

  assert.equal(result.score, 0);
  assert.equal(result.label, "EXTREME_FEAR");
});

test("Missing components are renormalized with lower coverage", () => {
  const result = calculateFearGreed({ breadth: report(80) });

  assert.equal(result.score, 80);
  assert.equal(result.confidence, 20);
  assert.equal(result.coverage, 20);
});

test("Fear and greed labels have deterministic boundaries", () => {
  assert.equal(classifyFearGreed(null), "UNKNOWN");
  assert.equal(classifyFearGreed(25), "EXTREME_FEAR");
  assert.equal(classifyFearGreed(40), "FEAR");
  assert.equal(classifyFearGreed(50), "NEUTRAL");
  assert.equal(classifyFearGreed(60), "GREED");
  assert.equal(classifyFearGreed(75), "EXTREME_GREED");
});

test("FearGreedEngine supports isolated custom weights", () => {
  const engine = new FearGreedEngine({
    weights: {
      volatility: 0,
      breadth: 100,
      momentum: 0,
      news: 0,
      market: 0,
    },
  });
  const result = engine.calculate({
    volatility: report(100),
    breadth: report(90),
  });

  assert.equal(result.score, 90);
});
