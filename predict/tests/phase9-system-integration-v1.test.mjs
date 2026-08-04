import test from "node:test";
import assert from "node:assert/strict";

import {
  PaperTradingModeOwnerV1,
  PAPER_TRADING_MODES,
} from "../paper/paper-trading-mode-owner-v1.js";
import { PaperTradingSafetyV1 } from "../paper/paper-trading-safety-v1.js";
import { PaperOrderAuditLogV1 } from "../paper/paper-order-audit-log-v1.js";

function memoryStorage() {
  const data = new Map();
  return {
    getItem(key) { return data.has(key) ? data.get(key) : null; },
    setItem(key, value) { data.set(key, String(value)); },
  };
}

class FakeConnectedOrchestrator {
  constructor() {
    this.submitted = [];
    this.processed = [];
    this.killSwitch = false;
  }

  analyze(input = {}) {
    return {
      id: `cycle-${input.symbol}-${input.price}`,
      symbol: input.symbol,
      state: "ORDER_READY",
      decision: "BUY",
      strategy: { finalScore: input.aiScore ?? 80, confidence: input.confidence ?? 0.9 },
      order: {
        symbol: input.symbol,
        side: "BUY",
        quantity: input.requestedQuantity ?? 10,
        price: input.price,
      },
    };
  }

  submit({ cycleId, timestamp }) {
    const result = {
      cycle: { id: cycleId, state: "ORDER_OPEN" },
      order: { id: `order-${cycleId}`, status: "OPEN", timestamp },
    };
    this.submitted.push(result);
    return structuredClone(result);
  }

  processMarket(snapshot) {
    const result = [{
      execution: { orderId: "paper-order", symbol: snapshot.symbol, side: "BUY" },
      portfolio: { equity: 1001000 },
      tradeMemory: { saved: true, source: "EXECUTION" },
    }];
    this.processed.push(result);
    return structuredClone(result);
  }

  activateKillSwitch() { this.killSwitch = true; return this.getState(); }
  deactivateKillSwitch() { this.killSwitch = false; return this.getState(); }
  getState() { return { killSwitch: this.killSwitch, integrationVersion: "fake-connected" }; }
}

test("Phase9 runtime modes preserve paper-only boundaries end to end", () => {
  const storage = memoryStorage();
  const auditLog = new PaperOrderAuditLogV1({ storage });
  const safety = new PaperTradingSafetyV1({
    maxOrdersPerSession: 5,
    maxHoldingAmount: 500000,
    minConfidence: 0,
    minAiScore: 0,
    allowList: ["7203"],
  });
  const orchestrator = new FakeConnectedOrchestrator();
  const owner = new PaperTradingModeOwnerV1({ orchestrator, safety, auditLog });

  assert.equal(owner.getState().mode, PAPER_TRADING_MODES.DRY_RUN);
  assert.equal(owner.getState().liveExecutionAllowed, false);
  assert.equal(owner.getState().brokerConnected, false);

  const dry = owner.analyze({ symbol: "7203", price: 1000, requestedQuantity: 10 });
  assert.equal(dry.status, "DRY_RUN_READY");
  assert.equal(orchestrator.submitted.length, 0);

  owner.setMode(PAPER_TRADING_MODES.MANUAL_APPROVAL);
  const pending = owner.analyze({ symbol: "7203", price: 1000, requestedQuantity: 10 });
  assert.equal(pending.status, "AWAITING_APPROVAL");
  assert.equal(owner.getPendingApprovals().length, 1);

  const approved = owner.approve({ cycleId: pending.cycle.id, approved: true });
  assert.equal(approved.status, "PAPER_ORDER_SUBMITTED");
  assert.equal(orchestrator.submitted.length, 1);

  owner.setMode(PAPER_TRADING_MODES.AUTO_PAPER);
  const auto = owner.analyze({ symbol: "7203", price: 1010, requestedQuantity: 10 });
  assert.equal(auto.status, "PAPER_ORDER_SUBMITTED");
  assert.equal(orchestrator.submitted.length, 2);

  const duplicate = owner.analyze({ symbol: "7203", price: 1010, requestedQuantity: 10 });
  assert.equal(duplicate.status, "BLOCKED");

  const market = owner.processMarket({ symbol: "7203", bid: 1009, ask: 1011, last: 1010 });
  assert.equal(market.status, "MARKET_PROCESSED");
  assert.equal(market.processed[0].tradeMemory.saved, true);

  owner.setMode(PAPER_TRADING_MODES.OFF);
  const off = owner.analyze({ symbol: "7203", price: 1000 });
  assert.equal(off.status, "BLOCKED");

  const blocked = new PaperTradingModeOwnerV1({
    mode: PAPER_TRADING_MODES.AUTO_PAPER,
    orchestrator: new FakeConnectedOrchestrator(),
    safety: new PaperTradingSafetyV1({ allowList: ["7203"] }),
  }).analyze({ symbol: "6758", price: 1000, requestedQuantity: 10 });
  assert.equal(blocked.status, "BLOCKED");

  const records = auditLog.getRecords();
  assert.ok(records.some((record) => record.type === "DRY_RUN_PROPOSAL_CREATED"));
  assert.ok(records.some((record) => record.type === "PAPER_ORDER_SUBMITTED"));
  assert.ok(records.some((record) => record.type === "MARKET_PROCESSED"));
});
