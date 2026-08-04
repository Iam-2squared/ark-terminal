import test from "node:test";
import assert from "node:assert/strict";

import {
  PAPER_TRADING_MODES,
  PaperTradingModeOwnerV1,
} from "../paper/paper-trading-mode-owner-v1.js";

import {
  PaperTradingSafetyV1,
} from "../paper/paper-trading-safety-v1.js";

import {
  PaperOrderAuditLogV1,
} from "../paper/paper-order-audit-log-v1.js";

class IntegratedFakeOrchestrator {
  constructor() {
    this.submitted = [];
    this.processed = [];
  }

  analyze() {
    return {
      id: "cycle-int-1",
      state: "ORDER_READY",
      symbol: "7203.T",
      decision: "BUY",
      strategy: {
        confidence: 88,
        finalScore: 82,
      },
      order: {
        symbol: "7203.T",
        side: "BUY",
        quantity: 10,
        price: 100,
      },
    };
  }

  submit({ cycleId, timestamp }) {
    const result = {
      cycle: {
        id: cycleId,
        state: "ORDER_OPEN",
      },
      order: {
        id: "paper-order-int-1",
        symbol: "7203.T",
        side: "BUY",
        quantity: 10,
        timestamp,
      },
    };
    this.submitted.push(result);
    return result;
  }

  processMarket(snapshot) {
    const result = {
      execution: {
        orderId: "paper-order-int-1",
        symbol: "7203.T",
        side: "BUY",
        quantity: 10,
        executionPrice: 101,
      },
      portfolio: {
        cash: 998990,
        positions: [{ symbol: "7203.T", quantity: 10 }],
      },
      tradeMemory: {
        saved: true,
        duplicate: false,
      },
    };
    this.processed.push({ snapshot, result });
    return [result];
  }

  getState() {
    return {
      killSwitch: false,
      liveExecutionAllowed: false,
    };
  }

  activateKillSwitch(reason) {
    return { killSwitch: true, reason };
  }

  deactivateKillSwitch() {
    return { killSwitch: false };
  }
}

test("AUTO_PAPER connects mode, safety, execution, portfolio result, Trade Memory result, and audit log", () => {
  const data = new Map();
  const storage = {
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
  };

  const auditLog = new PaperOrderAuditLogV1({ storage });
  const safety = new PaperTradingSafetyV1({
    maxOrdersPerSession: 5,
    maxHoldingAmount: 10000,
    minConfidence: 70,
    minAiScore: 70,
    allowList: ["7203.T"],
  });
  const orchestrator = new IntegratedFakeOrchestrator();
  const owner = new PaperTradingModeOwnerV1({
    mode: PAPER_TRADING_MODES.AUTO_PAPER,
    orchestrator,
    safety,
    auditLog,
  });

  const analysis = owner.analyze({
    symbol: "7203.T",
    price: 100,
    timestamp: "2026-08-04T00:00:00.000Z",
  });

  assert.equal(analysis.submitted, true);
  assert.equal(orchestrator.submitted.length, 1);
  assert.equal(safety.getState().submissionCount, 1);

  const market = owner.processMarket({
    symbol: "7203.T",
    bid: 100,
    ask: 101,
    last: 101,
    timestamp: "2026-08-04T00:01:00.000Z",
  });

  assert.equal(market.processed.length, 1);
  assert.equal(market.processed[0].portfolio.positions[0].quantity, 10);
  assert.equal(market.processed[0].tradeMemory.saved, true);

  const types = auditLog.getRecords().map((record) => record.type);
  assert.ok(types.includes("PAPER_ORDER_SUBMITTED"));
  assert.ok(types.includes("MARKET_PROCESSED"));
  assert.equal(owner.getState().liveExecutionAllowed, false);
  assert.equal(owner.getState().brokerConnected, false);
});
