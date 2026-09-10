import { assertExitV5ResearchSafety } from './phase57-exit-v5-continuation-dataset.js';
import { freezeExitV5ModelSpec, scoreExitV5Continuation, evaluateExitV5Predictions } from './phase57-exit-v5-continuation-model.js';

export const PHASE57_EXIT_V5_CONDITIONAL_POLICY = Object.freeze({
  modelType: 'DEVELOPMENT_ONLY_STANDARDIZED_KNN_CONTINUATION',
  primaryHorizonBars: 3,
  defaultK: 40,
  defaultMinNeighbors: 20,
  lowerQuantile: 0.10,
  fitSplit: 'development',
  evaluationSplits: Object.freeze(['validation', 'oos', 'prospective']),
  shuffleAllowed: false,
  validationRetuningAllowed: false,
  outerOosRetuningAllowed: false,
  prospectiveRetuningAllowed: false,
  featureNames: Object.freeze([
    'currentReturnAtr',
    'runningMfeAtr',
    'runningMaeAtr',
    'givebackAtr',
    'captureRatio',
    'mfeVelocityPctPerBar',
    'barsSinceLastMfe',
    'barsSinceLastMae',
    'vwapDistancePct',
    'vwapSlopePctPerBar',
    'rvol',
    'currentMomentumPct',
    'momentumDecelerationPct',
    'elapsedBars',
    'directionSign',
  ]),
});

function finite(value, name) {
  const n = Number(value);
  if (!Number.isFinite(n)) throw new Error(`${name} must be finite`);
  return n;
}

function primaryLabel(sample) {
  return finite(sample?.labels?.incrementalLiquidationReturnPctByHorizon?.[PHASE57_EXIT_V5_CONDITIONAL_POLICY.primaryHorizonBars], 'primary 3-bar label');
}

function assertChronological(samples, label) {
  for (let i = 1; i < samples.length; i += 1) {
    const prev = Date.parse(samples[i - 1]?.features?.featureAt);
    const next = Date.parse(samples[i]?.features?.featureAt);
    if (!Number.isFinite(prev) || !Number.isFinite(next) || next < prev) {
      throw new Error(`${label} samples must be chronological`);
    }
  }
}

function quantile(values, q) {
  const ordered = [...values].sort((a, b) => a - b);
  const index = (ordered.length - 1) * q;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) return ordered[lower];
  const weight = index - lower;
  return ordered[lower] * (1 - weight) + ordered[upper] * weight;
}

function buildScaler(samples, featureNames) {
  const stats = {};
  for (const name of featureNames) {
    const values = samples.map((sample) => finite(sample?.features?.[name], `feature ${name}`));
    const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
    const variance = values.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / values.length;
    const scale = Math.sqrt(variance);
    stats[name] = Object.freeze({ mean, scale: scale > 1e-12 ? scale : 1 });
  }
  return Object.freeze(stats);
}

function vectorize(features, featureNames, scaler) {
  return featureNames.map((name) => {
    const value = finite(features?.[name], `feature ${name}`);
    return (value - scaler[name].mean) / scaler[name].scale;
  });
}

function squaredDistance(a, b) {
  let total = 0;
  for (let i = 0; i < a.length; i += 1) total += (a[i] - b[i]) ** 2;
  return total;
}

/**
 * Fits only development observations. The scaler and training vectors are frozen
 * from development and no evaluation labels are accepted by this API.
 */
export function fitExitV5ConditionalModel(developmentSamples, {
  k = PHASE57_EXIT_V5_CONDITIONAL_POLICY.defaultK,
  minNeighbors = PHASE57_EXIT_V5_CONDITIONAL_POLICY.defaultMinNeighbors,
  lambda = 1,
  lowerQuantile = PHASE57_EXIT_V5_CONDITIONAL_POLICY.lowerQuantile,
} = {}) {
  assertExitV5ResearchSafety();
  if (!Array.isArray(developmentSamples) || developmentSamples.length < 2) throw new Error('developmentSamples must contain at least 2 samples');
  assertChronological(developmentSamples, 'development');
  if (!Number.isInteger(k) || k < 1) throw new Error('k must be a positive integer');
  if (!Number.isInteger(minNeighbors) || minNeighbors < 1 || minNeighbors > k) throw new Error('minNeighbors must be an integer in [1, k]');
  if (!(lowerQuantile > 0 && lowerQuantile < 0.5)) throw new Error('lowerQuantile must be between 0 and 0.5');

  const featureNames = PHASE57_EXIT_V5_CONDITIONAL_POLICY.featureNames;
  const scaler = buildScaler(developmentSamples, featureNames);
  const rows = developmentSamples.map((sample, index) => Object.freeze({
    index,
    featureAt: sample.features.featureAt,
    vector: Object.freeze(vectorize(sample.features, featureNames, scaler)),
    labelPct: primaryLabel(sample),
  }));

  return Object.freeze({
    modelType: PHASE57_EXIT_V5_CONDITIONAL_POLICY.modelType,
    trainedOn: 'development',
    sampleCount: rows.length,
    featureNames,
    scaler,
    rows: Object.freeze(rows),
    k,
    minNeighbors,
    spec: freezeExitV5ModelSpec({ lambda, selectedOn: 'development', lowerQuantile }),
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
  });
}

export function predictExitV5Conditional(features, fittedModel, { incrementalCostPct = 0 } = {}) {
  if (!fittedModel || fittedModel.modelType !== PHASE57_EXIT_V5_CONDITIONAL_POLICY.modelType || fittedModel.trainedOn !== 'development') {
    throw new Error('development-fitted EXIT v5 conditional model required');
  }
  const target = vectorize(features, fittedModel.featureNames, fittedModel.scaler);
  const neighbors = fittedModel.rows
    .map((row) => ({ row, distance2: squaredDistance(target, row.vector) }))
    .sort((a, b) => a.distance2 - b.distance2 || a.row.index - b.row.index)
    .slice(0, Math.min(fittedModel.k, fittedModel.rows.length));

  if (neighbors.length < fittedModel.minNeighbors) {
    return Object.freeze({ ready: false, decision: 'HOLD', reason: 'V5_INSUFFICIENT_DEVELOPMENT_NEIGHBORS', neighborCount: neighbors.length });
  }

  const labels = neighbors.map((neighbor) => neighbor.row.labelPct);
  const mean = labels.reduce((sum, value) => sum + value, 0) / labels.length;
  const q = quantile(labels, fittedModel.spec.lowerQuantile);
  const scored = scoreExitV5Continuation({
    meanIncrementalReturnPct: mean,
    q10IncrementalReturnPct: q,
    incrementalCostPct,
  }, fittedModel.spec);

  return Object.freeze({
    ready: true,
    neighborCount: neighbors.length,
    nearestDistance: Math.sqrt(neighbors[0].distance2),
    furthestDistance: Math.sqrt(neighbors.at(-1).distance2),
    ...scored,
  });
}

export function scoreExitV5ConditionalSplit(samples, fittedModel, { splitName, incrementalCostPct = 0 } = {}) {
  if (!PHASE57_EXIT_V5_CONDITIONAL_POLICY.evaluationSplits.includes(splitName)) throw new Error('splitName must be validation, oos, or prospective');
  if (!Array.isArray(samples) || samples.length === 0) throw new Error('samples must be non-empty');
  assertChronological(samples, splitName);

  const rows = samples.map((sample) => {
    const prediction = predictExitV5Conditional(sample.features, fittedModel, { incrementalCostPct });
    return Object.freeze({
      featureAt: sample.features.featureAt,
      realizedIncrementalReturnPct: primaryLabel(sample),
      ...prediction,
    });
  });
  const readyRows = rows.filter((row) => row.ready);

  return Object.freeze({
    splitName,
    rows: Object.freeze(rows),
    readyCount: readyRows.length,
    abstainCount: rows.length - readyRows.length,
    metrics: readyRows.length ? evaluateExitV5Predictions(readyRows) : null,
    refitPerformed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
  });
}

export function assertExitV5ConditionalPolicy() {
  if (PHASE57_EXIT_V5_CONDITIONAL_POLICY.fitSplit !== 'development') throw new Error('conditional fit must remain development-only');
  if (PHASE57_EXIT_V5_CONDITIONAL_POLICY.shuffleAllowed !== false) throw new Error('shuffle must remain disabled');
  if (PHASE57_EXIT_V5_CONDITIONAL_POLICY.outerOosRetuningAllowed !== false || PHASE57_EXIT_V5_CONDITIONAL_POLICY.prospectiveRetuningAllowed !== false) {
    throw new Error('outer/prospective retuning must remain disabled');
  }
  return true;
}
