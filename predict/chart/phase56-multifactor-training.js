import { trainModel } from '../models/phase47-real-training.js';

export const PHASE56_MULTIFACTOR_TRAINING_SAFETY = Object.freeze({
  mode: 'MULTIFACTOR_TRAINING_RESEARCH_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const finite = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const day = (value) => String(value ?? '').slice(0, 10);
const validDay = (value) => /^\d{4}-\d{2}-\d{2}$/.test(day(value));

function compareDay(a, b) {
  return day(a).localeCompare(day(b));
}

function normalizeInteractionDefs(interactions = []) {
  const seen = new Set();
  return Object.freeze((Array.isArray(interactions) ? interactions : []).map((item, index) => {
    const features = [...new Set(Array.isArray(item?.features) ? item.features.map(String) : [])];
    if (features.length < 2) throw new TypeError(`interaction ${index} requires at least two features`);
    const id = String(item?.id ?? features.join('*'));
    if (seen.has(id)) throw new TypeError(`duplicate interaction id: ${id}`);
    seen.add(id);
    return Object.freeze({ id, features: Object.freeze(features) });
  }));
}

function collectBaseFeatures(rows, requested = null) {
  if (Array.isArray(requested) && requested.length) return Object.freeze([...new Set(requested.map(String))].sort());
  return Object.freeze([...new Set(rows.flatMap((row) => Object.entries(row?.featureVector ?? {})
    .filter(([, value]) => finite(value))
    .map(([key]) => key)))].sort());
}

function materialize(featureVector, baseFeatures, interactions) {
  const features = {};
  for (const key of baseFeatures) features[`base::${key}`] = finite(featureVector?.[key]) ? Number(featureVector[key]) : 0;
  for (const interaction of interactions) {
    let product = 1;
    let available = true;
    for (const key of interaction.features) {
      if (!finite(featureVector?.[key])) { available = false; break; }
      product *= Number(featureVector[key]);
    }
    features[`ix::${interaction.id}`] = available ? product : 0;
  }
  return features;
}

function eligibleRow(row, trainingAsOf) {
  const sessionDate = day(row?.sessionDate);
  const featureCutoff = day(row?.featureCutoff ?? row?.sessionDate);
  const outcomeAt = day(row?.outcomeAt);
  if (![sessionDate, featureCutoff, outcomeAt, trainingAsOf].every(validDay)) return { ok: false, reason: 'INVALID_POINT_IN_TIME_METADATA' };
  if (compareDay(featureCutoff, sessionDate) > 0) return { ok: false, reason: 'FEATURE_FUTURE_LEAK_BLOCKED' };
  if (compareDay(outcomeAt, sessionDate) <= 0) return { ok: false, reason: 'OUTCOME_NOT_FORWARD' };
  if (compareDay(outcomeAt, trainingAsOf) > 0) return { ok: false, reason: 'OUTCOME_NOT_KNOWN_AT_TRAINING_CUTOFF' };
  if (compareDay(sessionDate, trainingAsOf) > 0) return { ok: false, reason: 'SESSION_AFTER_TRAINING_CUTOFF' };
  if (!finite(row?.actualReturn)) return { ok: false, reason: 'INVALID_ACTUAL_RETURN' };
  return { ok: true };
}

export function preparePhase56TrainingRows({ rows = [], trainingAsOf, baseFeatures = null, interactions = [] } = {}) {
  if (!validDay(trainingAsOf)) throw new TypeError('trainingAsOf must be YYYY-MM-DD');
  const interactionDefs = normalizeInteractionDefs(interactions);
  const featureNames = collectBaseFeatures(rows, baseFeatures);
  const accepted = [];
  const rejected = [];

  for (const [index, row] of rows.entries()) {
    const eligibility = eligibleRow(row, day(trainingAsOf));
    if (!eligibility.ok) {
      rejected.push(Object.freeze({ index, id: row?.id ?? null, reason: eligibility.reason }));
      continue;
    }
    const actualReturn = Number(row.actualReturn);
    accepted.push(Object.freeze({
      id: String(row.id ?? `${row.symbol ?? 'UNKNOWN'}:${day(row.sessionDate)}:${index}`),
      symbol: String(row.symbol ?? 'UNKNOWN'),
      sessionDate: day(row.sessionDate),
      label: actualReturn > 0 ? 1 : 0,
      actualReturn,
      features: Object.freeze(materialize(row.featureVector ?? {}, featureNames, interactionDefs)),
    }));
  }

  return Object.freeze({
    phase: '56.p11',
    status: accepted.length >= 20 ? 'TRAINING_ROWS_READY' : 'INSUFFICIENT_TRAINING_ROWS',
    trainingAsOf: day(trainingAsOf),
    baseFeatures: featureNames,
    interactions: interactionDefs,
    accepted: Object.freeze(accepted),
    rejected: Object.freeze(rejected),
    pointInTimeEnforced: true,
    futureOutcomeBlocked: true,
  });
}

function sourceFeaturesForTerm(name, interactions) {
  if (name.startsWith('base::')) return [name.slice('base::'.length)];
  if (name.startsWith('ix::')) {
    const id = name.slice('ix::'.length);
    const found = interactions.find((item) => item.id === id);
    return found ? [...found.features] : [];
  }
  return [];
}

export function trainPhase56MultifactorArtifact({ rows = [], trainingAsOf, baseFeatures = null, interactions = [], options = {} } = {}) {
  const prepared = preparePhase56TrainingRows({ rows, trainingAsOf, baseFeatures, interactions });
  if (prepared.accepted.length < 20) {
    return Object.freeze({
      phase: '56.p11', status: 'INSUFFICIENT_TRAINING_ROWS', model: null,
      trainingAsOf: prepared.trainingAsOf, acceptedRows: prepared.accepted.length,
      rejectedRows: prepared.rejected.length, pointInTimeEnforced: true,
      oosValidated: false, probabilityIsCalibrated: false, edgeClaimAllowed: false,
      recommendationAllowed: false, paperTradingAllowed: false, executionAllowed: false,
      brokerWriteAllowed: false, excelOrderWriteAllowed: false, rssOrderFunctionAllowed: false,
      liveTradingAllowed: false, automaticPromotionAllowed: false, productionUpdateAllowed: false,
      transmitted: false, humanApprovalRequired: true, safety: PHASE56_MULTIFACTOR_TRAINING_SAFETY,
    });
  }

  const trained = trainModel({ rows: prepared.accepted, modelType: 'LOGISTIC_REGRESSION', options });
  let intercept = Number(trained.bias ?? 0);
  const terms = [];
  trained.names.forEach((name, index) => {
    const stats = trained.scaler?.[name] ?? { mean: 0, scale: 1 };
    const scale = Number(stats.scale) || 1;
    const weight = Number(trained.weights?.[index] ?? 0);
    const rawWeight = weight / scale;
    intercept -= rawWeight * Number(stats.mean ?? 0);
    const features = sourceFeaturesForTerm(name, prepared.interactions);
    if (features.length) terms.push(Object.freeze({ features: Object.freeze(features), weight: rawWeight }));
  });

  const model = Object.freeze({
    version: `phase56-p11-${trained.modelId}`,
    type: 'INTERACTION_AWARE_LOGISTIC',
    intercept,
    terms: Object.freeze(terms),
    trainingAsOf: prepared.trainingAsOf,
    trainingRows: prepared.accepted.length,
    sourceModelId: trained.modelId,
  });

  return Object.freeze({
    phase: '56.p11', status: 'MULTIFACTOR_ARTIFACT_TRAINED', model,
    trainingAsOf: prepared.trainingAsOf, acceptedRows: prepared.accepted.length,
    rejectedRows: prepared.rejected.length, rejected: prepared.rejected,
    pointInTimeEnforced: true, futureOutcomeBlocked: true,
    oosValidated: false, probabilityIsCalibrated: false, edgeClaimAllowed: false,
    recommendationAllowed: false, paperTradingAllowed: false, executionAllowed: false,
    brokerWriteAllowed: false, excelOrderWriteAllowed: false, rssOrderFunctionAllowed: false,
    liveTradingAllowed: false, automaticPromotionAllowed: false, productionUpdateAllowed: false,
    transmitted: false, humanApprovalRequired: true, safety: PHASE56_MULTIFACTOR_TRAINING_SAFETY,
  });
}

export default trainPhase56MultifactorArtifact;
