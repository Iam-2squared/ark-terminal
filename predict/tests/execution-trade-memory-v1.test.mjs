import assert from "node:assert/strict";
import test from "node:test";

import {
  createExecutionTradeMemoryRecord,
  saveProcessedExecutionToTradeMemory,
} from "../trading/execution-trade-memory-v1.js";

function memoryStorage() {
  const values = new Map();

  return {
    getItem(key) {
      return values.has(key)
        ? values.get(key)
        : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    removeItem(key) {
      values.delete(key);
    },
  };
}

function sampleCycle() {
  return {
    id: "TRADE-CYCLE-00000001",
    symbol: "7203.T",
    decision: "BUY",
    executionOrderId: "ORDER-1",
    order: {
      quantity: 100,
      price: 2500,
    },
    strategy: {
      finalScore: 78,
      confidence: 82,
      reasons: ["trend", "volume"],
    },
    risk: {
      decision: "APPROVE",
      approvedQuantity: 100,
    },
  };
}

function sampleProcessedResult() {
  return {
    execution: {
      id: "EXEC-1",
      orderId: "ORDER-1",
      symbol: "7203.T",
      side: "BUY",
      quantity: 100,
      executionPrice: 2501,
      timestamp: "2026-08-05T00:00:00.000Z",
    },
    transactionCost: {
      totalCost: 120,
    },
    portfolio: {
      equity: 999880,
    },
  };
}

test("creates an execution-derived Trade Memory record", () => {
  const record = createExecutionTradeMemoryRecord({
    cycle: sampleCycle(),
    execution: sampleProcessedResult().execution,
    transactionCost: sampleProcessedResult().transactionCost,
    portfolio: sampleProcessedResult().portfolio,
    modelVersion: "model-v1",
  });

  assert.equal(record.symbol, "7203.T");
  assert.equal(record.action, "BUY");
  assert.equal(record.quantity, 100);
  assert.equal(record.entryPrice, 2501);
  assert.equal(record.aiScore, 78);
  assert.equal(record.confidence, 82);
  assert.equal(record.modelVersion, "model-v1");
  assert.equal(record.liveExecutionAllowed, false);
});

test("saves an execution once and rejects duplicates", () => {
  globalThis.localStorage = memoryStorage();

  const first = saveProcessedExecutionToTradeMemory({
    cycle: sampleCycle(),
    processedResult: sampleProcessedResult(),
    modelVersion: "model-v1",
  });

  const second = saveProcessedExecutionToTradeMemory({
    cycle: sampleCycle(),
    processedResult: sampleProcessedResult(),
    modelVersion: "model-v1",
  });

  assert.equal(first.saved, true);
  assert.equal(first.skipped, false);
  assert.equal(second.saved, false);
  assert.equal(second.duplicate, true);
});

test("skips market processing results without an execution", () => {
  const result = saveProcessedExecutionToTradeMemory({
    cycle: sampleCycle(),
    processedResult: {
      order: {
        status: "OPEN",
      },
    },
  });

  assert.equal(result.saved, false);
  assert.equal(result.skipped, true);
  assert.equal(result.reason, "NO_EXECUTION");
});

test("records SELL fills as resolved exits", () => {
  const record = createExecutionTradeMemoryRecord({
    cycle: {
      ...sampleCycle(),
      decision: "SELL",
    },
    execution: {
      ...sampleProcessedResult().execution,
      id: "EXEC-2",
      side: "SELL",
      executionPrice: 2600,
      pnl: 9900,
      returnPercent: 3.96,
    },
  });

  assert.equal(record.status, "resolved");
  assert.equal(record.exitPrice, 2600);
  assert.equal(record.pnl, 9900);
  assert.equal(record.evaluation.hit, true);
  assert.equal(record.evaluation.actualReturnPercent, 3.96);
});
