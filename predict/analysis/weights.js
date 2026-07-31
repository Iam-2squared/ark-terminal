import {
  DEFAULT_WEIGHTS,
  MINIMUM_OPTIMIZER_SAMPLES,
  STORAGE_KEYS,
} from "../config.js";

function finiteNumber(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function copyDefaultWeights() {
  return {
    ...DEFAULT_WEIGHTS,
  };
}

function normalizeWeights(weights) {
  const entries = Object.entries(DEFAULT_WEIGHTS).map(([key, fallback]) => [
    key,
    finiteNumber(weights?.[key])
      ? Math.max(0.1, Number(weights[key]))
      : fallback,
  ]);

  const total = entries.reduce((sum, [, value]) => sum + value, 0);

  if (!total) {
    return copyDefaultWeights();
  }

  return Object.fromEntries(
    entries.map(([key, value]) => [key, (value / total) * 100]),
  );
}

export function loadWeights() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.weights));

    return normalizeWeights(saved);
  } catch {
    return copyDefaultWeights();
  }
}

export function saveWeights(weights) {
  const normalized = normalizeWeights(weights);

  localStorage.setItem(STORAGE_KEYS.weights, JSON.stringify(normalized));

  return normalized;
}

export function resetWeights() {
  localStorage.removeItem(STORAGE_KEYS.weights);

  return copyDefaultWeights();
}

export function deriveOptimizedWeights(records, currentWeights) {
  const hasTrainingPartition = records.some(
    (record) => record.partition === "training",
  );
  const resolved = records.filter(
    (record) =>
      record.status === "resolved" &&
      finiteNumber(record.actualReturn) &&
      record.factorScores &&
      (!hasTrainingPartition || record.partition === "training"),
  );
  const normalizedCurrent = normalizeWeights(currentWeights);

  if (resolved.length < MINIMUM_OPTIMIZER_SAMPLES) {
    return {
      updated: false,
      weights: normalizedCurrent,
      sampleCount: resolved.length,
      required: MINIMUM_OPTIMIZER_SAMPLES,
      message: `重み調整には学習期間の確定済みデータが最低${MINIMUM_OPTIMIZER_SAMPLES}件必要です。`,
    };
  }

  const adjusted = {
    ...normalizedCurrent,
  };

  Object.keys(DEFAULT_WEIGHTS).forEach((key) => {
    const samples = resolved.filter(
      (record) =>
        finiteNumber(record.factorScores[key]) &&
        (Number(record.factorScores[key]) >= 55 ||
          Number(record.factorScores[key]) <= 45),
    );

    if (samples.length < MINIMUM_OPTIMIZER_SAMPLES) {
      return;
    }

    const correct = samples.filter((record) => {
      const factorScore = Number(record.factorScores[key]);

      const predictedUp = factorScore >= 55;

      const actualUp = Number(record.actualReturn) > 0;

      return predictedUp === actualUp;
    }).length;

    const accuracy = correct / samples.length;

    const adjustment = Math.max(-0.05, Math.min(0.05, (accuracy - 0.5) * 0.2));

    adjusted[key] = Number(normalizedCurrent[key]) * (1 + adjustment);
  });

  const weights = normalizeWeights(adjusted);

  return {
    updated: true,
    weights,
    sampleCount: resolved.length,
    required: MINIMUM_OPTIMIZER_SAMPLES,
    message: hasTrainingPartition
      ? "学習期間だけを使い、各重みを1回あたり最大5%の範囲で調整しました。検証・最終テスト期間は使っていません。"
      : "確定済み実績を基に、各重みを1回あたり最大5%の範囲で調整しました。",
  };
}

function factorEvidence(records, key) {
  const samples = records.filter(
    (record) =>
      finiteNumber(record.factorScores?.[key]) &&
      (Number(record.factorScores[key]) >= 55 ||
        Number(record.factorScores[key]) <= 45),
  );
  const correct = samples.filter((record) => {
    const predictedUp = Number(record.factorScores[key]) >= 55;
    const actualUp = Number(record.actualReturn) > 0;

    return predictedUp === actualUp;
  }).length;
  const accuracy = samples.length ? (correct / samples.length) * 100 : null;
  const shrinkage = samples.length / (samples.length + 30);
  const reliableAccuracy =
    accuracy === null ? null : 50 + (accuracy - 50) * shrinkage;

  return {
    sampleCount: samples.length,
    accuracy,
    reliableAccuracy,
  };
}

function recommendationRecords(records) {
  const hasTrainingPartition = records.some(
    (record) => record.partition === "training",
  );

  return {
    hasTrainingPartition,
    records: records.filter(
      (record) =>
        record.status === "resolved" &&
        finiteNumber(record.actualReturn) &&
        record.factorScores &&
        (!hasTrainingPartition || record.partition === "training"),
    ),
  };
}

export function recommendWeights(records, currentWeights = loadWeights()) {
  const source = recommendationRecords(records);
  const current = normalizeWeights(currentWeights);
  const evidence = Object.fromEntries(
    Object.keys(DEFAULT_WEIGHTS).map((key) => [
      key,
      factorEvidence(source.records, key),
    ]),
  );

  if (source.records.length < MINIMUM_OPTIMIZER_SAMPLES) {
    return {
      ready: false,
      sampleCount: source.records.length,
      required: MINIMUM_OPTIMIZER_SAMPLES,
      current,
      recommended: current,
      evidence,
      message: `推奨重みの算出には学習用の確定データが最低${MINIMUM_OPTIMIZER_SAMPLES}件必要です。`,
    };
  }

  const adjusted = Object.fromEntries(
    Object.entries(current).map(([key, value]) => {
      const item = evidence[key];

      if (item.sampleCount < 5 || !Number.isFinite(item.reliableAccuracy)) {
        return [key, value];
      }

      const adjustment = Math.max(
        -0.1,
        Math.min(0.1, ((item.reliableAccuracy - 50) / 50) * 0.1),
      );

      return [key, value * (1 + adjustment)];
    }),
  );
  const recommended = normalizeWeights(adjusted);

  return {
    ready: true,
    sampleCount: source.records.length,
    required: MINIMUM_OPTIMIZER_SAMPLES,
    current,
    recommended,
    evidence,
    trainingOnly: source.hasTrainingPartition,
    message: source.hasTrainingPartition
      ? "学習期間だけから推奨重みを計算しました。採用するまで現在のスコアには反映されません。"
      : "既存の確定データから推奨重みを計算しました。採用するまで現在のスコアには反映されません。",
  };
}

export function recommendWeightsByIndustry(
  records,
  currentWeights = loadWeights(),
) {
  const groups = new Map();

  records
    .filter((record) => record.status === "resolved")
    .forEach((record) => {
      const industry = record.industry || "未分類";

      if (!groups.has(industry)) groups.set(industry, []);
      groups.get(industry).push(record);
    });

  return Array.from(groups.entries())
    .map(([industry, items]) => ({
      industry,
      ...recommendWeights(items, currentWeights),
    }))
    .filter((item) => item.ready)
    .sort((first, second) => second.sampleCount - first.sampleCount);
}

export function optimizeWeights(records, currentWeights = loadWeights()) {
  const result = deriveOptimizedWeights(records, currentWeights);

  if (!result.updated) {
    return result;
  }

  return {
    ...result,
    weights: saveWeights(result.weights),
  };
}

export const WeightInternals = {
  normalizeWeights,
  factorEvidence,
  recommendationRecords,
};
