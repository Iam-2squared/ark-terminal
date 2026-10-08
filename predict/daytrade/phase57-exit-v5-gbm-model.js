import crypto from 'node:crypto';
import { assertExitV5ResearchSafety } from './phase57-exit-v5-continuation-dataset.js';
import { freezeExitV5ModelSpec, scoreExitV5Continuation, evaluateExitV5Predictions } from './phase57-exit-v5-continuation-model.js';
import { PHASE57_EXIT_V5_CONDITIONAL_POLICY } from './phase57-exit-v5-conditional-model.js';

export const PHASE57_EXIT_V5_GBM_POLICY = Object.freeze({
  modelType: 'DEVELOPMENT_ONLY_DETERMINISTIC_GBM_MEAN_QUANTILE_CONTINUATION',
  primaryHorizonBars: 3,
  meanObjective: 'SQUARED_ERROR',
  lowerQuantileObjective: 'PINBALL',
  defaultRounds: 32,
  defaultLearningRate: 0.05,
  defaultMaxThresholdCandidates: 16,
  defaultMinLeafSize: 64,
  lowerQuantile: 0.10,
  fitSplit: 'development',
  evaluationSplits: Object.freeze(['validation', 'oos', 'prospective']),
  shuffleAllowed: false,
  validationRetuningAllowed: false,
  outerOosRetuningAllowed: false,
  prospectiveRetuningAllowed: false,
  featureNames: PHASE57_EXIT_V5_CONDITIONAL_POLICY.featureNames,
});

const finite = (value, name) => {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(`${name} must be finite`);
  return number;
};

const mean = (values) => values.reduce((sum, value) => sum + value, 0) / values.length;

function quantile(values, q) {
  if (!values.length) throw new Error('quantile requires non-empty values');
  const ordered = [...values].sort((left, right) => left - right);
  const position = (ordered.length - 1) * q;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return ordered[lower];
  const weight = position - lower;
  return ordered[lower] * (1 - weight) + ordered[upper] * weight;
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function sha256(value) {
  return crypto.createHash('sha256').update(canonicalJson(value)).digest('hex');
}

function primaryLabel(sample) {
  return finite(
    sample?.labels?.incrementalLiquidationReturnPctByHorizon?.[PHASE57_EXIT_V5_GBM_POLICY.primaryHorizonBars],
    'primary 3-bar label',
  );
}

function assertChronological(samples, label) {
  let previous = -Infinity;
  for (const [index, sample] of samples.entries()) {
    const current = Date.parse(sample?.features?.featureAt);
    if (!Number.isFinite(current) || current < previous) throw new Error(`${label} samples must be chronological`);
    previous = current;
    for (const name of PHASE57_EXIT_V5_GBM_POLICY.featureNames) {
      finite(sample?.features?.[name], `${label}[${index}] feature ${name}`);
    }
  }
}

function freezeTree(tree) {
  return Object.freeze({
    featureName: tree.featureName,
    threshold: tree.threshold,
    leftValue: tree.leftValue,
    rightValue: tree.rightValue,
    splitLoss: tree.splitLoss,
  });
}

function candidateLeftCounts(sortedIndices, rows, featureName, maxCandidates, minLeafSize) {
  const available = sortedIndices.length - (2 * minLeafSize);
  if (available < 0) return Object.freeze([]);
  const counts = [];
  for (let rank = 1; rank <= maxCandidates; rank += 1) {
    const leftCount = minLeafSize + Math.floor((rank * (available + 1)) / (maxCandidates + 1));
    if (leftCount < minLeafSize || sortedIndices.length - leftCount < minLeafSize) continue;
    const leftValue = rows[sortedIndices[leftCount - 1]].features[featureName];
    const rightValue = rows[sortedIndices[leftCount]].features[featureName];
    if (leftValue === rightValue) continue;
    counts.push(leftCount);
  }
  return Object.freeze([...new Set(counts)].sort((left, right) => left - right));
}

function buildFeatureOrders(rows, featureNames, maxCandidates, minLeafSize) {
  return Object.freeze(Object.fromEntries(featureNames.map((featureName) => {
    const indices = rows.map((_, index) => index).sort((left, right) => (
      rows[left].features[featureName] - rows[right].features[featureName]
      || left - right
    ));
    return [featureName, Object.freeze({
      indices: Object.freeze(indices),
      leftCounts: candidateLeftCounts(indices, rows, featureName, maxCandidates, minLeafSize),
    })];
  })));
}

function bestSquaredErrorSplit({ rows, featureNames, featureOrders, pseudoResiduals }) {
  const totalSum = pseudoResiduals.reduce((sum, value) => sum + value, 0);
  const totalSquares = pseudoResiduals.reduce((sum, value) => sum + (value ** 2), 0);
  let best = null;

  for (const featureName of featureNames) {
    const { indices, leftCounts } = featureOrders[featureName];
    if (!leftCounts.length) continue;
    const wanted = new Set(leftCounts);
    let leftSum = 0;
    let leftSquares = 0;
    for (let sortedIndex = 0; sortedIndex < indices.length - 1; sortedIndex += 1) {
      const rowIndex = indices[sortedIndex];
      const residual = pseudoResiduals[rowIndex];
      leftSum += residual;
      leftSquares += residual ** 2;
      const leftCount = sortedIndex + 1;
      if (!wanted.has(leftCount)) continue;
      const rightCount = indices.length - leftCount;
      const rightSum = totalSum - leftSum;
      const rightSquares = totalSquares - leftSquares;
      const loss = Math.max(0, leftSquares - ((leftSum ** 2) / leftCount))
        + Math.max(0, rightSquares - ((rightSum ** 2) / rightCount));
      const leftFeatureValue = rows[indices[sortedIndex]].features[featureName];
      const rightFeatureValue = rows[indices[sortedIndex + 1]].features[featureName];
      const threshold = leftFeatureValue + ((rightFeatureValue - leftFeatureValue) / 2);
      if (!best || loss < best.splitLoss - 1e-15) {
        best = { featureName, threshold, splitLoss: loss };
      }
    }
  }
  if (!best) throw new Error('GBM could not find a valid Development split');
  return best;
}

function fitBoostedStumps({ rows, labels, featureNames, featureOrders, rounds, learningRate, objective, lowerQuantile }) {
  const baseValue = objective === 'MEAN' ? mean(labels) : quantile(labels, lowerQuantile);
  const predictions = Array(rows.length).fill(baseValue);
  const trees = [];

  for (let round = 0; round < rounds; round += 1) {
    const pseudoResiduals = labels.map((label, index) => (
      objective === 'MEAN'
        ? label - predictions[index]
        : lowerQuantile - (label < predictions[index] ? 1 : 0)
    ));
    const split = bestSquaredErrorSplit({ rows, featureNames, featureOrders, pseudoResiduals });
    const leftResiduals = [];
    const rightResiduals = [];
    for (let index = 0; index < rows.length; index += 1) {
      const residual = labels[index] - predictions[index];
      if (rows[index].features[split.featureName] <= split.threshold) leftResiduals.push(residual);
      else rightResiduals.push(residual);
    }
    if (!leftResiduals.length || !rightResiduals.length) throw new Error('GBM selected an empty leaf');
    const leftValue = objective === 'MEAN' ? mean(leftResiduals) : quantile(leftResiduals, lowerQuantile);
    const rightValue = objective === 'MEAN' ? mean(rightResiduals) : quantile(rightResiduals, lowerQuantile);
    const tree = freezeTree({ ...split, leftValue, rightValue });
    trees.push(tree);
    for (let index = 0; index < rows.length; index += 1) {
      const update = rows[index].features[tree.featureName] <= tree.threshold ? tree.leftValue : tree.rightValue;
      predictions[index] += learningRate * update;
    }
  }

  return Object.freeze({ objective, baseValue, learningRate, trees: Object.freeze(trees) });
}

function treePrediction(features, model) {
  let prediction = model.baseValue;
  for (const tree of model.trees) {
    const value = finite(features?.[tree.featureName], `feature ${tree.featureName}`);
    prediction += model.learningRate * (value <= tree.threshold ? tree.leftValue : tree.rightValue);
  }
  return prediction;
}

/**
 * Fits deterministic mean and lower-quantile GBM stumps using Development only.
 * The API deliberately accepts no Validation/OOS/Prospective observations.
 */
export function fitExitV5GbmModel(developmentSamples, {
  rounds = PHASE57_EXIT_V5_GBM_POLICY.defaultRounds,
  learningRate = PHASE57_EXIT_V5_GBM_POLICY.defaultLearningRate,
  maxThresholdCandidates = PHASE57_EXIT_V5_GBM_POLICY.defaultMaxThresholdCandidates,
  minLeafSize = PHASE57_EXIT_V5_GBM_POLICY.defaultMinLeafSize,
  lambda = 1,
  lowerQuantile = PHASE57_EXIT_V5_GBM_POLICY.lowerQuantile,
} = {}) {
  assertExitV5ResearchSafety();
  if (!Array.isArray(developmentSamples) || developmentSamples.length < 20) throw new Error('developmentSamples must contain at least 20 samples');
  if (!Number.isInteger(rounds) || rounds < 1 || rounds > 256) throw new Error('rounds must be an integer in [1, 256]');
  if (!(learningRate > 0 && learningRate <= 1)) throw new Error('learningRate must be in (0, 1]');
  if (!Number.isInteger(maxThresholdCandidates) || maxThresholdCandidates < 1 || maxThresholdCandidates > 128) throw new Error('maxThresholdCandidates must be an integer in [1, 128]');
  if (!Number.isInteger(minLeafSize) || minLeafSize < 2 || developmentSamples.length < 2 * minLeafSize) throw new Error('minLeafSize must leave at least two non-empty leaves');
  if (!(lowerQuantile > 0 && lowerQuantile < 0.5)) throw new Error('lowerQuantile must be between 0 and 0.5');
  assertChronological(developmentSamples, 'development');

  const featureNames = PHASE57_EXIT_V5_GBM_POLICY.featureNames;
  const rows = developmentSamples.map((sample, index) => Object.freeze({
    index,
    featureAt: sample.features.featureAt,
    features: Object.freeze(Object.fromEntries(featureNames.map((name) => [name, finite(sample.features[name], `development feature ${name}`)]))),
  }));
  const labels = developmentSamples.map(primaryLabel);
  const featureOrders = buildFeatureOrders(rows, featureNames, maxThresholdCandidates, minLeafSize);
  const meanModel = fitBoostedStumps({ rows, labels, featureNames, featureOrders, rounds, learningRate, objective: 'MEAN', lowerQuantile });
  const quantileModel = fitBoostedStumps({ rows, labels, featureNames, featureOrders, rounds, learningRate, objective: 'QUANTILE', lowerQuantile });
  const labelBounds = Object.freeze({ minimum: Math.min(...labels), maximum: Math.max(...labels) });
  const spec = freezeExitV5ModelSpec({ lambda, selectedOn: 'development', lowerQuantile });
  const serializable = Object.freeze({
    modelType: PHASE57_EXIT_V5_GBM_POLICY.modelType,
    featureNames,
    rounds,
    learningRate,
    maxThresholdCandidates,
    minLeafSize,
    lowerQuantile,
    labelBounds,
    meanModel,
    quantileModel,
    spec,
  });

  return Object.freeze({
    ...serializable,
    trainedOn: 'development',
    sampleCount: rows.length,
    developmentFirstFeatureAt: rows[0].featureAt,
    developmentLastFeatureAt: rows.at(-1).featureAt,
    developmentFingerprint: sha256(developmentSamples),
    modelFingerprint: sha256(serializable),
    refitAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
  });
}

export function predictExitV5Gbm(features, fittedModel, { incrementalCostPct = 0 } = {}) {
  if (!fittedModel || fittedModel.modelType !== PHASE57_EXIT_V5_GBM_POLICY.modelType || fittedModel.trainedOn !== 'development') {
    throw new Error('development-fitted EXIT v5 GBM model required');
  }
  const rawMean = treePrediction(features, fittedModel.meanModel);
  const rawQuantile = treePrediction(features, fittedModel.quantileModel);
  const meanIncrementalReturnPct = Math.min(fittedModel.labelBounds.maximum, Math.max(fittedModel.labelBounds.minimum, rawMean));
  const boundedQuantile = Math.min(fittedModel.labelBounds.maximum, Math.max(fittedModel.labelBounds.minimum, rawQuantile));
  const q10IncrementalReturnPct = Math.min(meanIncrementalReturnPct, boundedQuantile);
  const scored = scoreExitV5Continuation({
    meanIncrementalReturnPct,
    q10IncrementalReturnPct,
    incrementalCostPct,
  }, fittedModel.spec);
  return Object.freeze({
    ready: true,
    rawMeanIncrementalReturnPct: rawMean,
    rawQ10IncrementalReturnPct: rawQuantile,
    quantileCrossingCorrected: boundedQuantile > meanIncrementalReturnPct,
    ...scored,
  });
}

export function scoreExitV5GbmSplit(samples, fittedModel, { splitName, incrementalCostPct = 0 } = {}) {
  if (!PHASE57_EXIT_V5_GBM_POLICY.evaluationSplits.includes(splitName)) throw new Error('splitName must be validation, oos, or prospective');
  if (!Array.isArray(samples) || samples.length === 0) throw new Error('samples must be non-empty');
  assertChronological(samples, splitName);
  const rows = samples.map((sample) => Object.freeze({
    featureAt: sample.features.featureAt,
    realizedIncrementalReturnPct: primaryLabel(sample),
    ...predictExitV5Gbm(sample.features, fittedModel, { incrementalCostPct }),
  }));
  return Object.freeze({
    splitName,
    rows: Object.freeze(rows),
    metrics: evaluateExitV5Predictions(rows),
    developmentFingerprint: fittedModel.developmentFingerprint,
    modelFingerprint: fittedModel.modelFingerprint,
    refitPerformed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
  });
}

export function assertExitV5GbmPolicy() {
  if (PHASE57_EXIT_V5_GBM_POLICY.fitSplit !== 'development' || PHASE57_EXIT_V5_GBM_POLICY.shuffleAllowed !== false) throw new Error('GBM fit/shuffle policy drift');
  if (PHASE57_EXIT_V5_GBM_POLICY.validationRetuningAllowed !== false
    || PHASE57_EXIT_V5_GBM_POLICY.outerOosRetuningAllowed !== false
    || PHASE57_EXIT_V5_GBM_POLICY.prospectiveRetuningAllowed !== false) {
    throw new Error('GBM evaluation retuning must remain disabled');
  }
  if (PHASE57_EXIT_V5_GBM_POLICY.lowerQuantileObjective !== 'PINBALL') throw new Error('GBM lower quantile objective drift');
  return true;
}

export default {
  PHASE57_EXIT_V5_GBM_POLICY,
  assertExitV5GbmPolicy,
  fitExitV5GbmModel,
  predictExitV5Gbm,
  scoreExitV5GbmSplit,
};
