import {
  BACKTEST_SPLIT,
  MINIMUM_OPTIMIZER_SAMPLES,
} from "../config.js";

export const MODEL_PROMOTION_GATE_VERSION = "model-promotion-gate-v1";

function partitionCount(dataset, name) {
  const rows = dataset?.partitions?.[name];
  return Array.isArray(rows) ? rows.length : 0;
}

function normalizedPolicy(policy = {}) {
  return {
    minimumTotalSamples: Math.max(
      MINIMUM_OPTIMIZER_SAMPLES,
      Math.floor(Number(policy.minimumTotalSamples) || 0),
    ),
    minimumValidationSamples: Math.max(
      BACKTEST_SPLIT.minimumPartitionSamples,
      Math.floor(Number(policy.minimumValidationSamples) || 0),
    ),
    minimumTestSamples: Math.max(
      BACKTEST_SPLIT.minimumPartitionSamples,
      Math.floor(Number(policy.minimumTestSamples) || 0),
    ),
  };
}

export function evaluateModelPromotionCandidate(
  feedbackReport = {},
  { policy = {} } = {},
) {
  const requirements = normalizedPolicy(policy);
  const dataset = feedbackReport.learningDataset ?? {};
  const totalSamples = Array.isArray(dataset.rows) ? dataset.rows.length : 0;
  const validationSamples = partitionCount(dataset, "validation");
  const testSamples = partitionCount(dataset, "test");
  const candidateReady = feedbackReport.weightCandidate?.updated === true;
  const futureInformationIncluded =
    feedbackReport.audit?.futureInformationIncluded === true ||
    (Array.isArray(dataset.rows) &&
      dataset.rows.some(
        (row) => row?.audit?.futureInformationIncluded === true,
      ));
  const checks = {
    totalSamples:
      totalSamples >= requirements.minimumTotalSamples,
    validationSamples:
      validationSamples >= requirements.minimumValidationSamples,
    testSamples:
      testSamples >= requirements.minimumTestSamples,
    candidateReady,
    noFutureInformation: !futureInformationIncluded,
    activeWeightsUnchanged:
      feedbackReport.audit?.activeWeightsChanged !== true &&
      feedbackReport.weightCandidate?.applied !== true,
  };
  const eligible = Object.values(checks).every(Boolean);
  const reasons = [];

  if (!checks.totalSamples) {
    reasons.push(
      `確定データが${requirements.minimumTotalSamples}件未満です。`,
    );
  }
  if (!checks.validationSamples) {
    reasons.push(
      `検証データが${requirements.minimumValidationSamples}件未満です。`,
    );
  }
  if (!checks.testSamples) {
    reasons.push(
      `最終テストデータが${requirements.minimumTestSamples}件未満です。`,
    );
  }
  if (!checks.candidateReady) reasons.push("ウェイト候補が未生成です。");
  if (!checks.noFutureInformation) reasons.push("未来情報混入を検出しました。");
  if (!checks.activeWeightsUnchanged) {
    reasons.push("候補評価前に現行ウェイトが変更されています。");
  }

  return {
    version: MODEL_PROMOTION_GATE_VERSION,
    status: eligible ? "eligible_for_validation" : "collecting_evidence",
    eligible,
    candidate: eligible
      ? {
          sourceFeedbackId: feedbackReport.id,
          weights: { ...feedbackReport.weightCandidate.weights },
          generatedAt: feedbackReport.generatedAt,
          requiresBacktestValidation: true,
          requiresHumanApproval: true,
          executionAllowed: false,
        }
      : null,
    checks,
    evidence: {
      totalSamples,
      validationSamples,
      testSamples,
      trainingSamples: partitionCount(dataset, "training"),
    },
    requirements,
    reasons,
    promotionAllowed: false,
    requiresBacktestValidation: true,
    requiresHumanApproval: true,
    executionAllowed: false,
  };
}

export const ModelPromotionGateInternals = Object.freeze({
  partitionCount,
  normalizedPolicy,
});

export default evaluateModelPromotionCandidate;
