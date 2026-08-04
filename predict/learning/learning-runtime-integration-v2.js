import {
  runLearningCycle,
} from "./learning-orchestrator-v2.js";

import {
  evaluateLearningCandidate,
} from "./learning-candidate-evaluator-v2.js";

import {
  createLearningPromotionRequest,
} from "./learning-promotion-controller-v2.js";

import {
  LearningAuditV2,
} from "./learning-audit-v2.js";

import {
  buildLearningReport,
} from "./learning-report-v2.js";

export const LEARNING_RUNTIME_INTEGRATION_V2_VERSION =
  "learning-runtime-integration-v2";

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function normalizeTimestamp(
  value,
) {
  const milliseconds =
    typeof value === "number"
      ? value
      : Date.parse(
          value ??
          new Date().toISOString(),
        );

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(
      "Learning runtime timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function createAudit({
  audit,
  eventType,
  payload,
  timestamp,
}) {
  audit.append({
    eventType,
    actor:
      "learning-runtime",

    payload,

    timestamp,
  });
}

export function runLearningRuntime({
  predictions = [],
  outcomes = [],
  currentState = null,
  modelId = "default-model",
  modelVersion = "unknown",
  now = new Date().toISOString(),
  dryRun = false,
  requireHumanApproval = true,
  qualityConfig = {},
  feedbackConfig = {},
  learningConfig = {},
  evaluationConfig = {},
  requestedBy = "learning-runtime",
} = {}) {
  const timestamp =
    normalizeTimestamp(
      now,
    );

  const audit =
    new LearningAuditV2();

  createAudit({
    audit,

    eventType:
      "LEARNING_RUNTIME_STARTED",

    payload: {
      modelId,
      modelVersion,
      predictionCount:
        predictions.length,
      outcomeCount:
        outcomes.length,
      dryRun,
    },

    timestamp,
  });

  const cycle =
    runLearningCycle({
      predictions,
      outcomes,
      state:
        currentState,
      modelId,
      modelVersion,
      now:
        timestamp,
      dryRun,
      qualityConfig,
      feedbackConfig,
      learningConfig,
    });

  createAudit({
    audit,

    eventType:
      "LEARNING_CYCLE_COMPLETED",

    payload: {
      cycleId:
        cycle.cycleId,
      status:
        cycle.status,
      applied:
        cycle.applied,
      revision:
        cycle.state?.revision ??
        null,
    },

    timestamp,
  });

  let evaluation = null;
  let promotion = null;

  const candidateState =
    cycle.candidateState ??
    (
      cycle.applied
        ? cycle.state
        : null
    );

  const baselineState =
    cycle.previousState ??
    currentState ??
    cycle.state;

  if (
    candidateState &&
    baselineState &&
    candidateState.revision >
      baselineState.revision
  ) {
    evaluation =
      evaluateLearningCandidate({
        currentState:
          baselineState,

        candidateState,

        requireHumanApproval,

        ...evaluationConfig,
      });

    createAudit({
      audit,

      eventType:
        "LEARNING_CANDIDATE_EVALUATED",

      payload: {
        decision:
          evaluation.decision,
        score:
          evaluation.evaluationScore,
        blockers:
          evaluation.blockers,
        warnings:
          evaluation.warnings,
      },

      timestamp,
    });

    if (
      [
        "PROMOTE",
        "REQUIRE_HUMAN_APPROVAL",
      ].includes(
        evaluation.decision,
      ) &&
      evaluation.blockers.length ===
        0
    ) {
      promotion =
        createLearningPromotionRequest({
          evaluation,
          currentState:
            baselineState,
          candidateState,
          requestedBy,
          createdAt:
            timestamp,
          metadata: {
            cycleId:
              cycle.cycleId,
          },
        });

      createAudit({
        audit,

        eventType:
          "LEARNING_PROMOTION_REQUESTED",

        payload: {
          requestId:
            promotion.id,
          status:
            promotion.status,
          currentRevision:
            promotion.current.revision,
          candidateRevision:
            promotion.candidate.revision,
        },

        timestamp,
      });
    }
  }

  const auditSummary =
    audit.summary();

  const report =
    buildLearningReport({
      state:
        candidateState ??
        cycle.state,

      evaluation:
        evaluation ??
        {},

      promotion:
        promotion ??
        {},

      audit:
        auditSummary,

      feedback:
        cycle.feedback ??
        {},

      quality:
        cycle.quality ??
        {},

      generatedAt:
        timestamp,

      generatedBy:
        "learning-runtime-v2",
    });

  createAudit({
    audit,

    eventType:
      "LEARNING_REPORT_CREATED",

    payload: {
      health:
        report.health.status,
      recommendation:
        report.recommendation.action,
    },

    timestamp,
  });

  const finalAudit =
    audit.summary();

  return {
    version:
      LEARNING_RUNTIME_INTEGRATION_V2_VERSION,

    status:
      cycle.status,

    applied:
      cycle.applied,

    cycle:
      clone(cycle),

    evaluation:
      clone(evaluation),

    promotion:
      clone(promotion),

    report:
      clone(report),

    audit: {
      entries:
        audit.list(),

      summary:
        finalAudit,
    },

    summary: {
      cycleStatus:
        cycle.status,

      learningApplied:
        cycle.applied,

      candidateEvaluated:
        evaluation !== null,

      promotionRequested:
        promotion !== null,

      promotionStatus:
        promotion?.status ??
        null,

      health:
        report.health.status,

      recommendation:
        report.recommendation.action,

      auditValid:
        finalAudit.valid,

      auditEntryCount:
        finalAudit.entryCount,
    },
  };
}

export class LearningRuntimeIntegrationV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  run(input = {}) {
    const result =
      runLearningRuntime({
        ...this.config,
        ...input,
      });

    this.history.push({
      timestamp:
        result.report.generatedAt,

      status:
        result.status,

      applied:
        result.applied,

      revision:
        result.cycle.state
          ?.revision ??
        null,

      health:
        result.summary.health,

      recommendation:
        result.summary
          .recommendation,
    });

    return clone(result);
  }

  getHistory() {
    return clone(
      this.history,
    );
  }

  resetHistory() {
    this.history = [];
    return [];
  }
}

export const learningRuntimeIntegrationV2 =
  new LearningRuntimeIntegrationV2();

export default runLearningRuntime;