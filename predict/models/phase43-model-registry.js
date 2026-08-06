import { stableStringify } from "../data/phase41-data-lake.js";

const PHASE43_SAFETY = Object.freeze({
  mode: "MODEL_REGISTRY_REVIEW_ONLY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  automaticCandidatePromotionAllowed: false,
  automaticProductionUpdateAllowed: false,
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

function iso(value, field) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new TypeError(`${field} is invalid`);
  return date.toISOString();
}

function dateOnly(value, field) {
  return iso(value, field).slice(0, 10);
}

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeMetrics(metrics = {}) {
  const keys = [
    "winRate",
    "averageReturn",
    "medianReturn",
    "profitFactor",
    "maxDrawdown",
    "sharpeRatio",
    "sampleCount",
    "confidenceLow",
    "confidenceHigh",
  ];
  return Object.fromEntries(keys.map((key) => [key, finiteOrNull(metrics[key])]));
}

export function createModelVersion(input = {}) {
  const modelId = String(input.modelId ?? "").trim();
  const version = String(input.version ?? "").trim();
  const featureSetId = String(input.featureSetId ?? "").trim();
  if (!modelId) throw new TypeError("modelId is required");
  if (!version) throw new TypeError("version is required");
  if (!featureSetId) throw new TypeError("featureSetId is required");

  const normalized = {
    schemaVersion: 1,
    modelId,
    version,
    modelKey: `${modelId}:${version}`,
    status: ["EXPERIMENT", "CANDIDATE", "CHAMPION", "RETIRED"].includes(input.status)
      ? input.status
      : "EXPERIMENT",
    algorithm: String(input.algorithm ?? "UNKNOWN").trim() || "UNKNOWN",
    featureSetId,
    featureManifestHash: String(input.featureManifestHash ?? "").trim() || null,
    trainingWindow: {
      start: dateOnly(input.trainingWindow?.start, "trainingWindow.start"),
      end: dateOnly(input.trainingWindow?.end, "trainingWindow.end"),
    },
    validationWindow: {
      start: dateOnly(input.validationWindow?.start, "validationWindow.start"),
      end: dateOnly(input.validationWindow?.end, "validationWindow.end"),
    },
    testWindow: {
      start: dateOnly(input.testWindow?.start, "testWindow.start"),
      end: dateOnly(input.testWindow?.end, "testWindow.end"),
    },
    metrics: normalizeMetrics(input.metrics),
    artifactChecksum: String(input.artifactChecksum ?? "").trim() || null,
    datasetChecksum: String(input.datasetChecksum ?? "").trim() || null,
    createdAt: iso(input.createdAt ?? Date.now(), "createdAt"),
    createdBy: String(input.createdBy ?? "ARK_TERMINAL").trim() || "ARK_TERMINAL",
    notes: String(input.notes ?? "").trim() || null,
  };

  normalized.registryHash = fnv1a(stableStringify(normalized));
  return Object.freeze(normalized);
}

export function createModelRegistry({ models = [], generatedAt = new Date().toISOString() } = {}) {
  if (!Array.isArray(models)) throw new TypeError("models must be an array");
  const normalized = models.map(createModelVersion).sort((a, b) => a.modelKey.localeCompare(b.modelKey));
  const duplicates = [];
  const byKey = new Map();
  for (const model of normalized) {
    if (byKey.has(model.modelKey)) duplicates.push(model.modelKey);
    byKey.set(model.modelKey, model);
  }
  const records = [...byKey.values()].sort((a, b) => a.modelKey.localeCompare(b.modelKey));
  const championCount = records.filter((model) => model.status === "CHAMPION").length;
  const blockers = [];
  if (duplicates.length) blockers.push("DUPLICATE_MODEL_KEYS");
  if (championCount > 1) blockers.push("MULTIPLE_CHAMPIONS");

  return Object.freeze({
    schemaVersion: 1,
    generatedAt: iso(generatedAt, "generatedAt"),
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    modelCount: records.length,
    records: Object.freeze(records),
    blockers: Object.freeze([...new Set(blockers)]),
    registryChecksum: fnv1a(stableStringify(records)),
    safety: { ...PHASE43_SAFETY },
  });
}

export function evaluateTrainingRun(input = {}) {
  const blockers = [];
  const warnings = [];
  const model = createModelVersion(input.model);
  const metrics = model.metrics;
  const minimumSamples = Math.max(1, Number(input.minimumSamples ?? 100));
  const minimumProfitFactor = Number(input.minimumProfitFactor ?? 1);
  const maximumDrawdown = Number(input.maximumDrawdown ?? 0.25);
  const minimumConfidenceLow = Number(input.minimumConfidenceLow ?? -Infinity);

  if (!model.featureManifestHash) blockers.push("FEATURE_MANIFEST_HASH_MISSING");
  if (!model.datasetChecksum) blockers.push("DATASET_CHECKSUM_MISSING");
  if (!model.artifactChecksum) blockers.push("MODEL_ARTIFACT_CHECKSUM_MISSING");
  if (!Number.isFinite(metrics.sampleCount) || metrics.sampleCount < minimumSamples) blockers.push("INSUFFICIENT_SAMPLE_COUNT");
  if (!Number.isFinite(metrics.profitFactor) || metrics.profitFactor < minimumProfitFactor) blockers.push("PROFIT_FACTOR_BELOW_GATE");
  if (!Number.isFinite(metrics.maxDrawdown) || Math.abs(metrics.maxDrawdown) > maximumDrawdown) blockers.push("MAX_DRAWDOWN_EXCEEDED");
  if (Number.isFinite(metrics.confidenceLow) && metrics.confidenceLow < minimumConfidenceLow) blockers.push("CONFIDENCE_INTERVAL_BELOW_GATE");
  if (metrics.winRate === null) warnings.push("WIN_RATE_MISSING");
  if (metrics.averageReturn === null) warnings.push("AVERAGE_RETURN_MISSING");

  return {
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    canRegisterAsCandidate: blockers.length === 0,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    model,
    blockers: [...new Set(blockers)],
    warnings: [...new Set(warnings)],
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE43_SAFETY },
  };
}

export function compareChampionAndCandidate({ champion, candidate, gates = {} } = {}) {
  const blockers = [];
  const championModel = createModelVersion(champion);
  const candidateModel = createModelVersion(candidate);
  const requiredProfitFactorDelta = Number(gates.requiredProfitFactorDelta ?? 0);
  const requiredAverageReturnDelta = Number(gates.requiredAverageReturnDelta ?? 0);
  const allowedDrawdownIncrease = Number(gates.allowedDrawdownIncrease ?? 0);

  if (championModel.status !== "CHAMPION") blockers.push("CHAMPION_STATUS_INVALID");
  if (candidateModel.status !== "CANDIDATE") blockers.push("CANDIDATE_STATUS_INVALID");
  if (championModel.featureSetId !== candidateModel.featureSetId) blockers.push("FEATURE_SET_MISMATCH");

  const profitFactorDelta = (candidateModel.metrics.profitFactor ?? -Infinity) - (championModel.metrics.profitFactor ?? -Infinity);
  const averageReturnDelta = (candidateModel.metrics.averageReturn ?? -Infinity) - (championModel.metrics.averageReturn ?? -Infinity);
  const drawdownIncrease = Math.abs(candidateModel.metrics.maxDrawdown ?? Infinity) - Math.abs(championModel.metrics.maxDrawdown ?? Infinity);

  if (profitFactorDelta < requiredProfitFactorDelta) blockers.push("PROFIT_FACTOR_DELTA_BELOW_GATE");
  if (averageReturnDelta < requiredAverageReturnDelta) blockers.push("AVERAGE_RETURN_DELTA_BELOW_GATE");
  if (drawdownIncrease > allowedDrawdownIncrease) blockers.push("DRAWDOWN_DETERIORATION_EXCEEDED");

  return {
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    recommendation: blockers.length ? "KEEP_CHAMPION" : "REVIEW_CANDIDATE",
    profitFactorDelta,
    averageReturnDelta,
    drawdownIncrease,
    blockers: [...new Set(blockers)],
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE43_SAFETY },
  };
}

export function createRollbackPlan({ registry, targetModelKey, reason } = {}) {
  const target = registry?.records?.find((model) => model.modelKey === targetModelKey);
  const blockers = [];
  if (!target) blockers.push("ROLLBACK_TARGET_NOT_FOUND");
  if (!String(reason ?? "").trim()) blockers.push("ROLLBACK_REASON_REQUIRED");

  return {
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    targetModelKey: target?.modelKey ?? null,
    targetRegistryHash: target?.registryHash ?? null,
    reason: String(reason ?? "").trim() || null,
    executeAutomatically: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    blockers,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE43_SAFETY },
  };
}

export function createModelGovernanceDashboard({ registry, trainingEvaluations = [], comparisons = [], rollbackPlans = [] } = {}) {
  const blockers = [
    ...(registry?.blockers ?? []),
    ...trainingEvaluations.flatMap((item) => item.blockers ?? []),
    ...comparisons.flatMap((item) => item.blockers ?? []),
    ...rollbackPlans.flatMap((item) => item.blockers ?? []),
  ];
  const warnings = trainingEvaluations.flatMap((item) => item.warnings ?? []);
  const champions = registry?.records?.filter((model) => model.status === "CHAMPION") ?? [];
  const candidates = registry?.records?.filter((model) => model.status === "CANDIDATE") ?? [];

  return {
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    modelCount: registry?.modelCount ?? 0,
    championModelKey: champions[0]?.modelKey ?? null,
    candidateModelKeys: candidates.map((model) => model.modelKey),
    trainingRunCount: trainingEvaluations.length,
    comparisonCount: comparisons.length,
    rollbackPlanCount: rollbackPlans.length,
    blockers: [...new Set(blockers)],
    warnings: [...new Set(warnings)],
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE43_SAFETY },
  };
}

export { PHASE43_SAFETY };