import test from "node:test";
import assert from "node:assert/strict";

import {
  SHADOW_SAFETY,
  buildShadowDailyLog,
  createShadowPrediction,
  evaluateShadowPrediction,
  runShadowForwardOperations,
} from "../shadow/shadow-forward-operations.js";

test("creates immutable shadow prediction with execution disabled", () => {
  const prediction = createShadowPrediction({
    symbol: "7203",
    signal: "BUY",
    entryPrice: 1000,
    stopLoss: 950,
    takeProfit: 1100,
    confidence: 0.72,
    expectedHoldingDays: 5,
    marketRegime: "BULL",
  }, { now: "2026-08-06T00:00:00.000Z" });

  assert.equal(prediction.symbol, "7203.T");
  assert.equal(prediction.status, "PENDING_EVALUATION");
  assert.equal(prediction.immutable, true);
  assert.equal(prediction.safety.brokerWriteAllowed, false);
  assert.equal(prediction.safety.orderTriggerWriteAllowed, false);
});

test("rejects BUY or SELL prediction without positive entry price", () => {
  assert.throws(
    () => createShadowPrediction({ symbol: "7203", signal: "BUY", entryPrice: 0 }),
    /positive entryPrice/,
  );
});

test("evaluates cost-aware virtual pnl", () => {
  const prediction = createShadowPrediction({
    symbol: "7203",
    signal: "BUY",
    entryPrice: 1000,
    confidence: 0.8,
  }, { now: "2026-08-06T00:00:00.000Z", predictionId: "p1" });

  const result = evaluateShadowPrediction(
    prediction,
    { exitPrice: 1100, quantity: 10, holdingDays: 5, evaluatedAt: "2026-08-11T00:00:00.000Z" },
    { commission: 100, slippage: 50, delayCost: 25 },
  );

  assert.equal(result.status, "EVALUATED");
  assert.equal(result.grossPnl, 1000);
  assert.equal(result.costs, 175);
  assert.equal(result.netPnl, 825);
  assert.equal(result.directionCorrect, true);
});

test("records NO_TRADE without fabricating pnl", () => {
  const prediction = createShadowPrediction({ symbol: "9432", signal: "NO_TRADE" }, {
    now: "2026-08-06T00:00:00.000Z",
    predictionId: "p2",
  });
  const result = evaluateShadowPrediction(prediction, {});
  assert.equal(result.status, "NO_TRADE_CONFIRMED");
  assert.equal(result.netPnl, 0);
  assert.equal(result.directionCorrect, null);
});

test("builds daily log with pending, no-trade and settled counts", () => {
  const pending = createShadowPrediction({ symbol: "7203", signal: "BUY", entryPrice: 1000 }, {
    predictionId: "pending",
    now: "2026-08-06T00:00:00.000Z",
  });
  const settledPrediction = createShadowPrediction({ symbol: "9432", signal: "SELL", entryPrice: 150 }, {
    predictionId: "settled",
    now: "2026-08-06T00:00:00.000Z",
  });
  const noTrade = createShadowPrediction({ symbol: "9984", signal: "NO_TRADE" }, {
    predictionId: "no-trade",
    now: "2026-08-06T00:00:00.000Z",
  });
  const evaluation = evaluateShadowPrediction(settledPrediction, { exitPrice: 140, quantity: 100 }, {});

  const log = buildShadowDailyLog({
    date: "2026-08-06",
    predictions: [pending, settledPrediction, noTrade],
    evaluations: [evaluation],
  });

  assert.equal(log.predictionCount, 3);
  assert.equal(log.evaluatedCount, 1);
  assert.equal(log.pendingCount, 1);
  assert.equal(log.noTradeCount, 1);
  assert.equal(log.wins, 1);
  assert.equal(log.safety.liveTradingAllowed, false);
});

test("runs full shadow operation with zero broker side effects", () => {
  const result = runShadowForwardOperations({
    now: "2026-08-06T00:00:00.000Z",
    candidates: [
      { symbol: "7203", signal: "BUY", entryPrice: 1000, confidence: 0.7, marketRegime: "BULL" },
      { symbol: "9432", signal: "NO_TRADE" },
    ],
    outcomesBySymbol: {
      "7203.T": { exitPrice: 1050, quantity: 10, holdingDays: 3 },
    },
    costsBySymbol: {
      "7203.T": { commission: 50, slippage: 20, delayCost: 10 },
    },
  });

  assert.equal(result.status, "SHADOW_RUN_COMPLETE");
  assert.equal(result.predictions.length, 2);
  assert.equal(result.evaluations.length, 1);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
  assert.equal(result.excelOrderWrites, 0);
  assert.equal(result.orderTriggerChanges, 0);
  assert.deepEqual(result.safety, SHADOW_SAFETY);
});
