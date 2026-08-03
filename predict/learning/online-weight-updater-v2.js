export const ONLINE_WEIGHT_UPDATER_V2_VERSION =
  "online-weight-updater-v2";

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

function clamp(
  value,
  minimum = 0,
  maximum = 1,
) {
  const number =
    finiteOrNull(value);

  if (number === null) {
    return null;
  }

  return Math.min(
    maximum,
    Math.max(
      minimum,
      number,
    ),
  );
}

function round(
  value,
  digits = 6,
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

function normalizeRegime(value) {
  const text =
    String(
      value ??
      "UNKNOWN",
    )
      .trim()
      .toUpperCase()
      .replaceAll("-", "_")
      .replaceAll(" ", "_");

  const aliases = {
    BULL:
      "TRENDING_BULL",

    BULLISH:
      "TRENDING_BULL",

    UPTREND:
      "TRENDING_BULL",

    BEAR:
      "TRENDING_BEAR",

    BEARISH:
      "TRENDING_BEAR",

    DOWNTREND:
      "TRENDING_BEAR",

    SIDEWAYS:
      "RANGE",

    RANGING:
      "RANGE",

    HIGH_VOL:
      "HIGH_VOLATILITY",

    VOLATILE:
      "HIGH_VOLATILITY",

    LOW_VOL:
      "LOW_VOLATILITY",

    CALM:
      "LOW_VOLATILITY",
  };

  return aliases[text] ??
    text ??
    "UNKNOWN";
}

function normalizeDirection(value) {
  if (typeof value === "number") {
    if (value > 0) {
      return 1;
    }

    if (value < 0) {
      return -1;
    }

    return 0;
  }

  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "LONG",
      "BULLISH",
      "UP",
      "1",
    ].includes(text)
  ) {
    return 1;
  }

  if (
    [
      "SELL",
      "SHORT",
      "BEARISH",
      "DOWN",
      "-1",
    ].includes(text)
  ) {
    return -1;
  }

  return 0;
}

function directionLabel(value) {
  if (value > 0) {
    return "BUY";
  }

  if (value < 0) {
    return "SELL";
  }

  return "NEUTRAL";
}

function normalizeModel(
  model,
  index,
) {
  if (
    !model ||
    typeof model !== "object"
  ) {
    return null;
  }

  const id =
    String(
      model.id ??
      model.modelId ??
      model.name ??
      `model-${index + 1}`,
    ).trim();

  if (!id) {
    return null;
  }

  const weight =
    Math.max(
      0,
      finiteOrNull(
        model.weight ??
        model.baseWeight,
      ) ?? 1,
    );

  const minimumWeight =
    Math.max(
      0,
      finiteOrNull(
        model.minimumWeight,
      ) ?? 0.02,
    );

  const maximumWeight =
    Math.max(
      minimumWeight,
      finiteOrNull(
        model.maximumWeight,
      ) ?? 0.8,
    );

  const regimeWeights =
    model.regimeWeights &&
    typeof model.regimeWeights ===
      "object"
      ? Object.fromEntries(
          Object.entries(
            model.regimeWeights,
          ).map(
            (
              [
                regime,
                value,
              ],
            ) => [
              normalizeRegime(
                regime,
              ),

              Math.max(
                0,
                finiteOrNull(
                  value,
                ) ?? weight,
              ),
            ],
          ),
        )
      : {};

  return {
    id,

    family:
      String(
        model.family ??
        model.type ??
        "GENERAL",
      ).toUpperCase(),

    weight,

    minimumWeight,

    maximumWeight,

    regimeWeights,

    enabled:
      model.enabled !== false,

    metadata:
      model.metadata ??
      {},
  };
}

function normalizeOutcome(
  outcome,
  index,
) {
  if (
    !outcome ||
    typeof outcome !== "object"
  ) {
    return null;
  }

  const modelId =
    String(
      outcome.modelId ??
      outcome.id ??
      outcome.model ??
      "",
    ).trim();

  if (!modelId) {
    return null;
  }

  const prediction =
    outcome.prediction ??
    outcome.signal ??
    outcome.direction;

  const predictedDirection =
    normalizeDirection(
      typeof prediction === "object"
        ? prediction.direction ??
          prediction.signal ??
          prediction.value
        : prediction,
    );

  const confidence =
    clamp(
      (
        finiteOrNull(
          typeof prediction === "object"
            ? prediction.confidence ??
              prediction.probability ??
              outcome.confidence
            : outcome.confidence,
        ) ??
        50
      ) /
      100,
      0,
      1,
    ) ?? 0.5;

  const actualReturn =
    finiteOrNull(
      outcome.actualReturn ??
      outcome.return ??
      outcome.realizedReturn ??
      outcome.pnlPercent,
    );

  const actualDirection =
    actualReturn !== null
      ? actualReturn > 0
        ? 1
        : actualReturn < 0
          ? -1
          : 0
      : normalizeDirection(
          outcome.actualDirection ??
          outcome.result,
        );

  const timestampValue =
    outcome.timestamp ??
    outcome.date ??
    outcome.createdAt ??
    null;

  const parsedTimestamp =
    timestampValue === null
      ? null
      : Date.parse(
          timestampValue,
        );

  return {
    id:
      String(
        outcome.outcomeId ??
        outcome.recordId ??
        `outcome-${index + 1}`,
      ),

    modelId,

    regime:
      normalizeRegime(
        outcome.regime,
      ),

    predictedDirection,

    predictedDirectionLabel:
      directionLabel(
        predictedDirection,
      ),

    actualDirection,

    actualDirectionLabel:
      directionLabel(
        actualDirection,
      ),

    confidence,

    actualReturn:
      actualReturn ??
      0,

    timestamp:
      Number.isFinite(
        parsedTimestamp,
      )
        ? new Date(
            parsedTimestamp,
          ).toISOString()
        : null,
  };
}

function calculateReward({
  outcome,
  returnScale,
  confidencePenalty,
}) {
  const correct =
    outcome.predictedDirection ===
    outcome.actualDirection;

  const directionalReturn =
    outcome.predictedDirection === 0
      ? 0
      : outcome.actualReturn *
        outcome.predictedDirection;

  const directionReward =
    correct
      ? 1
      : -1;

  const returnReward =
    Math.tanh(
      directionalReturn /
      Math.max(
        0.000001,
        returnScale,
      ),
    );

  const confidenceError =
    correct
      ? 1 -
        outcome.confidence
      : outcome.confidence;

  const calibrationPenalty =
    confidenceError *
    confidencePenalty;

  const reward =
    directionReward *
      0.55 +
    returnReward *
      0.35 -
    calibrationPenalty *
      0.1;

  return {
    correct,

    directionalReturn:
      round(
        directionalReturn,
      ),

    directionReward:
      round(
        directionReward,
      ),

    returnReward:
      round(
        returnReward,
      ),

    calibrationPenalty:
      round(
        calibrationPenalty,
      ),

    reward:
      round(
        Math.max(
          -1,
          Math.min(
            1,
            reward,
          ),
        ),
      ),
  };
}

function calculateRecencyWeight({
  timestamp,
  newestTimestamp,
  halfLifeDays,
}) {
  if (
    !timestamp ||
    !Number.isFinite(
      newestTimestamp,
    ) ||
    halfLifeDays <= 0
  ) {
    return 1;
  }

  const parsed =
    Date.parse(
      timestamp,
    );

  if (!Number.isFinite(parsed)) {
    return 1;
  }

  const ageDays =
    Math.max(
      0,
      (
        newestTimestamp -
        parsed
      ) /
      86400000,
    );

  return (
    0.5 **
    (
      ageDays /
      halfLifeDays
    )
  );
}

function normalizeWeightSet(
  models,
) {
  const active =
    models.filter(
      (
        model,
      ) =>
        model.enabled,
    );

  const total =
    active.reduce(
      (
        sum,
        model,
      ) =>
        sum +
        model.weight,
      0,
    );

  if (!active.length) {
    return models;
  }

  if (total <= 0) {
    const equalWeight =
      1 /
      active.length;

    return models.map(
      (
        model,
      ) => ({
        ...model,

        weight:
          model.enabled
            ? equalWeight
            : 0,
      }),
    );
  }

  return models.map(
    (
      model,
    ) => ({
      ...model,

      weight:
        model.enabled
          ? model.weight /
            total
          : 0,
    }),
  );
}

function enforceWeightBounds(
  models,
  iterations = 20,
) {
  let normalized =
    normalizeWeightSet(
      models,
    );

  for (
    let iteration = 0;
    iteration < iterations;
    iteration += 1
  ) {
    let changed = false;

    normalized =
      normalized.map(
        (
          model,
        ) => {
          if (!model.enabled) {
            return {
              ...model,
              weight:
                0,
            };
          }

          const bounded =
            Math.min(
              model.maximumWeight,
              Math.max(
                model.minimumWeight,
                model.weight,
              ),
            );

          if (
            Math.abs(
              bounded -
              model.weight
            ) >
            1e-12
          ) {
            changed = true;
          }

          return {
            ...model,
            weight:
              bounded,
          };
        },
      );

    normalized =
      normalizeWeightSet(
        normalized,
      );

    if (!changed) {
      break;
    }
  }

  return normalized;
}

function aggregateModelOutcomes({
  outcomes,
  newestTimestamp,
  recencyHalfLifeDays,
  returnScale,
  confidencePenalty,
}) {
  const groups =
    new Map();

  for (
    const outcome
    of outcomes
  ) {
    if (
      !groups.has(
        outcome.modelId,
      )
    ) {
      groups.set(
        outcome.modelId,
        [],
      );
    }

    groups.get(
      outcome.modelId,
    ).push(
      outcome,
    );
  }

  return new Map(
    Array.from(
      groups.entries(),
    ).map(
      (
        [
          modelId,
          modelOutcomes,
        ],
      ) => {
        let weightedReward = 0;
        let totalWeight = 0;
        let correctCount = 0;

        const regimeRewards = {};

        for (
          const outcome
          of modelOutcomes
        ) {
          const reward =
            calculateReward({
              outcome,

              returnScale,

              confidencePenalty,
            });

          const recencyWeight =
            calculateRecencyWeight({
              timestamp:
                outcome.timestamp,

              newestTimestamp,

              halfLifeDays:
                recencyHalfLifeDays,
            });

          weightedReward +=
            reward.reward *
            recencyWeight;

          totalWeight +=
            recencyWeight;

          if (reward.correct) {
            correctCount += 1;
          }

          if (
            !regimeRewards[
              outcome.regime
            ]
          ) {
            regimeRewards[
              outcome.regime
            ] = {
              weightedReward:
                0,

              totalWeight:
                0,

              sampleCount:
                0,
            };
          }

          regimeRewards[
            outcome.regime
          ].weightedReward +=
            reward.reward *
            recencyWeight;

          regimeRewards[
            outcome.regime
          ].totalWeight +=
            recencyWeight;

          regimeRewards[
            outcome.regime
          ].sampleCount += 1;
        }

        return [
          modelId,

          {
            sampleCount:
              modelOutcomes.length,

            correctCount,

            accuracy:
              modelOutcomes.length
                ? correctCount /
                  modelOutcomes.length
                : 0,

            averageReward:
              totalWeight > 0
                ? weightedReward /
                  totalWeight
                : 0,

            regimeRewards:
              Object.fromEntries(
                Object.entries(
                  regimeRewards,
                ).map(
                  (
                    [
                      regime,
                      summary,
                    ],
                  ) => [
                    regime,

                    {
                      sampleCount:
                        summary.sampleCount,

                      averageReward:
                        summary.totalWeight > 0
                          ? summary.weightedReward /
                            summary.totalWeight
                          : 0,
                    },
                  ],
                ),
              ),
          },
        ];
      },
    ),
  );
}

function calculateAdaptiveRate({
  baseLearningRate,
  sampleCount,
  minimumSamples,
  maximumLearningRate,
}) {
  const sampleConfidence =
    Math.min(
      1,
      sampleCount /
      Math.max(
        1,
        minimumSamples,
      ),
    );

  return Math.min(
    maximumLearningRate,
    baseLearningRate *
    (
      0.25 +
      sampleConfidence *
      0.75
    ),
  );
}

function updateModel({
  model,
  summary,
  learningRate,
  maximumLearningRate,
  minimumSamples,
  regimeLearningRate,
}) {
  if (
    !summary ||
    summary.sampleCount <= 0
  ) {
    return {
      ...model,

      update: {
        changed:
          false,

        reason:
          "NO_OUTCOMES",

        sampleCount:
          0,

        reward:
          0,

        previousWeight:
          round(
            model.weight,
          ),

        newWeight:
          round(
            model.weight,
          ),
      },
    };
  }

  const adaptiveRate =
    calculateAdaptiveRate({
      baseLearningRate:
        learningRate,

      sampleCount:
        summary.sampleCount,

      minimumSamples,

      maximumLearningRate,
    });

  const multiplier =
    Math.exp(
      adaptiveRate *
      summary.averageReward,
    );

  const proposedWeight =
    Math.min(
      model.maximumWeight,
      Math.max(
        model.minimumWeight,
        model.weight *
        multiplier,
      ),
    );

  const updatedRegimeWeights = {
    ...model.regimeWeights,
  };

  for (
    const [
      regime,
      regimeSummary,
    ]
    of Object.entries(
      summary.regimeRewards,
    )
  ) {
    const current =
      finiteOrNull(
        updatedRegimeWeights[
          regime
        ],
      ) ??
      model.weight;

    const adaptiveRegimeRate =
      calculateAdaptiveRate({
        baseLearningRate:
          regimeLearningRate,

        sampleCount:
          regimeSummary.sampleCount,

        minimumSamples,

        maximumLearningRate,
      });

    const regimeMultiplier =
      Math.exp(
        adaptiveRegimeRate *
        regimeSummary.averageReward,
      );

    updatedRegimeWeights[
      regime
    ] =
      Math.min(
        model.maximumWeight,
        Math.max(
          model.minimumWeight,
          current *
          regimeMultiplier,
        ),
      );
  }

  return {
    ...model,

    weight:
      proposedWeight,

    regimeWeights:
      updatedRegimeWeights,

    update: {
      changed:
        Math.abs(
          proposedWeight -
          model.weight
        ) >
        1e-12,

      reason:
        summary.sampleCount <
        minimumSamples
          ? "LOW_SAMPLE_UPDATE"
          : "VALIDATED_UPDATE",

      sampleCount:
        summary.sampleCount,

      correctCount:
        summary.correctCount,

      accuracy:
        round(
          summary.accuracy *
          100,
          2,
        ),

      reward:
        round(
          summary.averageReward,
        ),

      adaptiveLearningRate:
        round(
          adaptiveRate,
        ),

      multiplier:
        round(
          multiplier,
        ),

      previousWeight:
        round(
          model.weight,
        ),

      proposedWeight:
        round(
          proposedWeight,
        ),
    },
  };
}

function buildAuditEntry({
  modelsBefore,
  modelsAfter,
  outcomeCount,
  configuration,
}) {
  const beforeMap =
    new Map(
      modelsBefore.map(
        (
          model,
        ) => [
          model.id,
          model,
        ],
      ),
    );

  return {
    version:
      ONLINE_WEIGHT_UPDATER_V2_VERSION,

    timestamp:
      new Date().toISOString(),

    outcomeCount,

    configuration,

    changes:
      modelsAfter.map(
        (
          model,
        ) => {
          const before =
            beforeMap.get(
              model.id,
            );

          return {
            modelId:
              model.id,

            previousWeight:
              round(
                before?.weight ??
                0,
              ),

            newWeight:
              round(
                model.weight,
              ),

            delta:
              round(
                model.weight -
                (
                  before?.weight ??
                  0
                ),
              ),

            reward:
              model.update?.reward ??
              0,

            sampleCount:
              model.update
                ?.sampleCount ??
              0,

            reason:
              model.update?.reason ??
              "UNKNOWN",
          };
        },
      ),
  };
}

export function updateOnlineModelWeights({
  models = [],
  outcomes = [],
  learningRate = 0.2,
  regimeLearningRate = 0.15,
  maximumLearningRate = 0.5,
  minimumSamples = 10,
  recencyHalfLifeDays = 30,
  returnScale = 3,
  confidencePenalty = 1,
} = {}) {
  if (!Array.isArray(models)) {
    throw new TypeError(
      "Online weight updater models must be an array.",
    );
  }

  if (!Array.isArray(outcomes)) {
    throw new TypeError(
      "Online weight updater outcomes must be an array.",
    );
  }

  const normalizedModels =
    models
      .map(
        normalizeModel,
      )
      .filter(Boolean);

  const normalizedOutcomes =
    outcomes
      .map(
        normalizeOutcome,
      )
      .filter(Boolean);

  if (!normalizedModels.length) {
    return {
      version:
        ONLINE_WEIGHT_UPDATER_V2_VERSION,

      ready:
        false,

      updated:
        false,

      modelCount:
        0,

      outcomeCount:
        normalizedOutcomes.length,

      models:
        [],

      audit:
        null,

      reason:
        "NO_MODELS",
    };
  }

  const normalizedLearningRate =
    Math.max(
      0,
      finiteOrNull(
        learningRate,
      ) ?? 0.2,
    );

  const normalizedRegimeLearningRate =
    Math.max(
      0,
      finiteOrNull(
        regimeLearningRate,
      ) ?? 0.15,
    );

  const normalizedMaximumLearningRate =
    Math.max(
      normalizedLearningRate,
      finiteOrNull(
        maximumLearningRate,
      ) ?? 0.5,
    );

  const normalizedMinimumSamples =
    Math.max(
      1,
      Math.floor(
        finiteOrNull(
          minimumSamples,
        ) ?? 10,
      ),
    );

  const normalizedRecencyHalfLife =
    Math.max(
      0,
      finiteOrNull(
        recencyHalfLifeDays,
      ) ?? 30,
    );

  const normalizedReturnScale =
    Math.max(
      0.000001,
      finiteOrNull(
        returnScale,
      ) ?? 3,
    );

  const normalizedConfidencePenalty =
    Math.max(
      0,
      finiteOrNull(
        confidencePenalty,
      ) ?? 1,
    );

  const timestampValues =
    normalizedOutcomes
      .map(
        (
          outcome,
        ) =>
          outcome.timestamp
            ? Date.parse(
                outcome.timestamp,
              )
            : null,
      )
      .filter(
        Number.isFinite,
      );

  const newestTimestamp =
    timestampValues.length
      ? Math.max(
          ...timestampValues,
        )
      : null;

  const summaries =
    aggregateModelOutcomes({
      outcomes:
        normalizedOutcomes,

      newestTimestamp,

      recencyHalfLifeDays:
        normalizedRecencyHalfLife,

      returnScale:
        normalizedReturnScale,

      confidencePenalty:
        normalizedConfidencePenalty,
    });

  const modelsBefore =
    enforceWeightBounds(
      normalizedModels,
    );

  const proposedModels =
    modelsBefore.map(
      (
        model,
      ) =>
        updateModel({
          model,

          summary:
            summaries.get(
              model.id,
            ),

          learningRate:
            normalizedLearningRate,

          regimeLearningRate:
            normalizedRegimeLearningRate,

          maximumLearningRate:
            normalizedMaximumLearningRate,

          minimumSamples:
            normalizedMinimumSamples,
        }),
    );

  const boundedModels =
    enforceWeightBounds(
      proposedModels,
    );

  const finalModels =
    boundedModels.map(
      (
        model,
      ) => ({
        ...model,

        weight:
          round(
            model.weight,
          ),

        regimeWeights:
          Object.fromEntries(
            Object.entries(
              model.regimeWeights,
            ).map(
              (
                [
                  regime,
                  value,
                ],
              ) => [
                regime,
                round(value),
              ],
            ),
          ),

        update: {
          ...model.update,

          newWeight:
            round(
              model.weight,
            ),

          normalizedDelta:
            round(
              model.weight -
              (
                model.update
                  ?.previousWeight ??
                model.weight
              ),
            ),
        },
      }),
    );

  const configuration = {
    learningRate:
      normalizedLearningRate,

    regimeLearningRate:
      normalizedRegimeLearningRate,

    maximumLearningRate:
      normalizedMaximumLearningRate,

    minimumSamples:
      normalizedMinimumSamples,

    recencyHalfLifeDays:
      normalizedRecencyHalfLife,

    returnScale:
      normalizedReturnScale,

    confidencePenalty:
      normalizedConfidencePenalty,
  };

  const audit =
    buildAuditEntry({
      modelsBefore,

      modelsAfter:
        finalModels,

      outcomeCount:
        normalizedOutcomes.length,

      configuration,
    });

  const updated =
    finalModels.some(
      (
        model,
        index,
      ) =>
        Math.abs(
          model.weight -
          modelsBefore[index].weight
        ) >
        1e-9,
    );

  return {
    version:
      ONLINE_WEIGHT_UPDATER_V2_VERSION,

    ready:
      true,

    updated,

    modelCount:
      finalModels.length,

    outcomeCount:
      normalizedOutcomes.length,

    configuration,

    models:
      finalModels,

    audit,

    diagnostics: {
      totalWeight:
        round(
          finalModels.reduce(
            (
              sum,
              model,
            ) =>
              sum +
              model.weight,
            0,
          ),
        ),

      activeModelCount:
        finalModels.filter(
          (
            model,
          ) =>
            model.enabled,
        ).length,

      updatedModelCount:
        finalModels.filter(
          (
            model,
          ) =>
            model.update
              ?.changed,
        ).length,

      unmatchedOutcomeCount:
        normalizedOutcomes.filter(
          (
            outcome,
          ) =>
            !finalModels.some(
              (
                model,
              ) =>
                model.id ===
                outcome.modelId,
            ),
        ).length,
    },
  };
}

export function createWeightPatch(
  result,
) {
  if (
    !result ||
    result.ready !== true
  ) {
    return {
      version:
        ONLINE_WEIGHT_UPDATER_V2_VERSION,

      ready:
        false,

      models:
        [],
    };
  }

  return {
    version:
      ONLINE_WEIGHT_UPDATER_V2_VERSION,

    ready:
      true,

    models:
      result.models.map(
        (
          model,
        ) => ({
          id:
            model.id,

          family:
            model.family,

          weight:
            model.weight,

          regimeWeights:
            model.regimeWeights,

          enabled:
            model.enabled,
        }),
      ),

    audit:
      result.audit,
  };
}

export class OnlineWeightUpdaterV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  update({
    models = [],
    outcomes = [],
    ...overrides
  } = {}) {
    return updateOnlineModelWeights({
      ...this.config,

      ...overrides,

      models,

      outcomes,
    });
  }

  createPatch(input = {}) {
    return createWeightPatch(
      this.update(input),
    );
  }
}

export const onlineWeightUpdaterV2 =
  new OnlineWeightUpdaterV2();

export default updateOnlineModelWeights;