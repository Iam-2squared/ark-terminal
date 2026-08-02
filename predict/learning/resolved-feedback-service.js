import { buildMachineLearningDataset } from "./dataset.js";
import { deriveOptimizedWeights } from "../analysis/weights.js";
import {
  buildPredictionWeightMetrics,
} from "../market-intelligence/prediction-feedback-adapter.js";
import { optimizeWeights } from "./weight-optimizer.js";
import { PREDICTION_FEATURE_KEYS } from "../market-intelligence/prediction-feature-model.js";

export const RESOLVED_FEEDBACK_VERSION = "resolved-feedback-v1";

function resolvedRecords(records) {
  return records.filter(
    (record) =>
      record?.status === "resolved" &&
      Number.isFinite(Number(record.actualReturn)),
  );
}

function reportId(rows) {
  const latest = [...rows]
    .sort((first, second) =>
      String(second.labelTimestamp).localeCompare(String(first.labelTimestamp)),
    )[0];

  return [
    "resolved-feedback",
    rows.length,
    latest?.labelTimestamp ?? "empty",
    latest?.id ?? "none",
  ].join(":");
}

function defaultMarketFeatureWeights() {
  return Object.fromEntries(PREDICTION_FEATURE_KEYS.map((key) => [key, 1]));
}

export function buildResolvedFeedback({
  records = [],
  currentWeights = {},
  currentMarketFeatureWeights = defaultMarketFeatureWeights(),
  generatedAt = new Date().toISOString(),
} = {}) {
  if (!Array.isArray(records)) {
    throw new TypeError("Resolved feedback records must be an array.");
  }

  const resolved = resolvedRecords(records);
  const learningDataset = buildMachineLearningDataset(resolved, {
    generatedAt,
  });
  const weightCandidate = deriveOptimizedWeights(resolved, currentWeights);
  const marketWeightMetrics = buildPredictionWeightMetrics(resolved);
  const marketFeatureCandidate = optimizeWeights({
    currentWeights: currentMarketFeatureWeights,
    learningResult: marketWeightMetrics,
  });
  const id = reportId(learningDataset.rows);

  return {
    id,
    version: RESOLVED_FEEDBACK_VERSION,
    generatedAt,
    status:
      learningDataset.rows.length === 0
        ? "empty"
        : weightCandidate.updated
          ? "candidate_ready"
          : "collecting",
    learningDataset,
    weightCandidate: {
      ...weightCandidate,
      applied: false,
      humanApprovalRequired: true,
    },
    marketFeatureCandidate: {
      ...marketFeatureCandidate,
      applied: false,
      humanApprovalRequired: true,
    },
    marketWeightMetrics,
    audit: {
      sourceRecordCount: records.length,
      resolvedCount: resolved.length,
      datasetRowCount: learningDataset.rows.length,
      snapshotCount: new Set(
        resolved
          .map((record) => record.marketIntelligenceSnapshot?.id)
          .filter(Boolean),
      ).size,
      futureInformationIncluded: false,
      activeWeightsChanged: false,
    },
    executionAllowed: false,
  };
}

export const ResolvedFeedbackServiceInternals = Object.freeze({
  resolvedRecords,
  reportId,
  defaultMarketFeatureWeights,
});

export default buildResolvedFeedback;
