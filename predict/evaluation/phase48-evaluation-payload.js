import { createHash } from "node:crypto";

export const PHASE48_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const finite = (value, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback;
const text = (value) => String(value ?? "").trim();
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function checksum(value) {
  return createHash("sha256").update(JSON.stringify(stable(value))).digest("hex");
}

export function classifyModelHealth(metrics = {}, audit = {}) {
  if ((audit.blockers?.length ?? 0) > 0 || audit.futureLeakDetected === true) return "BLOCKED";
  const auc = finite(metrics.auc, 0.5);
  const pf = finite(metrics.profitFactor, 0);
  const dd = Math.abs(finite(metrics.maximumDrawdown, 1));
  const brier = finite(metrics.brierScore, 1);
  if (auc >= 0.58 && pf >= 1.2 && dd <= 0.15 && brier <= 0.22) return "HEALTHY";
  if (auc >= 0.54 && pf >= 1.05 && dd <= 0.25 && brier <= 0.28) return "WARNING";
  return "DEGRADED";
}

export function buildPhase48EvaluationPayload({ candidate, prediction, regimeBreakdown = [], symbolBreakdown = [], featureReasons = [], risks = [] } = {}) {
  if (!candidate || typeof candidate !== "object") throw new TypeError("candidate is required");
  const metrics = candidate.metrics ?? candidate.aggregateMetrics ?? {};
  const audit = candidate.audit ?? {};
  const payload = {
    schemaVersion: 1,
    phase: 48,
    status: "EVALUATION_ONLY",
    modelHealth: classifyModelHealth(metrics, audit),
    model: {
      id: text(candidate.modelId),
      type: text(candidate.modelType),
      status: text(candidate.status || "CANDIDATE_REVIEW_ONLY"),
      trainingPeriod: candidate.trainingPeriod ?? null,
      testPeriod: candidate.testPeriod ?? null,
      walkForwardFolds: finite(candidate.walkForward?.foldCount ?? candidate.foldCount, 0),
      lineageChecksum: text(candidate.lineage?.checksum ?? candidate.lineageChecksum),
    },
    prediction: {
      symbol: text(prediction?.symbol),
      sessionDate: text(prediction?.sessionDate),
      aiScore: clamp(finite(prediction?.aiScore, 50), 0, 100),
      expectedReturn: finite(prediction?.expectedReturn, 0),
      confidence: clamp(finite(prediction?.confidence, 0), 0, 1),
      direction: text(prediction?.direction || "NEUTRAL"),
    },
    metrics: {
      accuracy: finite(metrics.accuracy),
      precision: finite(metrics.precision),
      recall: finite(metrics.recall),
      auc: finite(metrics.auc),
      brierScore: finite(metrics.brierScore),
      profitFactor: finite(metrics.profitFactor),
      sharpe: finite(metrics.sharpe),
      maximumDrawdown: finite(metrics.maximumDrawdown),
      cagr: finite(metrics.cagr),
      netReturn: finite(metrics.netReturn),
      tradeCount: finite(metrics.tradeCount),
    },
    regimeBreakdown: Object.freeze([...regimeBreakdown]),
    symbolBreakdown: Object.freeze([...symbolBreakdown]),
    majorReasons: Object.freeze(featureReasons.slice(0, 5)),
    majorRisks: Object.freeze(risks.slice(0, 5)),
    audit: {
      futureLeakDetected: audit.futureLeakDetected === true,
      blockerCount: audit.blockers?.length ?? 0,
      sampleCount: finite(candidate.sampleCount ?? metrics.sampleCount),
      reviewRequired: true,
    },
    safety: PHASE48_SAFETY,
  };
  return Object.freeze({ ...payload, checksum: checksum(payload) });
}

export function auditPhase48Payload(payload) {
  const blockers = [];
  if (!payload || typeof payload !== "object") blockers.push("PAYLOAD_REQUIRED");
  if (payload?.safety?.executionAllowed !== false) blockers.push("EXECUTION_MUST_BE_DISABLED");
  if (payload?.safety?.brokerWriteAllowed !== false) blockers.push("BROKER_WRITE_MUST_BE_DISABLED");
  if (payload?.safety?.excelOrderWriteAllowed !== false) blockers.push("EXCEL_ORDER_WRITE_MUST_BE_DISABLED");
  if (payload?.safety?.rssOrderFunctionAllowed !== false) blockers.push("RSS_ORDER_FUNCTION_MUST_BE_DISABLED");
  const candidate = payload ? { ...payload } : {};
  delete candidate.checksum;
  if (payload?.checksum !== checksum(candidate)) blockers.push("CHECKSUM_MISMATCH");
  return Object.freeze({ status: blockers.length ? "BLOCKED" : "VALID", blockers: Object.freeze(blockers) });
}
