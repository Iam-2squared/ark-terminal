import test from "node:test";
import assert from "node:assert/strict";

import { runPaperTradingAutomationV1 } from "../operations/paper-trading-automation-v1.js";
import { buildPostMarketReviewV1 } from "../operations/post-market-review-v1.js";
import { buildNotificationDailySummaryV1 } from "../operations/notification-daily-summary-v1.js";

test("paper trading fills only in paper mode and respects kill switch", () => {
  const result = runPaperTradingAutomationV1({
    predictions: [
      { symbol: "7203.T", action: "BUY", confidence: 80, aiScore: 75, brokerExecutionAllowed: false },
    ],
    portfolio: { cash: 100000, positions: [] },
    prices: { "7203.T": 2500 },
    maxPositionRate: 0.1,
  });
  assert.equal(result.status, "READY");
  assert.equal(result.orders.length, 1);
  assert.equal(result.paperOnly, true);
  assert.equal(result.liveTradingAllowed, false);
  assert.equal(result.brokerExecutionAllowed, false);

  const halted = runPaperTradingAutomationV1({ killSwitch: true });
  assert.equal(halted.status, "HALTED");
  assert.equal(halted.orders.length, 0);
});

test("post market review calculates accuracy and drift without auto promotion", () => {
  const result = buildPostMarketReviewV1({
    predictions: [
      { symbol: "A", action: "BUY", confidence: 80, aiScore: 75 },
      { symbol: "B", action: "SELL", confidence: 70, aiScore: 30 },
    ],
    outcomes: [
      { symbol: "A", return: 0.02 },
      { symbol: "B", return: -0.01 },
    ],
    previousAccuracy: 0.5,
  });
  assert.equal(result.status, "READY");
  assert.equal(result.overall.accuracy, 1);
  assert.equal(result.drift.detected, true);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.humanApprovalRequired, true);
});

test("daily summary emits alerts and remains advisory", () => {
  const result = buildNotificationDailySummaryV1({
    preMarket: { status: "READY", market: { regime: "RISK_ON" }, topCandidates: [], risks: [] },
    predictions: { predictions: [{ symbol: "A", action: "BUY", confidence: 80, aiScore: 75 }], summary: { total: 1, buy: 1, sell: 0, noTrade: 0 } },
    paperTrading: { orders: [{}], fills: [{}], killSwitch: false },
    postMarket: { overall: { accuracy: 0.6, sampleSize: 10 }, drift: { detected: false }, weakSegments: [], improvementSuggestions: [] },
  });
  assert.equal(result.status, "READY");
  assert.equal(result.notificationCount, 1);
  assert.equal(result.advisoryOnly, true);
  assert.equal(result.brokerExecutionAllowed, false);
});
