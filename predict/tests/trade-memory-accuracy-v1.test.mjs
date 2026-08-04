import assert from "node:assert/strict";
import test from "node:test";

import {
  auditTradeMemoryAccuracy,
  tradeMemoryRecordToAccuracyRecord,
} from "../analysis/trade-memory-accuracy-v1.js";

test("maps open BUY executions to pending accuracy records", () => {
  const record = tradeMemoryRecordToAccuracyRecord({
    id: "execution-buy-1",
    symbol: "7203.T",
    action: "BUY",
    status: "open",
    confidence: 78,
    evaluation: {
      evaluatedAt: null,
      actualReturnPercent: null,
      hit: null,
    },
  });

  assert.equal(record.action, "BUY");
  assert.equal(record.status, "PENDING");
  assert.equal(record.confidence, 78);
});

test("maps resolved SELL executions into WIN or LOSS", () => {
  const win = tradeMemoryRecordToAccuracyRecord({
    symbol: "7203.T",
    action: "SELL",
    status: "resolved",
    evaluation: {
      evaluatedAt: "2026-08-05T00:00:00.000Z",
      actualReturnPercent: 4.2,
      hit: true,
    },
  });

  const loss = tradeMemoryRecordToAccuracyRecord({
    symbol: "6758.T",
    action: "SELL",
    status: "resolved",
    evaluation: {
      evaluatedAt: "2026-08-05T00:00:00.000Z",
      actualReturnPercent: -2.1,
      hit: false,
    },
  });

  assert.equal(win.status, "WIN");
  assert.equal(loss.status, "LOSS");
});

test("excludes gate-only records from trade win rate as NO_TRADE", () => {
  const result = auditTradeMemoryAccuracy([
    {
      symbol: "2410.T",
      decision: "approve",
      status: "resolved",
      evaluation: {
        evaluatedAt: "2026-08-05T00:00:00.000Z",
        actualReturnPercent: 3,
        hit: true,
      },
    },
    {
      symbol: "7203.T",
      action: "BUY",
      status: "open",
      evaluation: {
        evaluatedAt: null,
      },
    },
    {
      symbol: "7203.T",
      action: "SELL",
      status: "resolved",
      evaluation: {
        evaluatedAt: "2026-08-05T01:00:00.000Z",
        actualReturnPercent: 3,
        hit: true,
      },
    },
  ]);

  assert.equal(result.audit.counts.all, 3);
  assert.equal(result.audit.counts.trade, 2);
  assert.equal(result.audit.counts.noTrade, 1);
  assert.equal(result.audit.tradePerformance.resolved, 1);
  assert.equal(result.audit.tradePerformance.winRate, 100);
});

test("reports reverse strategy from execution-derived Trade Memory", () => {
  const result = auditTradeMemoryAccuracy([
    {
      symbol: "7203.T",
      action: "SELL",
      status: "resolved",
      evaluation: {
        evaluatedAt: "2026-08-05T01:00:00.000Z",
        actualReturnPercent: -4,
        hit: false,
      },
    },
  ]);

  assert.equal(result.audit.reverseStrategy.original.winRate, 0);
  assert.equal(result.audit.reverseStrategy.reversed.winRate, 100);
});
