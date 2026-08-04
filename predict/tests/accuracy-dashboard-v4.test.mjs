import test from "node:test";
import assert from "node:assert/strict";

import { buildAccuracyDashboardV4 } from "../analysis/accuracy-dashboard-v4.js";

test("Accuracy Dashboard v4 separates resolved trades, pending and NO_TRADE", () => {
  const dashboard = buildAccuracyDashboardV4({
    tradeMemoryRecords: [
      { id: "1", symbol: "7203", action: "BUY", status: "WIN", returnPercent: 4 },
      { id: "2", symbol: "6758", action: "SELL", status: "LOSS", returnPercent: -2 },
      { id: "3", symbol: "9984", action: "BUY", status: "PENDING" },
      { id: "4", symbol: "9432", action: "NO_TRADE", status: "WIN", returnPercent: 1 },
    ],
    performance: { sharpe: 1.2, maxDrawdownPercent: 8.5 },
  });

  assert.equal(dashboard.sample.evaluations, 4);
  assert.equal(dashboard.sample.trades, 3);
  assert.equal(dashboard.sample.resolvedTrades, 2);
  assert.equal(dashboard.sample.pending, 1);
  assert.equal(dashboard.sample.noTrade, 1);
  assert.equal(dashboard.metrics.tradeWinRate, 50);
  assert.equal(dashboard.metrics.buyWinRate, 100);
  assert.equal(dashboard.metrics.sellWinRate, 0);
  assert.equal(dashboard.metrics.profitFactor, 2);
  assert.equal(dashboard.metrics.sharpe, 1.2);
  assert.equal(dashboard.metrics.maxDrawdownPercent, 8.5);
  assert.equal(dashboard.reverseStrategy.better, false);
  assert.ok(dashboard.warnings.includes("NO_TRADE_EXCLUDED_FROM_TRADE_WIN_RATE"));
});
