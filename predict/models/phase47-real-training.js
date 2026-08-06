import crypto from "node:crypto";

export const PHASE47_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const MODEL_TYPES = Object.freeze(["LOGISTIC_REGRESSION", "RANDOM_FOREST", "GRADIENT_BOOSTING"]);
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const sigmoid = (value) => 1 / (1 + Math.exp(-clamp(value, -35, 35)));
const mean = (values) => values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
const std = (values) => {
  if (values.length < 2) return 0;
  const m = mean(values);
  return Math.sqrt(mean(values.map((value) => (value - m) ** 2)));
};

function finite(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new TypeError(`${name} must be finite`);
  return number;
}

function stableHash(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

export function normalizeTrainingRows(rows = []) {
  if (!Array.isArray(rows) || rows.length < 20) throw new RangeError("at least 20 training rows are required");
  const normalized = rows.map((row, index) => {
    if (!row || typeof row !== "object") throw new TypeError(`row ${index} must be an object`);
    const date = String(row.sessionDate ?? row.featureCutoff ?? row.date ?? "");
    if (!/^\d{4}-\d{2}-\d{2}/.test(date)) throw new TypeError(`row ${index} has invalid date`);
    const label = Number(row.label ?? row.directionLabel ?? row.target);
    if (![0, 1].includes(label)) throw new TypeError(`row ${index} label must be 0 or 1`);
    const rawFeatures = row.features ?? row.featureValues ?? {};
    const entries = Object.entries(rawFeatures).filter(([, value]) => Number.isFinite(Number(value)));
    if (!entries.length) throw new TypeError(`row ${index} has no finite features`);
    return Object.freeze({
      id: String(row.id ?? `${row.symbol ?? "UNKNOWN"}:${date}:${index}`),
      symbol: String(row.symbol ?? "UNKNOWN"),
      sessionDate: date.slice(0, 10),
      label,
      actualReturn: finite(row.actualReturn ?? row.futureReturn ?? (label ? 0.01 : -0.01), `row ${index} actualReturn`),
      features: Object.freeze(Object.fromEntries(entries.map(([key, value]) => [key, Number(value)]))),
    });
  }).sort((a, b) => a.sessionDate.localeCompare(b.sessionDate) || a.id.localeCompare(b.id));
  return Object.freeze(normalized);
}

function featureNames(rows) {
  return [...new Set(rows.flatMap((row) => Object.keys(row.features)))].sort();
}

function standardizer(rows, names) {
  const stats = Object.fromEntries(names.map((name) => {
    const values = rows.map((row) => Number(row.features[name] ?? 0));
    const scale = std(values) || 1;
    return [name, { mean: mean(values), scale }];
  }));
  return {
    stats,
    vector(row) {
      return names.map((name) => (Number(row.features[name] ?? 0) - stats[name].mean) / stats[name].scale);
    },
  };
}

function trainLogistic(rows, names, options = {}) {
  const scaler = standardizer(rows, names);
  const learningRate = Number(options.learningRate ?? 0.08);
  const iterations = Number(options.iterations ?? 250);
  const l2 = Number(options.l2 ?? 0.001);
  const weights = Array(names.length).fill(0);
  let bias = 0;
  for (let step = 0; step < iterations; step += 1) {
    const gradient = Array(names.length).fill(0);
    let biasGradient = 0;
    for (const row of rows) {
      const x = scaler.vector(row);
      const probability = sigmoid(bias + weights.reduce((sum, weight, index) => sum + weight * x[index], 0));
      const error = probability - row.label;
      biasGradient += error;
      x.forEach((value, index) => { gradient[index] += error * value; });
    }
    bias -= learningRate * biasGradient / rows.length;
    weights.forEach((weight, index) => {
      weights[index] -= learningRate * ((gradient[index] / rows.length) + l2 * weight);
    });
  }
  return {
    type: "LOGISTIC_REGRESSION",
    names,
    scaler: scaler.stats,
    weights,
    bias,
    predict(row) {
      const x = names.map((name) => (Number(row.features[name] ?? 0) - scaler.stats[name].mean) / scaler.stats[name].scale);
      return sigmoid(bias + weights.reduce((sum, weight, index) => sum + weight * x[index], 0));
    },
  };
}

function bestStump(rows, names, residualSelector = (row) => row.label) {
  let best = null;
  for (const name of names) {
    const sorted = rows.map((row) => Number(row.features[name] ?? 0)).sort((a, b) => a - b);
    const candidates = sorted.filter((_, index) => index > 0 && index < sorted.length - 1).filter((_, index) => index % Math.max(1, Math.floor(sorted.length / 12)) === 0);
    for (const threshold of candidates) {
      const left = rows.filter((row) => Number(row.features[name] ?? 0) <= threshold);
      const right = rows.filter((row) => Number(row.features[name] ?? 0) > threshold);
      if (!left.length || !right.length) continue;
      const leftValue = mean(left.map(residualSelector));
      const rightValue = mean(right.map(residualSelector));
      const loss = [...left.map((row) => (residualSelector(row) - leftValue) ** 2), ...right.map((row) => (residualSelector(row) - rightValue) ** 2)].reduce((a, b) => a + b, 0);
      if (!best || loss < best.loss) best = { name, threshold, leftValue, rightValue, loss };
    }
  }
  return best ?? { name: names[0], threshold: 0, leftValue: 0.5, rightValue: 0.5, loss: Infinity };
}

function trainRandomForest(rows, names, options = {}) {
  const treeCount = Number(options.treeCount ?? 25);
  const trees = [];
  for (let treeIndex = 0; treeIndex < treeCount; treeIndex += 1) {
    const subset = rows.filter((_, index) => ((index * 17 + treeIndex * 13) % 7) < 5);
    const chosenNames = names.filter((_, index) => ((index + treeIndex) % 3) !== 0);
    trees.push(bestStump(subset.length >= 10 ? subset : rows, chosenNames.length ? chosenNames : names));
  }
  return {
    type: "RANDOM_FOREST",
    names,
    trees,
    predict(row) {
      return clamp(mean(trees.map((tree) => Number(row.features[tree.name] ?? 0) <= tree.threshold ? tree.leftValue : tree.rightValue)), 0.001, 0.999);
    },
  };
}

function trainGradientBoosting(rows, names, options = {}) {
  const rounds = Number(options.rounds ?? 30);
  const learningRate = Number(options.learningRate ?? 0.08);
  const base = clamp(mean(rows.map((row) => row.label)), 0.001, 0.999);
  const scores = new Map(rows.map((row) => [row.id, Math.log(base / (1 - base))]));
  const stumps = [];
  for (let round = 0; round < rounds; round += 1) {
    const stump = bestStump(rows, names, (row) => row.label - sigmoid(scores.get(row.id)));
    stumps.push(stump);
    for (const row of rows) {
      const update = Number(row.features[stump.name] ?? 0) <= stump.threshold ? stump.leftValue : stump.rightValue;
      scores.set(row.id, scores.get(row.id) + learningRate * update);
    }
  }
  const baseScore = Math.log(base / (1 - base));
  return {
    type: "GRADIENT_BOOSTING",
    names,
    baseScore,
    learningRate,
    stumps,
    predict(row) {
      const score = stumps.reduce((sum, stump) => sum + learningRate * (Number(row.features[stump.name] ?? 0) <= stump.threshold ? stump.leftValue : stump.rightValue), baseScore);
      return sigmoid(score);
    },
  };
}

export function trainModel({ rows, modelType, options = {} } = {}) {
  const normalized = normalizeTrainingRows(rows);
  const names = featureNames(normalized);
  if (!MODEL_TYPES.includes(modelType)) throw new TypeError(`unsupported modelType: ${modelType}`);
  const model = modelType === "LOGISTIC_REGRESSION" ? trainLogistic(normalized, names, options)
    : modelType === "RANDOM_FOREST" ? trainRandomForest(normalized, names, options)
      : trainGradientBoosting(normalized, names, options);
  const serializable = Object.fromEntries(Object.entries(model).filter(([, value]) => typeof value !== "function"));
  return Object.freeze({
    ...model,
    modelId: `phase47-${modelType.toLowerCase()}-${stableHash(serializable).slice(0, 16)}`,
    trainingRows: normalized.length,
    safety: PHASE47_SAFETY,
  });
}

function auc(labels, probabilities) {
  const positives = labels.map((label, index) => ({ label, probability: probabilities[index] })).filter((item) => item.label === 1);
  const negatives = labels.map((label, index) => ({ label, probability: probabilities[index] })).filter((item) => item.label === 0);
  if (!positives.length || !negatives.length) return 0.5;
  let score = 0;
  for (const positive of positives) for (const negative of negatives) score += positive.probability > negative.probability ? 1 : positive.probability === negative.probability ? 0.5 : 0;
  return score / (positives.length * negatives.length);
}

function strategyMetrics(rows, probabilities, threshold = 0.5, costRate = 0.001) {
  const returns = rows.map((row, index) => {
    const direction = probabilities[index] >= threshold ? 1 : -1;
    return direction * row.actualReturn - costRate;
  });
  const gains = returns.filter((value) => value > 0).reduce((a, b) => a + b, 0);
  const losses = Math.abs(returns.filter((value) => value < 0).reduce((a, b) => a + b, 0));
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  for (const value of returns) {
    equity *= 1 + value;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak ? (peak - equity) / peak : 0);
  }
  const sigma = std(returns);
  return {
    profitFactor: losses ? gains / losses : gains > 0 ? 999 : 0,
    sharpe: sigma ? mean(returns) / sigma * Math.sqrt(252) : 0,
    maxDrawdown,
    cagr: returns.length ? equity ** (252 / returns.length) - 1 : 0,
    tradeCount: returns.length,
    netReturn: equity - 1,
  };
}

export function evaluateModel({ model, rows, threshold = 0.5, costRate = 0.001 } = {}) {
  const normalized = normalizeTrainingRows(rows);
  const probabilities = normalized.map((row) => clamp(model.predict(row), 0.001, 0.999));
  const predictions = probabilities.map((value) => value >= threshold ? 1 : 0);
  const labels = normalized.map((row) => row.label);
  let tp = 0; let fp = 0; let tn = 0; let fn = 0;
  labels.forEach((label, index) => {
    if (label === 1 && predictions[index] === 1) tp += 1;
    else if (label === 0 && predictions[index] === 1) fp += 1;
    else if (label === 0 && predictions[index] === 0) tn += 1;
    else fn += 1;
  });
  return Object.freeze({
    accuracy: (tp + tn) / labels.length,
    precision: tp + fp ? tp / (tp + fp) : 0,
    recall: tp + fn ? tp / (tp + fn) : 0,
    auc: auc(labels, probabilities),
    brierScore: mean(probabilities.map((value, index) => (value - labels[index]) ** 2)),
    ...strategyMetrics(normalized, probabilities, threshold, costRate),
    threshold,
    sampleCount: labels.length,
    probabilities: Object.freeze(probabilities),
    safety: PHASE47_SAFETY,
  });
}

export { MODEL_TYPES };
