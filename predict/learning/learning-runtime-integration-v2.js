import {
  combineRegimeAdaptivePredictions,
} from "../analysis/regime-adaptive-ensemble-v2.js";

import {
  learnRegimePerformance,
  createEnsembleLearningPatch,
} from "./regime-performance-learning-v2.js";

import {
  updateOnlineModelWeights,
  createWeightPatch,
} from "./online-weight-updater-v2.js";

import {
  detectModelDriftBatch,
} from "./concept-drift-detector-v2.js";

import {
  evaluateModelPromotion,
} from "./model-promotion-gate-v2.js";

import {
  evaluateChampionChallenger,
} from "./champion-challenger-v2.js";

import {
  evaluateModelRollback,
} from "./model-rollback-manager-v2.js";

export const LEARNING_RUNTIME_INTEGRATION_V2_VERSION =
  "learning-runtime-integration-v2";

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function round(
  value,
  digits = 4,
) {
  if (!Number.isFinite(value)) {
    return value;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value * factor,
    ) / factor
  );
}

function safeArray(value) {
  return Array.isArray(value)
    ? value
    : [];
}

function modelIdOf(model) {
  return String(
    model?.id ??
    model?.modelId ??
    model?.name ??
    "",
  ).trim();
}

function mergeModelPatches({
  models,
  learningPatch,
  weightPatch,
}) {
  const learningById =
    new Map(
      safeArray(
        learningPatch?.models,
      ).map(
        (
          model,
        ) => [
          modelIdOf(model),
          model,
        ],
      ),
    );

  const weightById =
    new Map(
      safeArray(
        weightPatch?.models,
      ).map(
        (
          model,
        ) => [
          modelIdOf(model),
          model,
        ],
      ),
    );

  return safeArray(models).map(
    (
      model,
    ) => {
      const id =
        modelIdOf(model);

      const learned =
        learningById.get(id) ??
        {};

      const weighted =
        weightById.get(id) ??
        {};

      return {
        ...model,

        id,

        historicalAccuracy:
          finiteOrNull(
            learned.historicalAccuracy,
          ) ??
          finiteOrNull(
            model.historicalAccuracy,
          ) ??
          50,

        regimePerformance: {
          ...(
            model.regimePerformance ??
            {}
          ),

          ...(
            learned.regimePerformance ??
            {}
          ),
        },

        regimeMultipliers: {
          ...(
            model.regimeMultipliers ??
            {}
          ),

          ...(
            learned.regimeMultipliers ??
            {}
          ),

          ...(
            weighted.regimeWeights ??
            {}
          ),
        },

        weight:
          finiteOrNull(
            weighted.weight,
          ) ??
          finiteOrNull(
            model.weight,
          ) ??
          1,

        enabled:
          weighted.enabled ??
          model.enabled ??
          true,

        learningRecommendation:
          learned.recommendation ??
          null,

        performanceScore:
          finiteOrNull(
            learned.performanceScore,
          ),
      };
    },
  );
}

function applyLearningToEnsembleModels(
  models,
) {
  return safeArray(models).map(
    (
      model,
    ) => {
      const regimePerformance = {
        ...(
          model.regimePerformance ??
          {}
        ),
      };

      for (
        const [
          regime,
          multiplier,
        ]
        of Object.entries(
          model.regimeMultipliers ??
          {},
        )
      ) {
        if (
          finiteOrNull(
            regimePerformance[
              regime
            ],
          ) === null
        ) {
          regimePerformance[
            regime
          ] =
            (
              finiteOrNull(
                multiplier,
              ) ??
              1
            ) *
            50;
        }
      }

      return {
        ...model,

        regimePerformance,
      };
    },
  );
}

function findDriftForModel(
  driftBatch,
  modelId,
) {
  return safeArray(
    driftBatch?.results,
  ).find(
    (
      result,
    ) =>
      result.modelId ===
      modelId,
  ) ?? {
    ready:
      false,

    driftDetected:
      false,

    driftScore:
      0,

    driftLevel:
      "UNKNOWN",

    recommendation: {
      allowPromotion:
        false,

      action:
        "COLLECT_MORE_DATA",
    },
  };
}

function findLearningForModel(
  learning,
  modelId,
) {
  return safeArray(
    learning?.models,
  ).find(
    (
      model,
    ) =>
      model.modelId ===
      modelId,
  ) ?? {
    ready:
      false,

    recommendation: {
      action:
        "HOLD",
    },

    overall: {
      sampleCount:
        0,

      performanceScore:
        null,
    },
  };
}

function buildPromotionMetrics({
  learningModel,
  validationMetrics,
}) {
  const overall =
    learningModel?.overall ??
    {};

  return {
    accuracy:
      finiteOrNull(
        validationMetrics?.accuracy ??
        overall.weightedAccuracy ??
        overall.rawAccuracy,
      ),

    confidenceCalibrationError:
      finiteOrNull(
        validationMetrics
          ?.confidenceCalibrationError ??
        overall.calibrationError,
      ),

    profitFactor:
      finiteOrNull(
        validationMetrics
          ?.profitFactor ??
        overall.profitFactor,
      ),

    maximumDrawdown:
      finiteOrNull(
        validationMetrics
          ?.maximumDrawdown ??
        overall.maximumDrawdown,
      ),

    averageReturn:
      finiteOrNull(
        validationMetrics
          ?.averageReturn ??
        overall.averageReturn,
      ),

    sampleCount:
      finiteOrNull(
        validationMetrics
          ?.sampleCount ??
        overall.sampleCount,
      ) ?? 0,

    stabilityScore:
      finiteOrNull(
        validationMetrics
          ?.stabilityScore ??
        overall.performanceScore,
      ),

    monteCarloSuccessRate:
      finiteOrNull(
        validationMetrics
          ?.monteCarloSuccessRate,
      ),
  };
}

function buildRuntimeDecision({
  ensemble,
  promotion,
  challenger,
  rollback,
  driftBatch,
}) {
  const blockers = [];

  if (
    ensemble.ready !== true
  ) {
    blockers.push(
      "ENSEMBLE_NOT_READY",
    );
  }

  if (
    ensemble.approved !== true
  ) {
    blockers.push(
      "ENSEMBLE_NOT_APPROVED",
    );
  }

  if (
    driftBatch.driftedModelCount > 0
  ) {
    blockers.push(
      "MODEL_DRIFT_DETECTED",
    );
  }

  if (
    promotion &&
    promotion.decision !==
      "PROMOTE"
  ) {
    blockers.push(
      "PROMOTION_GATE_BLOCKED",
    );
  }

  if (
    challenger &&
    challenger.decision ===
      "REJECT_CHALLENGER"
  ) {
    blockers.push(
      "CHALLENGER_REJECTED",
    );
  }

  if (
    rollback &&
    rollback.action ===
      "ROLLBACK"
  ) {
    blockers.push(
      "ROLLBACK_REQUIRED",
    );
  }

  let action =
    "CONTINUE";

  if (
    rollback?.action ===
    "ROLLBACK"
  ) {
    action =
      "ROLLBACK";
  } else if (
    rollback?.action ===
      "FREEZE" ||
    driftBatch.driftedModelCount > 0
  ) {
    action =
      "FREEZE";
  } else if (
    promotion?.decision ===
      "PROMOTE" &&
    challenger?.decision ===
      "PROMOTE_CHALLENGER"
  ) {
    action =
      "PROMOTION_READY";
  } else if (
    ensemble.approved !== true
  ) {
    action =
      "HOLD";
  }

  return {
    action,

    approved:
      blockers.length === 0,

    blockerCount:
      blockers.length,

    blockers,
  };
}

export function runLearningRuntimeIntegration({
  models = [],
  learningRecords = [],
  outcomes = [],
  driftRecords = [],
  marketContext = {},
  regime = null,

  candidateModel = null,
  championModel = null,
  fallbackModel = null,

  promotionMetrics = {},
  benchmarkMetrics = {},

  championChallengerRecords = [],

  activeMetrics = {},
  baselineMetrics = {},

  learningConfig = {},
  weightConfig = {},
  driftConfig = {},
  ensembleConfig = {},
  promotionConfig = {},
  challengerConfig = {},
  rollbackConfig = {},
} = {}) {
  if (!Array.isArray(models)) {
    throw new TypeError(
      "Learning runtime models must be an array.",
    );
  }

  if (!models.length) {
    return {
      version:
        LEARNING_RUNTIME_INTEGRATION_V2_VERSION,

      ready:
        false,

      action:
        "HOLD",

      reason:
        "NO_MODELS",

      models:
        [],

      summary: {
        modelCount:
          0,

        outcomeCount:
          safeArray(
            outcomes,
          ).length,

        learningRecordCount:
          safeArray(
            learningRecords,
          ).length,

        driftRecordCount:
          safeArray(
            driftRecords,
          ).length,
      },
    };
  }

  const learning =
    learnRegimePerformance({
      ...learningConfig,

      records:
        safeArray(
          learningRecords,
        ),
    });

  const learningPatch =
    createEnsembleLearningPatch(
      learning,
    );

  const weightUpdate =
    updateOnlineModelWeights({
      ...weightConfig,

      models,

      outcomes:
        safeArray(
          outcomes,
        ),
    });

  const weightPatch =
    createWeightPatch(
      weightUpdate,
    );

  const learnedModels =
    mergeModelPatches({
      models,

      learningPatch,

      weightPatch,
    });

  const ensembleModels =
    applyLearningToEnsembleModels(
      learnedModels,
    );

  const ensemble =
    combineRegimeAdaptivePredictions({
      ...ensembleConfig,

      models:
        ensembleModels,

      marketContext,

      regime,
    });

  const driftBatch =
    detectModelDriftBatch({
      models:
        learnedModels,

      records:
        safeArray(
          driftRecords,
        ),

      config:
        driftConfig,
    });

  let promotion =
    null;

  if (candidateModel) {
    const candidateId =
      modelIdOf(
        candidateModel,
      );

    const candidateLearning =
      findLearningForModel(
        learning,
        candidateId,
      );

    const candidateDrift =
      findDriftForModel(
        driftBatch,
        candidateId,
      );

    promotion =
      evaluateModelPromotion({
        ...promotionConfig,

        candidate:
          candidateModel,

        metrics:
          buildPromotionMetrics({
            learningModel:
              candidateLearning,

            validationMetrics:
              promotionMetrics,
          }),

        benchmark:
          benchmarkMetrics,

        drift:
          candidateDrift,

        learning:
          candidateLearning,
      });
  }

  let challenger =
    null;

  if (
    championModel &&
    candidateModel
  ) {
    challenger =
      evaluateChampionChallenger({
        ...challengerConfig,

        champion:
          championModel,

        challenger:
          candidateModel,

        records:
          safeArray(
            championChallengerRecords,
          ),
      });
  }

  let rollback =
    null;

  if (
    championModel &&
    fallbackModel
  ) {
    const championId =
      modelIdOf(
        championModel,
      );

    rollback =
      evaluateModelRollback({
        ...rollbackConfig,

        activeModel:
          championModel,

        fallbackModel,

        activeMetrics,

        baselineMetrics,

        drift:
          findDriftForModel(
            driftBatch,
            championId,
          ),
      });
  }

  const decision =
    buildRuntimeDecision({
      ensemble,

      promotion,

      challenger,

      rollback,

      driftBatch,
    });

  return {
    version:
      LEARNING_RUNTIME_INTEGRATION_V2_VERSION,

    ready:
      true,

    action:
      decision.action,

    approved:
      decision.approved,

    blockers:
      decision.blockers,

    models:
      learnedModels,

    ensemble,

    learning,

    learningPatch,

    weightUpdate,

    weightPatch,

    drift:
      driftBatch,

    promotion,

    championChallenger:
      challenger,

    rollback,

    summary: {
      modelCount:
        learnedModels.length,

      activeModelCount:
        learnedModels.filter(
          (
            model,
          ) =>
            model.enabled !== false,
        ).length,

      learningRecordCount:
        safeArray(
          learningRecords,
        ).length,

      outcomeCount:
        safeArray(
          outcomes,
        ).length,

      driftRecordCount:
        safeArray(
          driftRecords,
        ).length,

      driftedModelCount:
        driftBatch.driftedModelCount,

      blockedModelCount:
        driftBatch.blockedModelCount,

      ensembleDirection:
        ensemble.direction,

      ensembleConfidence:
        ensemble.confidence,

      ensembleAgreement:
        ensemble.agreement,

      promotionDecision:
        promotion?.decision ??
        null,

      challengerDecision:
        challenger?.decision ??
        null,

      rollbackAction:
        rollback?.action ??
        null,

      blockerCount:
        decision.blockerCount,

      totalWeight:
        round(
          learnedModels.reduce(
            (
              sum,
              model,
            ) =>
              sum +
              (
                finiteOrNull(
                  model.weight,
                ) ??
                0
              ),
            0,
          ),
        ),
    },
  };
}

export class LearningRuntimeIntegrationV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  run(input = {}) {
    return runLearningRuntimeIntegration({
      ...this.config,

      ...input,
    });
  }
}

export const learningRuntimeIntegrationV2 =
  new LearningRuntimeIntegrationV2();

export default runLearningRuntimeIntegration;