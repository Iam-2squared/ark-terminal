import {
  PAPER_TRADING_MODES,
  PaperTradingModeOwnerV1,
} from "./paper-trading-mode-owner-v1.js";

export const PAPER_TRADING_FINAL_V1 = "paper-trading-final-v1";

function clone(value) {
  return value === undefined ? undefined : structuredClone(value);
}

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function portfolioSnapshot(orchestratorState = {}) {
  const portfolio = orchestratorState.portfolio ?? orchestratorState.account ?? {};
  const positions = Array.isArray(portfolio.positions)
    ? portfolio.positions
    : Array.isArray(orchestratorState.positions)
      ? orchestratorState.positions
      : [];

  return {
    cash: finite(portfolio.cash ?? orchestratorState.cash),
    equity: finite(portfolio.equity ?? portfolio.totalValue ?? orchestratorState.equity),
    realizedPnl: finite(portfolio.realizedPnl ?? orchestratorState.realizedPnl),
    unrealizedPnl: finite(portfolio.unrealizedPnl ?? orchestratorState.unrealizedPnl),
    positionCount: positions.length,
    positions: clone(positions),
  };
}

export class PaperTradingFinalV1 {
  constructor({ owner = null, ownerOptions = {} } = {}) {
    this.owner = owner ?? new PaperTradingModeOwnerV1(ownerOptions);
    this.lastResult = null;
  }

  setMode(mode) {
    const state = this.owner.setMode(mode);
    this.lastResult = { type: "MODE_CHANGED", state };
    return this.getView();
  }

  analyze(input = {}) {
    this.lastResult = this.owner.analyze(input);
    return {
      result: clone(this.lastResult),
      view: this.getView(),
    };
  }

  approve(cycleId, approved = true, timestamp = new Date().toISOString()) {
    this.lastResult = this.owner.approve({ cycleId, approved, timestamp });
    return {
      result: clone(this.lastResult),
      view: this.getView(),
    };
  }

  processMarket(snapshot = {}) {
    this.lastResult = this.owner.processMarket(snapshot);
    return {
      result: clone(this.lastResult),
      view: this.getView(),
    };
  }

  activateKillSwitch(reason = "MANUAL_KILL_SWITCH") {
    this.owner.activateKillSwitch(reason);
    this.lastResult = { status: "KILL_SWITCH_ACTIVE", reason };
    return this.getView();
  }

  deactivateKillSwitch() {
    this.owner.deactivateKillSwitch();
    this.lastResult = { status: "KILL_SWITCH_INACTIVE" };
    return this.getView();
  }

  getView() {
    const state = this.owner.getState();
    const orchestrator = state.orchestrator ?? {};
    const pendingApprovals = this.owner.getPendingApprovals?.() ?? [];
    const killSwitchActive = Boolean(
      orchestrator.killSwitchActive ??
      orchestrator.killSwitch?.active ??
      orchestrator.risk?.killSwitchActive,
    );

    return {
      version: PAPER_TRADING_FINAL_V1,
      mode: state.mode,
      status: this.lastResult?.status ?? "READY",
      liveExecutionAllowed: false,
      brokerConnected: false,
      controls: {
        canAnalyze: state.mode !== PAPER_TRADING_MODES.OFF && !killSwitchActive,
        canApprove: state.mode === PAPER_TRADING_MODES.MANUAL_APPROVAL && pendingApprovals.length > 0,
        canProcessMarket: [
          PAPER_TRADING_MODES.MANUAL_APPROVAL,
          PAPER_TRADING_MODES.AUTO_PAPER,
        ].includes(state.mode) && !killSwitchActive,
        killSwitchActive,
      },
      pendingApprovals: clone(pendingApprovals),
      portfolio: portfolioSnapshot(orchestrator),
      lastResult: clone(this.lastResult),
      safetyNotice:
        "Paper Trading専用です。実際の証券口座・発注APIには接続されません。",
      mobileReady: true,
    };
  }
}

export default PaperTradingFinalV1;
