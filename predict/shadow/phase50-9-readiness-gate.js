import crypto from "node:crypto";
import { PHASE50_SAFETY } from "./phase50-shadow-live.js";

function hash(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function evaluateSemiAutoReadiness({ stability, latestEvaluation, thresholds = {} } = {}) {
  const limits = {
    minStableDays: Math.max(5, Math.floor(finite(thresholds.minStableDays, 20))),
    minPromotionRate: Math.max(0, Math.min(1, finite(thresholds.minPromotionRate, 0.6))),
    maxDemotionRate: Math.max(0, Math.min(1, finite(thresholds.maxDemotionRate, 0.2))),
    minAverageProfitFactor: Math.max(0, finite(thresholds.minAverageProfitFactor, 1.15)),
    minAverageSharpe: finite(thresholds.minAverageSharpe, 0.25),
    maxWorstDrawdown: Math.max(0, finite(thresholds.maxWorstDrawdown, 0.15)),
    requireStableCandidate: thresholds.requireStableCandidate ?? true,
  };

  const blockers = [];
  const sm = stability?.metrics ?? {};
  const lm = latestEvaluation?.metrics ?? {};

  if (!stability || stability.mode !== "SHADOW_ONLY") blockers.push("INVALID_STABILITY_INPUT");
  if (!latestEvaluation || latestEvaluation.mode !== "SHADOW_ONLY") blockers.push("INVALID_LATEST_EVALUATION");
  if (stability?.classification === "BLOCKED" || latestEvaluation?.classification === "BLOCKED") blockers.push("UPSTREAM_BLOCKED");
  if (limits.requireStableCandidate && stability?.classification !== "STABLE_CANDIDATE") blockers.push("STABILITY_NOT_READY");
  if (finite(sm.dayCount) < limits.minStableDays) blockers.push("INSUFFICIENT_STABLE_DAYS");
  if (finite(sm.promotionRate) < limits.minPromotionRate) blockers.push("PROMOTION_RATE_BELOW_GATE");
  if (finite(sm.demotionRate) > limits.maxDemotionRate) blockers.push("DEMOTION_RATE_ABOVE_GATE");
  if (finite(sm.averageProfitFactor) < limits.minAverageProfitFactor) blockers.push("AVERAGE_PF_BELOW_GATE");
  if (finite(sm.averageSharpe) < limits.minAverageSharpe) blockers.push("AVERAGE_SHARPE_BELOW_GATE");
  if (finite(sm.worstDrawdown) > limits.maxWorstDrawdown) blockers.push("WORST_DRAWDOWN_ABOVE_GATE");
  if (latestEvaluation?.classification !== "PROMOTION_CANDIDATE") blockers.push("LATEST_NOT_PROMOTION_CANDIDATE");

  const safetyCounters = [
    latestEvaluation?.transmittedOrderCount,
    latestEvaluation?.brokerWriteCount,
    latestEvaluation?.excelOrderWriteCount,
    latestEvaluation?.rssOrderFunctionCallCount,
    latestEvaluation?.liveOrderCount,
  ].map((v) => finite(v));
  if (safetyCounters.some((v) => v !== 0)) blockers.push("SAFETY_COUNTER_NONZERO");

  const hardBlocked = blockers.some((x) => [
    "INVALID_STABILITY_INPUT",
    "INVALID_LATEST_EVALUATION",
    "UPSTREAM_BLOCKED",
    "SAFETY_COUNTER_NONZERO",
  ].includes(x));

  const status = hardBlocked ? "BLOCKED" : blockers.length ? "NOT_READY" : "READY";
  const result = {
    phase: 50.9,
    mode: "SHADOW_ONLY",
    status,
    blockers: [...new Set(blockers)],
    thresholds: limits,
    metrics: {
      stableDays: finite(sm.dayCount),
      promotionRate: finite(sm.promotionRate),
      demotionRate: finite(sm.demotionRate),
      averageProfitFactor: finite(sm.averageProfitFactor),
      averageSharpe: finite(sm.averageSharpe),
      worstDrawdown: finite(sm.worstDrawdown),
      latestSampleCount: finite(lm.sampleCount),
      latestWinRate: finite(lm.winRate),
      latestProfitFactor: finite(lm.profitFactor),
      latestSharpe: finite(lm.sharpe),
      latestMaxDrawdown: finite(lm.maxDrawdown),
    },
    semiAutoExecutionAllowed: false,
    liveTradingAllowed: false,
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
  return Object.freeze({ ...result, readinessId: hash(result) });
}

export function verifyReadinessGate(result) {
  const blockers = [];
  if (!result || result.mode !== "SHADOW_ONLY") blockers.push("INVALID_MODE");
  if (!["READY", "NOT_READY", "BLOCKED"].includes(result?.status)) blockers.push("INVALID_STATUS");
  if (result?.semiAutoExecutionAllowed !== false) blockers.push("SEMI_AUTO_EXECUTION_NOT_BLOCKED");
  if (result?.liveTradingAllowed !== false) blockers.push("LIVE_TRADING_NOT_BLOCKED");
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
