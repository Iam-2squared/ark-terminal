#!/usr/bin/env node
import fs from 'node:fs';
import { buildPortfolioOosMetrics } from '../predict/models/phase47-walk-forward.js';
import { evaluateModel, normalizeTrainingRows, trainModel } from '../predict/models/phase47-real-training.js';

const robustnessDir = process.argv[2] || 'data/phase49-robustness';
const guardPath = process.argv[3] || 'data/phase49-guard-robustness/summary.json';
const outDir = process.argv[4] || 'data/phase49-policy-portfolio-oos';
const POLICY_NAMES = ['strict', 'balanced', 'permissive'];
fs.mkdirSync(outDir, { recursive: true });

const guard = JSON.parse(fs.readFileSync(guardPath, 'utf8'));
const policiesByGroup = new Map((guard.groups || []).map((g) => [g.name, g]));

function selectedResult(model) {
  const wf = model.walkForward || {};
  const selectedModelType = wf.selectedModelType;
  const ranked = wf.ranked || [];
  const selected = ranked.find((x) => x.modelType === selectedModelType) || ranked[0];
  if (!selected) throw new Error('PHASE49_7_SELECTED_MODEL_MISSING');
  return { selectedModelType: selected.modelType, selected, aggregate: selected.aggregate };
}

function reconstructOosPredictions(groupName, model) {
  const datasetPath = `${robustnessDir}/${groupName}.json`;
  if (!fs.existsSync(datasetPath)) throw new Error(`PHASE49_7_DATASET_MISSING:${groupName}`);
  const dataset = JSON.parse(fs.readFileSync(datasetPath, 'utf8'));
  const rawRows = Array.isArray(dataset) ? dataset : (dataset.rows || dataset.dataset?.rows || []);
  const rows = normalizeTrainingRows(rawRows);
  const { selectedModelType, selected } = selectedResult(model);
  const folds = selected.folds || [];
  if (!folds.length) throw new Error(`PHASE49_7_FOLDS_MISSING:${groupName}`);

  const predictions = [];
  for (const fold of folds) {
    const trainRows = rows.filter((r) => String(r.sessionDate) >= String(fold.trainStart) && String(r.sessionDate) <= String(fold.trainEnd));
    const testRows = rows.filter((r) => String(r.sessionDate) >= String(fold.testStart) && String(r.sessionDate) <= String(fold.testEnd));
    if (trainRows.length < 20 || !testRows.length) throw new Error(`PHASE49_7_FOLD_ROWS_MISSING:${groupName}:${fold.fold}`);
    const trained = trainModel({ rows: trainRows, modelType: selectedModelType });
    const metrics = evaluateModel({ model: trained, rows: testRows, costRate: 0.001 });
    if (!Array.isArray(metrics.probabilities) || metrics.probabilities.length !== testRows.length) {
      throw new Error(`PHASE49_7_PROBABILITY_MISMATCH:${groupName}:${fold.fold}`);
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

function findPolicy(groupPolicy, policyName) {
  const policy = groupPolicy?.policies?.find((p) => (p?.policy?.name ?? p?.name) === policyName) || null;
  if (!policy) throw new Error(`PHASE49_7_POLICY_MISSING:${groupPolicy?.name ?? 'unknown'}:${policyName}`);
  return policy;
}

function intervalDecision(policy, sessionDate) {
  const decisions = policy?.decisions || [];
  const d = decisions.find((x) => String(sessionDate) >= String(x.testStart) && String(sessionDate) <= String(x.testEnd));
  if (!d) return { matched: false, guardedAllowed: true, reason: 'NO_GUARD_DECISION' };
  const allowed = d.guardedAllowed ?? d.allowed ?? true;
  return { matched: true, guardedAllowed: Boolean(allowed), reason: d.metaReason || d.reason || null };
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

function deltas(a, b) {
  return {
    netReturn: b.netReturn - a.netReturn,
    profitFactor: b.profitFactor - a.profitFactor,
    sharpe: b.sharpe - a.sharpe,
    maxDrawdown: b.maxDrawdown - a.maxDrawdown,
    cagr: b.cagr - a.cagr,
    exposure: b.exposure - a.exposure,
  };
}

function diagnosticScore(metrics, baseline) {
  const d = deltas(baseline, metrics);
  return d.netReturn * 1.0 + d.sharpe * 0.25 + d.profitFactor * 0.20 - d.maxDrawdown * 0.50;
}

const groups = [];
let totalMatchedPredictions = 0;
for (const file of fs.readdirSync(robustnessDir).filter((f) => f.endsWith('-model.json')).sort()) {
  const name = file.replace(/-model\.json$/, '');
  const model = JSON.parse(fs.readFileSync(`${robustnessDir}/${file}`, 'utf8'));
  const { selectedModelType, aggregate } = selectedResult(model);
  const predictions = reconstructOosPredictions(name, model);
  const baseline = buildPortfolioOosMetrics(predictions, { entryThreshold: null, costRate: 0.001 });
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
    throw new Error(`PHASE49_7_CANONICAL_REPRODUCTION_MISMATCH:${name}:${JSON.stringify(reproduction)}`);
  }

  const groupPolicy = policiesByGroup.get(name);
  if (!groupPolicy) throw new Error(`PHASE49_7_GROUP_POLICY_MISSING:${name}`);
  const policies = [];
  for (const policyName of POLICY_NAMES) {
    const policy = findPolicy(groupPolicy, policyName);
    let matchedPredictions = 0;
    let blockedPredictions = 0;
    const guardedPredictions = predictions.map((p) => {
      const decision = intervalDecision(policy, p.sessionDate);
      if (decision.matched) matchedPredictions += 1;
      if (decision.matched && !decision.guardedAllowed) blockedPredictions += 1;
      return decision.guardedAllowed ? p : { ...p, probability: -Infinity };
    });
    if (!matchedPredictions) throw new Error(`PHASE49_7_NO_POLICY_INTERVAL_MATCH:${name}:${policyName}`);
    totalMatchedPredictions += matchedPredictions;
    const guarded = buildPortfolioOosMetrics(guardedPredictions, { entryThreshold: null, costRate: 0.001 });
    policies.push({
      name: policyName,
      matchedPredictions,
      blockedPredictions,
      blockedPredictionRate: predictions.length ? blockedPredictions / predictions.length : 0,
      metrics: metricView(guarded),
      deltas: deltas(baseline, guarded),
      diagnosticScore: diagnosticScore(guarded, baseline),
      retrospectiveDiagnosticOnly: true,
      deploymentEligible: false,
    });
  }
  const diagnosticBest = [...policies].sort((a, b) => b.diagnosticScore - a.diagnosticScore || a.name.localeCompare(b.name))[0];
  groups.push({
    name,
    selectedModelType,
    reconstructedPredictionCount: predictions.length,
    canonicalReproduction: reproduction,
    baseline: metricView(baseline),
    policies,
    diagnosticBestPolicy: diagnosticBest.name,
    diagnosticBestPolicyScore: diagnosticBest.diagnosticScore,
    policySelectionMode: 'RETROSPECTIVE_DIAGNOSTIC_ONLY_NOT_FOR_DEPLOYMENT',
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
  });
}

if (!totalMatchedPredictions) throw new Error('PHASE49_7_NO_POLICY_MATCHES_GLOBAL');

const output = {
  phase: 49.7,
  purpose: 'Canonical apples-to-apples OOS sweep of strict/balanced/permissive causal guard policies. Policy ranking is retrospective diagnostics only and must not be used as a deployment choice.',
  groups,
  safety: {
    brokerWrites: 0,
    excelOrderWrites: 0,
    rssOrderCalls: 0,
    liveOrders: 0,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  },
};
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));
