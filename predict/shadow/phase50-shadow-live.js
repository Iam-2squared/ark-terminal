import crypto from "node:crypto";

export const PHASE50_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function finite(value, field) {
  const n = Number(value);
  if (!Number.isFinite(n)) throw new TypeError(`${field} must be finite`);
  return n;
}

function iso(value) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) throw new TypeError("timestamp must be valid");
  return d.toISOString();
}

function hash(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

export function normalizeShadowSnapshot(input = {}) {
  const symbol = String(input.symbol ?? "").trim().toUpperCase();
  if (!symbol) throw new TypeError("symbol is required");
  const bid = finite(input.bid, "bid");
  const ask = finite(input.ask, "ask");
  const last = finite(input.last, "last");
  if (bid <= 0 || ask <= 0 || last <= 0) throw new RangeError("prices must be positive");
  if (bid > ask) throw new RangeError("bid must not exceed ask");

  return Object.freeze({
    symbol,
    observedAt: iso(input.observedAt ?? Date.now()),
    bid,
    ask,
    last,
    volume: Math.max(0, finite(input.volume ?? 0, "volume")),
    source: String(input.source ?? "MARKETSPEED_RSS_READ_ONLY"),
    readOnly: true,
  });
}

export function buildShadowDecision({ snapshot, signal = {}, quantity = 100 } = {}) {
  const s = normalizeShadowSnapshot(snapshot);
  const side = String(signal.side ?? "HOLD").toUpperCase();
  if (!["BUY", "SELL", "HOLD"].includes(side)) throw new TypeError("unsupported side");
  const confidence = Math.max(0, Math.min(1, finite(signal.confidence ?? 0, "confidence")));
  const expectedReturn = finite(signal.expectedReturn ?? 0, "expectedReturn");
  const qty = Math.max(0, Math.floor(finite(quantity, "quantity")));
  const referencePrice = side === "BUY" ? s.ask : side === "SELL" ? s.bid : s.last;

  const decision = {
    mode: "SHADOW_ONLY",
    symbol: s.symbol,
    side,
    quantity: side === "HOLD" ? 0 : qty,
    referencePrice,
    confidence,
    expectedReturn,
    observedAt: s.observedAt,
    source: s.source,
    transmissionAllowed: false,
    transmitted: false,
    safety: PHASE50_SAFETY,
  };

  return Object.freeze({ ...decision, decisionId: hash(decision) });
}

export function settleShadowDecision({ decision, nextSnapshot, feeBps = 0, slippageBps = 0 } = {}) {
  if (!decision || decision.mode !== "SHADOW_ONLY") throw new TypeError("shadow decision required");
  const next = normalizeShadowSnapshot(nextSnapshot);
  if (next.symbol !== decision.symbol) throw new TypeError("symbol mismatch");
  const sideSign = decision.side === "BUY" ? 1 : decision.side === "SELL" ? -1 : 0;
  const exitReference = decision.side === "BUY" ? next.bid : decision.side === "SELL" ? next.ask : next.last;
  const costRate = Math.max(0, finite(feeBps, "feeBps") + finite(slippageBps, "slippageBps")) / 10000;
  const grossReturn = sideSign === 0 ? 0 : sideSign * (exitReference / decision.referencePrice - 1);
  const netReturn = grossReturn - (sideSign === 0 ? 0 : costRate);
  const notional = decision.referencePrice * decision.quantity;
  const pnl = notional * netReturn;
  const settlement = {
    decisionId: decision.decisionId,
    symbol: decision.symbol,
    side: decision.side,
    quantity: decision.quantity,
    entryReference: decision.referencePrice,
    exitReference,
    grossReturn,
    netReturn,
    pnl,
    settledAt: next.observedAt,
    transmitted: false,
    safety: PHASE50_SAFETY,
  };
  return Object.freeze({ ...settlement, settlementId: hash(settlement) });
}

export function auditShadowCycle({ snapshots = [], decisions = [], settlements = [] } = {}) {
  const blockers = [];
  for (const item of [...decisions, ...settlements]) {
    if (item?.transmitted !== false) blockers.push("TRANSMISSION_FLAG_INVALID");
    if (item?.safety?.brokerWriteAllowed !== false) blockers.push("BROKER_WRITE_NOT_BLOCKED");
    if (item?.safety?.rssOrderFunctionAllowed !== false) blockers.push("RSS_ORDER_NOT_BLOCKED");
    if (item?.safety?.excelOrderWriteAllowed !== false) blockers.push("EXCEL_ORDER_WRITE_NOT_BLOCKED");
  }
  for (let i = 1; i < snapshots.length; i += 1) {
    if (Date.parse(snapshots[i].observedAt) < Date.parse(snapshots[i - 1].observedAt)) blockers.push("NON_CHRONOLOGICAL_SNAPSHOT");
  }
  return Object.freeze({
    status: blockers.length ? "BLOCKED" : "VALID",
    blockers: Object.freeze([...new Set(blockers)]),
    snapshotCount: snapshots.length,
    decisionCount: decisions.length,
    settlementCount: settlements.length,
    safety: PHASE50_SAFETY,
  });
}
