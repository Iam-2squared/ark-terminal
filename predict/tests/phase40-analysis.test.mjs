import test from "node:test";
import assert from "node:assert/strict";

import {
  buildPhase40BacktestDashboard,
  comparePhase40ChampionCandidate,
  bootstrapPhase40Advantage,
  detectPhase40Overfitting,
  runPhase40Analysis,
} from "../backtest/phase40-analysis.js";

function row({
  modelRole = "CHAMPION",
  partition = "test",
  netReturn = 0.01,
  hit = true,
  symbol = "7203.T",
  sector = "AUTO",
  regime = "BULL",
  horizonDays = 5,
  drawdown = 0.01,
} = {}) {
  return {
    modelRole,
    partition,
    netReturn,
    hit,
    symbol,
    sector,
    regime,
    horizonDays,
    drawdown,
  };
}

test("builds a multi-dimensional backtest dashboard", () => {
  const result = buildPhase40BacktestDashboard([
    row(),
    row({ symbol: "6758.T", sector: "TECH", regime: "RANGE", horizonDays: 10 }),
  ]);
  assert.equal(result.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(result.overall.sampleCount, 2);
  assert.equal(result.bySymbol.length, 2);
  assert.equal(result.safety.brokerWriteAllowed, false);
});

test("compares champion and candidate without allowing promotion", () => {
  const result = comparePhase40ChampionCandidate([
    row({ modelRole: "CHAMPION", netReturn: 0.01 }),
    row({ modelRole: "CANDIDATE", netReturn: 0.02 }),
  ]);
  assert.equal(result.status, "READY_FOR_HUMAN_REVIEW");
  assert.ok(result.deltas.averageNetReturn > 0);
  assert.equal(result.promotionAllowed, false);
});

test("bootstrap advantage is deterministic for a fixed seed", () => {
  const rows = [
    row({ modelRole: "CHAMPION", netReturn: 0.00 }),
    row({ modelRole: "CHAMPION", netReturn: 0.01 }),
    row({ modelRole: "CANDIDATE", netReturn: 0.02 }),
    row({ modelRole: "CANDIDATE", netReturn: 0.03 }),
  ];
  const first = bootstrapPhase40Advantage(rows, { iterations: 200, seed: 7 });
  const second = bootstrapPhase40Advantage(rows, { iterations: 200, seed: 7 });
  assert.equal(first.meanAdvantage, second.meanAdvantage);
  assert.equal(first.lower95, second.lower95);
  assert.equal(first.promotionAllowed, false);
});

test("detects training-to-test performance decay", () => {
  const rows = [];
  for (let index = 0; index < 25; index += 1) {
    rows.push(row({ partition: "training", netReturn: 0.03, hit: true }));
    rows.push(row({ partition: "validation", netReturn: 0.01, hit: true }));
    rows.push(row({ partition: "test", netReturn: -0.02, hit: false, drawdown: 0.05 }));
  }
  const result = detectPhase40Overfitting(rows, { minSamples: 20 });
  assert.equal(result.status, "OVERFIT_WARNING");
  assert.ok(result.warnings.includes("TRAIN_POSITIVE_TEST_NONPOSITIVE"));
  assert.ok(result.warnings.includes("WIN_RATE_DECAY"));
  assert.equal(result.automaticPromotionAllowed, false);
});

test("full analysis remains historical and review-only", () => {
  const rows = [
    row({ modelRole: "CHAMPION", partition: "training", netReturn: 0.01 }),
    row({ modelRole: "CANDIDATE", partition: "training", netReturn: 0.02 }),
    row({ modelRole: "CHAMPION", partition: "validation", netReturn: 0.01 }),
    row({ modelRole: "CANDIDATE", partition: "validation", netReturn: 0.02 }),
    row({ modelRole: "CHAMPION", partition: "test", netReturn: 0.01 }),
    row({ modelRole: "CANDIDATE", partition: "test", netReturn: 0.02 }),
  ];
  const result = runPhase40Analysis(rows, {
    bootstrap: { iterations: 100, seed: 3 },
    overfitting: { minSamples: 1 },
  });
  assert.equal(result.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
});
