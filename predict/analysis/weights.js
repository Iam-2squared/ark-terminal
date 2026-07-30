import {
  DEFAULT_WEIGHTS,
  MINIMUM_OPTIMIZER_SAMPLES,
  STORAGE_KEYS,
} from "../config.js";

function copyDefaultWeights() {
  return {
    ...DEFAULT_WEIGHTS,
  };
}

function normalizeWeights(weights) {
  const entries = Object.entries(DEFAULT_WEIGHTS).map(([key, fallback]) => [
    key,
    Number.isFinite(Number(weights?.[key]))
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
      Number.isFinite(Number(record.actualReturn)) &&
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
        Number.isFinite(Number(record.factorScores[key])) &&
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
};
