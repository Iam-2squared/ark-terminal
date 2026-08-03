export const CONCEPT_DRIFT_DETECTOR_V2_VERSION =
  "concept-drift-detector-v2";

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
  maximum = 100,
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

function average(values) {
  const available =
    values.filter(
      Number.isFinite,
    );

  if (!available.length) {
    return null;
  }

  return (
    available.reduce(
      (
        sum,
        value,
      ) =>
        sum + value,
      0,
    ) /
    available.length
  );
}

function standardDeviation(values) {
  const mean =
    average(values);

  if (mean === null) {
    return null;
  }

  const variance =
    values.reduce(
      (
        sum,
        value,
      ) =>
        sum +
        (
          value -
          mean
        ) ** 2,
      0,
    ) /
    values.length;

  return Math.sqrt(
    variance,
  );
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
      "UP",
      "BULLISH",
      "1",
    ].includes(text)
  ) {
    return 1;
  }

  if (
    [
      "SELL",
      "SHORT",
      "DOWN",
      "BEARISH",
      "-1",
    ].includes(text)
  ) {
    return -1;
  }

  return 0;
}

function normalizeRecord(
  record,
  index,
) {
  if (
    !record ||
    typeof record !== "object"
  ) {
    return null;
  }

  const predictedDirection =
    normalizeDirection(
      record.prediction?.direction ??
      record.predictedDirection ??
      record.direction ??
      record.signal,
    );

  const actualReturn =
    finiteOrNull(
      record.actualReturn ??
      record.realizedReturn ??
      record.return ??
      record.pnlPercent,
    );

  const actualDirection =
    actualReturn !== null
      ? actualReturn > 0
        ? 1
        : actualReturn < 0
          ? -1
          : 0
      : normalizeDirection(
          record.actualDirection ??
          record.outcome,
        );

  const confidence =
    clamp(
      record.prediction?.confidence ??
      record.confidence ??
      50,
    ) ?? 50;

  const timestampValue =
    record.timestamp ??
    record.date ??
    record.createdAt ??
    null;

  const timestamp =
    timestampValue === null
      ? null
      : Date.parse(
          timestampValue,
        );

  return {
    id:
      String(
        record.id ??
        `record-${index + 1}`,
      ),

    modelId:
      String(
        record.modelId ??
        record.model ??
        "default-model",
      ),

    predictedDirection,

    actualDirection,

    actualReturn:
      actualReturn ?? 0,

    confidence,

    correct:
      predictedDirection ===
      actualDirection,

    timestamp:
      Number.isFinite(timestamp)
        ? timestamp
        : index,

    features:
      record.features &&
      typeof record.features === "object"
        ? record.features
        : {},
  };
}

function normalizeRecords(records) {
  if (!Array.isArray(records)) {
    throw new TypeError(
      "Concept drift records must be an array.",
    );
  }

  return records
    .map(
      normalizeRecord,
    )
    .filter(Boolean)
    .sort(
      (
        left,
        right,
      ) =>
        left.timestamp -
        right.timestamp,
    );
}

function calculateWindowMetrics(records) {
  if (!records.length) {
    return {
      sampleCount:
        0,

      accuracy:
        null,

      averageReturn:
        null,

      volatility:
        null,

      confidence:
        null,

      calibrationError:
        null,
    };
  }

  const correctness =
    records.map(
      (
        record,
      ) =>
        record.correct
          ? 1
          : 0,
    );

  const directionalReturns =
    records.map(
      (
        record,
      ) =>
        record.actualReturn *
        record.predictedDirection,
    );

  const confidence =
    records.map(
      (
        record,
      ) =>
        record.confidence,
    );

  const calibrationErrors =
    records.map(
      (
        record,
      ) =>
        Math.abs(
          (
            record.correct
              ? 100
              : 0
          ) -
          record.confidence,
        ),
    );

  return {
    sampleCount:
      records.length,

    accuracy:
      round(
        average(
          correctness,
        ) *
        100,
        2,
      ),

    averageReturn:
      round(
        average(
          directionalReturns,
        ),
      ),

    volatility:
      round(
        standardDeviation(
          directionalReturns,
        ),
      ),

    confidence:
      round(
        average(
          confidence,
        ),
        2,
      ),

    calibrationError:
      round(
        average(
          calibrationErrors,
        ),
        2,
      ),
  };
}

function extractNumericFeatures(records) {
  const keys =
    new Set();

  for (
    const record
    of records
  ) {
    for (
      const [
        key,
        value,
      ]
      of Object.entries(
        record.features,
      )
    ) {
      if (
        finiteOrNull(
          value,
        ) !== null
      ) {
        keys.add(key);
      }
    }
  }

  return Array.from(keys);
}

function calculateFeatureDrift({
  baseline,
  recent,
  minimumStandardDeviation,
}) {
  const featureKeys =
    extractNumericFeatures([
      ...baseline,
      ...recent,
    ]);

  return featureKeys
    .map(
      (
        feature,
      ) => {
        const baselineValues =
          baseline
            .map(
              (
                record,
              ) =>
                finiteOrNull(
                  record.features[
                    feature
                  ],
                ),
            )
            .filter(
              Number.isFinite,
            );

        const recentValues =
          recent
            .map(
              (
                record,
              ) =>
                finiteOrNull(
                  record.features[
                    feature
                  ],
                ),
            )
            .filter(
              Number.isFinite,
            );

        if (
          !baselineValues.length ||
          !recentValues.length
        ) {
          return null;
        }

        const baselineMean =
          average(
            baselineValues,
          );

        const recentMean =
          average(
            recentValues,
          );

        const baselineStd =
          Math.max(
            minimumStandardDeviation,
            standardDeviation(
              baselineValues,
            ) ?? 0,
          );

        const standardizedShift =
          Math.abs(
            recentMean -
            baselineMean,
          ) /
          baselineStd;

        return {
          feature,

          baselineMean:
            round(
              baselineMean,
            ),

          recentMean:
            round(
              recentMean,
            ),

          baselineStandardDeviation:
            round(
              baselineStd,
            ),

          standardizedShift:
            round(
              standardizedShift,
            ),

          driftScore:
            round(
              clamp(
                standardizedShift *
                25,
              ) ?? 0,
              2,
            ),
        };
      },
    )
    .filter(Boolean)
    .sort(
      (
        left,
        right,
      ) =>
        right.driftScore -
        left.driftScore,
    );
}

function calculatePerformanceDrift({
  baselineMetrics,
  recentMetrics,
}) {
  const accuracyDrop =
    Math.max(
      0,
      (
        baselineMetrics.accuracy ??
        0
      ) -
      (
        recentMetrics.accuracy ??
        0
      ),
    );

  const returnDrop =
    Math.max(
      0,
      (
        baselineMetrics.averageReturn ??
        0
      ) -
      (
        recentMetrics.averageReturn ??
        0
      ),
    );

  const volatilityIncrease =
    Math.max(
      0,
      (
        recentMetrics.volatility ??
        0
      ) -
      (
        baselineMetrics.volatility ??
        0
      ),
    );

  const calibrationIncrease =
    Math.max(
      0,
      (
        recentMetrics.calibrationError ??
        0
      ) -
      (
        baselineMetrics.calibrationError ??
        0
      ),
    );

  const score =
    clamp(
      accuracyDrop *
        0.55 +
      returnDrop *
        8 +
      volatilityIncrease *
        5 +
      calibrationIncrease *
        0.25,
    ) ?? 0;

  return {
    score:
      round(
        score,
        2,
      ),

    accuracyDrop:
      round(
        accuracyDrop,
        2,
      ),

    returnDrop:
      round(
        returnDrop,
      ),

    volatilityIncrease:
      round(
        volatilityIncrease,
      ),

    calibrationIncrease:
      round(
        calibrationIncrease,
        2,
      ),
  };
}

function calculateSequentialChange(
  records,
) {
  if (records.length < 4) {
    return {
      score:
        0,

      maximumLossStreak:
        0,

      recentLossStreak:
        0,
    };
  }

  let maximumLossStreak = 0;
  let currentLossStreak = 0;

  for (
    const record
    of records
  ) {
    if (!record.correct) {
      currentLossStreak += 1;

      maximumLossStreak =
        Math.max(
          maximumLossStreak,
          currentLossStreak,
        );
    } else {
      currentLossStreak = 0;
    }
  }

  const score =
    clamp(
      maximumLossStreak *
      12.5,
    ) ?? 0;

  return {
    score:
      round(
        score,
        2,
      ),

    maximumLossStreak,

    recentLossStreak:
      currentLossStreak,
  };
}

function driftLevel(score) {
  if (score >= 75) {
    return "CRITICAL";
  }

  if (score >= 55) {
    return "HIGH";
  }

  if (score >= 30) {
    return "MEDIUM";
  }

  return "LOW";
}

function buildRecommendation({
  level,
  recentMetrics,
  minimumRecentAccuracy,
}) {
  if (
    level === "CRITICAL"
  ) {
    return {
      action:
        "RETRAIN",

      allowPromotion:
        false,

      reason:
        "CRITICAL_CONCEPT_DRIFT",
    };
  }

  if (
    level === "HIGH" ||
    (
      recentMetrics.accuracy ??
      0
    ) <
    minimumRecentAccuracy
  ) {
    return {
      action:
        "FREEZE_AND_REVALIDATE",

      allowPromotion:
        false,

      reason:
        "PERFORMANCE_DEGRADATION",
    };
  }

  if (
    level === "MEDIUM"
  ) {
    return {
      action:
        "MONITOR",

      allowPromotion:
        false,

      reason:
        "POSSIBLE_CONCEPT_DRIFT",
    };
  }

  return {
    action:
      "CONTINUE",

    allowPromotion:
      true,

    reason:
      "MODEL_BEHAVIOR_STABLE",
  };
}

export function detectConceptDrift({
  records = [],
  baselineWindow = 60,
  recentWindow = 20,
  minimumSamples = 40,
  minimumRecentAccuracy = 50,
  featureDriftWeight = 0.3,
  performanceDriftWeight = 0.5,
  sequentialDriftWeight = 0.2,
  minimumStandardDeviation = 0.000001,
} = {}) {
  const normalizedRecords =
    normalizeRecords(
      records,
    );

  const normalizedBaselineWindow =
    Math.max(
      1,
      Math.floor(
        finiteOrNull(
          baselineWindow,
        ) ?? 60,
      ),
    );

  const normalizedRecentWindow =
    Math.max(
      1,
      Math.floor(
        finiteOrNull(
          recentWindow,
        ) ?? 20,
      ),
    );

  const normalizedMinimumSamples =
    Math.max(
      normalizedRecentWindow +
      1,
      Math.floor(
        finiteOrNull(
          minimumSamples,
        ) ?? 40,
      ),
    );

  if (
    normalizedRecords.length <
    normalizedMinimumSamples
  ) {
    return {
      version:
        CONCEPT_DRIFT_DETECTOR_V2_VERSION,

      ready:
        false,

      driftDetected:
        false,

      driftScore:
        0,

      driftLevel:
        "UNKNOWN",

      recordCount:
        normalizedRecords.length,

      requiredRecordCount:
        normalizedMinimumSamples,

      recommendation: {
        action:
          "COLLECT_MORE_DATA",

        allowPromotion:
          false,

        reason:
          "INSUFFICIENT_SAMPLES",
      },

      featureDrift:
        [],

      diagnostics: {
        baselineCount:
          0,

        recentCount:
          0,
      },
    };
  }

  const recent =
    normalizedRecords.slice(
      -normalizedRecentWindow,
    );

  const baselineEnd =
    normalizedRecords.length -
    normalizedRecentWindow;

  const baselineStart =
    Math.max(
      0,
      baselineEnd -
      normalizedBaselineWindow,
    );

  const baseline =
    normalizedRecords.slice(
      baselineStart,
      baselineEnd,
    );

  const baselineMetrics =
    calculateWindowMetrics(
      baseline,
    );

  const recentMetrics =
    calculateWindowMetrics(
      recent,
    );

  const featureDrift =
    calculateFeatureDrift({
      baseline,

      recent,

      minimumStandardDeviation:
        Math.max(
          0.000000001,
          finiteOrNull(
            minimumStandardDeviation,
          ) ?? 0.000001,
        ),
    });

  const averageFeatureDrift =
    featureDrift.length
      ? average(
          featureDrift.map(
            (
              feature,
            ) =>
              feature.driftScore,
          ),
        )
      : 0;

  const performanceDrift =
    calculatePerformanceDrift({
      baselineMetrics,

      recentMetrics,
    });

  const sequentialDrift =
    calculateSequentialChange(
      recent,
    );

  const totalWeight =
    Math.max(
      0.000001,
      featureDriftWeight +
      performanceDriftWeight +
      sequentialDriftWeight,
    );

  const driftScore =
    clamp(
      (
        averageFeatureDrift *
          featureDriftWeight +
        performanceDrift.score *
          performanceDriftWeight +
        sequentialDrift.score *
          sequentialDriftWeight
      ) /
      totalWeight,
    ) ?? 0;

  const level =
    driftLevel(
      driftScore,
    );

  const recommendation =
    buildRecommendation({
      level,

      recentMetrics,

      minimumRecentAccuracy:
        clamp(
          minimumRecentAccuracy,
        ) ?? 50,
    });

  return {
    version:
      CONCEPT_DRIFT_DETECTOR_V2_VERSION,

    ready:
      true,

    driftDetected:
      level === "HIGH" ||
      level === "CRITICAL",

    driftScore:
      round(
        driftScore,
        2,
      ),

    driftLevel:
      level,

    recordCount:
      normalizedRecords.length,

    baseline:
      baselineMetrics,

    recent:
      recentMetrics,

    performanceDrift,

    sequentialDrift,

    featureDrift,

    recommendation,

    diagnostics: {
      baselineCount:
        baseline.length,

      recentCount:
        recent.length,

      featureCount:
        featureDrift.length,

      averageFeatureDrift:
        round(
          averageFeatureDrift,
          2,
        ),

      componentWeights: {
        feature:
          featureDriftWeight,

        performance:
          performanceDriftWeight,

        sequential:
          sequentialDriftWeight,
      },
    },
  };
}

export function detectModelDriftBatch({
  models = [],
  records = [],
  config = {},
} = {}) {
  if (!Array.isArray(models)) {
    throw new TypeError(
      "Concept drift models must be an array.",
    );
  }

  if (!Array.isArray(records)) {
    throw new TypeError(
      "Concept drift records must be an array.",
    );
  }

  const results =
    models.map(
      (
        model,
      ) => {
        const modelId =
          String(
            model.id ??
            model.modelId ??
            model.name,
          );

        const modelRecords =
          records.filter(
            (
              record,
            ) =>
              String(
                record.modelId ??
                record.model ??
                "default-model",
              ) ===
              modelId,
          );

        return {
          modelId,

          ...detectConceptDrift({
            ...config,

            records:
              modelRecords,
          }),
        };
      },
    );

  return {
    version:
      CONCEPT_DRIFT_DETECTOR_V2_VERSION,

    ready:
      results.some(
        (
          result,
        ) =>
          result.ready,
      ),

    modelCount:
      models.length,

    driftedModelCount:
      results.filter(
        (
          result,
        ) =>
          result.driftDetected,
      ).length,

    blockedModelCount:
      results.filter(
        (
          result,
        ) =>
          result.recommendation
            ?.allowPromotion ===
          false,
      ).length,

    results,
  };
}

export class ConceptDriftDetectorV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  detect(
    records = [],
    overrides = {},
  ) {
    return detectConceptDrift({
      ...this.config,

      ...overrides,

      records,
    });
  }

  detectBatch({
    models = [],
    records = [],
    config = {},
  } = {}) {
    return detectModelDriftBatch({
      models,

      records,

      config: {
        ...this.config,

        ...config,
      },
    });
  }
}

export const conceptDriftDetectorV2 =
  new ConceptDriftDetectorV2();

export default detectConceptDrift;