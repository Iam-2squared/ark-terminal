import test from "node:test";
import assert from "node:assert/strict";

import {
  CompositeMarketScoreEngine,
  calculateCompositeMarketScore,
} from "../market-intelligence/composite-market-score.js";
import { analyzeLiquidity } from "../market-intelligence/liquidity-engine.js";
import { analyzeMarketBreadth } from "../market-intelligence/market-breadth.js";
import { analyzeSectorRotation } from "../market-intelligence/sector-rotation-engine.js";
import { analyzeSectorStrength } from "../market-intelligence/sector-strength-engine.js";

const NOW = Date.parse("2026-08-02T04:05:06.000Z");

function report(score, confidence = 100, coverage = 100) {
  return { score, confidence, coverage };
}

test("Composite market score combines all four Bundle 3 reports", () => {
  const composite = calculateCompositeMarketScore({
    breadth: report(100),
    liquidity: report(100),
    sectorStrength: report(100),
    sectorRotation: report(100),
    now: () => NOW,
  });

  assert.equal(composite.score, 100);
  assert.equal(composite.confidence, 100);
  assert.equal(composite.coverage, 100);
  assert.equal(composite.sentiment, "BULLISH");
  assert.equal(composite.timestamp, "2026-08-02T04:05:06.000Z");
});

test("Missing rotation is excluded while confidence reflects the gap", () => {
  const composite = calculateCompositeMarketScore({
    breadth: report(80),
    liquidity: report(60),
    sectorStrength: report(40),
    sectorRotation: report(null, 0, 0),
    now: () => NOW,
  });

  assert.equal(composite.score, 62.35);
  assert.equal(composite.confidence, 85);
  assert.equal(composite.coverage, 85);
  assert.equal(composite.components[3].available, false);
});

test("Nested component coverage reaches the composite report", () => {
  const composite = calculateCompositeMarketScore({
    breadth: report(80, 50, 50),
    now: () => NOW,
  });

  assert.equal(composite.score, 80);
  assert.equal(composite.confidence, 17.5);
  assert.equal(composite.coverage, 17.5);
});

test("Custom component weights are normalized by available weight", () => {
  const composite = calculateCompositeMarketScore({
    breadth: report(100),
    liquidity: report(0),
    sectorStrength: report(0),
    sectorRotation: report(0),
    weights: {
      breadth: 100,
      liquidity: 0,
      sectorStrength: 0,
      sectorRotation: 0,
    },
    now: () => NOW,
  });

  assert.equal(composite.score, 100);
  assert.equal(composite.confidence, 100);
  assert.equal(composite.coverage, 100);
});

test("No Bundle 3 reports produces unknown rather than neutral", () => {
  const composite = calculateCompositeMarketScore({ now: () => NOW });

  assert.equal(composite.score, null);
  assert.equal(composite.confidence, 0);
  assert.equal(composite.coverage, 0);
  assert.equal(composite.sentiment, "UNKNOWN");
});

test("Composite score validates its clock and timestamp", () => {
  assert.throws(
    () => calculateCompositeMarketScore({ now: NOW }),
    /clock must be a function/,
  );
  assert.throws(
    () => calculateCompositeMarketScore({ timestamp: "invalid" }),
    /timestamp is invalid/,
  );
  assert.throws(
    () => new CompositeMarketScoreEngine({ now: NOW }),
    /clock must be a function/,
  );
});

test("CompositeMarketScoreEngine keeps deterministic weights and clock", () => {
  const engine = new CompositeMarketScoreEngine({ now: () => NOW });
  const input = {
    breadth: report(80),
    liquidity: report(60),
    sectorStrength: report(40),
    sectorRotation: report(20),
  };

  assert.deepEqual(
    engine.calculate(input),
    calculateCompositeMarketScore({ ...input, now: () => NOW }),
  );
});

test("Bundle 3 modules compose from observations without mutating input", () => {
  const observations = [
    {
      symbol: "T1",
      sector: "Technology",
      changePercent: 2,
      volumeRatio: 2,
      turnoverRatio: 2,
      volume: 200,
      aboveMa20: true,
      aboveMa50: true,
      newHigh: true,
      newLow: false,
    },
    {
      symbol: "E1",
      sector: "Energy",
      changePercent: -1,
      volumeRatio: 1,
      turnoverRatio: 1,
      volume: 100,
      aboveMa20: false,
      aboveMa50: false,
      newHigh: false,
      newLow: true,
    },
  ];
  const original = structuredClone(observations);
  const breadth = analyzeMarketBreadth(observations);
  const liquidity = analyzeLiquidity(observations);
  const sectorStrength = analyzeSectorStrength(observations);
  const sectorRotation = analyzeSectorRotation({
    current: {
      ...sectorStrength,
      timestamp: "2026-08-02T00:00:00.000Z",
    },
    previous: {
      sectors: [
        { sector: "Technology", score: 50 },
        { sector: "Energy", score: 50 },
      ],
      timestamp: "2026-08-01T00:00:00.000Z",
    },
  });
  const composite = calculateCompositeMarketScore({
    breadth,
    liquidity,
    sectorStrength,
    sectorRotation,
    now: () => NOW,
  });

  assert.equal(typeof composite.score, "number");
  assert.equal(composite.components.length, 4);
  assert.deepEqual(observations, original);
});
