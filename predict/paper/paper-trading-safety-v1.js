export const PAPER_TRADING_SAFETY_V1_VERSION =
  "paper-trading-safety-v1";

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalizedSymbol(value) {
  return String(value ?? "").trim().toUpperCase();
}

function orderKey(cycle = {}) {
  const order = cycle.order ?? {};
  return [
    normalizedSymbol(cycle.symbol ?? order.symbol),
    String(order.side ?? cycle.decision ?? "").toUpperCase(),
    finite(order.quantity),
    finite(order.price),
  ].join("|");
}

export class PaperTradingSafetyV1 {
  constructor({
    maxOrdersPerSession = 20,
    maxHoldingAmount = 300000,
    minConfidence = 0,
    minAiScore = 0,
    allowList = [],
    enforceMarketHours = false,
    marketOpenHourJst = 9,
    marketCloseHourJst = 15,
    anomalyDetector = null,
  } = {}) {
    this.config = {
      maxOrdersPerSession: Math.max(0, Math.floor(finite(maxOrdersPerSession, 20))),
      maxHoldingAmount: Math.max(0, finite(maxHoldingAmount, 300000)),
      minConfidence: finite(minConfidence, 0),
      minAiScore: finite(minAiScore, 0),
      allowList: new Set(allowList.map(normalizedSymbol).filter(Boolean)),
      enforceMarketHours: Boolean(enforceMarketHours),
      marketOpenHourJst: finite(marketOpenHourJst, 9),
      marketCloseHourJst: finite(marketCloseHourJst, 15),
    };
    this.anomalyDetector = anomalyDetector;
    this.submissions = [];
    this.submittedKeys = new Set();
  }

  evaluate({ cycle = {}, ownerState = {}, timestamp = new Date().toISOString() } = {}) {
    const blockers = [];
    const order = cycle.order ?? {};
    const symbol = normalizedSymbol(cycle.symbol ?? order.symbol);
    const confidence = finite(cycle.strategy?.confidence, 0);
    const aiScore = finite(cycle.strategy?.finalScore ?? cycle.strategy?.score, 0);
    const holdingAmount = finite(order.quantity) * finite(order.price);
    const key = orderKey(cycle);

    if (ownerState?.orchestrator?.killSwitch) blockers.push("KILL_SWITCH_ACTIVE");
    if (this.submissions.length >= this.config.maxOrdersPerSession) blockers.push("MAX_ORDER_COUNT_REACHED");
    if (holdingAmount > this.config.maxHoldingAmount) blockers.push("MAX_HOLDING_AMOUNT_EXCEEDED");
    if (confidence < this.config.minConfidence) blockers.push("CONFIDENCE_BELOW_MINIMUM");
    if (aiScore < this.config.minAiScore) blockers.push("AI_SCORE_BELOW_MINIMUM");
    if (this.config.allowList.size > 0 && !this.config.allowList.has(symbol)) blockers.push("SYMBOL_NOT_ALLOWED");
    if (this.submittedKeys.has(key)) blockers.push("DUPLICATE_ORDER");
    if (this.config.enforceMarketHours && !this.#isMarketHours(timestamp)) blockers.push("OUTSIDE_MARKET_HOURS");

    const anomaly = this.anomalyDetector?.({ cycle, timestamp }) ?? null;
    if (anomaly === true || anomaly?.stop === true) blockers.push("ANOMALY_STOP");

    return {
      version: PAPER_TRADING_SAFETY_V1_VERSION,
      allowed: blockers.length === 0,
      blockers,
      checks: {
        orderCount: this.submissions.length,
        holdingAmount,
        confidence,
        aiScore,
        symbol,
        duplicateKey: key,
      },
    };
  }

  recordSubmission({ cycleId = null, order = {}, timestamp = new Date().toISOString() } = {}) {
    const cycle = {
      id: cycleId,
      symbol: order.symbol,
      decision: order.side,
      order,
    };
    const key = orderKey(cycle);
    this.submittedKeys.add(key);
    this.submissions.push({ cycleId, order: structuredClone(order), key, timestamp });
    return this.getState();
  }

  resetSession() {
    this.submissions = [];
    this.submittedKeys.clear();
    return this.getState();
  }

  getState() {
    return {
      version: PAPER_TRADING_SAFETY_V1_VERSION,
      submissionCount: this.submissions.length,
      submittedKeys: Array.from(this.submittedKeys),
      config: {
        ...this.config,
        allowList: Array.from(this.config.allowList),
      },
    };
  }

  #isMarketHours(timestamp) {
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return false;
    const jst = new Date(date.getTime() + 9 * 60 * 60 * 1000);
    const day = jst.getUTCDay();
    const hour = jst.getUTCHours() + jst.getUTCMinutes() / 60;
    return day >= 1 && day <= 5 && hour >= this.config.marketOpenHourJst && hour < this.config.marketCloseHourJst;
  }
}

export default PaperTradingSafetyV1;
