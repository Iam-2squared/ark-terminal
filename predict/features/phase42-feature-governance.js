import {
  PHASE42_SAFETY,
  auditFeatureStoreShard,
  validateFeatureStoreManifest,
} from "./phase42-feature-store.js";

const PHASE42_GOVERNANCE_SAFETY = Object.freeze({
  ...PHASE42_SAFETY,
  mode: "FEATURE_GOVERNANCE_REVIEW_ONLY",
  automaticCandidateCreationAllowed: false,
  humanApprovalRequired: true,
});

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeFeatureNames(records = []) {
  return [...new Set(records.flatMap((record) => Object.keys(record?.features ?? {})))].sort();
}

export function analyzeFeatureDrift({ baselineRecords = [], currentRecords = [], thresholds = {} } = {}) {
  const blockers = [];
  const warnings = [];
  const maximumMeanShift = Math.max(0, Number(thresholds.maximumMeanShift ?? 0.25));
  const minimumSamples = Math.max(1, Number(thresholds.minimumSamples ?? 2));
  const featureNames = normalizeFeatureNames([...baselineRecords, ...currentRecords]);

  if (!baselineRecords.length) blockers.push("BASELINE_FEATURES_MISSING");
  if (!currentRecords.length) blockers.push("CURRENT_FEATURES_MISSING");

  const features = featureNames.map((name) => {
    const baseline = baselineRecords
      .map((record) => finiteOrNull(record?.features?.[name]))
      .filter(Number.isFinite);
    const current = currentRecords
      .map((record) => finiteOrNull(record?.features?.[name]))
      .filter(Number.isFinite);
    const baselineMean = baseline.length ? baseline.reduce((sum, value) => sum + value, 0) / baseline.length : null;
    const currentMean = current.length ? current.reduce((sum, value) => sum + value, 0) / current.length : null;
    const scale = Number.isFinite(baselineMean) ? Math.max(Math.abs(baselineMean), 1e-9) : null;
    const normalizedMeanShift = Number.isFinite(baselineMean) && Number.isFinite(currentMean)
      ? Math.abs(currentMean - baselineMean) / scale
      : null;
    const enoughSamples = baseline.length >= minimumSamples && current.length >= minimumSamples;
    const status = !enoughSamples
      ? "INSUFFICIENT_DATA"
      : normalizedMeanShift > maximumMeanShift
        ? "DRIFT_REVIEW"
        : "STABLE";

    if (!enoughSamples) warnings.push(`INSUFFICIENT_DRIFT_SAMPLES:${name}`);
    if (status === "DRIFT_REVIEW") warnings.push(`FEATURE_DRIFT_REVIEW:${name}`);

    return {
      name,
      baselineCount: baseline.length,
      currentCount: current.length,
      baselineMean,
      currentMean,
      normalizedMeanShift,
      status,
    };
  });

  return {
    status: blockers.length ? "BLOCKED" : warnings.length ? "REVIEW" : "STABLE",
    canAutoApplyChanges: false,
    features,
    blockers: [...new Set(blockers)],
    warnings: [...new Set(warnings)],
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE42_GOVERNANCE_SAFETY },
  };
}

export function evaluateFeatureLineage({ manifest, shards = [] } = {}) {
  const validation = validateFeatureStoreManifest(manifest, shards);
  const blockers = [...validation.blockers];
  const warnings = [];

  for (const shard of shards) {
    for (const record of shard?.records ?? []) {
      if (!record.sourceShardId) blockers.push(`SOURCE_SHARD_MISSING:${record.featureKey}`);
      if (!record.sourceChecksum) blockers.push(`SOURCE_CHECKSUM_MISSING:${record.featureKey}`);
      if (!record.contentHash) blockers.push(`FEATURE_CONTENT_HASH_MISSING:${record.featureKey}`);
    }
  }

  if (!manifest?.generatedAt) warnings.push("MANIFEST_GENERATED_AT_MISSING");

  return {
    status: blockers.length ? "BLOCKED" : warnings.length ? "WARNING" : "VALID",
    canUseForTrainingReview: blockers.length === 0,
    blockers: [...new Set(blockers)],
    warnings: [...new Set(warnings)],
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE42_GOVERNANCE_SAFETY },
  };
}

export function buildFeatureGovernanceDashboard({ manifest, shards = [], baselineRecords = [], currentRecords = [] } = {}) {
  const audits = shards.map((shard) => ({
    shardId: shard?.shardId ?? null,
    audit: auditFeatureStoreShard(shard),
  }));
  const lineage = evaluateFeatureLineage({ manifest, shards });
  const drift = analyzeFeatureDrift({ baselineRecords, currentRecords });
  const blockers = [
    ...lineage.blockers,
    ...drift.blockers,
    ...audits.flatMap((entry) => entry.audit.blockers),
  ];
  const warnings = [
    ...lineage.warnings,
    ...drift.warnings,
    ...audits.flatMap((entry) => entry.audit.warnings),
  ];

  return Object.freeze({
    mode: "READ_ONLY_FEATURE_REVIEW",
    state: blockers.length ? "BLOCKED" : warnings.length ? "READY_FOR_HUMAN_REVIEW" : "READY_FOR_HUMAN_REVIEW",
    manifestStatus: manifest?.status ?? "UNKNOWN",
    shardCount: shards.length,
    recordCount: shards.reduce((sum, shard) => sum + Number(shard?.recordCount ?? 0), 0),
    auditSummary: Object.freeze(audits),
    lineage,
    drift,
    blockers: Object.freeze([...new Set(blockers)]),
    warnings: Object.freeze([...new Set(warnings)]),
    recommendedAction: blockers.length
      ? "STOP_AND_REVIEW_FEATURE_DATA"
      : warnings.length
        ? "REVIEW_WARNINGS_BEFORE_MODEL_USE"
        : "HUMAN_REVIEW_ONLY",
    canCreateOrders: false,
    canTransmitOrders: false,
    canPromoteAutomatically: false,
    canUpdateProduction: false,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE42_GOVERNANCE_SAFETY },
  });
}

export { PHASE42_GOVERNANCE_SAFETY };
