import test from "node:test";
import assert from "node:assert/strict";

import {
  PredictionFeatureComposer,
  composePredictionFeatures,
} from "../market-intelligence/prediction-feature-composer.js";
import { scoreVixVolatility } from "../market-intelligence/market-regime.js";

const NOW = Date.parse("2026-08-02T12:00:00Z");
const SOURCE_TIME = "2026-08-02T11:00:00Z";

function report(score, overrides = {}) {
  return {
    score,
    confidence: 100,
    coverage: 100,
    timestamp: SOURCE_TIME,
    ...overrides,
  };
}

function snapshot() {
  return {
    indexes: report(80),
    macro: {
      ...report(60),
      vixLevel: 20,
      items: [
        {
          symbol: "VIX",
          price: 20,
          confidence: 100,
          available: true,
        },
      ],
    },
    score: 74,
    timestamp: SOURCE_TIME,
  };
}

function input() {
  return {
    marketSnapshot: snapshot(),
    breadth: report(80),
    liquidity: report(75),
    sectorStrength: report(70),
    newsIntelligence: report(85),
    technical: {
      changePercent: 5,
      confidence: 100,
      timestamp: SOURCE_TIME,
    },
  };
}

test("Composer generates all required Prediction Engine features", () => {
  const result = composePredictionFeatures(input(), { now: () => NOW });

  assert.equal(result.availableCount, 10);
  assert.equal(result.marketScore, 74);
  assert.equal(result.breadth, 80);
  assert.equal(result.liquidity, 75);
  assert.equal(result.volatility, 33.33);
  assert.equal(result.macro, 60);
  assert.equal(result.newsScore, 85);
  assert.equal(result.sectorStrength, 70);
  assert.equal(result.momentum, 100);
  assert.ok(Number.isFinite(result.fearGreed));
  assert.ok(Number.isFinite(result.compositeAI));
  assert.equal(result.status, "ready");
});

test("VIX level conversion reuses the Market Regime scale", () => {
  assert.equal(scoreVixVolatility(null), null);
  assert.equal(scoreVixVolatility(10), 0);
  assert.equal(scoreVixVolatility(25), 50);
  assert.equal(scoreVixVolatility(40), 100);
});

test("Missing reports remain unavailable and reduce coverage", () => {
  const result = composePredictionFeatures(
    { marketSnapshot: snapshot() },
    { now: () => NOW },
  );

  assert.equal(result.breadth, null);
  assert.equal(result.liquidity, null);
  assert.equal(result.newsScore, null);
  assert.equal(result.availability.newsScore, false);
  assert.ok(result.coverage < 70);
  assert.equal(result.status, "partial");
});

test("Point-in-time guard rejects future source data", () => {
  assert.throws(
    () =>
      composePredictionFeatures(
        {
          ...input(),
          breadth: report(80, { timestamp: "2026-08-03T00:00:00Z" }),
        },
        { now: () => NOW },
      ),
    /later than the feature snapshot/,
  );
});

test("Composer does not mutate source reports", () => {
  const source = input();
  const original = structuredClone(source);

  composePredictionFeatures(source, { now: () => NOW });

  assert.deepEqual(source, original);
});

test("Composer class keeps a deterministic clock and validates it", () => {
  const composer = new PredictionFeatureComposer({ now: () => NOW });
  const result = composer.compose(input());

  assert.equal(result.timestamp, "2026-08-02T12:00:00.000Z");
  assert.throws(
    () => new PredictionFeatureComposer({ now: NOW }),
    /clock must be a function/,
  );
});
