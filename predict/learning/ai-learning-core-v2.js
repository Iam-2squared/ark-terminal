export const AI_LEARNING_CORE_V2_VERSION =
  "ai-learning-core-v2";

export const AI_LEARNING_CORE_V2_SCHEMA_VERSION =
  1;

const DIRECTIONS =
  Object.freeze({
    BUY:
      1,

    NEUTRAL:
      0,

    SELL:
      -1,
  });

const DEFAULT_REGIME =
  "UNKNOWN";

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

function finiteNumber(
  value,
  fallback = 0,
) {
  return (
    finiteOrNull(value) ??
    fallback
  );
}

function clamp(
  value,
  minimum = 0,
  maximum = 100,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      finiteNumber(
        value,
        minimum,
      ),
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
      value *
      factor,
    ) /
    factor
  );
}

function average(values = []) {
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
        sum +
        value,
      0,
    ) /
    available.length
  );
}

function median(values = []) {
  const available =
    values
      .filter(
        Number.isFinite,
      )
      .sort(
        (
          left,
          right,
        ) =>
          left -
          right,
      );

  if (!available.length) {
    return null;
  }

  const middle =
    Math.floor(
      available.length /
      2,
    );

  if (
    available.length %
    2 ===
    0
  ) {
    return (
      available[
        middle -
        1
      ] +
      available[
        middle
      ]
    ) /
    2;
  }

  return available[
    middle
  ];
}

function standardDeviation(
  values = [],
) {
  const mean =
    average(values);

  if (mean === null) {
    return null;
  }

  const available =
    values.filter(
      Number.isFinite,
    );

  const variance =
    available.reduce(
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
    available.length;

  return Math.sqrt(
    variance,
  );
}

function normalizeDirection(value) {
  if (typeof value === "number") {
    if (value > 0) {
      return DIRECTIONS.BUY;
    }

    if (value < 0) {
      return DIRECTIONS.SELL;
    }

    return DIRECTIONS.NEUTRAL;
  }

  const text =
    String(
      value ??
      "",
    )
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "LONG",
      "BULLISH",
      "UP",
      "POSITIVE",
      "1",
    ].includes(text)
  ) {
    return DIRECTIONS.BUY;
  }

  if (
    [
      "SELL",
      "SHORT",
      "BEARISH",
      "DOWN",
      "NEGATIVE",
      "-1",
    ].includes(text)
  ) {
    return DIRECTIONS.SELL;
  }

  return DIRECTIONS.NEUTRAL;
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

function normalizeRegime(value) {
  const text =
    String(
      value ??
      DEFAULT_REGIME,
    )
      .trim()
      .toUpperCase()
      .replaceAll(
        "-",
        "_",
      )
      .replaceAll(
        " ",
        "_",
      );

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

    RISKON:
      "RISK_ON",

    RISKOFF:
      "RISK_OFF",
  };

  return (
    aliases[text] ??
    text ??
    DEFAULT_REGIME
  );
}

function normalizeTimestamp(
  value,
  fallbackIndex = 0,
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return {
      milliseconds:
        fallbackIndex,

      iso:
        null,
    };
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return {
        milliseconds:
          fallbackIndex,

        iso:
          null,
      };
    }

    return {
      milliseconds:
        value,

      iso:
        new Date(
          value,
        ).toISOString(),
    };
  }

  const parsed =
    Date.parse(value);

  if (!Number.isFinite(parsed)) {
    return {
      milliseconds:
        fallbackIndex,

      iso:
        null,
    };
  }

  return {
    milliseconds:
      parsed,

    iso:
      new Date(
        parsed,
      ).toISOString(),
  };
}

function normalizeFeatures(
  features,
) {
  if (
    !features ||
    typeof features !== "object" ||
    Array.isArray(features)
  ) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(features)
      .map(
        (
          [
            key,
            value,
          ],
        ) => {
          const number =
            finiteOrNull(value);

          return number === null
            ? null
            : [
                String(key),
                number,
              ];
        },
      )
      .filter(Boolean),
  );
}

function normalizeMetadata(
  metadata,
) {
  if (
    !metadata ||
    typeof metadata !== "object" ||
    Array.isArray(metadata)
  ) {
    return {};
  }

  return {
    ...metadata,
  };
}

export function normalizeLearningRecord(
  record,
  index = 0,
) {
  if (
    !record ||
    typeof record !== "object" ||
    Array.isArray(record)
  ) {
    return null;
  }

  const symbol =
    String(
      record.symbol ??
      record.code ??
      record.ticker ??
      "UNKNOWN",
    )
      .trim()
      .toUpperCase();

  const modelId =
    String(
      record.modelId ??
      record.model ??
      record.engine ??
      "default-model",
    ).trim();

  const prediction =
    record.prediction ??
    record.signal ??
    {};

  const predictedDirection =
    normalizeDirection(
      prediction.direction ??
      prediction.signal ??
      record.predictedDirection ??
      record.direction,
    );

  const confidence =
    clamp(
      prediction.confidence ??
      prediction.probability ??
      record.confidence ??
      50,
    );

  const predictedScore =
    clamp(
      prediction.score ??
      record.score ??
      record.aiScore ??
      confidence,
    );

  const actualReturn =
    finiteOrNull(
      record.actualReturn ??
      record.realizedReturn ??
      record.return ??
      record.pnlPercent ??
      record.outcomeReturn,
    );

  const actualDirection =
    actualReturn !== null
      ? actualReturn > 0
        ? DIRECTIONS.BUY
        : actualReturn < 0
          ? DIRECTIONS.SELL
          : DIRECTIONS.NEUTRAL
      : normalizeDirection(
          record.actualDirection ??
          record.outcomeDirection ??
          record.result,
        );

  const timestamp =
    normalizeTimestamp(
      record.timestamp ??
      record.date ??
      record.createdAt ??
      record.generatedAt,
      index,
    );

  const horizon =
    Math.max(
      1,
      Math.floor(
        finiteNumber(
          record.horizon ??
          record.predictionHorizon ??
          record.period,
          1,
        ),
      ),
    );

  const weight =
    Math.max(
      0,
      finiteNumber(
        record.weight,
        1,
      ),
    );

  const transactionCostPercent =
    Math.max(
      0,
      finiteNumber(
        record.transactionCostPercent ??
        record.costPercent ??
        record.feesPercent,
        0,
      ),
    );

  const directionalReturn =
    actualReturn === null
      ? null
      : (
          predictedDirection *
          actualReturn
        ) -
        transactionCostPercent;

  const correct =
    predictedDirection ===
    actualDirection;

  const calibrationError =
    Math.abs(
      (
        correct
          ? 100
          : 0
      ) -
      confidence,
    );

  return {
    id:
      String(
        record.id ??
        `${modelId}:${symbol}:${timestamp.milliseconds}:${index}`,
      ),

    schemaVersion:
      AI_LEARNING_CORE_V2_SCHEMA_VERSION,

    symbol,

    modelId,

    modelVersion:
      String(
        record.modelVersion ??
        record.version ??
        "unknown",
      ),

    family:
      String(
        record.family ??
        record.modelFamily ??
        "GENERAL",
      )
        .trim()
        .toUpperCase(),

    regime:
      normalizeRegime(
        record.regime ??
        record.marketRegime,
      ),

    horizon,

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

    predictedScore,

    actualReturn:
      actualReturn ??
      0,

    directionalReturn:
      directionalReturn ??
      0,

    transactionCostPercent,

    correct,

    calibrationError,

    weight,

    timestamp:
      timestamp.iso,

    timestampMilliseconds:
      timestamp.milliseconds,

    features:
      normalizeFeatures(
        record.features ??
        record.indicators,
      ),

    metadata:
      normalizeMetadata(
        record.metadata,
      ),
  };
}

export function normalizeLearningRecords(
  records = [],
) {
  if (!Array.isArray(records)) {
    throw new TypeError(
      "AI Learning Core records must be an array.",
    );
  }

  return records
    .map(
      (
        record,
        index,
      ) =>
        normalizeLearningRecord(
          record,
          index,
        ),
    )
    .filter(Boolean)
    .sort(
      (
        left,
        right,
      ) =>
        left.timestampMilliseconds -
        right.timestampMilliseconds,
    );
}

function calculateProfitFactor(
  returns,
) {
  const grossProfit =
    returns
      .filter(
        (
          value,
        ) =>
          value > 0,
      )
      .reduce(
        (
          sum,
          value,
        ) =>
          sum +
          value,
        0,
      );

  const grossLoss =
    Math.abs(
      returns
        .filter(
          (
            value,
          ) =>
            value < 0,
        )
        .reduce(
          (
            sum,
            value,
          ) =>
            sum +
            value,
          0,
        ),
    );

  if (grossLoss === 0) {
    return grossProfit > 0
      ? Infinity
      : 0;
  }

  return (
    grossProfit /
    grossLoss
  );
}

function calculateMaximumDrawdown(
  returns,
) {
  let equity = 100;
  let peak = 100;
  let maximumDrawdown = 0;

  for (const value of returns) {
    equity *=
      1 +
      value /
      100;

    peak =
      Math.max(
        peak,
        equity,
      );

    const drawdown =
      peak > 0
        ? (
            (
              peak -
              equity
            ) /
            peak
          ) *
          100
        : 0;

    maximumDrawdown =
      Math.max(
        maximumDrawdown,
        drawdown,
      );
  }

  return maximumDrawdown;
}

function calculateStreaks(
  records,
) {
  let currentWinStreak = 0;
  let currentLossStreak = 0;
  let maximumWinStreak = 0;
  let maximumLossStreak = 0;

  for (const record of records) {
    if (record.correct) {
      currentWinStreak += 1;
      currentLossStreak = 0;

      maximumWinStreak =
        Math.max(
          maximumWinStreak,
          currentWinStreak,
        );
    } else {
      currentLossStreak += 1;
      currentWinStreak = 0;

      maximumLossStreak =
        Math.max(
          maximumLossStreak,
          currentLossStreak,
        );
    }
  }

  return {
    currentWinStreak,

    currentLossStreak,

    maximumWinStreak,

    maximumLossStreak,
  };
}

export function calculateLearningMetrics(
  records = [],
) {
  const normalized =
    normalizeLearningRecords(
      records,
    );

  if (!normalized.length) {
    return {
      ready:
        false,

      sampleCount:
        0,

      accuracy:
        null,

      weightedAccuracy:
        null,

      averageReturn:
        null,

      medianReturn:
        null,

      volatility:
        null,

      profitFactor:
        null,

      profitFactorInfinite:
        false,

      maximumDrawdown:
        null,

      calibrationError:
        null,

      averageConfidence:
        null,

      averageScore:
        null,

      streaks: {
        currentWinStreak:
          0,

        currentLossStreak:
          0,

        maximumWinStreak:
          0,

        maximumLossStreak:
          0,
      },
    };
  }

  const wins =
    normalized.filter(
      (
        record,
      ) =>
        record.correct,
    ).length;

  const totalWeight =
    normalized.reduce(
      (
        sum,
        record,
      ) =>
        sum +
        record.weight,
      0,
    );

  const weightedWins =
    normalized.reduce(
      (
        sum,
        record,
      ) =>
        sum +
        (
          record.correct
            ? record.weight
            : 0
        ),
      0,
    );

  const returns =
    normalized.map(
      (
        record,
      ) =>
        record.directionalReturn,
    );

  const profitFactor =
    calculateProfitFactor(
      returns,
    );

  return {
    ready:
      true,

    sampleCount:
      normalized.length,

    winCount:
      wins,

    lossCount:
      normalized.length -
      wins,

    accuracy:
      round(
        (
          wins /
          normalized.length
        ) *
        100,
        2,
      ),

    weightedAccuracy:
      totalWeight > 0
        ? round(
            (
              weightedWins /
              totalWeight
            ) *
            100,
            2,
          )
        : null,

    averageReturn:
      round(
        average(
          returns,
        ) ?? 0,
        4,
      ),

    medianReturn:
      round(
        median(
          returns,
        ) ?? 0,
        4,
      ),

    volatility:
      round(
        standardDeviation(
          returns,
        ) ?? 0,
        4,
      ),

    profitFactor:
      Number.isFinite(
        profitFactor,
      )
        ? round(
            profitFactor,
            4,
          )
        : null,

    profitFactorInfinite:
      profitFactor === Infinity,

    maximumDrawdown:
      round(
        calculateMaximumDrawdown(
          returns,
        ),
        4,
      ),

    calibrationError:
      round(
        average(
          normalized.map(
            (
              record,
            ) =>
              record.calibrationError,
          ),
        ) ?? 0,
        2,
      ),

    averageConfidence:
      round(
        average(
          normalized.map(
            (
              record,
            ) =>
              record.confidence,
          ),
        ) ?? 0,
        2,
      ),

    averageScore:
      round(
        average(
          normalized.map(
            (
              record,
            ) =>
              record.predictedScore,
          ),
        ) ?? 0,
        2,
      ),

    streaks:
      calculateStreaks(
        normalized,
      ),
  };
}

export function createInitialLearningState({
  modelId = "default-model",
  modelVersion = "unknown",
  baseWeight = 1,
  minimumWeight = 0.02,
  maximumWeight = 0.8,
  createdAt = null,
} = {}) {
  const timestamp =
    createdAt ??
    new Date().toISOString();

  return {
    version:
      AI_LEARNING_CORE_V2_VERSION,

    schemaVersion:
      AI_LEARNING_CORE_V2_SCHEMA_VERSION,

    modelId:
      String(modelId),

    modelVersion:
      String(modelVersion),

    createdAt:
      timestamp,

    updatedAt:
      timestamp,

    revision:
      0,

    enabled:
      true,

    weights: {
      base:
        Math.max(
          0,
          finiteNumber(
            baseWeight,
            1,
          ),
        ),

      minimum:
        Math.max(
          0,
          finiteNumber(
            minimumWeight,
            0.02,
          ),
        ),

      maximum:
        Math.max(
          finiteNumber(
            minimumWeight,
            0.02,
          ),
          finiteNumber(
            maximumWeight,
            0.8,
          ),
        ),

      byRegime:
        {},

      byHorizon:
        {},
    },

    metrics:
      calculateLearningMetrics(
        [],
      ),

    history: {
      recordCount:
        0,

      latestRecordId:
        null,

      latestTimestamp:
        null,
    },

    safeguards: {
      frozen:
        false,

      freezeReason:
        null,

      promotionAllowed:
        false,

      rollbackRequired:
        false,
    },

    metadata:
      {},
  };
}

export {
  DIRECTIONS,
  normalizeDirection,
  directionLabel,
  normalizeRegime,
};
function groupRecords(
  records,
  selector,
) {
  const groups =
    new Map();

  for (const record of records) {
    const key =
      selector(record);

    if (!groups.has(key)) {
      groups.set(
        key,
        [],
      );
    }

    groups.get(
      key,
    ).push(
      record,
    );
  }

  return groups;
}

function calculateRecencyWeight({
  timestampMilliseconds,
  newestTimestamp,
  halfLifeDays,
}) {
  if (
    !Number.isFinite(
      timestampMilliseconds,
    ) ||
    !Number.isFinite(
      newestTimestamp,
    ) ||
    halfLifeDays <= 0
  ) {
    return 1;
  }

  const ageDays =
    Math.max(
      0,
      (
        newestTimestamp -
        timestampMilliseconds
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

function calculateReward({
  record,
  returnScale,
  confidencePenalty,
}) {
  const directionReward =
    record.correct
      ? 1
      : -1;

  const returnReward =
    Math.tanh(
      record.directionalReturn /
      Math.max(
        0.000001,
        returnScale,
      ),
    );

  const normalizedConfidence =
    record.confidence /
    100;

  const calibrationPenalty =
    record.correct
      ? (
          1 -
          normalizedConfidence
        )
      : normalizedConfidence;

  return Math.max(
    -1,
    Math.min(
      1,
      directionReward *
        0.55 +
      returnReward *
        0.35 -
      calibrationPenalty *
        confidencePenalty *
        0.1,
    ),
  );
}

function summarizeRewardGroup({
  records,
  newestTimestamp,
  halfLifeDays,
  returnScale,
  confidencePenalty,
}) {
  let weightedReward = 0;
  let totalWeight = 0;

  for (const record of records) {
    const recencyWeight =
      calculateRecencyWeight({
        timestampMilliseconds:
          record.timestampMilliseconds,

        newestTimestamp,

        halfLifeDays,
      });

    const effectiveWeight =
      recencyWeight *
      record.weight;

    weightedReward +=
      calculateReward({
        record,

        returnScale,

        confidencePenalty,
      }) *
      effectiveWeight;

    totalWeight +=
      effectiveWeight;
  }

  return {
    sampleCount:
      records.length,

    averageReward:
      totalWeight > 0
        ? weightedReward /
          totalWeight
        : 0,

    effectiveWeight:
      totalWeight,
  };
}

function normalizeWeightBounds({
  minimumWeight,
  maximumWeight,
}) {
  const minimum =
    Math.max(
      0,
      finiteNumber(
        minimumWeight,
        0.02,
      ),
    );

  const maximum =
    Math.max(
      minimum,
      finiteNumber(
        maximumWeight,
        0.8,
      ),
    );

  return {
    minimum,
    maximum,
  };
}

function boundWeight(
  value,
  bounds,
) {
  return Math.min(
    bounds.maximum,
    Math.max(
      bounds.minimum,
      value,
    ),
  );
}

function calculateAdaptiveRate({
  learningRate,
  sampleCount,
  minimumSamples,
  maximumLearningRate,
}) {
  const confidence =
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
    learningRate *
    (
      0.25 +
      confidence *
      0.75
    ),
  );
}

export function evaluateLearningSafeguards({
  metrics,
  minimumSamples = 20,
  minimumAccuracy = 45,
  maximumDrawdown = 25,
  maximumCalibrationError = 35,
  maximumLossStreak = 8,
} = {}) {
  const blockers = [];
  const warnings = [];

  if (
    !metrics ||
    metrics.ready !== true
  ) {
    blockers.push(
      "METRICS_NOT_READY",
    );
  }

  if (
    (
      metrics?.sampleCount ??
      0
    ) <
    minimumSamples
  ) {
    warnings.push(
      "INSUFFICIENT_SAMPLES",
    );
  }

  if (
    Number.isFinite(
      metrics?.accuracy,
    ) &&
    metrics.accuracy <
    minimumAccuracy
  ) {
    blockers.push(
      "LOW_ACCURACY",
    );
  }

  if (
    Number.isFinite(
      metrics?.maximumDrawdown,
    ) &&
    metrics.maximumDrawdown >
    maximumDrawdown
  ) {
    blockers.push(
      "EXCESSIVE_DRAWDOWN",
    );
  }

  if (
    Number.isFinite(
      metrics?.calibrationError,
    ) &&
    metrics.calibrationError >
    maximumCalibrationError
  ) {
    warnings.push(
      "POOR_CONFIDENCE_CALIBRATION",
    );
  }

  if (
    (
      metrics?.streaks
        ?.currentLossStreak ??
      0
    ) >=
    maximumLossStreak
  ) {
    blockers.push(
      "LOSS_STREAK_LIMIT",
    );
  }

  const frozen =
    blockers.length > 0;

  return {
    frozen,

    freezeReason:
      frozen
        ? blockers[0]
        : null,

    promotionAllowed:
      !frozen &&
      warnings.length === 0 &&
      (
        metrics?.sampleCount ??
        0
      ) >=
      minimumSamples,

    rollbackRequired:
      blockers.includes(
        "EXCESSIVE_DRAWDOWN",
      ) ||
      blockers.includes(
        "LOSS_STREAK_LIMIT",
      ),

    blockers,

    warnings,
  };
}

export function updateLearningState({
  state,
  records = [],
  learningRate = 0.25,
  regimeLearningRate = 0.2,
  horizonLearningRate = 0.15,
  maximumLearningRate = 0.5,
  minimumSamples = 10,
  recencyHalfLifeDays = 45,
  returnScale = 3,
  confidencePenalty = 1,
  safeguards = {},
  updatedAt = null,
} = {}) {
  const normalizedRecords =
    normalizeLearningRecords(
      records,
    );

  const currentState =
    state &&
    typeof state === "object"
      ? structuredClone(state)
      : createInitialLearningState({
          modelId:
            normalizedRecords[0]
              ?.modelId ??
            "default-model",

          modelVersion:
            normalizedRecords[0]
              ?.modelVersion ??
            "unknown",
        });

  if (!normalizedRecords.length) {
    return {
      ...currentState,

      updatedAt:
        updatedAt ??
        currentState.updatedAt,

      safeguards:
        evaluateLearningSafeguards({
          metrics:
            currentState.metrics,

          ...safeguards,
        }),

      update: {
        changed:
          false,

        reason:
          "NO_RECORDS",

        recordCount:
          0,
      },
    };
  }

  const bounds =
    normalizeWeightBounds({
      minimumWeight:
        currentState.weights
          ?.minimum,

      maximumWeight:
        currentState.weights
          ?.maximum,
    });

  const newestTimestamp =
    Math.max(
      ...normalizedRecords.map(
        (
          record,
        ) =>
          record.timestampMilliseconds,
      ),
    );

  const overallSummary =
    summarizeRewardGroup({
      records:
        normalizedRecords,

      newestTimestamp,

      halfLifeDays:
        Math.max(
          0,
          finiteNumber(
            recencyHalfLifeDays,
            45,
          ),
        ),

      returnScale:
        Math.max(
          0.000001,
          finiteNumber(
            returnScale,
            3,
          ),
        ),

      confidencePenalty:
        Math.max(
          0,
          finiteNumber(
            confidencePenalty,
            1,
          ),
        ),
    });

  const adaptiveRate =
    calculateAdaptiveRate({
      learningRate:
        Math.max(
          0,
          finiteNumber(
            learningRate,
            0.25,
          ),
        ),

      sampleCount:
        overallSummary.sampleCount,

      minimumSamples:
        Math.max(
          1,
          finiteNumber(
            minimumSamples,
            10,
          ),
        ),

      maximumLearningRate:
        Math.max(
          0,
          finiteNumber(
            maximumLearningRate,
            0.5,
          ),
        ),
    });

  const previousBaseWeight =
    finiteNumber(
      currentState.weights
        ?.base,
      1,
    );

  const updatedBaseWeight =
    boundWeight(
      previousBaseWeight *
      Math.exp(
        adaptiveRate *
        overallSummary.averageReward,
      ),
      bounds,
    );

  const byRegime = {
    ...(
      currentState.weights
        ?.byRegime ??
      {}
    ),
  };

  const regimeGroups =
    groupRecords(
      normalizedRecords,
      (
        record,
      ) =>
        record.regime,
    );

  for (
    const [
      regime,
      regimeRecords,
    ]
    of regimeGroups.entries()
  ) {
    const summary =
      summarizeRewardGroup({
        records:
          regimeRecords,

        newestTimestamp,

        halfLifeDays:
          Math.max(
            0,
            finiteNumber(
              recencyHalfLifeDays,
              45,
            ),
          ),

        returnScale:
          Math.max(
            0.000001,
            finiteNumber(
              returnScale,
              3,
            ),
          ),

        confidencePenalty:
          Math.max(
            0,
            finiteNumber(
              confidencePenalty,
              1,
            ),
          ),
      });

    const rate =
      calculateAdaptiveRate({
        learningRate:
          Math.max(
            0,
            finiteNumber(
              regimeLearningRate,
              0.2,
            ),
          ),

        sampleCount:
          summary.sampleCount,

        minimumSamples:
          Math.max(
            1,
            finiteNumber(
              minimumSamples,
              10,
            ),
          ),

        maximumLearningRate:
          Math.max(
            0,
            finiteNumber(
              maximumLearningRate,
              0.5,
            ),
          ),
      });

    const previous =
      finiteNumber(
        byRegime[
          regime
        ],
        previousBaseWeight,
      );

    byRegime[
      regime
    ] =
      round(
        boundWeight(
          previous *
          Math.exp(
            rate *
            summary.averageReward,
          ),
          bounds,
        ),
      );
  }

  const byHorizon = {
    ...(
      currentState.weights
        ?.byHorizon ??
      {}
    ),
  };

  const horizonGroups =
    groupRecords(
      normalizedRecords,
      (
        record,
      ) =>
        String(
          record.horizon,
        ),
    );

  for (
    const [
      horizon,
      horizonRecords,
    ]
    of horizonGroups.entries()
  ) {
    const summary =
      summarizeRewardGroup({
        records:
          horizonRecords,

        newestTimestamp,

        halfLifeDays:
          Math.max(
            0,
            finiteNumber(
              recencyHalfLifeDays,
              45,
            ),
          ),

        returnScale:
          Math.max(
            0.000001,
            finiteNumber(
              returnScale,
              3,
            ),
          ),

        confidencePenalty:
          Math.max(
            0,
            finiteNumber(
              confidencePenalty,
              1,
            ),
          ),
      });

    const rate =
      calculateAdaptiveRate({
        learningRate:
          Math.max(
            0,
            finiteNumber(
              horizonLearningRate,
              0.15,
            ),
          ),

        sampleCount:
          summary.sampleCount,

        minimumSamples:
          Math.max(
            1,
            finiteNumber(
              minimumSamples,
              10,
            ),
          ),

        maximumLearningRate:
          Math.max(
            0,
            finiteNumber(
              maximumLearningRate,
              0.5,
            ),
          ),
      });

    const previous =
      finiteNumber(
        byHorizon[
          horizon
        ],
        previousBaseWeight,
      );

    byHorizon[
      horizon
    ] =
      round(
        boundWeight(
          previous *
          Math.exp(
            rate *
            summary.averageReward,
          ),
          bounds,
        ),
      );
  }

  const metrics =
    calculateLearningMetrics(
      normalizedRecords,
    );

  const evaluatedSafeguards =
    evaluateLearningSafeguards({
      metrics,

      ...safeguards,
    });

  const latestRecord =
    normalizedRecords[
      normalizedRecords.length -
      1
    ];

  const nextState = {
    ...currentState,

    version:
      AI_LEARNING_CORE_V2_VERSION,

    schemaVersion:
      AI_LEARNING_CORE_V2_SCHEMA_VERSION,

    modelId:
      currentState.modelId ??
      latestRecord.modelId,

    modelVersion:
      currentState.modelVersion ??
      latestRecord.modelVersion,

    updatedAt:
      updatedAt ??
      new Date().toISOString(),

    revision:
      Math.max(
        0,
        Math.floor(
          finiteNumber(
            currentState.revision,
            0,
          ),
        ),
      ) +
      1,

    weights: {
      base:
        round(
          updatedBaseWeight,
        ),

      minimum:
        bounds.minimum,

      maximum:
        bounds.maximum,

      byRegime,

      byHorizon,
    },

    metrics,

    history: {
      recordCount:
        (
          currentState.history
            ?.recordCount ??
          0
        ) +
        normalizedRecords.length,

      latestRecordId:
        latestRecord.id,

      latestTimestamp:
        latestRecord.timestamp,
    },

    safeguards:
      evaluatedSafeguards,

    update: {
      changed:
        Math.abs(
          updatedBaseWeight -
          previousBaseWeight
        ) >
        0.0000001,

      reason:
        evaluatedSafeguards.frozen
          ? "UPDATED_AND_FROZEN"
          : "LEARNING_UPDATE_APPLIED",

      recordCount:
        normalizedRecords.length,

      averageReward:
        round(
          overallSummary.averageReward,
        ),

      adaptiveLearningRate:
        round(
          adaptiveRate,
        ),

      previousBaseWeight:
        round(
          previousBaseWeight,
        ),

      newBaseWeight:
        round(
          updatedBaseWeight,
        ),
    },
  };

  return nextState;
}

export function createLearningPatch(
  state,
) {
  if (
    !state ||
    typeof state !== "object"
  ) {
    return {
      version:
        AI_LEARNING_CORE_V2_VERSION,

      ready:
        false,

      reason:
        "STATE_NOT_AVAILABLE",
    };
  }

  return {
    version:
      AI_LEARNING_CORE_V2_VERSION,

    schemaVersion:
      AI_LEARNING_CORE_V2_SCHEMA_VERSION,

    ready:
      state.metrics
        ?.ready === true,

    modelId:
      state.modelId,

    modelVersion:
      state.modelVersion,

    revision:
      state.revision,

    enabled:
      state.enabled !== false,

    weight:
      state.weights
        ?.base ??
      1,

    regimeWeights: {
      ...(
        state.weights
          ?.byRegime ??
        {}
      ),
    },

    horizonWeights: {
      ...(
        state.weights
          ?.byHorizon ??
        {}
      ),
    },

    historicalAccuracy:
      state.metrics
        ?.weightedAccuracy ??
      state.metrics
        ?.accuracy ??
      null,

    performance: {
      accuracy:
        state.metrics
          ?.accuracy ??
        null,

      averageReturn:
        state.metrics
          ?.averageReturn ??
        null,

      profitFactor:
        state.metrics
          ?.profitFactor ??
        null,

      maximumDrawdown:
        state.metrics
          ?.maximumDrawdown ??
        null,

      calibrationError:
        state.metrics
          ?.calibrationError ??
        null,

      sampleCount:
        state.metrics
          ?.sampleCount ??
        0,
    },

    safeguards: {
      ...(
        state.safeguards ??
        {}
      ),
    },

    updatedAt:
      state.updatedAt,
  };
}

export function buildLearningReport({
  state,
  records = [],
} = {}) {
  const normalizedRecords =
    normalizeLearningRecords(
      records,
    );

  const byRegime =
    Object.fromEntries(
      Array.from(
        groupRecords(
          normalizedRecords,
          (
            record,
          ) =>
            record.regime,
        ).entries(),
      ).map(
        (
          [
            regime,
            regimeRecords,
          ],
        ) => [
          regime,
          calculateLearningMetrics(
            regimeRecords,
          ),
        ],
      ),
    );

  const byHorizon =
    Object.fromEntries(
      Array.from(
        groupRecords(
          normalizedRecords,
          (
            record,
          ) =>
            String(
              record.horizon,
            ),
        ).entries(),
      ).map(
        (
          [
            horizon,
            horizonRecords,
          ],
        ) => [
          horizon,
          calculateLearningMetrics(
            horizonRecords,
          ),
        ],
      ),
    );

  return {
    version:
      AI_LEARNING_CORE_V2_VERSION,

    ready:
      state?.metrics
        ?.ready === true,

    modelId:
      state?.modelId ??
      null,

    revision:
      state?.revision ??
      0,

    overall:
      state?.metrics ??
      calculateLearningMetrics(
        normalizedRecords,
      ),

    byRegime,

    byHorizon,

    weights:
      state?.weights ??
      null,

    safeguards:
      state?.safeguards ??
      null,

    update:
      state?.update ??
      null,

    diagnostics: {
      recordCount:
        normalizedRecords.length,

      regimeCount:
        Object.keys(
          byRegime,
        ).length,

      horizonCount:
        Object.keys(
          byHorizon,
        ).length,
    },
  };
}

export class AILearningCoreV2 {
  constructor({
    state = null,
    config = {},
  } = {}) {
    this.config = {
      ...config,
    };

    this.state =
      state
        ? structuredClone(
            state,
          )
        : createInitialLearningState(
            config,
          );
  }

  learn(
    records = [],
    overrides = {},
  ) {
    this.state =
      updateLearningState({
        ...this.config,

        ...overrides,

        state:
          this.state,

        records,
      });

    return structuredClone(
      this.state,
    );
  }

  getState() {
    return structuredClone(
      this.state,
    );
  }

  getPatch() {
    return createLearningPatch(
      this.state,
    );
  }

  report(
    records = [],
  ) {
    return buildLearningReport({
      state:
        this.state,

      records,
    });
  }

  reset(config = {}) {
    this.state =
      createInitialLearningState({
        ...this.config,

        ...config,
      });

    return this.getState();
  }
}

export const aiLearningCoreV2 =
  new AILearningCoreV2();

export default updateLearningState;