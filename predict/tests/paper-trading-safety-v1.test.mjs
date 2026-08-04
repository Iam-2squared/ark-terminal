import test from "node:test";
import assert from "node:assert/strict";

import {
  PaperTradingSafetyV1,
} from "../paper/paper-trading-safety-v1.js";

import {
  PaperOrderAuditLogV1,
} from "../paper/paper-order-audit-log-v1.js";

function cycle(overrides = {}) {
  return {
    id: "cycle-1",
    symbol: "7203.T",
    decision: "BUY",
    strategy: {
      confidence: 80,
      finalScore: 75,
    },
    order: {
      symbol: "7203.T",
      side: "BUY",
      quantity: 10,
      price: 100,
    },
    ...overrides,
  };
}

test("safety allows a valid paper proposal", () => {
  const safety = new PaperTradingSafetyV1({
    maxOrdersPerSession: 2,
    maxHoldingAmount: 5000,
    minConfidence: 60,
    minAiScore: 60,
    allowList: ["7203.T"],
  });

  const result = safety.evaluate({ cycle: cycle() });
  assert.equal(result.allowed, true);
  assert.deepEqual(result.blockers, []);
});

test("safety blocks amount, confidence, score, allow-list, duplicate, and order-count violations", () => {
  const safety = new PaperTradingSafetyV1({
    maxOrdersPerSession: 1,
    maxHoldingAmount: 500,
    minConfidence: 90,
    minAiScore: 90,
    allowList: ["6758.T"],
  });

  const first = safety.evaluate({ cycle: cycle() });
  assert.equal(first.allowed, false);
  assert.ok(first.blockers.includes("MAX_HOLDING_AMOUNT_EXCEEDED"));
  assert.ok(first.blockers.includes("CONFIDENCE_BELOW_MINIMUM"));
  assert.ok(first.blockers.includes("AI_SCORE_BELOW_MINIMUM"));
  assert.ok(first.blockers.includes("SYMBOL_NOT_ALLOWED"));

  safety.recordSubmission({
    cycleId: "cycle-1",
    order: cycle().order,
  });

  const second = safety.evaluate({ cycle: cycle() });
  assert.ok(second.blockers.includes("MAX_ORDER_COUNT_REACHED"));
  assert.ok(second.blockers.includes("DUPLICATE_ORDER"));
});

test("market-hours and anomaly stop are enforceable", () => {
  const safety = new PaperTradingSafetyV1({
    enforceMarketHours: true,
    anomalyDetector: () => ({ stop: true }),
  });

  const result = safety.evaluate({
    cycle: cycle(),
    timestamp: "2026-08-02T03:00:00.000Z",
  });

  assert.ok(result.blockers.includes("OUTSIDE_MARKET_HOURS"));
  assert.ok(result.blockers.includes("ANOMALY_STOP"));
});

test("audit log persists and reloads records", () => {
  const data = new Map();
  const storage = {
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
  };

  const first = new PaperOrderAuditLogV1({ storage });
  first.append({
    type: "PAPER_ORDER_SUBMITTED",
    mode: "AUTO_PAPER",
    timestamp: "2026-08-04T00:00:00.000Z",
    data: { symbol: "7203.T" },
  });

  const second = new PaperOrderAuditLogV1({ storage });
  const records = second.getRecords();
  assert.equal(records.length, 1);
  assert.equal(records[0].type, "PAPER_ORDER_SUBMITTED");
  assert.equal(records[0].data.symbol, "7203.T");
});
