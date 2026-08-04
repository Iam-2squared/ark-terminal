import {
  TradeMemoryConnectedOrchestratorV1,
} from "./trade-memory-connected-orchestrator-v1.js";

export const PAPER_TRADING_MODE_OWNER_V1_VERSION =
  "paper-trading-mode-owner-v1";

export const PAPER_TRADING_MODES =
  Object.freeze({
    OFF: "OFF",
    DRY_RUN: "DRY_RUN",
    MANUAL_APPROVAL: "MANUAL_APPROVAL",
    AUTO_PAPER: "AUTO_PAPER",
  });

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function normalizeMode(value) {
  const mode = String(value ?? "")
    .trim()
    .toUpperCase();

  if (!Object.values(PAPER_TRADING_MODES).includes(mode)) {
    throw new TypeError(`Unsupported paper trading mode: ${value}`);
  }

  return mode;
}

export class PaperTradingModeOwnerV1 {
  constructor({
    mode = PAPER_TRADING_MODES.DRY_RUN,
    orchestrator = null,
    orchestratorOptions = {},
    safety = null,
    auditLog = null,
  } = {}) {
    this.mode = normalizeMode(mode);
    this.orchestrator =
      orchestrator ??
      new TradeMemoryConnectedOrchestratorV1(
        orchestratorOptions,
      );
    this.safety = safety;
    this.auditLog = auditLog;
    this.pendingApprovals = new Map();
  }

  setMode(mode) {
    this.mode = normalizeMode(mode);
    this.#audit("MODE_CHANGED", { mode: this.mode });
    return this.getState();
  }

  analyze(input = {}) {
    if (this.mode === PAPER_TRADING_MODES.OFF) {
      const result = {
        mode: this.mode,
        status: "BLOCKED",
        blockers: ["PAPER_TRADING_OFF"],
        cycle: null,
      };
      this.#audit("ANALYSIS_BLOCKED", result);
      return clone(result);
    }

    const cycle = this.orchestrator.analyze(input);

    if (!cycle?.order) {
      const result = {
        mode: this.mode,
        status: cycle?.state ?? "NO_ORDER",
        cycle,
        submitted: false,
      };
      this.#audit("ANALYSIS_COMPLETED", result);
      return clone(result);
    }

    const safetyResult = this.safety
      ? this.safety.evaluate({
          cycle,
          ownerState: this.getState(),
          timestamp: input.timestamp,
        })
      : { allowed: true, blockers: [] };

    if (!safetyResult.allowed) {
      const result = {
        mode: this.mode,
        status: "BLOCKED",
        cycle,
        safety: safetyResult,
        submitted: false,
      };
      this.#audit("ORDER_BLOCKED_BY_RUNTIME_SAFETY", result);
      return clone(result);
    }

    if (this.mode === PAPER_TRADING_MODES.DRY_RUN) {
      const result = {
        mode: this.mode,
        status: "DRY_RUN_READY",
        cycle,
        safety: safetyResult,
        submitted: false,
      };
      this.#audit("DRY_RUN_PROPOSAL_CREATED", result);
      return clone(result);
    }

    if (this.mode === PAPER_TRADING_MODES.MANUAL_APPROVAL) {
      this.pendingApprovals.set(cycle.id, {
        cycleId: cycle.id,
        createdAt: input.timestamp ?? new Date().toISOString(),
        symbol: cycle.symbol,
        order: clone(cycle.order),
      });

      const result = {
        mode: this.mode,
        status: "AWAITING_APPROVAL",
        cycle,
        safety: safetyResult,
        submitted: false,
      };
      this.#audit("MANUAL_APPROVAL_REQUESTED", result);
      return clone(result);
    }

    return this.#submitCycle(cycle.id, input.timestamp, safetyResult);
  }

  approve({ cycleId, approved = true, timestamp = new Date().toISOString() } = {}) {
    if (this.mode !== PAPER_TRADING_MODES.MANUAL_APPROVAL) {
      throw new Error("Manual approval is only available in MANUAL_APPROVAL mode.");
    }

    const pending = this.pendingApprovals.get(cycleId);
    if (!pending) {
      throw new Error(`Pending approval not found: ${cycleId}`);
    }

    this.pendingApprovals.delete(cycleId);

    if (!approved) {
      const result = {
        mode: this.mode,
        status: "REJECTED",
        cycleId,
        submitted: false,
      };
      this.#audit("MANUAL_APPROVAL_REJECTED", result, timestamp);
      return clone(result);
    }

    return this.#submitCycle(cycleId, timestamp, { allowed: true, blockers: [] });
  }

  processMarket(snapshot = {}) {
    if ([PAPER_TRADING_MODES.OFF, PAPER_TRADING_MODES.DRY_RUN].includes(this.mode)) {
      const result = {
        mode: this.mode,
        status: "MARKET_PROCESSING_SKIPPED",
        processed: [],
      };
      this.#audit("MARKET_PROCESSING_SKIPPED", result, snapshot.timestamp);
      return clone(result);
    }

    const processed = this.orchestrator.processMarket(snapshot);
    const result = {
      mode: this.mode,
      status: "MARKET_PROCESSED",
      processed,
    };
    this.#audit("MARKET_PROCESSED", result, snapshot.timestamp);
    return clone(result);
  }

  activateKillSwitch(reason = "MANUAL_KILL_SWITCH") {
    const state = this.orchestrator.activateKillSwitch(reason);
    this.#audit("KILL_SWITCH_ACTIVATED", { reason });
    return state;
  }

  deactivateKillSwitch() {
    const state = this.orchestrator.deactivateKillSwitch();
    this.#audit("KILL_SWITCH_DEACTIVATED", {});
    return state;
  }

  getPendingApprovals() {
    return clone(Array.from(this.pendingApprovals.values()));
  }

  getState() {
    return {
      version: PAPER_TRADING_MODE_OWNER_V1_VERSION,
      mode: this.mode,
      liveExecutionAllowed: false,
      brokerConnected: false,
      pendingApprovalCount: this.pendingApprovals.size,
      orchestrator: this.orchestrator.getState?.() ?? null,
    };
  }

  #submitCycle(cycleId, timestamp, safety) {
    const submission = this.orchestrator.submit({ cycleId, timestamp });
    this.safety?.recordSubmission?.({
      cycleId,
      order: submission.order,
      timestamp,
    });

    const result = {
      mode: this.mode,
      status: "PAPER_ORDER_SUBMITTED",
      cycle: submission.cycle,
      order: submission.order,
      safety,
      submitted: true,
      liveExecutionAllowed: false,
    };
    this.#audit("PAPER_ORDER_SUBMITTED", result, timestamp);
    return clone(result);
  }

  #audit(type, data = {}, timestamp = new Date().toISOString()) {
    this.auditLog?.append?.({
      type,
      data: clone(data),
      timestamp,
      mode: this.mode,
    });
  }
}

export default PaperTradingModeOwnerV1;
