import test from "node:test";
import assert from "node:assert/strict";

import {
  LiquidityEngine,
  analyzeLiquidity,
  scoreLiquidityRatio,
} from "../market-intelligence/liquidity-engine.js";

function observation(symbol, changePercent, ratio = 1, overrides = {}) {
  return {
    symbol,
    changePercent,
    volume: 100 * ratio,
    averageVolume: 100,
    turnover: 1000 * ratio,
    averageTurnover: 1000,
    confidence: 100,
    ...overrides,
  };
}

test("Liquidity activity ratios have stable score boundaries", () => {
  assert.equal(scoreLiquidityRatio(0), 0);
  assert.equal(scoreLiquidityRatio(1), 50);
  assert.equal(scoreLiquidityRatio(2), 100);
  assert.equal(scoreLiquidityRatio(4), 100);
  assert.equal(scoreLiquidityRatio(-1), null);
});

test("High activity with positive volume flow produces strong liquidity", () => {
  const report = analyzeLiquidity([
    observation("A", 1, 2),
    observation("B", 2, 2),
  ]);

  assert.equal(report.score, 100);
  assert.equal(report.confidence, 100);
  assert.equal(report.coverage, 100);
  assert.equal(report.medianVolumeRatio, 2);
  assert.equal(report.upVolumePercent, 100);
});

test("Down-volume dominance reduces flow without erasing activity", () => {
  const report = analyzeLiquidity([
    observation("A", 1, 1, { volume: 100 }),
    observation("B", -1, 1, { volume: 300, averageVolume: 300 }),
  ]);

  assert.equal(report.volumeActivity.score, 50);
  assert.equal(report.volumeFlow.score, 25);
  assert.equal(report.upVolumePercent, 25);
  assert.ok(report.score < 50);
});

test("Raw volume and turnover derive normalized activity ratios", () => {
  const report = analyzeLiquidity([
    observation("A", 1, 1.5),
    observation("B", -1, 0.5),
  ]);

  assert.equal(report.medianVolumeRatio, 1);
  assert.equal(report.medianTurnoverRatio, 1);
  assert.equal(report.activeVolumePercent, 50);
});

test("Missing turnover is excluded and lowers metric coverage", () => {
  const report = analyzeLiquidity([
    {
      symbol: "A",
      changePercent: 1,
      volume: 200,
      averageVolume: 100,
    },
  ]);

  assert.equal(report.score, 100);
  assert.equal(report.coverage, 80);
  assert.equal(report.confidence, 80);
  assert.equal(report.turnoverActivity.score, null);
});

test("Expected universe size reduces liquidity confidence", () => {
  const report = analyzeLiquidity([observation("A", 1, 2)], {
    expectedCount: 2,
  });

  assert.equal(report.score, 100);
  assert.equal(report.coverage, 50);
  assert.equal(report.confidence, 50);
});

test("Empty liquidity input remains unavailable", () => {
  const report = analyzeLiquidity();

  assert.equal(report.score, null);
  assert.equal(report.confidence, 0);
  assert.equal(report.coverage, 0);
});

test("LiquidityEngine exposes stateless analysis", () => {
  const inputs = [observation("A", 1, 2)];
  const engine = new LiquidityEngine();

  assert.deepEqual(engine.analyze(inputs), analyzeLiquidity(inputs));
});

test("Liquidity report carries the latest constituent timestamp", () => {
  const report = analyzeLiquidity([
    observation("A", 1, 1, { timestamp: "2026-08-01T00:00:00Z" }),
    observation("B", -1, 1, { timestamp: "2026-08-02T00:00:00Z" }),
  ]);

  assert.equal(report.timestamp, "2026-08-02T00:00:00.000Z");
});
