export const OPENAI_LEARNING_ADVISOR_VERSION = "openai-learning-advisor-v1";

const MAX_FAILURE_EXAMPLES = 80;
const MAX_FEATURES_PER_EXAMPLE = 30;
const MAX_WEIGHTS = 50;

function finiteNumber(value, fallback = null) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function cleanText(value, maximumLength = 240) {
  return String(value ?? "").trim().slice(0, maximumLength);
}

function normalizeAction(value) {
  const normalized = String(value ?? "")
    .trim()
    .toUpperCase()
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\s+/g, " ");

  if (["BUY", "STRONG BUY", "LONG"].includes(normalized)) return "BUY";
  if (["SELL", "STRONG SELL", "SHORT", "REDUCE"].includes(normalized)) return "SELL";
  return "NON_DIRECTIONAL";
}

function normalizeNumericRecord(record = {}, maximumEntries = 30) {
  if (!record || typeof record !== "object" || Array.isArray(record)) return {};

  return Object.fromEntries(
    Object.entries(record)
      .filter(([, value]) => Number.isFinite(Number(value)))
      .slice(0, maximumEntries)
      .map(([key, value]) => [cleanText(key, 80), Number(value)]),
  );
}

function normalizeMetrics(summary = {}) {
  return {
    sourceTotal: finiteNumber(summary.sourceTotal ?? summary.sourceRows, 0),
    directionalTotal: finiteNumber(summary.total, 0),
    correct: finiteNumber(summary.correct, 0),
    accuracyPercent: finiteNumber(summary.accuracy ?? summary.accuracyPercent, 0),
    buySignals: finiteNumber(summary.buySignals, 0),
    buyPrecisionPercent: finiteNumber(summary.buyPrecision, 0),
    sellSignals: finiteNumber(summary.sellSignals, 0),
    sellPrecisionPercent: finiteNumber(summary.sellPrecision, 0),
    averageStrategyReturnPercent: finiteNumber(summary.averageStrategyReturn, 0),
    profitFactor: finiteNumber(summary.profitFactor, 0),
    maximumDrawdownPercent: finiteNumber(summary.maximumDrawdown, 0),
    calibrationError: finiteNumber(summary.calibrationError),
  };
}

function normalizeFailureExample(item = {}) {
  const action = normalizeAction(item.action ?? item.signal);
  const resolved =
    item.resolutionStatus === undefined ||
    String(item.resolutionStatus).toUpperCase() === "RESOLVED";
  const correct = item.correct;

  if (!resolved || !["BUY", "SELL"].includes(action) || correct !== false) {
    return null;
  }

  return {
    symbol: cleanText(item.symbol, 20).toUpperCase(),
    entryDate: cleanText(item.entryDate ?? item.date, 32),
    exitDate: cleanText(item.exitDate, 32),
    horizon: finiteNumber(item.horizon),
    horizonUnit: cleanText(item.horizonUnit ?? "TRADING_SESSIONS", 40),
    action,
    predictedDirection: cleanText(item.predictedDirection, 20),
    actualDirection: cleanText(item.actualDirection, 20),
    score: finiteNumber(item.score),
    confidence: finiteNumber(item.confidence),
    returnPercent: finiteNumber(item.returnPercent),
    strategyReturnPercent: finiteNumber(item.strategyReturn),
    marketRegime: cleanText(
      item.marketRegime ?? item.regime ?? item.features?.marketRegime,
      80,
    ),
    features: normalizeNumericRecord(item.features ?? item.featureSnapshot, MAX_FEATURES_PER_EXAMPLE),
  };
}

export function selectLearningFailureExamples(
  predictions = [],
  maximumExamples = MAX_FAILURE_EXAMPLES,
) {
  const safeMaximum = Math.max(1, Math.min(MAX_FAILURE_EXAMPLES, Number(maximumExamples) || 1));

  return (Array.isArray(predictions) ? predictions : [])
    .map(normalizeFailureExample)
    .filter(Boolean)
    .sort((first, second) => String(second.entryDate).localeCompare(String(first.entryDate)))
    .slice(0, safeMaximum);
}

export function buildLearningAdvisorPayload({
  audit = {},
  currentModel = {},
  failureExamples,
  maximumExamples = MAX_FAILURE_EXAMPLES,
} = {}) {
  if (!audit || typeof audit !== "object" || Array.isArray(audit)) {
    throw new TypeError("audit must be an object");
  }

  const summary = audit.summary ?? audit.metrics;
  if (!summary || typeof summary !== "object" || Array.isArray(summary)) {
    throw new TypeError("audit.summary must be an object");
  }

  const sourceFailures = Array.isArray(failureExamples)
    ? failureExamples
    : audit.predictions;

  return {
    version: OPENAI_LEARNING_ADVISOR_VERSION,
    audit: {
      version: cleanText(audit.version, 80),
      generatedAt: cleanText(audit.generatedAt, 40),
      horizon: finiteNumber(audit.horizon),
      horizonUnit: cleanText(audit.horizonUnit ?? "TRADING_SESSIONS", 40),
      neutralThresholdPercent: finiteNumber(audit.neutralThreshold),
      futureLeakChecked: audit.futureLeakChecked === true,
      crossSymbolJoinBlocked: audit.crossSymbolJoinBlocked === true,
      labelPolicyVersion: cleanText(
        audit.labelPolicy?.version ?? summary.denominatorPolicy?.version,
        80,
      ),
      joinPolicyVersion: cleanText(audit.joinPolicy?.version, 80),
      metrics: normalizeMetrics(summary),
      excluded: {
        total: finiteNumber(summary.excluded?.total, 0),
        hold: finiteNumber(summary.excluded?.hold, 0),
        noTrade: finiteNumber(summary.excluded?.noTrade, 0),
        unknown: finiteNumber(summary.excluded?.unknown, 0),
        unresolved: finiteNumber(summary.excluded?.unresolved, 0),
      },
      diagnostics: {
        sourceRows: finiteNumber(audit.diagnostics?.sourceRows ?? audit.sourceRows, 0),
        normalizedRows: finiteNumber(audit.diagnostics?.normalizedRows ?? audit.normalizedRows, 0),
        invalidRows: finiteNumber(audit.diagnostics?.invalidRows, 0),
        duplicateRows: finiteNumber(audit.diagnostics?.duplicateRows, 0),
        symbols: finiteNumber(audit.diagnostics?.symbols, 0),
      },
    },
    currentModel: {
      version: cleanText(currentModel.version, 100),
      metrics: normalizeMetrics(currentModel.metrics ?? {}),
      weights: normalizeNumericRecord(currentModel.weights, MAX_WEIGHTS),
      calibration: normalizeNumericRecord(currentModel.calibration, 20),
    },
    failureExamples: selectLearningFailureExamples(sourceFailures, maximumExamples),
    constraints: {
      advisoryOnly: true,
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
      labelsMayBeRecalculatedByOpenAI: false,
      candidateMustPassOutOfSampleValidation: true,
      candidateMustPassFutureLeakCheck: true,
      candidateMustBeatProductionRiskMetrics: true,
    },
  };
}

export function validateLearningAdvisorAdvice(advice = {}) {
  if (!advice || typeof advice !== "object" || Array.isArray(advice)) {
    throw new TypeError("advice must be an object");
  }

  const safety = advice.safety ?? {};
  const safe =
    safety.advisoryOnly === true &&
    safety.humanApprovalRequired === true &&
    safety.productionUpdateAllowed === false &&
    safety.brokerWriteAllowed === false;

  if (!safe) {
    throw new Error("LEARNING_ADVISOR_SAFETY_CONTRACT_VIOLATION");
  }

  return {
    version: OPENAI_LEARNING_ADVISOR_VERSION,
    status: "ADVISORY_ONLY",
    candidateCreationAllowed: false,
    productionUpdateAllowed: false,
    brokerWriteAllowed: false,
    humanApprovalRequired: true,
    advice,
  };
}

export const OpenAiLearningAdvisorInternals = {
  MAX_FAILURE_EXAMPLES,
  MAX_FEATURES_PER_EXAMPLE,
  MAX_WEIGHTS,
  cleanText,
  finiteNumber,
  normalizeAction,
  normalizeFailureExample,
  normalizeMetrics,
  normalizeNumericRecord,
};
