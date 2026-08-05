export const PHASE20_CANDIDATE_PROPOSAL_VERSION =
  "phase20-candidate-proposal-v1";

const MAX_WEIGHT_DELTA = 0.2;
const MAX_EXCLUSION_RULES = 20;

function finiteNumber(value, fallback = null) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function round(value, digits = 8) {
  if (!Number.isFinite(Number(value))) return value;
  const factor = 10 ** digits;
  return Math.round(Number(value) * factor) / factor;
}

function cleanText(value, maximumLength = 240) {
  return String(value ?? "").trim().slice(0, maximumLength);
}

function normalizeNumericRecord(record = {}) {
  if (!record || typeof record !== "object" || Array.isArray(record)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(record)
      .filter(([key, value]) => key && Number.isFinite(Number(value)))
      .map(([key, value]) => [cleanText(key, 80), Number(value)]),
  );
}

function extractValidatedAdvice(review = {}) {
  const wrapper = review?.review ?? review;
  const advice = wrapper?.advice ?? wrapper;
  const safety = advice?.safety ?? {};

  const wrapperSafe =
    wrapper?.status === "ADVISORY_ONLY" &&
    wrapper?.productionUpdateAllowed === false &&
    wrapper?.brokerWriteAllowed === false &&
    wrapper?.humanApprovalRequired === true;

  const adviceSafe =
    safety.advisoryOnly === true &&
    safety.humanApprovalRequired === true &&
    safety.productionUpdateAllowed === false &&
    safety.brokerWriteAllowed === false;

  if (!wrapperSafe || !adviceSafe) {
    throw new Error("LEARNING_ADVISOR_SAFETY_CONTRACT_REQUIRED");
  }

  return advice;
}

function applyWeightChanges(currentWeights, changes = []) {
  const base = normalizeNumericRecord(currentWeights);
  const baseKeys = new Set(Object.keys(base));
  const proposed = { ...base };
  const applied = [];
  const rejected = [];

  for (const change of Array.isArray(changes) ? changes : []) {
    const feature = cleanText(change?.feature, 80);
    const direction = cleanText(change?.direction, 20).toUpperCase();
    const requestedDelta = finiteNumber(change?.delta);

    if (!baseKeys.has(feature)) {
      rejected.push({
        type: "WEIGHT",
        feature,
        reason: "UNKNOWN_FEATURE_KEY",
      });
      continue;
    }

    if (!["INCREASE", "DECREASE", "HOLD"].includes(direction)) {
      rejected.push({
        type: "WEIGHT",
        feature,
        reason: "INVALID_DIRECTION",
      });
      continue;
    }

    if (direction === "HOLD") continue;

    if (requestedDelta === null || requestedDelta < 0) {
      rejected.push({
        type: "WEIGHT",
        feature,
        reason: "INVALID_DELTA",
      });
      continue;
    }

    const delta = Math.min(MAX_WEIGHT_DELTA, requestedDelta);
    const before = proposed[feature];
    const signedDelta = direction === "INCREASE" ? delta : -delta;
    const after = Math.max(0, before + signedDelta);
    proposed[feature] = after;

    applied.push({
      type: "WEIGHT",
      feature,
      direction,
      requestedDelta,
      appliedDelta: round(after - before),
      before: round(before),
      after: round(after),
      reason: cleanText(change?.reason, 400),
    });
  }

  const baseTotal = Object.values(base).reduce((sum, value) => sum + value, 0);
  const proposedTotal = Object.values(proposed).reduce((sum, value) => sum + value, 0);

  if (baseTotal > 0 && proposedTotal > 0) {
    const scale = baseTotal / proposedTotal;
    for (const key of Object.keys(proposed)) {
      proposed[key] = round(proposed[key] * scale);
    }
  }

  return {
    base,
    proposed,
    applied,
    rejected,
    totalPreserved:
      round(Object.values(proposed).reduce((sum, value) => sum + value, 0)) ===
      round(baseTotal),
  };
}

function applyThresholdChanges(
  currentThresholds = {},
  thresholdPolicy = {},
  changes = [],
) {
  const current = normalizeNumericRecord(currentThresholds);
  const proposed = { ...current };
  const applied = [];
  const rejected = [];

  for (const change of Array.isArray(changes) ? changes : []) {
    const name = cleanText(change?.name, 80);
    const policy = thresholdPolicy?.[name];
    const before = current[name];
    const requested = finiteNumber(change?.proposedValue);

    if (!Object.hasOwn(current, name) || !policy) {
      rejected.push({
        type: "THRESHOLD",
        name,
        reason: "THRESHOLD_NOT_ALLOWLISTED",
      });
      continue;
    }

    if (requested === null) {
      rejected.push({
        type: "THRESHOLD",
        name,
        reason: "NON_NUMERIC_THRESHOLD",
      });
      continue;
    }

    const minimum = finiteNumber(policy.minimum, -Infinity);
    const maximum = finiteNumber(policy.maximum, Infinity);
    const maximumDelta = Math.max(0, finiteNumber(policy.maximumDelta, 0));
    const boundedTarget = Math.min(maximum, Math.max(minimum, requested));
    const difference = boundedTarget - before;
    const appliedDifference =
      Math.abs(difference) <= maximumDelta
        ? difference
        : Math.sign(difference) * maximumDelta;
    const after = round(before + appliedDifference);

    proposed[name] = after;
    applied.push({
      type: "THRESHOLD",
      name,
      requestedValue: requested,
      before,
      after,
      reason: cleanText(change?.reason, 400),
    });
  }

  return { current, proposed, applied, rejected };
}

export function createCandidateProposalFromAdvice({
  review,
  currentModel = {},
  audit = {},
  requestedBy,
  thresholdPolicy = {},
  minimumDirectionalSamples = 50,
  candidateId,
  now = () => new Date(),
} = {}) {
  const reviewer = cleanText(requestedBy, 120);
  if (!reviewer) throw new Error("HUMAN_REQUESTER_REQUIRED");

  const advice = extractValidatedAdvice(review);
  const hypothesis = advice?.candidateHypothesis ?? {};

  if (hypothesis.shouldCreateCandidate !== true) {
    throw new Error("OPENAI_DID_NOT_RECOMMEND_CANDIDATE");
  }

  const directionalSamples = finiteNumber(
    audit?.summary?.total ?? audit?.metrics?.directionalTotal,
    0,
  );
  const minimumSamples = Math.max(1, Number(minimumDirectionalSamples) || 50);

  if (directionalSamples < minimumSamples) {
    throw new Error("INSUFFICIENT_DIRECTIONAL_SAMPLES_FOR_CANDIDATE");
  }

  const modelVersion = cleanText(currentModel?.version, 100);
  const modelId = cleanText(
    currentModel?.id ?? currentModel?.modelId ?? "ark-prediction-model",
    100,
  );
  const currentWeights = normalizeNumericRecord(currentModel?.weights);

  if (!modelVersion) throw new Error("CURRENT_MODEL_VERSION_REQUIRED");
  if (Object.keys(currentWeights).length === 0) {
    throw new Error("CURRENT_MODEL_WEIGHTS_REQUIRED");
  }

  const weights = applyWeightChanges(
    currentWeights,
    hypothesis.weightChanges,
  );
  const thresholds = applyThresholdChanges(
    currentModel?.thresholds,
    thresholdPolicy,
    hypothesis.thresholdChanges,
  );

  if (weights.applied.length === 0 && thresholds.applied.length === 0) {
    throw new Error("NO_EXECUTABLE_CANDIDATE_CHANGES");
  }

  const createdAt = now().toISOString();
  const id = cleanText(
    candidateId ??
      `${modelId}-${modelVersion}-candidate-${createdAt.replaceAll(/[^0-9]/g, "").slice(0, 14)}`,
    160,
  );

  return {
    version: PHASE20_CANDIDATE_PROPOSAL_VERSION,
    id,
    candidateVersion: `${modelVersion}-candidate`,
    status: "PROPOSED_FOR_VALIDATION",
    createdAt,
    requestedBy: reviewer,
    source: "OPENAI_LEARNING_ADVISOR",
    baseModel: {
      id: modelId,
      version: modelVersion,
    },
    sourceDirectionalSamples: directionalSamples,
    rationale: cleanText(hypothesis.rationale, 1_500),
    weights: weights.proposed,
    thresholds: thresholds.proposed,
    proposedExclusionRules: (Array.isArray(hypothesis.exclusionRules)
      ? hypothesis.exclusionRules
      : [])
      .map((rule) => cleanText(rule, 300))
      .filter(Boolean)
      .slice(0, MAX_EXCLUSION_RULES),
    exclusionRulesExecutable: false,
    changeLog: [...weights.applied, ...thresholds.applied],
    rejectedChanges: [...weights.rejected, ...thresholds.rejected],
    validationRequirements: {
      minimumSamples,
      outOfSampleRequired: true,
      sameSymbolSessionJoinRequired: true,
      futureLeakCheckRequired: true,
      pairedChampionComparisonRequired: true,
      humanApprovalRequired: true,
    },
    safety: {
      executable: false,
      advisoryOnlySource: true,
      humanApprovalRequired: true,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
    },
  };
}

export function registerCandidateProposal({
  proposal,
  orchestrator,
  registeredBy,
} = {}) {
  if (!proposal || proposal.status !== "PROPOSED_FOR_VALIDATION") {
    throw new Error("VALID_CANDIDATE_PROPOSAL_REQUIRED");
  }

  const reviewer = cleanText(registeredBy, 120);
  if (!reviewer) throw new Error("HUMAN_REGISTRAR_REQUIRED");
  if (typeof orchestrator?.createCandidate !== "function") {
    throw new TypeError("orchestrator.createCandidate is required");
  }

  return orchestrator.createCandidate({
    sourceTradeCount: proposal.sourceDirectionalSamples,
    weights: proposal.weights,
    metadata: {
      version: proposal.candidateVersion,
      proposalId: proposal.id,
      source: proposal.source,
      requestedBy: proposal.requestedBy,
      registeredBy: reviewer,
      thresholds: proposal.thresholds,
      proposedExclusionRules: proposal.proposedExclusionRules,
      exclusionRulesExecutable: false,
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
    },
  });
}

export const Phase20CandidateProposalInternals = {
  MAX_WEIGHT_DELTA,
  applyThresholdChanges,
  applyWeightChanges,
  extractValidatedAdvice,
  finiteNumber,
  normalizeNumericRecord,
};
