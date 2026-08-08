import crypto from "node:crypto";
import { PHASE50_SAFETY, auditShadowCycle } from "./phase50-shadow-live.js";

function hash(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function pf(values) {
  const gains = values.filter((v) => v > 0).reduce((a, b) => a + b, 0);
  const losses = Math.abs(values.filter((v) => v < 0).reduce((a, b) => a + b, 0));
  if (!losses) return gains > 0 ? Infinity : 0;
  return gains / losses;
}

function maxDrawdown(values) {
  let equity = 1;
  let peak = 1;
  let dd = 0;
  for (const r of values) {
    equity *= 1 + r;
    peak = Math.max(peak, equity);
    dd = Math.max(dd, peak > 0 ? (peak - equity) / peak : 0);
  }
  return dd;
}

function sharpe(values) {
  if (values.length < 2) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((sum, v) => sum + ((v - mean) ** 2), 0) / (values.length - 1);
  const sd = Math.sqrt(variance);
  return sd > 0 ? mean / sd * Math.sqrt(values.length) : 0;
}

export function summarizeShadowPerformance(settlements = []) {
  const active = settlements.filter((s) => finite(s?.quantity) > 0 && Number.isFinite(Number(s?.netReturn)));
  const returns = active.map((s) => Number(s.netReturn));
  const netPnl = active.reduce((sum, s) => sum + finite(s.pnl), 0);
  const netReturn = returns.reduce((equity, r) => equity * (1 + r), 1) - 1;
  return Object.freeze({
    sampleCount: returns.length,
    winRate: returns.length ? returns.filter((r) => r > 0).length / returns.length : 0,
    profitFactor: pf(returns),
    sharpe: sharpe(returns),
    maxDrawdown: maxDrawdown(returns),
    netReturn,
    netPnl,
  });
}

export function evaluatePromotionCandidate({ snapshots = [], decisions = [], settlements = [], baseline = null, thresholds = {} } = {}) {
  const audit = auditShadowCycle({ snapshots, decisions, settlements });
  const current = summarizeShadowPerformance(settlements);
  const limits = {
    minSamples: Math.max(20, Math.floor(finite(thresholds.minSamples, 60))),
    minProfitFactor: Math.max(0, finite(thresholds.minProfitFactor, 1.15)),
    minWinRate: Math.max(0, Math.min(1, finite(thresholds.minWinRate, 0.5))),
    minSharpe: finite(thresholds.minSharpe, 0.25),
    maxDrawdown: Math.max(0, finite(thresholds.maxDrawdown, 0.15)),
    maxBaselineNetReturnLag: Math.max(0, finite(thresholds.maxBaselineNetReturnLag, 0.02)),
  };

  const blockers = [];
  if (audit.status !== "VALID") blockers.push("SHADOW_AUDIT_FAILED");
  if (current.sampleCount < limits.minSamples) blockers.push("INSUFFICIENT_SAMPLES");
  if (current.profitFactor < limits.minProfitFactor) blockers.push("PROFIT_FACTOR_BELOW_GATE");
  if (current.winRate < limits.minWinRate) blockers.push("WIN_RATE_BELOW_GATE");
  if (current.sharpe < limits.minSharpe) blockers.push("SHARPE_BELOW_GATE");
  if (current.maxDrawdown > limits.maxDrawdown) blockers.push("DRAWDOWN_ABOVE_GATE");

  const baselineMetrics = baseline ? Object.freeze({
    netReturn: finite(baseline.netReturn),
    profitFactor: finite(baseline.profitFactor),
    sharpe: finite(baseline.sharpe),
    maxDrawdown: Math.max(0, finite(baseline.maxDrawdown)),
  }) : null;
  if (baselineMetrics && current.netReturn + limits.maxBaselineNetReturnLag < baselineMetrics.netReturn) {
    blockers.push("BASELINE_NET_RETURN_LAG");
  }

  let classification = "HOLD";
  if (audit.status !== "VALID") classification = "BLOCKED";
  else if (current.sampleCount < limits.minSamples) classification = "OBSERVE";
  else if (!blockers.length) classification = "PROMOTION_CANDIDATE";
  else if (blockers.some((x) => ["PROFIT_FACTOR_BELOW_GATE", "SHARPE_BELOW_GATE", "DRAWDOWN_ABOVE_GATE", "BASELINE_NET_RETURN_LAG"].includes(x))) classification = "DEMOTION_CANDIDATE";

  const result = {
    phase: 50.7,
    mode: "SHADOW_ONLY",
    classification,
    blockers: [...new Set(blockers)],
    thresholds: limits,
    metrics: current,
    baseline: baselineMetrics,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    transmittedOrderCount: 0,
    brokerWriteCount: 0,
    excelOrderWriteCount: 0,
    rssOrderFunctionCallCount: 0,
    liveOrderCount: 0,
    safety: PHASE50_SAFETY,
    audit,
  };
  return Object.freeze({ ...result, evaluationId: hash(result) });
}

export function verifyPromotionEvaluation(result) {
  const blockers = [];
  if (!result || result.mode !== "SHADOW_ONLY") blockers.push("INVALID_MODE");
  if (result?.automaticPromotionAllowed !== false) blockers.push("AUTOMATIC_PROMOTION_NOT_BLOCKED");
  if (result?.productionUpdateAllowed !== false) blockers.push("PRODUCTION_UPDATE_NOT_BLOCKED");
  if (result?.humanApprovalRequired !== true) blockers.push("HUMAN_APPROVAL_NOT_REQUIRED");
  for (const [field, code] of [
    ["transmittedOrderCount", "ORDER_TRANSMISSION_DETECTED"],
    ["brokerWriteCount", "BROKER_WRITE_DETECTED"],
    ["excelOrderWriteCount", "EXCEL_ORDER_WRITE_DETECTED"],
    ["rssOrderFunctionCallCount", "RSS_ORDER_CALL_DETECTED"],
    ["liveOrderCount", "LIVE_ORDER_DETECTED"],
  ]) {
    if (result?.[field] !== 0) blockers.push(code);
  }
  return Object.freeze({ status: blockers.length ? "BLOCKED" : "VALID", blockers: Object.freeze(blockers), safety: PHASE50_SAFETY });
}
