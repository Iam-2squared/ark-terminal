const DEFAULT_WEIGHT = 1;
const MINIMUM_SAMPLE_SIZE = 10;
const FULL_CONFIDENCE_SAMPLE_SIZE = 50;
const MAXIMUM_WEIGHT_CHANGE = 0.2;

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function clamp(value, minimum, maximum) {
  return Math.min(
    maximum,
    Math.max(minimum, value),
  );
}

function average(values) {
  const safeValues =
    values.filter(finite).map(Number);

  if (!safeValues.length) {
    return null;
  }

  return (
    safeValues.reduce(
      (sum, value) => sum + value,
      0,
    ) / safeValues.length
  );
}

function round(value, digits = 4) {
  if (!finite(value)) {
    return null;
  }

  const factor = 10 ** digits;

  return (
    Math.round(Number(value) * factor) /
    factor
  );
}

function resolvedApprovedRecords(records) {
  return (
    Array.isArray(records)
      ? records
      : []
  ).filter(
    (record) =>
      record?.status === "resolved" &&
      record?.decision === "approve" &&
      finite(
        record?.evaluation
          ?.actualReturnPercent,
      ),
  );
}

function indicatorSnapshot(record) {
  const indicators =
    record?.daily?.indicators || {};

  const movingAverages =
    indicators.movingAverages || {};

  const macd =
    indicators.macd || {};

  const currentPrice =
    finite(indicators.currentPrice)
      ? Number(indicators.currentPrice)
      : null;

  const ma25 =
    finite(movingAverages.ma25)
      ? Number(movingAverages.ma25)
      : null;

  const ma75 =
    finite(movingAverages.ma75)
      ? Number(movingAverages.ma75)
      : null;

  return {
    movingAverage:
      currentPrice !== null &&
      ma25 !== null
        ? (
            currentPrice >= ma25 &&
            (
              ma75 === null ||
              ma25 >= ma75
            )
          )
        : null,

    rsi:
      finite(indicators.rsi)
        ? Number(indicators.rsi)
        : null,

    macd:
      finite(macd.histogram)
        ? Number(macd.histogram) > 0
        : (
            finite(macd.value) &&
            finite(macd.signal)
              ? Number(macd.value) >=
                Number(macd.signal)
              : null
          ),

    adx:
      finite(indicators.adx?.value)
        ? Number(indicators.adx.value)
        : (
            finite(indicators.adx)
              ? Number(indicators.adx)
              : null
          ),

    volumeRatio:
      finite(record?.intraday?.volumeRatio)
        ? Number(record.intraday.volumeRatio)
        : null,

    setupStrength:
      finite(
        record?.intraday
          ?.setupStrengthScore,
      )
        ? Number(
            record.intraday
              .setupStrengthScore,
          )
        : null,

    dataQuality:
      finite(
        record?.intraday
          ?.dataQualityScore,
      )
        ? Number(
            record.intraday
              .dataQualityScore,
          )
        : null,

    marketRegime:
      record?.daily?.marketRegime ??
      null,
  };
}

function classifySignals(record) {
  const snapshot =
    indicatorSnapshot(record);

  return {
    movingAverage:
      snapshot.movingAverage === true,

    rsi:
      finite(snapshot.rsi) &&
      snapshot.rsi >= 35 &&
      snapshot.rsi <= 65,

    macd:
      snapshot.macd === true,

    adx:
      finite(snapshot.adx) &&
      snapshot.adx >= 20,

    volume:
      finite(snapshot.volumeRatio) &&
      snapshot.volumeRatio >= 1,

    setupStrength:
      finite(snapshot.setupStrength) &&
      snapshot.setupStrength >= 70,

    dataQuality:
      finite(snapshot.dataQuality) &&
      snapshot.dataQuality >= 80,

    marketEnvironment:
      [
        "bullish",
        "risk-on",
        "strong",
        "positive",
      ].includes(
        String(
          snapshot.marketRegime || "",
        ).toLowerCase(),
      ),
  };
}

function confidenceFromSampleSize(sampleSize) {
  if (sampleSize < MINIMUM_SAMPLE_SIZE) {
    return 0;
  }

  return clamp(
    (
      sampleSize -
      MINIMUM_SAMPLE_SIZE
    ) /
    (
      FULL_CONFIDENCE_SAMPLE_SIZE -
      MINIMUM_SAMPLE_SIZE
    ),
    0,
    1,
  );
}

function metricScore({
  winRate,
  averageReturnPercent,
  averageAdverseMovePercent,
}) {
  const winComponent =
    finite(winRate)
      ? (
          Number(winRate) - 50
        ) / 50
      : 0;

  const returnComponent =
    finite(averageReturnPercent)
      ? clamp(
          Number(averageReturnPercent) /
          10,
          -1,
          1,
        )
      : 0;

  const adversePenalty =
    finite(averageAdverseMovePercent)
      ? clamp(
          Math.abs(
            Math.min(
              0,
              Number(
                averageAdverseMovePercent,
              ),
            ),
          ) / 10,
          0,
          1,
        )
      : 0;

  return clamp(
    (
      winComponent * 0.55 +
      returnComponent * 0.35 -
      adversePenalty * 0.1
    ),
    -1,
    1,
  );
}

function suggestedWeight({
  score,
  sampleSize,
  baseWeight = DEFAULT_WEIGHT,
}) {
  const confidence =
    confidenceFromSampleSize(sampleSize);

  const change =
    clamp(
      score *
      confidence *
      MAXIMUM_WEIGHT_CHANGE,
      -MAXIMUM_WEIGHT_CHANGE,
      MAXIMUM_WEIGHT_CHANGE,
    );

  return round(
    Number(baseWeight) *
    (1 + change),
    4,
  );
}

function summarizeSignal(
  records,
  signalName,
  baseWeight,
) {
  const matched =
    records.filter(
      (record) =>
        classifySignals(record)[signalName] === true,
    );

  const sampleSize =
    matched.length;

  const wins =
    matched.filter(
      (record) =>
        record?.evaluation?.hit === true,
    ).length;

  const winRate =
    sampleSize > 0
      ? (wins / sampleSize) * 100
      : null;

  const averageReturnPercent =
    average(
      matched.map(
        (record) =>
          record?.evaluation
            ?.actualReturnPercent,
      ),
    );

  const averageFavorableMovePercent =
    average(
      matched.map(
        (record) =>
          record?.evaluation
            ?.maximumFavorableMovePercent,
      ),
    );

  const averageAdverseMovePercent =
    average(
      matched.map(
        (record) =>
          record?.evaluation
            ?.maximumAdverseMovePercent,
      ),
    );

  const score =
    metricScore({
      winRate,
      averageReturnPercent,
      averageAdverseMovePercent,
    });

  const confidence =
    confidenceFromSampleSize(sampleSize);

  return {
    signal: signalName,
    sampleSize,
    wins,

    losses:
      sampleSize - wins,

    winRate:
      round(winRate, 2),

    averageReturnPercent:
      round(
        averageReturnPercent,
        3,
      ),

    averageFavorableMovePercent:
      round(
        averageFavorableMovePercent,
        3,
      ),

    averageAdverseMovePercent:
      round(
        averageAdverseMovePercent,
        3,
      ),

    score:
      round(score, 4),

    confidence:
      round(confidence, 4),

    enoughData:
      sampleSize >=
      MINIMUM_SAMPLE_SIZE,

    baseWeight,

    suggestedWeight:
      suggestedWeight({
        score,
        sampleSize,
        baseWeight,
      }),

    maximumChangePercent:
      MAXIMUM_WEIGHT_CHANGE * 100,
  };
}

export function analyzeTradeMemoryLearning(
  records,
  baseWeights = {},
) {
  const resolved =
    resolvedApprovedRecords(records);

  const signals = [
    "movingAverage",
    "rsi",
    "macd",
    "adx",
    "volume",
    "setupStrength",
    "dataQuality",
    "marketEnvironment",
  ];

  const metrics =
    Object.fromEntries(
      signals.map(
        (signal) => [
          signal,

          summarizeSignal(
            resolved,
            signal,
            finite(baseWeights[signal])
              ? Number(baseWeights[signal])
              : DEFAULT_WEIGHT,
          ),
        ],
      ),
    );

  const eligible =
    Object.values(metrics)
      .filter(
        (metric) =>
          metric.enoughData,
      );

  return {
    version:
      "ark-trade-memory-learning-v1",

    generatedAt:
      new Date().toISOString(),

    resolvedApprovalCount:
      resolved.length,

    minimumSampleSize:
      MINIMUM_SAMPLE_SIZE,

    fullConfidenceSampleSize:
      FULL_CONFIDENCE_SAMPLE_SIZE,

    maximumWeightChangePercent:
      MAXIMUM_WEIGHT_CHANGE * 100,

    readyForOptimization:
      eligible.length > 0,

    eligibleSignalCount:
      eligible.length,

    metrics,

    suggestedWeights:
      Object.fromEntries(
        Object.entries(metrics)
          .map(
            ([signal, metric]) => [
              signal,
              metric.suggestedWeight,
            ],
          ),
      ),

    warnings: [
      resolved.length <
      MINIMUM_SAMPLE_SIZE
        ? "解決済みの承認記録が少ないため、重みは実質変更されません。"
        : null,

      "推奨ウェイトは候補値です。自動適用前にバックテスト検証が必要です。",
    ].filter(Boolean),
  };
}

export function applyLearningWeightsSafely(
  currentWeights,
  learningResult,
  options = {},
) {
  const allowApply =
    options.allowApply === true;

  if (!allowApply) {
    return {
      applied: false,

      reason:
        "explicit_approval_required",

      weights: {
        ...currentWeights,
      },
    };
  }

  if (
    !learningResult
      ?.readyForOptimization
  ) {
    return {
      applied: false,

      reason:
        "insufficient_data",

      weights: {
        ...currentWeights,
      },
    };
  }

  const nextWeights = {
    ...currentWeights,
  };

  for (
    const [
      signal,
      metric,
    ] of Object.entries(
      learningResult.metrics || {},
    )
  ) {
    if (!metric.enoughData) {
      continue;
    }

    const current =
      finite(currentWeights?.[signal])
        ? Number(currentWeights[signal])
        : DEFAULT_WEIGHT;

    const lower =
      current *
      (
        1 -
        MAXIMUM_WEIGHT_CHANGE
      );

    const upper =
      current *
      (
        1 +
        MAXIMUM_WEIGHT_CHANGE
      );

    nextWeights[signal] =
      clamp(
        Number(
          metric.suggestedWeight,
        ),
        lower,
        upper,
      );
  }

  return {
    applied: true,
    reason: "approved",
    weights: nextWeights,
  };
}

export const TradeMemoryLearningInternals = {
  average,
  classifySignals,
  confidenceFromSampleSize,
  finite,
  indicatorSnapshot,
  metricScore,
  resolvedApprovedRecords,
  suggestedWeight,
};