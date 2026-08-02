import test from "node:test";
import assert from "node:assert/strict";

import {
  MarketRegime,
  SNAPSHOT_REGIMES,
  detectSnapshotMarketRegime,
} from "../market-intelligence/market-regime.js";

function input(score, indexScore, vixLevel = 20) {
  return {
    score,
    indexes: { score: indexScore, confidence: 90 },
    macro: { score: 60, confidence: 80, vixLevel },
  };
}

test("Strong broad markets are classified as bull regime", () => {
  const report = detectSnapshotMarketRegime(input(75, 75));

  assert.equal(report.name, SNAPSHOT_REGIMES.BULL);
  assert.equal(report.recommendation, "Trend Following");
  assert.equal(report.riskMultiplier, 1.2);
  assert.ok(report.confidence > 0);
});

test("Weak broad markets are classified as bear regime", () => {
  const report = detectSnapshotMarketRegime(input(30, 30));

  assert.equal(report.name, SNAPSHOT_REGIMES.BEAR);
  assert.equal(report.recommendation, "Defensive");
  assert.equal(report.riskMultiplier, 0.45);
});

test("VIX at 35 overrides directional signals as high volatility", () => {
  const report = detectSnapshotMarketRegime(input(80, 80, 35));

  assert.equal(report.name, SNAPSHOT_REGIMES.HIGH_VOLATILITY);
  assert.equal(report.recommendation, "Reduce Position");
  assert.match(report.reasons.at(-1), /VIXは35/);
});

test("Quiet neutral markets are classified as low volatility", () => {
  const report = detectSnapshotMarketRegime(input(50, 50, 15));

  assert.equal(report.name, SNAPSHOT_REGIMES.LOW_VOLATILITY);
  assert.equal(report.recommendation, "Breakout Watch");
});

test("Indecisive markets remain in a range regime", () => {
  const report = detectSnapshotMarketRegime(input(55, 55, 20));

  assert.equal(report.name, SNAPSHOT_REGIMES.RANGE);
  assert.equal(report.recommendation, "Swing Trade");
});

test("No composite score produces an explicit unknown regime", () => {
  const report = detectSnapshotMarketRegime({});

  assert.equal(report.name, SNAPSHOT_REGIMES.UNKNOWN);
  assert.equal(report.confidence, 0);
  assert.equal(report.riskMultiplier, 0);
  assert.equal(report.recommendation, "Neutral");
});

test("MarketRegime exposes the same detection contract", () => {
  const engine = new MarketRegime();
  assert.deepEqual(engine.detect(input(75, 75)), detectSnapshotMarketRegime(input(75, 75)));
});
