import {
  buildLearningFeedback,
} from "./learning-feedback-pipeline-v2.js";

import {
  evaluateLearningDatasetQuality,
} from "./learning-dataset-quality-gate-v2.js";

import {
  createInitialLearningState,
  createLearningPatch,
  updateLearningState,
} from "./ai-learning-core-v2.js";

export const LEARNING_ORCHESTRATOR_V2_VERSION =
  "learning-orchestrator-v2";

function normalizeText(
  value,
  fallback = "",
) {
  const text =
    String(
      value ??
      fallback,
    ).trim();

  return text || fallback;
}

function normalizeTimestamp(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const timestamp =
    typeof value === "number"
      ? value
      : Date.parse(value);

  return Number.isFinite(timestamp)
    ? timestamp
    : null;
}

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function createAuditEntry({
  cycleId,
  status,
  stage,
  message,
  now,
  details = {},
}) {
  return {
    version:
      LEARNING_ORCHESTRATOR_V2_VERSION,

    cycleId,

    status,

    stage,

    message,

    timestamp:
      new Date(now).toISOString(),

    details: {
      ...details,
    },
  };
}

function createCycleId({
  modelId,
  now,
}) {
  return [
    "learning-cycle",
    normalizeText(
      modelId,
      "default-model",
    ),
    now,
  ].join(":");
}

function createFailure({
  cycleId,
  stage,
  code,
  message,
  state,
  feedback,
  quality,
  auditTrail,
  now,
}) {
  const audit =
    createAuditEntry({
      cycleId,

      status:
        "FAILED",

      stage,

      message,

      now,

      details: {
        code,
      },
    });

  return {
    version:
      LEARNING_ORCHESTRATOR_V2_VERSION,

    cycleId,

    status:
      "FAILED",

    applied:
      false,

    stage,

    code,

    message,

    state:
      clone(state),

    patch:
      createLearningPatch(
        state,
      ),

    feedback:
      feedback ??
      null,

    quality:
      quality ??
      null,

    auditTrail: [
      ...auditTrail,
      audit,
    ],
  };
}

export function runLearningCycle({
  predictions = [],
  outcomes = [],
  existingRecordIds = [],
  state = null,
  modelId = "default-model",
  modelVersion = "unknown",
  now = Date.now(),
  dryRun = false,
  requireQualityPass = true,
  feedbackConfig = {},
  qualityConfig = {},
  learningConfig = {},
} = {}) {
  if (!Array.isArray(predictions)) {
    throw new TypeError(
      "Learning cycle predictions must be an array.",
    );
  }

  if (!Array.isArray(outcomes)) {
    throw new TypeError(
      "Learning cycle outcomes must be an array.",
    );
  }

  if (!Array.isArray(existingRecordIds)) {
    throw new TypeError(
      "Learning cycle existingRecordIds must be an array.",
    );
  }

  const normalizedNow =
    normalizeTimestamp(now);

  if (normalizedNow === null) {
    throw new TypeError(
      "Learning cycle now value is invalid.",
    );
  }

  const cycleId =
    createCycleId({
      modelId,
      now:
        normalizedNow,
    });

  const currentState =
    state &&
    typeof state ===
      "object"
      ? clone(state)
      : createInitialLearningState({
          modelId,

          modelVersion,

          createdAt:
            new Date(
              normalizedNow,
            ).toISOString(),
        });

  const auditTrail = [
    createAuditEntry({
      cycleId,

      status:
        "STARTED",

      stage:
        "INITIALIZATION",

      message:
        "Learning cycle started.",

      now:
        normalizedNow,

      details: {
        dryRun:
          dryRun === true,

        predictionCount:
          predictions.length,

        outcomeCount:
          outcomes.length,
      },
    }),
  ];

  let feedback;

  try {
    feedback =
      buildLearningFeedback({
        predictions,

        outcomes,

        existingRecordIds,

        now:
          normalizedNow,

        ...feedbackConfig,
      });
  }
  catch (error) {
    return createFailure({
      cycleId,

      stage:
        "FEEDBACK",

      code:
        "FEEDBACK_PIPELINE_ERROR",

      message:
        error.message,

      state:
        currentState,

      feedback:
        null,

      quality:
        null,

      auditTrail,

      now:
        normalizedNow,
    });
  }

  auditTrail.push(
    createAuditEntry({
      cycleId,

      status:
        feedback.records.length >
          0
          ? "PASSED"
          : "NO_DATA",

      stage:
        "FEEDBACK",

      message:
        feedback.records.length >
          0
          ? "Learning feedback records created."
          : "No resolved learning feedback available.",

      now:
        normalizedNow,

      details: {
        createdCount:
          feedback.summary
            .createdCount,

        pendingCount:
          feedback.summary
            .pendingCount,

        rejectedCount:
          feedback.summary
            .rejectedCount,
      },
    }),
  );

  if (
    feedback.records.length ===
    0
  ) {
    return {
      version:
        LEARNING_ORCHESTRATOR_V2_VERSION,

      cycleId,

      status:
        "NO_DATA",

      applied:
        false,

      stage:
        "FEEDBACK",

      code:
        "NO_LEARNING_RECORDS",

      message:
        "No completed prediction outcomes are available for learning.",

      state:
        currentState,

      patch:
        createLearningPatch(
          currentState,
        ),

      feedback,

      quality:
        null,

      auditTrail,
    };
  }

  let quality;

  try {
    quality =
      evaluateLearningDatasetQuality({
        records:
          feedback.records,

        now:
          normalizedNow,

        ...qualityConfig,
      });
  }
  catch (error) {
    return createFailure({
      cycleId,

      stage:
        "QUALITY_GATE",

      code:
        "QUALITY_GATE_ERROR",

      message:
        error.message,

      state:
        currentState,

      feedback,

      quality:
        null,

      auditTrail,

      now:
        normalizedNow,
    });
  }

  auditTrail.push(
    createAuditEntry({
      cycleId,

      status:
        quality.passed
          ? "PASSED"
          : "FAILED",

      stage:
        "QUALITY_GATE",

      message:
        quality.passed
          ? "Learning dataset passed quality checks."
          : "Learning dataset failed quality checks.",

      now:
        normalizedNow,

      details: {
        qualityScore:
          quality.qualityScore,

        acceptedCount:
          quality.summary
            .acceptedCount,

        rejectedCount:
          quality.summary
            .rejectedCount,

        criticalCount:
          quality.summary
            .criticalCount,

        errorCount:
          quality.summary
            .errorCount,

        warningCount:
          quality.summary
            .warningCount,
      },
    }),
  );

  if (
    requireQualityPass &&
    !quality.passed
  ) {
    return {
      version:
        LEARNING_ORCHESTRATOR_V2_VERSION,

      cycleId,

      status:
        "BLOCKED",

      applied:
        false,

      stage:
        "QUALITY_GATE",

      code:
        "QUALITY_GATE_BLOCKED",

      message:
        "Learning update was blocked by the dataset quality gate.",

      state:
        currentState,

      patch:
        createLearningPatch(
          currentState,
        ),

      feedback,

      quality,

      auditTrail,
    };
  }

  if (
    quality.acceptedRecords
      .length ===
    0
  ) {
    return {
      version:
        LEARNING_ORCHESTRATOR_V2_VERSION,

      cycleId,

      status:
        "BLOCKED",

      applied:
        false,

      stage:
        "QUALITY_GATE",

      code:
        "NO_ACCEPTED_RECORDS",

      message:
        "No accepted learning records remain after quality checks.",

      state:
        currentState,

      patch:
        createLearningPatch(
          currentState,
        ),

      feedback,

      quality,

      auditTrail,
    };
  }

  let candidateState;

  try {
    candidateState =
      updateLearningState({
        state:
          currentState,

        records:
          quality.acceptedRecords,

        updatedAt:
          new Date(
            normalizedNow,
          ).toISOString(),

        ...learningConfig,
      });
  }
  catch (error) {
    return createFailure({
      cycleId,

      stage:
        "LEARNING_UPDATE",

      code:
        "LEARNING_UPDATE_ERROR",

      message:
        error.message,

      state:
        currentState,

      feedback,

      quality,

      auditTrail,

      now:
        normalizedNow,
    });
  }

  auditTrail.push(
    createAuditEntry({
      cycleId,

      status:
        "PASSED",

      stage:
        "LEARNING_UPDATE",

      message:
        "Candidate learning state created.",

      now:
        normalizedNow,

      details: {
        previousRevision:
          currentState.revision,

        candidateRevision:
          candidateState.revision,

        recordCount:
          quality.acceptedRecords
            .length,

        frozen:
          candidateState
            .safeguards
            .frozen,

        promotionAllowed:
          candidateState
            .safeguards
            .promotionAllowed,
      },
    }),
  );

  if (
    candidateState
      .safeguards
      .rollbackRequired
  ) {
    auditTrail.push(
      createAuditEntry({
        cycleId,

        status:
          "BLOCKED",

        stage:
          "SAFEGUARDS",

        message:
          "Candidate state requires rollback and was not applied.",

        now:
          normalizedNow,

        details: {
          blockers:
            candidateState
              .safeguards
              .blockers,
        },
      }),
    );

    return {
      version:
        LEARNING_ORCHESTRATOR_V2_VERSION,

      cycleId,

      status:
        "ROLLBACK_REQUIRED",

      applied:
        false,

      stage:
        "SAFEGUARDS",

      code:
        "LEARNING_ROLLBACK_REQUIRED",

      message:
        "Learning safeguards require rollback.",

      state:
        currentState,

      candidateState,

      patch:
        createLearningPatch(
          currentState,
        ),

      candidatePatch:
        createLearningPatch(
          candidateState,
        ),

      feedback,

      quality,

      auditTrail,
    };
  }

  if (dryRun) {
    auditTrail.push(
      createAuditEntry({
        cycleId,

        status:
          "DRY_RUN",

        stage:
          "COMMIT",

        message:
          "Dry run completed without applying the candidate state.",

        now:
          normalizedNow,

        details: {
          candidateRevision:
            candidateState.revision,
        },
      }),
    );

    return {
      version:
        LEARNING_ORCHESTRATOR_V2_VERSION,

      cycleId,

      status:
        "DRY_RUN",

      applied:
        false,

      stage:
        "COMMIT",

      code:
        "DRY_RUN_COMPLETE",

      message:
        "Candidate learning state was evaluated but not applied.",

      state:
        currentState,

      candidateState,

      patch:
        createLearningPatch(
          currentState,
        ),

      candidatePatch:
        createLearningPatch(
          candidateState,
        ),

      feedback,

      quality,

      auditTrail,
    };
  }

  auditTrail.push(
    createAuditEntry({
      cycleId,

      status:
        "COMPLETED",

      stage:
        "COMMIT",

      message:
        "Candidate learning state applied.",

      now:
        normalizedNow,

      details: {
        revision:
          candidateState.revision,

        baseWeight:
          candidateState
            .weights
            .base,

        acceptedRecordCount:
          quality.acceptedRecords
            .length,
      },
    }),
  );

  return {
    version:
      LEARNING_ORCHESTRATOR_V2_VERSION,

    cycleId,

    status:
      "COMPLETED",

    applied:
      true,

    stage:
      "COMMIT",

    code:
      "LEARNING_UPDATE_APPLIED",

    message:
      "Learning cycle completed successfully.",

    state:
      candidateState,

    previousState:
      currentState,

    patch:
      createLearningPatch(
        candidateState,
      ),

    feedback,

    quality,

    auditTrail,

    summary: {
      predictionCount:
        predictions.length,

      outcomeCount:
        outcomes.length,

      feedbackRecordCount:
        feedback.records.length,

      acceptedRecordCount:
        quality.acceptedRecords
          .length,

      rejectedRecordCount:
        quality.rejectedRecords
          .length,

      previousRevision:
        currentState.revision,

      revision:
        candidateState.revision,

      dryRun:
        false,
    },
  };
}

export class LearningOrchestratorV2 {
  constructor({
    state = null,
    config = {},
  } = {}) {
    this.config = {
      ...config,
    };

    this.state =
      state &&
      typeof state ===
        "object"
        ? clone(state)
        : createInitialLearningState({
            modelId:
              config.modelId ??
              "default-model",

            modelVersion:
              config.modelVersion ??
              "unknown",

            createdAt:
              config.createdAt,
          });

    this.processedRecordIds =
      new Set(
        config.processedRecordIds ??
        [],
      );

    this.history = [];
  }

  run(input = {}) {
    const result =
      runLearningCycle({
        ...this.config,
        ...input,

        state:
          this.state,

        existingRecordIds: [
          ...this.processedRecordIds,
          ...(
            input.existingRecordIds ??
            []
          ),
        ],
      });

    if (
      result.applied &&
      result.state
    ) {
      this.state =
        clone(
          result.state,
        );

      for (
        const record
        of result.feedback
          ?.records ??
        []
      ) {
        this.processedRecordIds.add(
          record.id,
        );
      }
    }

    this.history.push({
      cycleId:
        result.cycleId,

      status:
        result.status,

      applied:
        result.applied,

      revision:
        result.state
          ?.revision ??
        this.state.revision,

      timestamp:
        result.auditTrail[
          result.auditTrail.length -
          1
        ]?.timestamp ??
        null,
    });

    return clone(result);
  }

  getState() {
    return clone(
      this.state,
    );
  }

  getPatch() {
    return createLearningPatch(
      this.state,
    );
  }

  getHistory() {
    return clone(
      this.history,
    );
  }

  reset({
    state = null,
    clearProcessedRecords = true,
    clearHistory = true,
  } = {}) {
    this.state =
      state
        ? clone(state)
        : createInitialLearningState({
            modelId:
              this.config.modelId ??
              "default-model",

            modelVersion:
              this.config.modelVersion ??
              "unknown",
          });

    if (clearProcessedRecords) {
      this.processedRecordIds.clear();
    }

    if (clearHistory) {
      this.history = [];
    }

    return this.getState();
  }
}

export const learningOrchestratorV2 =
  new LearningOrchestratorV2();

export default runLearningCycle;