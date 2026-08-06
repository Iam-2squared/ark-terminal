export const OPENAI_FAILURE_REVIEW_V2_VERSION = "openai-failure-review-v2";

const MAX_FAILURES = 100;
const MAX_FEATURES = 40;

function finite(value, fallback = null) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function cleanText(value, max = 240) {
  return String(value ?? "").trim().slice(0, max);
}

function normalizeAction(value) {
  const normalized = cleanText(value, 30).toUpperCase();
  if (["BUY", "LONG", "STRONG BUY"].includes(normalized)) return "BUY";
  if (["SELL", "SHORT", "STRONG SELL", "REDUCE"].includes(normalized)) return "SELL";
  return "NON_DIRECTIONAL";
}

function normalizeFeatures(features = {}) {
  if (!features || typeof features !== "object" || Array.isArray(features)) return {};
  return Object.fromEntries(
    Object.entries(features)
      .filter(([, value]) => Number.isFinite(Number(value)))
      .slice(0, MAX_FEATURES)
      .map(([key, value]) => [cleanText(key, 80), Number(value)]),
  );
}

function normalizeFailure(row = {}) {
  const action = normalizeAction(row.action ?? row.signal ?? row.direction);
  const resolved = row.status === "resolved" || row.resolved === true || row.resolutionStatus === "RESOLVED";
  const failed = row.directionHit === false || row.correct === false || row.hit === false;
  if (!resolved || !failed || !["BUY", "SELL"].includes(action)) return null;

  return {
    id: cleanText(row.id, 100),
    symbol: cleanText(row.symbol ?? row.ticker ?? row.code, 24).toUpperCase(),
    industry: cleanText(row.industry ?? row.sector, 100),
    marketSection: cleanText(row.marketSection ?? row.market, 80),
    action,
    entryDate: cleanText(row.entryDate ?? row.date, 40),
    resolvedAt: cleanText(row.resolvedAt ?? row.exitDate, 40),
    evaluationHorizon: finite(row.evaluationHorizon ?? row.horizon ?? row.period),
    holdingPeriod: finite(row.holdingPeriod ?? row.evaluationHorizon ?? row.horizon),
    confidence: finite(row.confidence?.score ?? row.confidenceScore ?? row.confidence),
    confidenceGap: finite(row.confidenceGap),
    actualReturn: finite(row.actualReturn ?? row.returnPercent),
    costAdjustedReturn: finite(row.costAdjustedReturn ?? row.netReturn),
    marketRegime: cleanText(row.marketRegime ?? row.regime ?? row.marketEnvironment?.regime, 80),
    newsContext: cleanText(row.newsContext ?? row.newsSummary, 500),
    features: normalizeFeatures(row.features ?? row.featureSnapshot ?? row.indicators),
  };
}

export function selectFailureReviewExamples(rows = [], maximum = MAX_FAILURES) {
  const safeMaximum = Math.max(1, Math.min(MAX_FAILURES, Number(maximum) || 1));
  return (Array.isArray(rows) ? rows : [])
    .map(normalizeFailure)
    .filter(Boolean)
    .sort((a, b) => String(b.entryDate).localeCompare(String(a.entryDate)))
    .slice(0, safeMaximum);
}

export function buildFailureReviewV2Payload({
  failures = [],
  metrics = {},
  currentModel = {},
  maximum = MAX_FAILURES,
} = {}) {
  return {
    version: OPENAI_FAILURE_REVIEW_V2_VERSION,
    metrics: {
      accuracy: finite(metrics.accuracy ?? metrics.accuracyPercent),
      profitFactor: finite(metrics.profitFactor),
      maximumDrawdown: finite(metrics.maximumDrawdown ?? metrics.maxDrawdown),
      calibrationError: finite(metrics.calibrationError),
      brierScore: finite(metrics.brierScore),
      sampleCount: finite(metrics.sampleCount, 0),
    },
    currentModel: {
      version: cleanText(currentModel.version, 120),
      weights: normalizeFeatures(currentModel.weights),
      thresholds: normalizeFeatures(currentModel.thresholds),
    },
    failures: selectFailureReviewExamples(failures, maximum),
    requiredOutput: {
      failurePatterns: true,
      overconfidenceConditions: true,
      missingFeatures: true,
      improvementHypotheses: true,
      weightChangeCandidates: true,
      thresholdChangeCandidates: true,
      exclusionRuleCandidates: true,
      additionalValidation: true,
    },
    constraints: {
      advisoryOnly: true,
      humanApprovalRequired: true,
      labelsMayBeChanged: false,
      automaticCandidatePromotionAllowed: false,
      productionUpdateAllowed: false,
      executionAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
    },
  };
}

export function validateFailureReviewV2Advice(advice = {}) {
  if (!advice || typeof advice !== "object" || Array.isArray(advice)) {
    throw new TypeError("advice must be an object");
  }
  const safety = advice.safety ?? {};
  const safe =
    safety.advisoryOnly === true &&
    safety.humanApprovalRequired === true &&
    safety.productionUpdateAllowed === false &&
    safety.brokerWriteAllowed === false;

  if (!safe) throw new Error("FAILURE_REVIEW_V2_SAFETY_CONTRACT_VIOLATION");

  return {
    version: OPENAI_FAILURE_REVIEW_V2_VERSION,
    status: "ADVISORY_ONLY",
    candidateCreationAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWriteAllowed: false,
    advice,
  };
}

export const FailureReviewV2Internals = Object.freeze({
  normalizeAction,
  normalizeFailure,
  normalizeFeatures,
});

export default buildFailureReviewV2Payload;
