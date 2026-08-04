import assert from "node:assert/strict";
import test from "node:test";

import {
  clearTradeMemory,
  getTradeMemory,
} from "../trading/trade-memory.js";

import {
  saveProcessedExecutionToTradeMemory,
} from "../trading/execution-trade-memory-v1.js";

import {
  auditTradeMemoryAccuracy,
} from "../analysis/trade-memory-accuracy-v1.js";

function memoryStorage() {
  const values = new Map();

  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    removeItem(key) {
      values.delete(key);
    },
    clear() {
      values.clear();
    },
  };
}

function cycle({ id, decision, score = 75, confidence = 80 } = {}) {
  return {
    id,
    symbol: "7203.T",
    decision,
    strategy: {
      finalScore: score,
      confidence,
      reasons: ["trend aligned"],
    },
    risk: {
      decision: "APPROVE",
      blockers: [],
    },
    order: {
      quantity: 100,
      price: 2500,
    },
  };
}

test("Phase8 persists executions and refreshes Accuracy from stored Trade Memory", () => {
  globalThis.localStorage = memoryStorage();
  globalThis.indexedDB = undefined;
  clearTradeMemory();

  const buy = saveProcessedExecutionToTradeMemory({
    cycle: cycle({
      id: "cycle-buy",
      decision: "BUY",
    }),
    processedResult: {
      execution: {
        id: "fill-buy",
        orderId: "order-buy",
        symbol: "7203.T",
        side: "BUY",
        quantity: 100,
        executionPrice: 2500,
        timestamp: "2026-08-05T00:00:00.000Z",
      },
      transactionCost: {
        totalCost: 120,
      },
      portfolio: {
        equity: 1000000,
      },
    },
    modelVersion: "model-test-v1",
  });

  const sell = saveProcessedExecutionToTradeMemory({
    cycle: cycle({
      id: "cycle-sell",
      decision: "SELL",
      score: 82,
      confidence: 86,
    }),
    processedResult: {
      execution: {
        id: "fill-sell",
        orderId: "order-sell",
        symbol: "7203.T",
        side: "SELL",
        quantity: 100,
        executionPrice: 2600,
        returnPercent: 4,
        pnl: 10000,
        timestamp: "2026-08-05T01:00:00.000Z",
      },
      transactionCost: {
        totalCost: 130,
      },
      portfolio: {
        equity: 1009870,
      },
    },
    modelVersion: "model-test-v1",
  });

  const duplicate = saveProcessedExecutionToTradeMemory({
    cycle: cycle({
      id: "cycle-sell",
      decision: "SELL",
    }),
    processedResult: {
      execution: {
        id: "fill-sell",
        orderId: "order-sell",
        symbol: "7203.T",
        side: "SELL",
        quantity: 100,
        executionPrice: 2600,
        returnPercent: 4,
        pnl: 10000,
        timestamp: "2026-08-05T01:00:00.000Z",
      },
      transactionCost: {
        totalCost: 130,
      },
      portfolio: {
        equity: 1009870,
      },
    },
    modelVersion: "model-test-v1",
  });

  assert.equal(buy.saved, true);
  assert.equal(sell.saved, true);
  assert.equal(duplicate.saved, false);
  assert.equal(duplicate.duplicate, true);

  const stored = getTradeMemory();
  assert.equal(stored.length, 2);
  assert.equal(stored[0].liveExecutionAllowed, false);
  assert.equal(stored[1].modelVersion, "model-test-v1");

  const accuracy = auditTradeMemoryAccuracy(stored);

  assert.equal(accuracy.audit.counts.trade, 2);
  assert.equal(accuracy.audit.counts.pending, 1);
  assert.equal(accuracy.audit.tradePerformance.resolved, 1);
  assert.equal(accuracy.audit.tradePerformance.winRate, 100);
  assert.equal(accuracy.audit.tradePerformance.profitFactor, "Infinity");
});

test("Phase8 skips market snapshots that contain no execution", () => {
  globalThis.localStorage = memoryStorage();
  globalThis.indexedDB = undefined;
  clearTradeMemory();

  const result = saveProcessedExecutionToTradeMemory({
    cycle: cycle({
      id: "cycle-no-fill",
      decision: "BUY",
    }),
    processedResult: {
      order: {
        status: "OPEN",
      },
    },
  });

  assert.equal(result.skipped, true);
  assert.equal(result.reason, "NO_EXECUTION");
  assert.equal(getTradeMemory().length, 0);
});
