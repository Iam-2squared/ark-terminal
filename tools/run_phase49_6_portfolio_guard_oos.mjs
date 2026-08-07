#!/usr/bin/env node
import fs from 'node:fs';
import { buildPortfolioOosMetrics } from '../predict/models/phase47-walk-forward.js';
import { evaluateModel, normalizeTrainingRows, trainModel } from '../predict/models/phase47-real-training.js';

const robustnessDir = process.argv[2] || 'data/phase49-robustness';
const guardPath = process.argv[3] || 'data/phase49-guard-robustness/summary.json';
const outDir = process.argv[4] || 'data/phase49-portfolio-guard-oos';
fs.mkdirSync(outDir, { recursive: true });

const guard = JSON.parse(fs.readFileSync(guardPath, 'utf8'));
const policiesByGroup = new Map((guard.groups || []).map((g) => [g.name, g]));

function selectedResult(model) {
  const wf = model.walkForward || {};
  const selectedModelType = wf.selectedModelType;
  const ranked = wf.ranked || [];
  const selected = ranked.find((x) => x.modelType === selectedModelType) || ranked[0];
  if (!selected) throw new Error('PHASE49_6_SELECTED_MODEL_MISSING');
  return { selectedModelType: selected.modelType, selected, aggregate: selected.aggregate };
}

function reconstructOosPredictions(groupName, model) {
  const datasetPath = `${robustnessDir}/${groupName}.json`;
  if (!fs.existsSync(datasetPath)) throw new Error(`PHASE49_6_DATASET_MISSING:${groupName}`);
  const dataset = JSON.parse(fs.readFileSync(datasetPath, 'utf8'));
  const rawRows = Array.isArray(dataset) ? dataset : (dataset.rows || dataset.dataset?.rows || []);
  const rows = normalizeTrainingRows(rawRows);
  const { selectedModelType, selected } = selectedResult(model);
  const folds = selected.folds || [];
  if (!folds.length) throw new Error(`PHASE49_6_FOLDS_MISSING:${groupName}`);

  const predictions = [];
  for (const fold of folds) {
    const trainRows = rows.filter((r) => String(r.sessionDate) >= String(fold.trainStart) && String(r.sessionDate) <= String(fold.trainEnd));
    const testRows = rows.filter((r) => String(r.sessionDate) >= String(fold.testStart) && String(r.sessionDate) <= String(fold.testEnd));
    if (trainRows.length < 20 || !testRows.length) throw new Error(`PHASE49_6_FOLD_ROWS_MISSING:${groupName}:${fold.fold}`);
    const trained = trainModel({ rows: trainRows, modelType: selectedModelType });
    const metrics = evaluateModel({ model: trained, rows: testRows, costRate: 0.001 });
    if (!Array.isArray(metrics.probabilities) || metrics.probabilities.length !== testRows.length) {
      throw new Error(`PHASE49_6_PROBABILITY_MISMATCH:${groupName}:${fold.fold}`);
    }
    for (let i = 0; i < testRows.length; i += 1) {
      const row = testRows[i];
      predictions.push(Object.freeze({
        id: row.id,
        symbol: row.symbol,
        sessionDate: row.sessionDate,
        probability: metrics.probabilities[i],
        label: row.label,
        actualReturn: row.actualReturn,
        outerFold: fold.fold,
        selectedThreshold: fold.selectedThreshold,
      }));
    }
  }
  return predictions;
}

function intervalDecision(groupPolicy, sessionDate, policyName = 'balanced') {
  const policy = groupPolicy?.policies?.find((p) => (p.name ?? p.policy?.name) === policyName)
    || groupPolicy?.policyResults?.find((p) => (p.name ?? p.policy?.name) === policyName)
    || groupPolicy?.[policyName]
    || null;
  const decisions = policy?.decisions || groupPolicy?.decisions || [];
  const d = decisions.find((x) => String(sessionDate) >= String(x.testStart) && String(sessionDate) <= String(x.testEnd));
  if (!d) return { matched: false, guardedAllowed: true, robustnessActive: false, reason: 'NO_GUARD_DECISION' };
  const allowed = d.guardedAllowed ?? d.allowed ?? true;
  return {
    matched: true,
    guardedAllowed: Boolean(allowed),
    robustnessActive: Boolean(d.robustnessActive ?? d.metaActive),
    reason: d.robustnessReason || d.metaReason || d.reason || null,
  };
}

function metricView(metrics) {
  return {
    netReturn: metrics.netReturn,
    profitFactor: metrics.profitFactor,
    sharpe: metrics.sharpe,
    maxDrawdown: metrics.maxDrawdown,
    cagr: metrics.cagr,
    exposure: metrics.exposure,
    positionChanges: metrics.positionChanges,
    sampleCount: metrics.sampleCount,
    portfolioDays: metrics.portfolioDays,
  };
}

const groups = [];
for (const file of fs.readdirSync(robustnessDir).filter((f) => f.endsWith('-model.json')).sort()) {
  const name = file.replace(/-model\.json$/, '');
  const model = JSON.parse(fs.readFileSync(`${robustnessDir}/${file}`, 'utf8'));
  const { selectedModelType, aggregate } = selectedResult(model);
  const predictions = reconstructOosPredictions(name, model);
  const groupPolicy = policiesByGroup.get(name);
  if (!groupPolicy) throw new Error(`PHASE49_6_GUARD_GROUP_MISSING:${name}`);

  let matchedGuardDecisionCount = 0;
  let blockedPredictionCount = 0;
  const balancedPredictions = predictions.map((p) => {
    const decision = intervalDecision(groupPolicy, p.sessionDate, 'balanced');
    if (decision.matched) matchedGuardDecisionCount += 1;
    if (!decision.guardedAllowed) blockedPredictionCount += 1;
    return decision.guardedAllowed ? p : { ...p, probability: -Infinity };
  });
  if (!matchedGuardDecisionCount) throw new Error(`PHASE49_6_BALANCED_GUARD_DECISIONS_NOT_MATCHED:${name}`);

  const baseline = buildPortfolioOosMetrics(predictions, { entryThreshold: null, costRate: 0.001 });
  const balancedGuard = buildPortfolioOosMetrics(balancedPredictions, { entryThreshold: null, costRate: 0.001 });
  const source = aggregate?.oos || {};
  const reproductionTolerance = 1e-10;
  const reproduction = {
    netReturnDelta: baseline.netReturn - Number(source.netReturn ?? baseline.netReturn),
    profitFactorDelta: baseline.profitFactor - Number(source.profitFactor ?? baseline.profitFactor),
    sharpeDelta: baseline.sharpe - Number(source.sharpe ?? baseline.sharpe),
    maxDrawdownDelta: baseline.maxDrawdown - Number(source.maxDrawdown ?? baseline.maxDrawdown),
  };
  reproduction.matchesCanonicalSource = Object.values(reproduction).every((v) => typeof v !== 'number' || Math.abs(v) <= reproductionTolerance);
  if (!reproduction.matchesCanonicalSource) {
    throw new Error(`PHASE49_6_CANONICAL_REPRODUCTION_MISMATCH:${name}:${JSON.stringify(reproduction)}`);
  }

  groups.push({
    name,
    selectedModelType,
    sourceAggregate: metricView(source),
    reconstructedPredictionCount: predictions.length,
    matchedGuardDecisionCount,
    blockedPredictionCount,
    blockedPredictionRate: predictions.length ? blockedPredictionCount / predictions.length : 0,
    canonicalReproduction: reproduction,
    baseline: metricView(baseline),
    balancedGuard: metricView(balancedGuard),
    deltas: {
      netReturn: balancedGuard.netReturn - baseline.netReturn,
      profitFactor: balancedGuard.profitFactor - baseline.profitFactor,
      sharpe: balancedGuard.sharpe - baseline.sharpe,
      maxDrawdown: balancedGuard.maxDrawdown - baseline.maxDrawdown,
      cagr: balancedGuard.cagr - baseline.cagr,
      exposure: balancedGuard.exposure - baseline.exposure,
    },
    safety: {
      brokerWrites: 0,
      excelOrderWrites: 0,
      rssOrderCalls: 0,
      liveOrders: 0,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
    },
  });
}

const output = {
  phase: 49.6,
  purpose: 'Apples-to-apples portfolio-level OOS comparison using the canonical Phase47 portfolio evaluator. OOS predictions are reconstructed from each already-selected model and its serialized outer-fold train/test boundaries and nested thresholds; no current/future fold is used to train its own prediction.',
  policy: 'balanced',
  limitations: [
    'Guard decisions remain fold-level diagnostics derived only from prior folds.',
    'No live trading or promotion actions are permitted.',
    'Canonical reproduction is fail-closed: evaluation stops if reconstructed baseline metrics differ from the source aggregate.',
    'Balanced guard integration is fail-closed: evaluation stops if no serialized guard interval matches reconstructed OOS predictions.'
  ],
  groups,
  safety: {
    brokerWrites: 0,
    excelOrderWrites: 0,
    rssOrderCalls: 0,
    liveOrders: 0,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
  },
};
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));
