import { PHASE57_EXIT_V5_DATASET_POLICY, assertExitV5ResearchSafety } from './phase57-exit-v5-continuation-dataset.js';
import { freezeExitV5ModelSpec, scoreExitV5Continuation, evaluateExitV5Predictions } from './phase57-exit-v5-continuation-model.js';

export const PHASE57_EXIT_V5_TRAINING_POLICY = Object.freeze({
  primaryHorizonBars: 3,
  fitSplit: 'development',
  lambdaSelectionSplit: 'development',
  evaluationSplits: Object.freeze(['validation', 'oos', 'prospective']),
  shuffleAllowed: false,
  boundaryPurgingRequired: true,
  validationRetuningAllowed: false,
  outerOosRetuningAllowed: false,
  prospectiveRetuningAllowed: false,
});

function finite(value, name) {
  const n = Number(value);
  if (!Number.isFinite(n)) throw new Error(`${name} must be finite`);
  return n;
}

function primaryLabel(sample) {
  const value = sample?.labels?.incrementalLiquidationReturnPctByHorizon?.[PHASE57_EXIT_V5_TRAINING_POLICY.primaryHorizonBars];
  return finite(value, 'primary 3-bar label');
}

function assertChronological(samples, label) {
  for (let i = 1; i < samples.length; i += 1) {
    const prev = Date.parse(samples[i - 1]?.features?.featureAt);
    const next = Date.parse(samples[i]?.features?.featureAt);
    if (!Number.isFinite(prev) || !Number.isFinite(next) || next <= prev) {
      throw new Error(`${label} samples must be strictly chronological`);
    }
  }
}

function quantile(values, q) {
  if (!values.length) throw new Error('quantile requires non-empty values');
  const ordered = [...values].sort((a, b) => a - b);
  const index = (ordered.length - 1) * q;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) return ordered[lower];
  const weight = index - lower;
  return ordered[lower] * (1 - weight) + ordered[upper] * weight;
}

/**
 * Leakage-safe baseline fitter. Deliberately simple: development-only unconditional
 * mean and lower quantile. It exists as a sanity-control training harness before any
 * GBM is introduced. Validation/OOS/prospective outcomes never affect fitted values.
 */
export function fitExitV5DevelopmentBaseline(developmentSamples, { lambda = 1, lowerQuantile = 0.10 } = {}) {
  assertExitV5ResearchSafety();
  if (!Array.isArray(developmentSamples) || developmentSamples.length < 2) throw new Error('developmentSamples must contain at least 2 samples');
  assertChronological(developmentSamples, 'development');
  const labels = developmentSamples.map(primaryLabel);
  const mean = labels.reduce((sum, x) => sum + x, 0) / labels.length;
  const q = quantile(labels, lowerQuantile);
  const spec = freezeExitV5ModelSpec({ lambda, selectedOn: 'development', lowerQuantile });
  return Object.freeze({
    modelType: 'DEVELOPMENT_ONLY_UNCONDITIONAL_SANITY_BASELINE',
    trainedOn: 'development',
    sampleCount: labels.length,
    meanIncrementalReturnPct: mean,
    q10IncrementalReturnPct: q,
    spec,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
  });
}

export function scoreExitV5Split(samples, fittedModel, { splitName, incrementalCostPct = 0 } = {}) {
  if (!PHASE57_EXIT_V5_TRAINING_POLICY.evaluationSplits.includes(splitName)) {
    throw new Error('splitName must be validation, oos, or prospective');
  }
  if (!fittedModel || fittedModel.trainedOn !== 'development') throw new Error('development-fitted model required');
  if (!Array.isArray(samples) || samples.length === 0) throw new Error('samples must be non-empty');
  assertChronological(samples, splitName);

  const rows = samples.map((sample) => {
    const scored = scoreExitV5Continuation({
      meanIncrementalReturnPct: fittedModel.meanIncrementalReturnPct,
      q10IncrementalReturnPct: fittedModel.q10IncrementalReturnPct,
      incrementalCostPct,
    }, fittedModel.spec);
    return Object.freeze({
      featureAt: sample.features.featureAt,
      realizedIncrementalReturnPct: primaryLabel(sample),
      ...scored,
    });
  });

  return Object.freeze({
    splitName,
    rows: Object.freeze(rows),
    metrics: evaluateExitV5Predictions(rows),
    spec: fittedModel.spec,
    refitPerformed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
  });
}

/**
 * Accepts only already-purged split output. The harness intentionally has no API for
 * fitting validation/OOS/prospective, preventing silent outer-split retuning.
 */
export function runExitV5BaselineWalkForward(purgedSplit, options = {}) {
  if (!purgedSplit?.development || !purgedSplit?.validation || !purgedSplit?.oos) throw new Error('purged split is required');
  if (purgedSplit.development.length < 2) throw new Error('development split is too small');
  const model = fitExitV5DevelopmentBaseline(purgedSplit.development, options);
  const result = { model };
  for (const splitName of PHASE57_EXIT_V5_TRAINING_POLICY.evaluationSplits) {
    const samples = purgedSplit[splitName] ?? [];
    if (samples.length) result[splitName] = scoreExitV5Split(samples, model, { splitName, incrementalCostPct: options.incrementalCostPct ?? 0 });
  }
  return Object.freeze(result);
}

export function assertExitV5TrainingPolicy() {
  if (PHASE57_EXIT_V5_DATASET_POLICY.primaryHorizonBars !== PHASE57_EXIT_V5_TRAINING_POLICY.primaryHorizonBars) throw new Error('dataset/training horizon mismatch');
  if (PHASE57_EXIT_V5_TRAINING_POLICY.shuffleAllowed !== false) throw new Error('shuffle must remain disabled');
  if (PHASE57_EXIT_V5_TRAINING_POLICY.boundaryPurgingRequired !== true) throw new Error('boundary purging must remain required');
  if (PHASE57_EXIT_V5_TRAINING_POLICY.outerOosRetuningAllowed !== false || PHASE57_EXIT_V5_TRAINING_POLICY.prospectiveRetuningAllowed !== false) throw new Error('outer/prospective retuning must remain disabled');
  return true;
}
