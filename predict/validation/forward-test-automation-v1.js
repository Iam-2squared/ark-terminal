export const FORWARD_TEST_AUTOMATION_V1 = "forward-test-automation-v1";
export const FORWARD_TEST_MODES = Object.freeze({
  DRY_RUN: "DRY_RUN",
  MANUAL_APPROVAL: "MANUAL_APPROVAL",
  AUTO_PAPER: "AUTO_PAPER",
});

function keyOf(signal = {}) {
  return signal.id ?? `${signal.symbol ?? "UNKNOWN"}|${signal.timestamp ?? signal.signalAt ?? "UNKNOWN"}|${signal.action ?? "NO_TRADE"}`;
}

function normalizeMode(mode) {
  const value = String(mode ?? FORWARD_TEST_MODES.DRY_RUN).toUpperCase();
  if (!Object.values(FORWARD_TEST_MODES).includes(value)) throw new Error(`UNSUPPORTED_FORWARD_TEST_MODE:${value}`);
  return value;
}

export class ForwardTestAutomationV1 {
  constructor({ mode = FORWARD_TEST_MODES.DRY_RUN, now = () => new Date(), marketHours = () => true } = {}) {
    this.mode = normalizeMode(mode);
    this.now = now;
    this.marketHours = marketHours;
    this.killSwitchActive = false;
    this.seen = new Set();
    this.pending = new Map();
    this.events = [];
  }

  setMode(mode) {
    this.mode = normalizeMode(mode);
    return this.getState();
  }

  activateKillSwitch(reason = "MANUAL_KILL_SWITCH") {
    this.killSwitchActive = true;
    this.events.push({ type: "KILL_SWITCH_ACTIVATED", reason, at: this.now().toISOString() });
    return this.getState();
  }

  deactivateKillSwitch() {
    this.killSwitchActive = false;
    this.events.push({ type: "KILL_SWITCH_DEACTIVATED", at: this.now().toISOString() });
    return this.getState();
  }

  submit(signal = {}) {
    const key = keyOf(signal);
    if (this.killSwitchActive) return { status: "BLOCKED", reason: "KILL_SWITCH_ACTIVE", key };
    if (!this.marketHours(this.now(), signal)) return { status: "BLOCKED", reason: "MARKET_CLOSED", key };
    if (this.seen.has(key)) return { status: "BLOCKED", reason: "DUPLICATE_ORDER", key };
    this.seen.add(key);

    if (this.mode === FORWARD_TEST_MODES.DRY_RUN) {
      const event = { type: "DRY_RUN_RECORDED", key, signal, at: this.now().toISOString() };
      this.events.push(event);
      return { status: "DRY_RUN_READY", submitted: false, key, event };
    }

    if (this.mode === FORWARD_TEST_MODES.MANUAL_APPROVAL) {
      const pending = { key, signal, createdAt: this.now().toISOString() };
      this.pending.set(key, pending);
      this.events.push({ type: "APPROVAL_REQUIRED", ...pending });
      return { status: "APPROVAL_REQUIRED", submitted: false, key };
    }

    return this.#paperFill(key, signal);
  }

  approve(key, approved = true) {
    const pending = this.pending.get(key);
    if (!pending) return { status: "BLOCKED", reason: "APPROVAL_NOT_FOUND", key };
    this.pending.delete(key);
    if (!approved) {
      this.events.push({ type: "REJECTED", key, at: this.now().toISOString() });
      return { status: "REJECTED", submitted: false, key };
    }
    if (this.killSwitchActive) return { status: "BLOCKED", reason: "KILL_SWITCH_ACTIVE", key };
    return this.#paperFill(key, pending.signal);
  }

  #paperFill(key, signal) {
    const fill = {
      type: "PAPER_FILL",
      key,
      symbol: signal.symbol,
      action: signal.action,
      quantity: Number(signal.quantity ?? 0),
      price: Number(signal.price ?? 0),
      at: this.now().toISOString(),
    };
    this.events.push(fill);
    return {
      status: "PAPER_FILLED",
      submitted: true,
      liveExecutionAllowed: false,
      brokerConnected: false,
      fill,
      pipeline: ["ORDER", "FILL", "PORTFOLIO", "TRADE_MEMORY", "ACCURACY"],
    };
  }

  dailySummary(date = this.now().toISOString().slice(0, 10)) {
    const rows = this.events.filter((event) => String(event.at ?? "").startsWith(date));
    return {
      version: FORWARD_TEST_AUTOMATION_V1,
      date,
      totalEvents: rows.length,
      paperFills: rows.filter((event) => event.type === "PAPER_FILL").length,
      approvalsPending: this.pending.size,
      killSwitchActive: this.killSwitchActive,
      liveExecutionAllowed: false,
      brokerConnected: false,
    };
  }

  getState() {
    return {
      version: FORWARD_TEST_AUTOMATION_V1,
      mode: this.mode,
      killSwitchActive: this.killSwitchActive,
      pendingApprovals: [...this.pending.values()],
      eventCount: this.events.length,
      liveExecutionAllowed: false,
      brokerConnected: false,
    };
  }
}

export default ForwardTestAutomationV1;
