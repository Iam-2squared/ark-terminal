import test from "node:test";
import assert from "node:assert/strict";

import { PaperTradingFinalV1 } from "../paper/paper-trading-final-v1.js";

class OwnerStub {
  constructor() {
    this.mode = "DRY_RUN";
    this.pending = [];
    this.kill = false;
  }

  setMode(mode) {
    this.mode = mode;
    return this.getState();
  }

  analyze() {
    return { status: "DRY_RUN_READY", submitted: false };
  }

  approve({ cycleId, approved }) {
    return { status: approved ? "PAPER_ORDER_SUBMITTED" : "REJECTED", cycleId };
  }

  processMarket() {
    return { status: "MARKET_PROCESSED", processed: [] };
  }

  activateKillSwitch() {
    this.kill = true;
  }

  deactivateKillSwitch() {
    this.kill = false;
  }

  getPendingApprovals() {
    return structuredClone(this.pending);
  }

  getState() {
    return {
      mode: this.mode,
      liveExecutionAllowed: false,
      brokerConnected: false,
      orchestrator: {
        killSwitchActive: this.kill,
        portfolio: {
          cash: 90000,
          equity: 101000,
          realizedPnl: 500,
          unrealizedPnl: 1000,
          positions: [{ symbol: "7203.T", quantity: 100 }],
        },
      },
    };
  }
}

test("paper trading final exposes a paper-only mobile view", () => {
  const terminal = new PaperTradingFinalV1({ owner: new OwnerStub() });
  const view = terminal.getView();

  assert.equal(view.version, "paper-trading-final-v1");
  assert.equal(view.liveExecutionAllowed, false);
  assert.equal(view.brokerConnected, false);
  assert.equal(view.mobileReady, true);
  assert.equal(view.portfolio.positionCount, 1);
  assert.equal(view.controls.canAnalyze, true);
});

test("manual approval and kill switch controls are reflected", () => {
  const owner = new OwnerStub();
  owner.pending = [{ cycleId: "cycle-1" }];
  const terminal = new PaperTradingFinalV1({ owner });

  let view = terminal.setMode("MANUAL_APPROVAL");
  assert.equal(view.controls.canApprove, true);

  view = terminal.activateKillSwitch("test");
  assert.equal(view.controls.killSwitchActive, true);
  assert.equal(view.controls.canAnalyze, false);
  assert.equal(view.controls.canProcessMarket, false);
});

test("actions return both the result and refreshed view", () => {
  const terminal = new PaperTradingFinalV1({ owner: new OwnerStub() });
  const output = terminal.analyze({ symbol: "7203.T" });

  assert.equal(output.result.status, "DRY_RUN_READY");
  assert.equal(output.view.status, "DRY_RUN_READY");
});
