import test from "node:test";
import assert from "node:assert/strict";

import {
  PAPER_TRADING_MODES,
  PaperTradingModeOwnerV1,
} from "../paper/paper-trading-mode-owner-v1.js";

import {
  TradeMemoryConnectedOrchestratorV1,
} from "../paper/trade-memory-connected-orchestrator-v1.js";

class FakeOrchestrator {
  constructor() {
    this.submissions = [];
    this.marketCalls = [];
    this.killSwitch = false;
  }

  analyze(input = {}) {
    return {
      id: "cycle-1",
      state: "ORDER_READY",
      symbol: input.symbol ?? "7203.T",
      decision: "BUY",
      strategy: {
        confidence: 80,
        finalScore: 75,
      },
      order: {
        symbol: input.symbol ?? "7203.T",
        side: "BUY",
        quantity: 10,
        price: input.price ?? 100,
      },
    };
  }

  submit({ cycleId, timestamp }) {
    const submission = {
      cycle: { id: cycleId, state: "ORDER_OPEN" },
      order: {
        id: `order-${this.submissions.length + 1}`,
        symbol: "7203.T",
        side: "BUY",
        quantity: 10,
        timestamp,
      },
    };
    this.submissions.push(submission);
    return submission;
  }

  processMarket(snapshot) {
    this.marketCalls.push(snapshot);
    return [{ execution: { orderId: "order-1", symbol: "7203.T" } }];
  }

  activateKillSwitch(reason) {
    this.killSwitch = true;
    return { killSwitch: true, killSwitchReason: reason };
  }

  deactivateKillSwitch() {
    this.killSwitch = false;
    return { killSwitch: false };
  }

  getState() {
    return { killSwitch: this.killSwitch };
  }
}

function createOwner(mode) {
  return new PaperTradingModeOwnerV1({
    mode,
    orchestrator: new FakeOrchestrator(),
  });
}

test("default mode is DRY_RUN and uses the existing connected orchestrator", () => {
  const owner = new PaperTradingModeOwnerV1();
  assert.equal(owner.getState().mode, PAPER_TRADING_MODES.DRY_RUN);
  assert.equal(owner.getState().liveExecutionAllowed, false);
  assert.equal(owner.getState().brokerConnected, false);
  assert.ok(owner.orchestrator instanceof TradeMemoryConnectedOrchestratorV1);
});

test("OFF blocks analysis and creates no proposal", () => {
  const owner = createOwner(PAPER_TRADING_MODES.OFF);
  const result = owner.analyze({ symbol: "7203.T", price: 100 });
  assert.equal(result.status, "BLOCKED");
  assert.deepEqual(result.blockers, ["PAPER_TRADING_OFF"]);
  assert.equal(owner.orchestrator.submissions.length, 0);
});

test("DRY_RUN analyzes but never submits or processes fills", () => {
  const owner = createOwner(PAPER_TRADING_MODES.DRY_RUN);
  const result = owner.analyze({ symbol: "7203.T", price: 100 });
  assert.equal(result.status, "DRY_RUN_READY");
  assert.equal(result.submitted, false);
  assert.equal(owner.orchestrator.submissions.length, 0);

  const market = owner.processMarket({ symbol: "7203.T", last: 101 });
  assert.equal(market.status, "MARKET_PROCESSING_SKIPPED");
  assert.equal(owner.orchestrator.marketCalls.length, 0);
});

test("MANUAL_APPROVAL queues and submits only after approval", () => {
  const owner = createOwner(PAPER_TRADING_MODES.MANUAL_APPROVAL);
  const result = owner.analyze({ symbol: "7203.T", price: 100 });
  assert.equal(result.status, "AWAITING_APPROVAL");
  assert.equal(owner.getPendingApprovals().length, 1);
  assert.equal(owner.orchestrator.submissions.length, 0);

  const approved = owner.approve({ cycleId: "cycle-1", approved: true });
  assert.equal(approved.status, "PAPER_ORDER_SUBMITTED");
  assert.equal(owner.getPendingApprovals().length, 0);
  assert.equal(owner.orchestrator.submissions.length, 1);
});

test("MANUAL_APPROVAL rejection never submits", () => {
  const owner = createOwner(PAPER_TRADING_MODES.MANUAL_APPROVAL);
  owner.analyze({ symbol: "7203.T", price: 100 });
  const rejected = owner.approve({ cycleId: "cycle-1", approved: false });
  assert.equal(rejected.status, "REJECTED");
  assert.equal(owner.orchestrator.submissions.length, 0);
});

test("AUTO_PAPER submits and forwards market snapshots to paper execution", () => {
  const owner = createOwner(PAPER_TRADING_MODES.AUTO_PAPER);
  const result = owner.analyze({ symbol: "7203.T", price: 100 });
  assert.equal(result.status, "PAPER_ORDER_SUBMITTED");
  assert.equal(result.liveExecutionAllowed, false);
  assert.equal(owner.orchestrator.submissions.length, 1);

  const market = owner.processMarket({ symbol: "7203.T", last: 101 });
  assert.equal(market.status, "MARKET_PROCESSED");
  assert.equal(owner.orchestrator.marketCalls.length, 1);
});
