import assert from "node:assert/strict";
import test from "node:test";

import { runDailyPaperPipeline } from "../forward/daily-paper-pipeline.js";
import { settlePredictionHorizons } from "../forward/multi-horizon-settlement.js";
import { compareChampionCandidateForward } from "../forward/champion-candidate-forward-comparison.js";

test("Phase25 Part1 runs a paper-only daily pipeline with zero broker writes", async () => {
  const calls = [];
  const result = await runDailyPaperPipeline({
    marketDate: "2026-08-06",
    symbols: ["7203.t", "7203.T", "6758.t"],
    dependencies: {
      async getMarketSnapshot() { calls.push("snapshot"); return { source: "paper" }; },
      async validateData() { calls.push("validate"); return { status: "PASS" }; },
      async detectRegime() { calls.push("regime"); return { label: "BULL" }; },
      async rankSymbols({ symbols }) { calls.push("rank"); return symbols.map((symbol, index) => ({ symbol, rank: index + 1 })); },
      async generatePredictions({ rankings }) { calls.push("predict"); return rankings.map((row) => ({ symbol: row.symbol, signal: "BUY" })); },
      async createPaperOrders({ predictions }) { calls.push("paper-orders"); return predictions.map((row) => ({ ...row, quantity: 1 })); },
      async simulateFills({ paperOrders }) { calls.push("fills"); return paperOrders.map((row) => ({ ...row, status: "FILLED" })); },
      async persistRun() { calls.push("persist"); return { saved: true }; },
    },
  });

  assert.equal(result.status, "COMPLETED");
  assert.deepEqual(result.symbols, ["7203.T", "6758.T"]);
  assert.equal(result.sideEffects.brokerWrites, 0);
  assert.equal(result.sideEffects.liveOrders, 0);
  assert.equal(result.safety.orderCreationAllowed, false);
  assert.deepEqual(calls, ["snapshot", "validate", "regime", "rank", "predict", "paper-orders", "fills", "persist"]);
});

test("Phase25 Part1 stops when data quality is blocked", async () => {
  let rankCalled = false;
  const result = await runDailyPaperPipeline({
    marketDate: "2026-08-06",
    symbols: ["7203.T"],
    dependencies: {
      async getMarketSnapshot() { return {}; },
      async validateData() { return { status: "BLOCKED" }; },
      async detectRegime() { return {}; },
      async rankSymbols() { rankCalled = true; return []; },
      async generatePredictions() { return []; },
      async createPaperOrders() { return []; },
      async simulateFills() { return []; },
      async persistRun() { return { saved: true }; },
    },
  });

  assert.equal(result.status, "BLOCKED");
  assert.equal(rankCalled, false);
  assert.equal(result.sideEffects.brokerWrites, 0);
});

test("Phase25 Part2 settles due horizons with costs and leaves future horizons pending", () => {
  const rows = settlePredictionHorizons({
    prediction: { signal: "BUY", entryPrice: 100, createdAt: "2026-08-01T00:00:00.000Z" },
    prices: { 1: 102, 3: 104, 5: 110, 10: 120 },
    asOf: "2026-08-06T00:00:00.000Z",
    feePercent: 0.1,
    slippagePercent: 0.2,
  });

  const oneDay = rows.find((row) => row.horizon === 1);
  const fiveDay = rows.find((row) => row.horizon === 5);
  const tenDay = rows.find((row) => row.horizon === 10);
  assert.equal(oneDay.status, "RESOLVED");
  assert.ok(Math.abs(oneDay.netReturnPercent - 1.7) < 1e-9);
  assert.equal(fiveDay.status, "RESOLVED");
  assert.equal(tenDay.status, "PENDING");
});

test("Phase25 Part3 compares champion and candidate but never promotes automatically", () => {
  const champion = [
    { status: "RESOLVED", netReturnPercent: 1 },
    { status: "RESOLVED", netReturnPercent: -0.5 },
  ];
  const candidate = [
    { status: "RESOLVED", netReturnPercent: 1.5 },
    { status: "RESOLVED", netReturnPercent: -0.25 },
  ];
  const result = compareChampionCandidateForward({ champion, candidate, comparisonId: "2026-08-06" });

  assert.equal(result.recommendation, "READY_FOR_HUMAN_REVIEW");
  assert.equal(result.promotionExecuted, false);
  assert.equal(result.safety.automaticPromotionAllowed, false);
  assert.equal(result.safety.productionUpdateAllowed, false);
  assert.equal(result.safety.brokerWriteAllowed, false);
});
