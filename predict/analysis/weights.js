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

export function optimizeWeights(records, currentWeights = loadWeights()) {
  const resolved = records.filter(
    (record) =>
      record.status === "resolved" &&
      Number.isFinite(Number(record.actualReturn)) &&
      record.factorScores,
  );

  if (resolved.length < MINIMUM_OPTIMIZER_SAMPLES) {
    return {
      updated: false,
      weights: normalizeWeights(currentWeights),
      sampleCount: resolved.length,
      required: MINIMUM_OPTIMIZER_SAMPLES,
      message: `最適化には最低${MINIMUM_OPTIMIZER_SAMPLES}件の確定済みデータが必要です。`,
    };
  }

  const adjusted = {
    ...currentWeights,
  };

  Object.keys(DEFAULT_WEIGHTS).forEach((key) => {
    const samples = resolved.filter((record) =>
      Number.isFinite(Number(record.factorScores[key])),
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

    adjusted[key] = Number(currentWeights[key]) * (1 + adjustment);
  });

  const weights = saveWeights(adjusted);

  return {
    updated: true,
    weights,
    sampleCount: resolved.length,
    required: MINIMUM_OPTIMIZER_SAMPLES,
    message:
      "確定済み実績を基に、各重みを1回あたり最大5%の範囲で調整しました。",
  };
}

export const WeightInternals = {
  normalizeWeights,
};
