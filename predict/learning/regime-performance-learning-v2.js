export const REGIME_PERFORMANCE_LEARNING_V2_VERSION =
  "regime-performance-learning-v2";

const REGIMES =
  Object.freeze([
    "TRENDING_BULL",
    "TRENDING_BEAR",
    "RANGE",
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
    "UNKNOWN",
  ]);

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
          value - mean
        ) ** 2,
      0,
    ) /
    values.length;

  return Math.sqrt(
    variance,
  );
}

function normalizeRegime(value) {
  const text =
    String(value ?? "")
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

  const normalized =
    aliases[text] ??
    text;

  return REGIMES.includes(
    normalized,
  )
    ? normalized
    : "UNKNOWN";
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

  const modelId =
    String(
      record.modelId ??
      record.model ??
      record.name ??
      "",
    ).trim();

  if (!modelId) {
    return null;
  }

  const prediction =
    record.prediction ??
    record.signal ??
    record.direction;

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
      typeof prediction === "object"
        ? prediction.confidence ??
          prediction.probability ??
          record.confidence ??
          50
        : record.confidence ??
          50,
    ) ?? 50;

  const actualReturn =
    finiteOrNull(
      record.actualReturn ??
      record.return ??
      record.realizedReturn ??
      record.outcome,
    );

  const actualDirection =
    actualReturn === null
      ? normalizeDirection(
          record.actualDirection ??
          record.resultDirection,
        )
      : actualReturn > 0
        ? 1
        : actualReturn < 0
          ? -1
          : 0;

  const timestampValue =
    record.timestamp ??
    record.date ??
    record.createdAt ??
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
        record.id ??
        `record-${index + 1}`,
      ),

    modelId,

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
        record.regime,
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

    weight:
      Math.max(
        0,
        finiteOrNull(
          record.weight,
        ) ?? 1,
      ),
  };
}

function isCorrect(
  predictedDirection,
  actualDirection,
) {
  if (
    predictedDirection === 0 ||
    actualDirection === 0
  ) {
    return (
      predictedDirection ===
      actualDirection
    );
  }

  return (
    predictedDirection ===
    actualDirection
  );
}

function calculateDirectionalReturn(
  record,
) {
  if (
    record.predictedDirection === 0
  ) {
    return 0;
  }

  return (
    record.actualReturn *
    record.predictedDirection
  );
}

function wilsonLowerBound(
  successes,
  trials,
  z = 1.96,
) {
  if (
    !trials ||
    trials <= 0
  ) {
    return null;
  }

  const probability =
    successes /
    trials;

  const denominator =
    1 +
    (
      z ** 2 /
      trials
    );

  const centre =
    probability +
    (
      z ** 2 /
      (
        2 *
        trials
      )
    );

  const margin =
    z *
    Math.sqrt(
      (
        probability *
        (
          1 -
          probability
        ) /
        trials
      ) +
      (
        z ** 2 /
        (
          4 *
          trials ** 2
        )
      ),
    );

  return (
    (
      centre -
      margin
    ) /
    denominator
  );
}

function calculateProfitFactor(
  directionalReturns,
) {
  const grossProfit =
    directionalReturns
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
          sum + value,
        0,
      );

  const grossLoss =
    Math.abs(
      directionalReturns
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
            sum + value,
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
  directionalReturns,
) {
  let equity = 100;
  let peak = 100;
  let maximumDrawdown = 0;

  for (
    const value
    of directionalReturns
  ) {
    equity *=
      1 +
      value / 100;

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

function groupBy(
  values,
  selector,
) {
  const groups =
    new Map();

  for (
    const value
    of values
  ) {
    const key =
      selector(value);

    if (!groups.has(key)) {
      groups.set(
        key,
        [],
      );
    }

    groups.get(
      key,
    ).push(
      value,
    );
  }

  return groups;
}

function calculateRecencyWeight(
  record,
  newestTimestamp,
  halfLifeDays,
) {
  if (
    !record.timestamp ||
    !Number.isFinite(
      newestTimestamp,
    ) ||
    halfLifeDays <= 0
  ) {
    return 1;
  }

  const timestamp =
    Date.parse(
      record.timestamp,
    );

  if (!Number.isFinite(timestamp)) {
    return 1;
  }

  const ageDays =
    Math.max(
      0,
      (
        newestTimestamp -
        timestamp
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

function summarizeRecords(
  records,
  {
    minimumSamples,
    priorAccuracy,
    priorStrength,
    recencyHalfLifeDays,
  },
) {
  const timestampValues =
    records
      .map(
        (
          record,
        ) =>
          record.timestamp
            ? Date.parse(
                record.timestamp,
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

  let weightedTrials = 0;
  let weightedCorrect = 0;
  let weightedConfidence = 0;
  let weightedConfidenceError = 0;

  const directionalReturns = [];
  const correctness = [];

  for (
    const record
    of records
  ) {
    const correct =
      isCorrect(
        record.predictedDirection,
        record.actualDirection,
      );

    const recencyWeight =
      calculateRecencyWeight(
        record,
        newestTimestamp,
        recencyHalfLifeDays,
      );

    const effectiveWeight =
      record.weight *
      recencyWeight;

    weightedTrials +=
      effectiveWeight;

    if (correct) {
      weightedCorrect +=
        effectiveWeight;
    }

    weightedConfidence +=
      record.confidence *
      effectiveWeight;

    weightedConfidenceError +=
      Math.abs(
        (
          correct
            ? 100
            : 0
        ) -
        record.confidence,
      ) *
      effectiveWeight;

    correctness.push(
      correct,
    );

    directionalReturns.push(
      calculateDirectionalReturn(
        record,
      ),
    );
  }

  const wins =
    correctness.filter(Boolean)
      .length;

  const losses =
    correctness.length -
    wins;

  const rawAccuracy =
    records.length
      ? (
          wins /
          records.length
        ) *
        100
      : null;

  const weightedAccuracy =
    weightedTrials > 0
      ? (
          weightedCorrect /
          weightedTrials
        ) *
        100
      : null;

  const shrunkAccuracy =
    weightedTrials > 0
      ? (
          (
            weightedCorrect +
            (
              priorAccuracy /
              100
            ) *
            priorStrength
          ) /
          (
            weightedTrials +
            priorStrength
          )
        ) *
        100
      : priorAccuracy;

  const lowerBound =
    wilsonLowerBound(
      wins,
      records.length,
    );

  const averageReturn =
    average(
      directionalReturns,
    );

  const volatility =
    standardDeviation(
      directionalReturns,
    );

  const profitFactor =
    calculateProfitFactor(
      directionalReturns,
    );

  const maximumDrawdown =
    calculateMaximumDrawdown(
      directionalReturns,
    );

  const averageConfidence =
    weightedTrials > 0
      ? weightedConfidence /
        weightedTrials
      : null;

  const calibrationError =
    weightedTrials > 0
      ? weightedConfidenceError /
        weightedTrials
      : null;

  const sampleConfidence =
    Math.min(
      1,
      records.length /
      Math.max(
        1,
        minimumSamples,
      ),
    );

  const returnScore =
    clamp(
      50 +
      (
        averageReturn ??
        0
      ) *
      8,
    ) ?? 50;

  const drawdownScore =
    clamp(
      100 -
      maximumDrawdown *
      4,
    ) ?? 0;

  const profitFactorScore =
    Number.isFinite(
      profitFactor,
    )
      ? clamp(
          profitFactor *
          35,
        ) ?? 0
      : profitFactor === Infinity
        ? 100
        : 0;

  const calibrationScore =
    clamp(
      100 -
      (
        calibrationError ??
        50
      ),
    ) ?? 0;

  const performanceScore =
    (
      shrunkAccuracy *
        0.45 +
      returnScore *
        0.2 +
      profitFactorScore *
        0.15 +
      drawdownScore *
        0.1 +
      calibrationScore *
        0.1
    ) *
    (
      0.5 +
      sampleConfidence *
      0.5
    );

  const multiplier =
    Math.min(
      1.75,
      Math.max(
        0.25,
        performanceScore /
        50,
      ),
    );

  return {
    sampleCount:
      records.length,

    wins,

    losses,

    rawAccuracy:
      rawAccuracy === null
        ? null
        : round(
            rawAccuracy,
            2,
          ),

    weightedAccuracy:
      weightedAccuracy === null
        ? null
        : round(
            weightedAccuracy,
            2,
          ),

    shrunkAccuracy:
      round(
        shrunkAccuracy,
        2,
      ),

    wilsonLowerBound:
      lowerBound === null
        ? null
        : round(
            lowerBound *
            100,
            2,
          ),

    averageReturn:
      averageReturn === null
        ? null
        : round(
            averageReturn,
            4,
          ),

    volatility:
      volatility === null
        ? null
        : round(
            volatility,
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
        : profitFactor === Infinity
          ? null
          : 0,

    profitFactorInfinite:
      profitFactor === Infinity,

    maximumDrawdown:
      round(
        maximumDrawdown,
        4,
      ),

    averageConfidence:
      averageConfidence === null
        ? null
        : round(
            averageConfidence,
            2,
          ),

    calibrationError:
      calibrationError === null
        ? null
        : round(
            calibrationError,
            2,
          ),

    performanceScore:
      round(
        performanceScore,
        2,
      ),

    multiplier:
      round(
        multiplier,
        4,
      ),

    sampleConfidence:
      round(
        sampleConfidence *
        100,
        2,
      ),

    ready:
      records.length >=
      minimumSamples,
  };
}

function buildRecommendation(
  summary,
  {
    promotionThreshold,
    demotionThreshold,
    minimumSamples,
  },
) {
  if (
    summary.sampleCount <
    minimumSamples
  ) {
    return {
      action:
        "HOLD",

      reason:
        "INSUFFICIENT_SAMPLES",
    };
  }

  if (
    summary.performanceScore >=
    promotionThreshold &&
    (
      summary.wilsonLowerBound ??
      0
    ) >= 50
  ) {
    return {
      action:
        "PROMOTE",

      reason:
        "STRONG_VALIDATED_PERFORMANCE",
    };
  }

  if (
    summary.performanceScore <=
    demotionThreshold
  ) {
    return {
      action:
        "DEMOTE",

      reason:
        "WEAK_REGIME_PERFORMANCE",
    };
  }

  return {
    action:
      "HOLD",

    reason:
      "PERFORMANCE_WITHIN_HOLD_RANGE",
  };
}

export function learnRegimePerformance({
  records = [],
  minimumSamples = 10,
  priorAccuracy = 50,
  priorStrength = 8,
  recencyHalfLifeDays = 45,
  promotionThreshold = 65,
  demotionThreshold = 40,
} = {}) {
  if (!Array.isArray(records)) {
    throw new TypeError(
      "Regime performance records must be an array.",
    );
  }

  const normalizedMinimumSamples =
    Math.max(
      1,
      Math.floor(
        finiteOrNull(
          minimumSamples,
        ) ?? 10,
      ),
    );

  const normalizedPriorAccuracy =
    clamp(
      priorAccuracy,
    ) ?? 50;

  const normalizedPriorStrength =
    Math.max(
      0,
      finiteOrNull(
        priorStrength,
      ) ?? 8,
    );

  const normalizedHalfLife =
    Math.max(
      0,
      finiteOrNull(
        recencyHalfLifeDays,
      ) ?? 45,
    );

  const normalizedRecords =
    records
      .map(
        normalizeRecord,
      )
      .filter(Boolean);

  if (!normalizedRecords.length) {
    return {
      version:
        REGIME_PERFORMANCE_LEARNING_V2_VERSION,

      ready:
        false,

      recordCount:
        0,

      modelCount:
        0,

      models:
        [],

      regimeSummary:
        {},

      recommendations: {
        promote:
          [],

        hold:
          [],

        demote:
          [],
      },
    };
  }

  const modelGroups =
    groupBy(
      normalizedRecords,
      (
        record,
      ) =>
        record.modelId,
    );

  const models = [];

  for (
    const [
      modelId,
      modelRecords,
    ]
    of modelGroups.entries()
  ) {
    const regimeGroups =
      groupBy(
        modelRecords,
        (
          record,
        ) =>
          record.regime,
      );

    const regimes = {};

    for (
      const regime
      of REGIMES
    ) {
      const regimeRecords =
        regimeGroups.get(
          regime,
        ) ?? [];

      if (!regimeRecords.length) {
        continue;
      }

      const summary =
        summarizeRecords(
          regimeRecords,
          {
            minimumSamples:
              normalizedMinimumSamples,

            priorAccuracy:
              normalizedPriorAccuracy,

            priorStrength:
              normalizedPriorStrength,

            recencyHalfLifeDays:
              normalizedHalfLife,
          },
        );

      regimes[
        regime
      ] = {
        ...summary,

        recommendation:
          buildRecommendation(
            summary,
            {
              promotionThreshold,

              demotionThreshold,

              minimumSamples:
                normalizedMinimumSamples,
            },
          ),
      };
    }

    const overall =
      summarizeRecords(
        modelRecords,
        {
          minimumSamples:
            normalizedMinimumSamples,

          priorAccuracy:
            normalizedPriorAccuracy,

          priorStrength:
            normalizedPriorStrength,

          recencyHalfLifeDays:
            normalizedHalfLife,
        },
      );

    const recommendation =
      buildRecommendation(
        overall,
        {
          promotionThreshold,

          demotionThreshold,

          minimumSamples:
            normalizedMinimumSamples,
        },
      );

    const regimePerformance =
      Object.fromEntries(
        Object.entries(
          regimes,
        ).map(
          (
            [
              regime,
              summary,
            ],
          ) => [
            regime,
            summary.shrunkAccuracy,
          ],
        ),
      );

    const regimeMultipliers =
      Object.fromEntries(
        Object.entries(
          regimes,
        ).map(
          (
            [
              regime,
              summary,
            ],
          ) => [
            regime,
            summary.multiplier,
          ],
        ),
      );

    models.push({
      modelId,

      family:
        modelRecords[0]
          ?.family ??
        "GENERAL",

      overall,

      regimes,

      regimePerformance,

      regimeMultipliers,

      recommendation,
    });
  }

  models.sort(
    (
      left,
      right,
    ) =>
      right.overall
        .performanceScore -
      left.overall
        .performanceScore,
  );

  const regimeSummary = {};

  for (
    const regime
    of REGIMES
  ) {
    const regimeRecords =
      normalizedRecords.filter(
        (
          record,
        ) =>
          record.regime ===
          regime,
      );

    if (!regimeRecords.length) {
      continue;
    }

    regimeSummary[
      regime
    ] =
      summarizeRecords(
        regimeRecords,
        {
          minimumSamples:
            normalizedMinimumSamples,

          priorAccuracy:
            normalizedPriorAccuracy,

          priorStrength:
            normalizedPriorStrength,

          recencyHalfLifeDays:
            normalizedHalfLife,
        },
      );
  }

  return {
    version:
      REGIME_PERFORMANCE_LEARNING_V2_VERSION,

    ready:
      true,

    recordCount:
      normalizedRecords.length,

    modelCount:
      models.length,

    configuration: {
      minimumSamples:
        normalizedMinimumSamples,

      priorAccuracy:
        normalizedPriorAccuracy,

      priorStrength:
        normalizedPriorStrength,

      recencyHalfLifeDays:
        normalizedHalfLife,

      promotionThreshold,

      demotionThreshold,
    },

    models,

    regimeSummary,

    recommendations: {
      promote:
        models
          .filter(
            (
              model,
            ) =>
              model.recommendation
                .action ===
              "PROMOTE",
          )
          .map(
            (
              model,
            ) =>
              model.modelId,
          ),

      hold:
        models
          .filter(
            (
              model,
            ) =>
              model.recommendation
                .action ===
              "HOLD",
          )
          .map(
            (
              model,
            ) =>
              model.modelId,
          ),

      demote:
        models
          .filter(
            (
              model,
            ) =>
              model.recommendation
                .action ===
              "DEMOTE",
          )
          .map(
            (
              model,
            ) =>
              model.modelId,
          ),
    },
  };
}

export function createEnsembleLearningPatch(
  learningResult,
) {
  if (
    !learningResult ||
    learningResult.ready !== true
  ) {
    return {
      version:
        REGIME_PERFORMANCE_LEARNING_V2_VERSION,

      ready:
        false,

      models:
        [],
    };
  }

  return {
    version:
      REGIME_PERFORMANCE_LEARNING_V2_VERSION,

    ready:
      true,

    models:
      learningResult.models.map(
        (
          model,
        ) => ({
          id:
            model.modelId,

          family:
            model.family,

          historicalAccuracy:
            model.overall
              .shrunkAccuracy,

          regimePerformance:
            model.regimePerformance,

          regimeMultipliers:
            model.regimeMultipliers,

          performanceScore:
            model.overall
              .performanceScore,

          recommendation:
            model.recommendation,
        }),
      ),
  };
}

export class RegimePerformanceLearningV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  learn(
    records = [],
    overrides = {},
  ) {
    return learnRegimePerformance({
      ...this.config,

      ...overrides,

      records,
    });
  }

  createPatch(
    records = [],
    overrides = {},
  ) {
    return createEnsembleLearningPatch(
      this.learn(
        records,
        overrides,
      ),
    );
  }
}

export const regimePerformanceLearningV2 =
  new RegimePerformanceLearningV2();

export {
  normalizeRegime,
};

export default learnRegimePerformance;