export const CONTINUOUS_MODEL_VERSION = "continuous-ridge-v1";

export const CONTINUOUS_FEATURE_KEYS = Object.freeze([
  "rsiCentered",
  "macdHistogram",
  "ma25Atr",
  "volumeLog",
  "adxStrength",
  "stochasticCentered",
  "bollingerCentered",
  "highProximity",
  "adxTrend",
  "volumeTrend",
]);

const LABEL_VALUES = Object.freeze({
  上昇: 1,
  中立: 0,
  下落: -1,
});

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, Number(value)));
}

function average(values) {
  return values.length
    ? values.reduce((sum, value) => sum + Number(value), 0) / values.length
    : 0;
}

function labelValue(record) {
  return Object.hasOwn(LABEL_VALUES, record?.actualLabel)
    ? LABEL_VALUES[record.actualLabel]
    : null;
}

export function extractContinuousFeatures(record = {}) {
  const values = record.features?.values || {};
  const rsi = finite(values.rsi) ? Number(values.rsi) : null;
  const macdHistogram = finite(values.macdHistogram)
    ? Number(values.macdHistogram)
    : null;
  const ma25Deviation = finite(values.ma25Deviation)
    ? Number(values.ma25Deviation)
    : null;
  const volumeRatio = finite(values.volumeRatio)
    ? Number(values.volumeRatio)
    : null;
  const atrPercent = finite(values.atrPercent)
    ? Math.abs(Number(values.atrPercent))
    : null;
  const adx = finite(values.adx) ? Number(values.adx) : null;
  const stochasticK = finite(values.stochasticK)
    ? Number(values.stochasticK)
    : null;
  const bollingerPercentB = finite(values.bollingerPercentB)
    ? Number(values.bollingerPercentB)
    : null;
  const distanceFrom52WeekHigh = finite(values.distanceFrom52WeekHigh)
    ? Number(values.distanceFrom52WeekHigh)
    : null;

  const ma25Atr =
    finite(ma25Deviation) && finite(atrPercent)
      ? clamp(
          ma25Deviation / Math.max(atrPercent, 0.25),
          -6,
          6,
        )
      : null;

  const base = {
    rsiCentered: finite(rsi) ? clamp((rsi - 50) / 25, -2, 2) : null,
    macdHistogram,
    ma25Atr,
    volumeLog:
      finite(volumeRatio) && volumeRatio > 0
        ? clamp(Math.log(volumeRatio), -3, 3)
        : null,
    adxStrength: finite(adx) ? clamp((adx - 20) / 20, -1, 3) : null,
    stochasticCentered: finite(stochasticK)
      ? clamp((stochasticK - 50) / 25, -2, 2)
      : null,
    bollingerCentered: finite(bollingerPercentB)
      ? clamp((bollingerPercentB - 0.5) * 2, -2, 2)
      : null,
    highProximity: finite(distanceFrom52WeekHigh)
      ? clamp(1 + distanceFrom52WeekHigh / 20, -2, 1)
      : null,
  };

  const trendAxis = finite(base.ma25Atr)
    ? Math.tanh(base.ma25Atr)
    : null;

  return {
    ...base,
    adxTrend:
      finite(base.adxStrength) && finite(trendAxis)
        ? base.adxStrength * trendAxis
        : null,
    volumeTrend:
      finite(base.volumeLog) && finite(trendAxis)
        ? base.volumeLog * trendAxis
        : null,
  };
}

function availableFeatureCount(features) {
  return CONTINUOUS_FEATURE_KEYS.filter((key) => finite(features[key])).length;
}

function featureStatistics(rows) {
  return Object.fromEntries(
    CONTINUOUS_FEATURE_KEYS.map((key) => {
      const values = rows
        .map((row) => row.features[key])
        .filter(finite)
        .map(Number);
      const mean = average(values);
      const variance = values.length
        ? average(values.map((value) => (value - mean) ** 2))
        : 0;
      const deviation = Math.sqrt(variance);

      return [
        key,
        {
          mean,
          deviation: deviation > 1e-9 ? deviation : 1,
          availableCount: values.length,
        },
      ];
    }),
  );
}

function standardizedVector(features, statistics) {
  return CONTINUOUS_FEATURE_KEYS.map((key) => {
    const statistic = statistics[key];

    if (!finite(features[key])) {
      return 0;
    }

    return clamp(
      (Number(features[key]) - statistic.mean) / statistic.deviation,
      -4,
      4,
    );
  });
}

function dot(first, second) {
  return first.reduce(
    (sum, value, index) => sum + value * second[index],
    0,
  );
}

function modelLoss(rows, intercept, weights, regularization) {
  if (!rows.length) {
    return null;
  }

  const errorLoss = average(
    rows.map((row) => {
      const error = intercept + dot(weights, row.vector) - row.label;
      return error ** 2;
    }),
  );
  const penalty =
    regularization *
    weights.reduce((sum, weight) => sum + weight ** 2, 0);

  return errorLoss + penalty;
}

export function fitContinuousModel(
  records,
  {
    minimumSamples = 20,
    minimumAvailableFeatures = 5,
    epochs = 700,
    learningRate = 0.03,
    regularization = 0.08,
  } = {},
) {
  const prepared = (records || [])
    .map((record) => ({
      record,
      label: labelValue(record),
      features: extractContinuousFeatures(record),
    }))
    .filter(
      (row) =>
        row.label !== null &&
        availableFeatureCount(row.features) >= minimumAvailableFeatures,
    );

  if (prepared.length < minimumSamples) {
    return {
      ready: false,
      version: CONTINUOUS_MODEL_VERSION,
      sampleCount: prepared.length,
      minimumSamples,
      reason: `学習に必要な${minimumSamples}件へ到達していません。`,
    };
  }

  const statistics = featureStatistics(prepared);
  const rows = prepared.map((row) => ({
    label: row.label,
    vector: standardizedVector(row.features, statistics),
  }));
  const labelAverage = average(rows.map((row) => row.label));

  let intercept = labelAverage;
  let weights = Array(CONTINUOUS_FEATURE_KEYS.length).fill(0);

  for (let epoch = 0; epoch < epochs; epoch += 1) {
    let interceptGradient = 0;
    const weightGradients = Array(weights.length).fill(0);

    rows.forEach((row) => {
      const prediction = intercept + dot(weights, row.vector);
      const error = prediction - row.label;

      interceptGradient += (2 * error) / rows.length;

      row.vector.forEach((value, index) => {
        weightGradients[index] +=
          (2 * error * value) / rows.length;
      });
    });

    weights = weights.map(
      (weight, index) =>
        weight -
        learningRate *
          (weightGradients[index] + 2 * regularization * weight),
    );
    intercept -= learningRate * interceptGradient;
  }

  const labelCounts = prepared.reduce(
    (counts, row) => {
      const label = row.record.actualLabel;

      counts[label] = (counts[label] || 0) + 1;
      return counts;
    },
    {},
  );

  return {
    ready: true,
    version: CONTINUOUS_MODEL_VERSION,
    sampleCount: rows.length,
    featureCount: CONTINUOUS_FEATURE_KEYS.length,
    featureKeys: [...CONTINUOUS_FEATURE_KEYS],
    statistics,
    intercept,
    weights,
    regularization,
    epochs,
    labelCounts,
    trainingLoss: modelLoss(
      rows,
      intercept,
      weights,
      regularization,
    ),
    leakageGuard:
      "予測時点に保存されたfeatures.valuesだけを説明変数として使用",
  };
}

export function predictContinuousValue(model, record) {
  if (!model?.ready) {
    return null;
  }

  const features = extractContinuousFeatures(record);
  const vector = standardizedVector(features, model.statistics);

  return model.intercept + dot(model.weights, vector);
}

export function predictContinuousScore(model, record) {
  const value = predictContinuousValue(model, record);

  if (!finite(value)) {
    return null;
  }

  return clamp(50 + clamp(value, -2, 2) * 25, 0, 100);
}

export const ContinuousModelInternals = {
  finite,
  clamp,
  labelValue,
  availableFeatureCount,
  featureStatistics,
  standardizedVector,
  dot,
  modelLoss,
};