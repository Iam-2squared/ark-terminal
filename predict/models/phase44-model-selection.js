import { stableStringify } from "../data/phase41-data-lake.js";

const PHASE44_SAFETY = Object.freeze({
  mode: "MODEL_SELECTION_REVIEW_ONLY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  automaticRollbackAllowed: false,
  humanApprovalRequired: true,
});

function fnv1a(value) {
  let hash = 0x811c9dc5;
  for (const char of String(value)) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function finite(value, fallback = null) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function normalizeRegimeMetrics(input = {}) {
  return Object.fromEntries(
    Object.entries(input).map(([regime, metrics]) => [String(regime), {
      winRate: finite(metrics?.winRate),
      profitFactor: finite(metrics?.profitFactor),
      maxDrawdown: finite(metrics?.maxDrawdown),
      sampleCount: finite(metrics?.sampleCount, 0),
    }]),
  );
}

export function createValidationCandidate(input = {}) {
  const modelId = String(input.modelId ?? "").trim();
  const version = String(input.version ?? "").trim();
  if (!modelId || !version) throw new TypeError("modelId and version are required");

  const normalized = {
    modelId,
    version,
    featureSetId: String(input.featureSetId ?? "").trim() || null,
    datasetHash: String(input.datasetHash ?? "").trim() || null,
    artifactHash: String(input.artifactHash ?? "").trim() || null,
    metrics: {
      winRate: finite(input.metrics?.winRate),
      averageReturn: finite(input.metrics?.averageReturn),
      profitFactor: finite(input.metrics?.profitFactor),
      maxDrawdown: finite(input.metrics?.maxDrawdown),
      sharpe: finite(input.metrics?.sharpe),
      sampleCount: finite(input.metrics?.sampleCount, 0),
    },
    walkForward: {
      folds: finite(input.walkForward?.folds, 0),
      successfulFolds: finite(input.walkForward?.successfulFolds, 0),
      stabilityScore: finite(input.walkForward?.stabilityScore),
    },
    regimeMetrics: normalizeRegimeMetrics(input.regimeMetrics),
    createdAt: new Date(input.createdAt ?? Date.now()).toISOString(),
  };

  normalized.candidateKey = `${modelId}:${version}`;
  normalized.contentHash = fnv1a(stableStringify(normalized));
  return Object.freeze(normalized);
}

function scoreCandidate(candidate, weights) {
  const m = candidate.metrics;
  const wf = candidate.walkForward;
  const ddPenalty = Math.abs(m.maxDrawdown ?? 1);
  const samplePenalty = m.sampleCount < weights.minimumSamples ? 1 : 0;
  const score =
    (m.winRate ?? 0) * weights.winRate +
    (m.profitFactor ?? 0) * weights.profitFactor +
    (m.sharpe ?? 0) * weights.sharpe +
    (wf.stabilityScore ?? 0) * weights.stability -
    ddPenalty * weights.maxDrawdownPenalty -
    samplePenalty * weights.samplePenalty;
  return Number(score.toFixed(8));
}

export function evaluateOverfitting(candidate, options = {}) {
  const blockers = [];
  const warnings = [];
  const minimumFolds = Number(options.minimumFolds ?? 3);
  const minimumStability = Number(options.minimumStability ?? 0.5);
  const minimumSamples = Number(options.minimumSamples ?? 100);

  if ((candidate.walkForward?.folds ?? 0) < minimumFolds) blockers.push("INSUFFICIENT_WALK_FORWARD_FOLDS");
  if ((candidate.walkForward?.stabilityScore ?? -Infinity) < minimumStability) blockers.push("UNSTABLE_WALK_FORWARD_RESULTS");
  if ((candidate.metrics?.sampleCount ?? 0) < minimumSamples) blockers.push("INSUFFICIENT_SAMPLE_COUNT");
  if ((candidate.metrics?.profitFactor ?? 0) > 5) warnings.push("EXTREME_PROFIT_FACTOR_REVIEW_REQUIRED");
  if ((candidate.metrics?.winRate ?? 0) > 0.9) warnings.push("EXTREME_WIN_RATE_REVIEW_REQUIRED");

  return {
    status: blockers.length ? "BLOCKED" : warnings.length ? "WARNING" : "VALID",
    blockers,
    warnings,
    canRank: blockers.length === 0,
    safety: { ...PHASE44_SAFETY },
  };
}

export function rankValidationCandidates({ candidates = [], champion = null, weights = {} } = {}) {
  const resolvedWeights = {
    winRate: Number(weights.winRate ?? 1),
    profitFactor: Number(weights.profitFactor ?? 1),
    sharpe: Number(weights.sharpe ?? 0.5),
    stability: Number(weights.stability ?? 1),
    maxDrawdownPenalty: Number(weights.maxDrawdownPenalty ?? 1),
    samplePenalty: Number(weights.samplePenalty ?? 1),
    minimumSamples: Number(weights.minimumSamples ?? 100),
  };

  const normalized = candidates.map(createValidationCandidate);
  const ranked = normalized.map((candidate) => {
    const validation = evaluateOverfitting(candidate, { minimumSamples: resolvedWeights.minimumSamples });
    return {
      candidate,
      validation,
      score: validation.canRank ? scoreCandidate(candidate, resolvedWeights) : null,
      featureSetMatchesChampion: !champion || champion.featureSetId === candidate.featureSetId,
    };
  }).sort((a, b) => {
    if (a.score === null) return 1;
    if (b.score === null) return -1;
    return b.score - a.score;
  });

  return {
    status: ranked.some((item) => item.validation.status === "BLOCKED") ? "REVIEW_REQUIRED" : "READY_FOR_HUMAN_REVIEW",
    ranked,
    recommendedCandidateKey: ranked.find((item) => item.score !== null && item.featureSetMatchesChampion)?.candidate.candidateKey ?? null,
    promotionAllowed: false,
    productionUpdateAllowed: false,
    safety: { ...PHASE44_SAFETY },
  };
}

export function compareChampionCandidate(championInput, candidateInput, thresholds = {}) {
  const champion = createValidationCandidate(championInput);
  const candidate = createValidationCandidate(candidateInput);
  const blockers = [];
  const reasons = [];
  const minPfGain = Number(thresholds.minimumProfitFactorGain ?? 0);
  const maxDdWorsening = Number(thresholds.maximumDrawdownWorsening ?? 0);

  if (champion.featureSetId !== candidate.featureSetId) blockers.push("FEATURE_SET_MISMATCH");
  if (champion.datasetHash !== candidate.datasetHash) blockers.push("DATASET_MISMATCH");
  if ((candidate.metrics.profitFactor ?? -Infinity) < (champion.metrics.profitFactor ?? -Infinity) + minPfGain) reasons.push("PROFIT_FACTOR_NOT_IMPROVED");
  if (Math.abs(candidate.metrics.maxDrawdown ?? 1) > Math.abs(champion.metrics.maxDrawdown ?? 1) + maxDdWorsening) reasons.push("MAX_DRAWDOWN_WORSE");
  if ((candidate.walkForward.stabilityScore ?? 0) < (champion.walkForward.stabilityScore ?? 0)) reasons.push("WALK_FORWARD_STABILITY_WORSE");

  return {
    status: blockers.length ? "BLOCKED" : reasons.length ? "REJECT_RECOMMENDED" : "REVIEW_PROMOTION",
    champion: champion.candidateKey,
    candidate: candidate.candidateKey,
    blockers,
    reasons,
    automaticPromotion: false,
    humanApprovalRequired: true,
    safety: { ...PHASE44_SAFETY },
  };
}

export function buildSelectionDashboard({ ranking, comparison = null } = {}) {
  const blockers = [];
  if (!ranking) blockers.push("RANKING_MISSING");
  if (ranking?.status === "REVIEW_REQUIRED") blockers.push("CANDIDATE_VALIDATION_BLOCKERS");
  if (comparison?.status === "BLOCKED") blockers.push(...comparison.blockers);

  return {
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    recommendedCandidateKey: ranking?.recommendedCandidateKey ?? null,
    ranking: ranking?.ranked?.map((item, index) => ({
      rank: index + 1,
      candidateKey: item.candidate.candidateKey,
      score: item.score,
      validationStatus: item.validation.status,
      blockers: item.validation.blockers,
      warnings: item.validation.warnings,
    })) ?? [],
    comparison,
    blockers: [...new Set(blockers)],
    automaticPromotion: false,
    productionUpdateAllowed: false,
    safety: { ...PHASE44_SAFETY },
  };
}

export { PHASE44_SAFETY };
