export const CONTINUOUS_MODEL_VERSION = "continuous-robust-ridge-v2";

export const CONTINUOUS_FEATURE_KEYS = Object.freeze([
  "rsiCentered",
  "macdHistogram",
  "ma25Atr",
  "volumeLog",
  "adxStrength",
  "stochasticCentered",
  "bollingerCentered",
  "highProximity",
  "lowProximity",
  "volatilityLog",
  "adxTrend",
  "volumeTrend",
  "rangeReversion",
  "trendMomentum",
]);

export const CONTINUOUS_MODEL_CANDIDATE_OPTIONS = Object.freeze([
  Object.freeze({
    id: "balanced-r04-h05",
    regularization: 0.04,
    huberDelta: 0.5,
  }),
  Object.freeze({
    id: "balanced-r04-h10",
    regularization: 0.04,
    huberDelta: 1,
  }),
  Object.freeze({
    id: "balanced-r08-h05",
    regularization: 0.08,
    huberDelta: 0.5,
  }),
  Object.freeze({
    id: "balanced-r08-h10",
    regularization: 0.08,
    huberDelta: 1,
  }),
  Object.freeze({
    id: "balanced-r16-h05",
    regularization: 0.16,
    huberDelta: 0.5,
  }),
  Object.freeze({
    id: "balanced-r16-h10",
    regularization: 0.16,
    huberDelta: 1,
  }),
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

function median(values) {
  if (!values.length) {
    return 0;
  }

  const ordered = [...values].sort((first, second) => first - second);
  const middle = Math.floor(ordered.length / 2);

  return ordered.length % 2
    ? ordered[middle]
    : (ordered[middle - 1] + ordered[middle]) / 2;
}

function weightedAverage(items) {
  const totalWeight = items.reduce(
    (sum, item) => sum + Number(item.weight || 0),
    0,
  );

  if (totalWeight <= 0) {
    return 0;
  }

  return (
    items.reduce(
      (sum, item) =>
        sum + Number(item.value || 0) * Number(item.weight || 0),
      0,
    ) / totalWeight
  );
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
  const distanceFrom52WeekLow = finite(values.distanceFrom52WeekLow)
    ? Number(values.distanceFrom52WeekLow)
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
    rsiCentered: finite(rsi)
      ? clamp((rsi - 50) / 25, -2, 2)
      : null,
    macdHistogram,
    ma25Atr,
    volumeLog:
      finite(volumeRatio) && volumeRatio > 0
        ? clamp(Math.log(volumeRatio), -3, 3)
        : null,
    adxStrength: finite(adx)
      ? clamp((adx - 20) / 20, -1, 3)
      : null,
    stochasticCentered: finite(stochasticK)
      ? clamp((stochasticK - 50) / 25, -2, 2)
      : null,
    bollingerCentered: finite(bollingerPercentB)
      ? clamp((bollingerPercentB - 0.5) * 2, -2, 2)
      : null,
    highProximity: finite(distanceFrom52WeekHigh)
      ? clamp(1 + distanceFrom52WeekHigh / 20, -2, 1)
      : null,
    lowProximity: finite(distanceFrom52WeekLow)
      ? clamp(1 - distanceFrom52WeekLow / 20, -2, 1)
      : null,
    volatilityLog:
      finite(atrPercent) && atrPercent > 0
        ? clamp(Math.log(Math.max(atrPercent, 0.05)), -3, 3)
        : null,
  };

  const trendAxis = finite(base.ma25Atr)
    ? Math.tanh(base.ma25Atr)
    : null;
  const trendWeight = finite(base.adxStrength)
    ? clamp(base.adxStrength, 0, 2)
    : null;
  const rangeWeight = finite(base.adxStrength)
    ? clamp(1 - Math.max(base.adxStrength, 0), 0, 1)
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
    rangeReversion:
      finite(base.rsiCentered) && finite(rangeWeight)
        ? base.rsiCentered * rangeWeight
        : null,
    trendMomentum:
      finite(trendAxis) &&
      finite(trendWeight) &&
      finite(base.rsiCentered)
        ? trendAxis *
          trendWeight *
          (1 + Math.abs(base.rsiCentered) * 0.5)
        : null,
  };
}

function availableFeatureCount(features) {
  return CONTINUOUS_FEATURE_KEYS.filter((key) =>
    finite(features[key]),
  ).length;
}

function robustStatistic(values) {
  const numbers = values.filter(finite).map(Number);

  if (!numbers.length) {
    return {
      center: 0,
      scale: 1,
      median: 0,
      mad: 0,
      availableCount: 0,
    };
  }

  const center = median(numbers);
  const absoluteDeviations = numbers.map((value) =>
    Math.abs(value - center),
  );
  const mad = median(absoluteDeviations);
  const madScale = mad * 1.4826;

  const ordered = [...numbers].sort((first, second) => first - second);
  const lower = ordered[Math.floor((ordered.length - 1) * 0.25)];
  const upper = ordered[Math.floor((ordered.length - 1) * 0.75)];
  const iqrScale = (upper - lower) / 1.349;

  const mean = average(numbers);
  const variance = average(
    numbers.map((value) => (value - mean) ** 2),
  );
  const deviation = Math.sqrt(variance);

  const scale =
    madScale > 1e-9
      ? madScale
      : iqrScale > 1e-9
        ? iqrScale
        : deviation > 1e-9
          ? deviation
          : 1;

  return {
    center,
    scale,
    median: center,
    mad,
    availableCount: numbers.length,
  };
}

function featureStatistics(rows) {
  return Object.fromEntries(
    CONTINUOUS_FEATURE_KEYS.map((key) => [
      key,
      robustStatistic(rows.map((row) => row.features[key])),
    ]),
  );
}

function standardizedVector(features, statistics) {
  return CONTINUOUS_FEATURE_KEYS.map((key) => {
    const statistic = statistics[key];

    if (!finite(features[key])) {
      return 0;
    }

    return clamp(
      (Number(features[key]) - statistic.center) /
        statistic.scale,
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

function huberLoss(error, delta) {
  const absoluteError = Math.abs(error);

  return absoluteError <= delta
    ? 0.5 * error ** 2
    : delta * (absoluteError - 0.5 * delta);
}

function huberGradient(error, delta) {
  if (Math.abs(error) <= delta) {
    return error;
  }

  return delta * Math.sign(error);
}

function classWeightMap(prepared, enabled = true) {
  const counts = prepared.reduce((result, row) => {
    result[row.labelName] = (result[row.labelName] || 0) + 1;
    return result;
  }, {});

  if (!enabled) {
    return Object.fromEntries(
      Object.keys(counts).map((key) => [key, 1]),
    );
  }

  const classCount = Math.max(1, Object.keys(counts).length);
  const total = prepared.length;

  return Object.fromEntries(
    Object.entries(counts).map(([key, count]) => [
      key,
      total / (classCount * count),
    ]),
  );
}

function modelLoss(
  rows,
  intercept,
  weights,
  regularization,
  huberDelta,
) {
  if (!rows.length) {
    return null;
  }

  const totalWeight = rows.reduce(
    (sum, row) => sum + row.sampleWeight,
    0,
  );

  const errorLoss =
    rows.reduce((sum, row) => {
      const error =
        intercept + dot(weights, row.vector) - row.label;

      return (
        sum +
        row.sampleWeight * huberLoss(error, huberDelta)
      );
    }, 0) / Math.max(totalWeight, 1e-9);

  const penalty =
    regularization *
    weights.reduce((sum, weight) => sum + weight ** 2, 0);

  return errorLoss + penalty;
}

export function fitContinuousModel(
  records,
  {
    candidateId = "default",
    minimumSamples = 20,
    minimumAvailableFeatures = 5,
    epochs = 1000,
    learningRate = 0.025,
    regularization = 0.08,
    huberDelta = 0.75,
    classBalance = true,
    patience = 100,
    tolerance = 1e-7,
  } = {},
) {
  const prepared = (records || [])
    .map((record) => ({
      record,
      labelName: record?.actualLabel || null,
      label: labelValue(record),
      features: extractContinuousFeatures(record),
    }))
    .filter(
      (row) =>
        row.label !== null &&
        availableFeatureCount(row.features) >=
          minimumAvailableFeatures,
    );

  if (prepared.length < minimumSamples) {
    return {
      ready: false,
      version: CONTINUOUS_MODEL_VERSION,
      candidateId,
      sampleCount: prepared.length,
      minimumSamples,
      reason: `学習に必要な${minimumSamples}件へ到達していません。`,
    };
  }

  const statistics = featureStatistics(prepared);
  const classWeights = classWeightMap(prepared, classBalance);
  const rows = prepared.map((row) => ({
    label: row.label,
    vector: standardizedVector(row.features, statistics),
    sampleWeight: classWeights[row.labelName] || 1,
  }));

  let intercept = weightedAverage(
    rows.map((row) => ({
      value: row.label,
      weight: row.sampleWeight,
    })),
  );
  let weights = Array(CONTINUOUS_FEATURE_KEYS.length).fill(0);
  let bestLoss = Number.POSITIVE_INFINITY;
  let bestIntercept = intercept;
  let bestWeights = [...weights];
  let staleEpochs = 0;
  let epochsCompleted = 0;

  for (let epoch = 0; epoch < epochs; epoch += 1) {
    const totalWeight = rows.reduce(
      (sum, row) => sum + row.sampleWeight,
      0,
    );
    let interceptGradient = 0;
    const weightGradients = Array(weights.length).fill(0);

    rows.forEach((row) => {
      const prediction = intercept + dot(weights, row.vector);
      const error = prediction - row.label;
      const weightedGradient =
        (row.sampleWeight / Math.max(totalWeight, 1e-9)) *
        huberGradient(error, huberDelta);

      interceptGradient += weightedGradient;

      row.vector.forEach((value, index) => {
        weightGradients[index] += weightedGradient * value;
      });
    });

    weights = weights.map((weight, index) => {
      const gradient =
        weightGradients[index] +
        2 * regularization * weight;

      return weight - learningRate * clamp(gradient, -5, 5);
    });

    intercept -=
      learningRate * clamp(interceptGradient, -5, 5);
    epochsCompleted = epoch + 1;

    const loss = modelLoss(
      rows,
      intercept,
      weights,
      regularization,
      huberDelta,
    );

    if (loss + tolerance < bestLoss) {
      bestLoss = loss;
      bestIntercept = intercept;
      bestWeights = [...weights];
      staleEpochs = 0;
    } else {
      staleEpochs += 1;

      if (staleEpochs >= patience) {
        break;
      }
    }
  }

  intercept = bestIntercept;
  weights = bestWeights;

  const labelCounts = prepared.reduce((counts, row) => {
    counts[row.labelName] = (counts[row.labelName] || 0) + 1;
    return counts;
  }, {});

  return {
    ready: true,
    version: CONTINUOUS_MODEL_VERSION,
    candidateId,
    sampleCount: rows.length,
    featureCount: CONTINUOUS_FEATURE_KEYS.length,
    featureKeys: [...CONTINUOUS_FEATURE_KEYS],
    statistics,
    intercept,
    weights,
    regularization,
    huberDelta,
    classBalance,
    classWeights,
    epochsRequested: epochs,
    epochsCompleted,
    labelCounts,
    trainingLoss: bestLoss,
    preprocessing: "median-mad-robust-scaling",
    lossFunction: "class-balanced-huber-ridge",
    leakageGuard:
      "予測時点に保存されたfeatures.valuesだけを説明変数として使用",
  };
}

export function fitContinuousModelCandidates(
  records,
  {
    candidates = CONTINUOUS_MODEL_CANDIDATE_OPTIONS,
    ...sharedOptions
  } = {},
) {
  return candidates.map((candidate) =>
    fitContinuousModel(records, {
      ...sharedOptions,
      ...candidate,
      candidateId: candidate.id,
    }),
  );
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
  average,
  median,
  weightedAverage,
  labelValue,
  availableFeatureCount,
  robustStatistic,
  featureStatistics,
  standardizedVector,
  dot,
  huberLoss,
  huberGradient,
  classWeightMap,
  modelLoss,
};