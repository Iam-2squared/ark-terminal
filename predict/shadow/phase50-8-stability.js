import crypto from "node:crypto";
import { PHASE50_SAFETY } from "./phase50-shadow-live.js";

function hash(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function isoDay(value) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) throw new TypeError("valid timestamp required");
  return d.toISOString().slice(0, 10);
}

function average(values) {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
}

export function buildDailyShadowHistory({ previous = [], evaluation, observedAt = new Date().toISOString() } = {}) {
  if (!evaluation || evaluation.mode !== "SHADOW_ONLY") throw new TypeError("shadow evaluation required");
  const day = isoDay(observedAt);
  const clean = (Array.isArray(previous) ? previous : []).filter((x) => x && x.day && x.day !== day);
  const entry = Object.freeze({
    day,
    evaluationId: evaluation.evaluationId ?? null,
    classification: String(evaluation.classification ?? "OBSERVE"),
    sampleCount: finite(evaluation.metrics?.sampleCount),
    winRate: finite(evaluation.metrics?.winRate),
    profitFactor: finite(evaluation.metrics?.profitFactor),
    sharpe: finite(evaluation.metrics?.sharpe),
    maxDrawdown: finite(evaluation.metrics?.maxDrawdown),
    netReturn: finite(evaluation.metrics?.netReturn),
    netPnl: finite(evaluation.metrics?.netPnl),
    transmittedOrderCount: 0,
    brokerWriteCount: 0,
    excelOrderWriteCount: 0,
    rssOrderFunctionCallCount: 0,
    liveOrderCount: 0,
  });
  return Object.freeze([...clean, entry].sort((a, b) => a.day.localeCompare(b.day)));
}

export function evaluateShadowStability({ history = [], thresholds = {} } = {}) {
  const rows = (Array.isArray(history) ? history : []).slice().sort((a, b) => String(a.day).localeCompare(String(b.day)));
  const limits = {
    minDays: Math.max(3, Math.floor(finite(thresholds.minDays, 10))),
    maxDrawdown: Math.max(0, finite(thresholds.maxDrawdown, 0.15)),
    minAverageProfitFactor: Math.max(0, finite(thresholds.minAverageProfitFactor, 1.1)),
    minAverageSharpe: finite(thresholds.minAverageSharpe, 0.2),
    maxDemotionRate: Math.max(0, Math.min(1, finite(thresholds.maxDemotionRate, 0.25))),
  };

  const blockers = [];
  if (rows.some((r) => ["transmittedOrderCount", "brokerWriteCount", "excelOrderWriteCount", "rssOrderFunctionCallCount", "liveOrderCount"].some((k) => finite(r?.[k]) !== 0))) {
    blockers.push("SAFETY_COUNTER_NONZERO");
  }
  const dayCount = rows.length;
  const promotionDays = rows.filter((r) => r.classification === "PROMOTION_CANDIDATE").length;
  const demotionDays = rows.filter((r) => r.classification === "DEMOTION_CANDIDATE").length;
  const avgPf = average(rows.map((r) => finite(r.profitFactor)));
  const avgSharpe = average(rows.map((r) => finite(r.sharpe)));
  const worstDrawdown = rows.reduce((m, r) => Math.max(m, Math.max(0, finite(r.maxDrawdown))), 0);
  const demotionRate = dayCount ? demotionDays / dayCount : 0;

  if (dayCount < limits.minDays) blockers.push("INSUFFICIENT_DAYS");
  if (avgPf < limits.minAverageProfitFactor) blockers.push("AVERAGE_PF_BELOW_GATE");
  if (avgSharpe < limits.minAverageSharpe) blockers.push("AVERAGE_SHARPE_BELOW_GATE");
  if (worstDrawdown > limits.maxDrawdown) blockers.push("DRAWDOWN_ABOVE_GATE");
  if (demotionRate > limits.maxDemotionRate) blockers.push("DEMOTION_RATE_ABOVE_GATE");

  let classification = "OBSERVE";
  if (blockers.includes("SAFETY_COUNTER_NONZERO")) classification = "BLOCKED";
  else if (dayCount >= limits.minDays && blockers.length === 0) classification = "STABLE_CANDIDATE";
  else if (dayCount >= limits.minDays) classification = "UNSTABLE";

  const result = {
    phase: 50.8,
    mode: "SHADOW_ONLY",
    classification,
    blockers: [...new Set(blockers)],
    thresholds: limits,
    metrics: {
      dayCount,
      promotionDays,
      demotionDays,
      promotionRate: dayCount ? promotionDays / dayCount : 0,
      demotionRate,
      averageProfitFactor: avgPf,
      averageSharpe: avgSharpe,
      worstDrawdown,
      latestNetReturn: rows.length ? finite(rows.at(-1).netReturn) : 0,
      latestNetPnl: rows.length ? finite(rows.at(-1).netPnl) : 0,
    },
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    transmittedOrderCount: 0,
    brokerWriteCount: 0,
    excelOrderWriteCount: 0,
    rssOrderFunctionCallCount: 0,
    liveOrderCount: 0,
    safety: PHASE50_SAFETY,
  };
  return Object.freeze({ ...result, stabilityId: hash(result) });
}

export function verifyShadowStability(result) {
  const blockers = [];
  if (!result || result.mode !== "SHADOW_ONLY") blockers.push("INVALID_MODE");
  if (result?.automaticPromotionAllowed !== false) blockers.push("AUTOMATIC_PROMOTION_NOT_BLOCKED");
  if (result?.productionUpdateAllowed !== false) blockers.push("PRODUCTION_UPDATE_NOT_BLOCKED");
  if (result?.humanApprovalRequired !== true) blockers.push("HUMAN_APPROVAL_NOT_REQUIRED");
  for (const field of ["transmittedOrderCount", "brokerWriteCount", "excelOrderWriteCount", "rssOrderFunctionCallCount", "liveOrderCount"]) {
    if (result?.[field] !== 0) blockers.push(`NONZERO_${field}`);
  }
  return Object.freeze({ status: blockers.length ? "BLOCKED" : "VALID", blockers: Object.freeze(blockers), safety: PHASE50_SAFETY });
}
