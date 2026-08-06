import crypto from "node:crypto";
import { PHASE50_SAFETY, auditShadowCycle, buildShadowDecision, normalizeShadowSnapshot, settleShadowDecision } from "./phase50-shadow-live.js";

function hash(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function pf(values) {
  const gains = values.filter((v) => v > 0).reduce((a, b) => a + b, 0);
  const losses = Math.abs(values.filter((v) => v < 0).reduce((a, b) => a + b, 0));
  if (losses === 0) return gains > 0 ? Infinity : 0;
  return gains / losses;
}

function maxDrawdown(values) {
  let equity = 1;
  let peak = 1;
  let max = 0;
  for (const r of values) {
    equity *= 1 + r;
    peak = Math.max(peak, equity);
    max = Math.max(max, peak === 0 ? 0 : (peak - equity) / peak);
  }
  return max;
}

export function runShadowSession({ observations = [], signals = [], quantity = 100, feeBps = 0, slippageBps = 0 } = {}) {
  if (!Array.isArray(observations) || observations.length < 2) throw new RangeError("at least two observations are required");
  if (!Array.isArray(signals)) throw new TypeError("signals must be an array");

  const snapshots = observations.map(normalizeShadowSnapshot).sort((a, b) => Date.parse(a.observedAt) - Date.parse(b.observedAt));
  const decisions = [];
  const settlements = [];

  for (let i = 0; i < snapshots.length - 1; i += 1) {
    const signal = signals[i] ?? { side: "HOLD", confidence: 0, expectedReturn: 0 };
    const decision = buildShadowDecision({ snapshot: snapshots[i], signal, quantity });
    const settlement = settleShadowDecision({ decision, nextSnapshot: snapshots[i + 1], feeBps, slippageBps });
    decisions.push(decision);
    settlements.push(settlement);
  }

  const audit = auditShadowCycle({ snapshots, decisions, settlements });
  if (audit.status !== "VALID") {
    return Object.freeze({ status: "BLOCKED", audit, snapshots: Object.freeze([]), decisions: Object.freeze([]), settlements: Object.freeze([]), safety: PHASE50_SAFETY });
  }

  const returns = settlements.filter((x) => x.quantity > 0).map((x) => x.netReturn);
  const pnl = settlements.reduce((sum, x) => sum + x.pnl, 0);
  const report = {
    status: "SHADOW_COMPLETE",
    mode: "SHADOW_ONLY",
    snapshotCount: snapshots.length,
    decisionCount: decisions.length,
    settlementCount: settlements.length,
    activeTradeCount: returns.length,
    winRate: returns.length ? returns.filter((r) => r > 0).length / returns.length : 0,
    netPnl: pnl,
    averageNetReturn: returns.length ? returns.reduce((a, b) => a + b, 0) / returns.length : 0,
    profitFactor: pf(returns),
    maxDrawdown: maxDrawdown(returns),
    transmittedOrderCount: 0,
    brokerWriteCount: 0,
    excelOrderWriteCount: 0,
    rssOrderFunctionCallCount: 0,
    safety: PHASE50_SAFETY,
  };

  return Object.freeze({ ...report, reportId: hash(report), snapshots: Object.freeze(snapshots), decisions: Object.freeze(decisions), settlements: Object.freeze(settlements), audit });
}

export function verifyShadowReport(report) {
  const blockers = [];
  if (!report || report.mode !== "SHADOW_ONLY") blockers.push("INVALID_MODE");
  if (report?.transmittedOrderCount !== 0) blockers.push("ORDER_TRANSMISSION_DETECTED");
  if (report?.brokerWriteCount !== 0) blockers.push("BROKER_WRITE_DETECTED");
  if (report?.excelOrderWriteCount !== 0) blockers.push("EXCEL_ORDER_WRITE_DETECTED");
  if (report?.rssOrderFunctionCallCount !== 0) blockers.push("RSS_ORDER_CALL_DETECTED");
  return Object.freeze({ status: blockers.length ? "BLOCKED" : "VALID", blockers: Object.freeze(blockers), safety: PHASE50_SAFETY });
}
