import test from "node:test";
import assert from "node:assert/strict";

import { auditAccuracy } from "../analysis/accuracy-audit-v3.js";

test("excludes no-trade and pending records from trade win rate", () => {
  const result = auditAccuracy([
    { action: "BUY", status: "WIN", returnPercent: 5 },
    { action: "SELL", status: "LOSS", returnPercent: -2 },
    { action: "NO_TRADE", status: "WIN", returnPercent: 0 },
    { action: "BUY", status: "PENDING" },
  ]);

  assert.equal(result.counts.all, 4);
  assert.equal(result.counts.trade, 3);
  assert.equal(result.tradePerformance.resolved, 2);
  assert.equal(result.tradePerformance.winRate, 50);
  assert.ok(result.warnings.includes("NO_TRADE_EXCLUDED_FROM_TRADE_WIN_RATE"));
});

test("reports BUY and SELL separately", () => {
  const result = auditAccuracy([
    { action: "BUY", status: "WIN", returnPercent: 3 },
    { action: "BUY", status: "WIN", returnPercent: 2 },
    { action: "SELL", status: "LOSS", returnPercent: -1 },
  ]);

  assert.equal(result.byAction.BUY.winRate, 100);
  assert.equal(result.byAction.SELL.winRate, 0);
});

test("compares reverse strategy", () => {
  const result = auditAccuracy([
    { action: "BUY", status: "LOSS", returnPercent: -4 },
    { action: "SELL", status: "LOSS", returnPercent: -2 },
  ]);

  assert.equal(result.reverseStrategy.original.winRate, 0);
  assert.equal(result.reverseStrategy.reversed.winRate, 100);
  assert.equal(result.reverseStrategy.better, true);
});

test("warns when the sample is too small", () => {
  const result = auditAccuracy([
    { action: "BUY", status: "WIN", returnPercent: 1 },
  ]);

  assert.ok(result.warnings.includes("INSUFFICIENT_TRADE_SAMPLE"));
});
