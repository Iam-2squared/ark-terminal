#!/usr/bin/env node
import fs from 'node:fs';
import { buildPortfolioOosMetrics } from '../predict/models/phase47-walk-forward.js';
import { evaluateModel, normalizeTrainingRows, trainModel } from '../predict/models/phase47-real-training.js';

const robustnessDir = process.argv[2] || 'data/phase49-robustness';
const guardPath = process.argv[3] || 'data/phase49-guard-robustness/summary.json';
const outDir = process.argv[4] || 'data/phase49-nested-policy-selection';
const POLICY_NAMES = ['baseline', 'strict', 'balanced', 'permissive'];
const MIN_HISTORY_FOLDS = 4;
const MIN_SCORE_ADVANTAGE = 0.01;
fs.mkdirSync(outDir, { recursive: true });

const guard = JSON.parse(fs.readFileSync(guardPath, 'utf8'));
const policiesByGroup = new Map((guard.groups || []).map((g) => [g.name, g]));

function selectedResult(model) {
  const wf = model.walkForward || {};
  const selectedModelType = wf.selectedModelType;
  const ranked = wf.ranked || [];
  const selected = ranked.find((x) => x.modelType === selectedModelType) || ranked[0];
  if (!selected) throw new Error('PHASE49_8_SELECTED_MODEL_MISSING');
  return { selectedModelType: selected.modelType, selected, aggregate: selected.aggregate };
}

function reconstructOosPredictions(groupName, model) {
  const datasetPath = `${robustnessDir}/${groupName}.json`;
  if (!fs.existsSync(datasetPath)) throw new Error(`PHASE49_8_DATASET_MISSING:${groupName}`);
  const dataset = JSON.parse(fs.readFileSync(datasetPath, 'utf8'));
  const rawRows = Array.isArray(dataset) ? dataset : (dataset.rows || dataset.dataset?.rows || []);
  const rows = normalizeTrainingRows(rawRows);
  const { selectedModelType, selected } = selectedResult(model);
  const folds = selected.folds || [];
  if (!folds.length) throw new Error(`PHASE49_8_FOLDS_MISSING:${groupName}`);

  const predictions = [];
  for (const fold of folds) {
    const trainRows = rows.filter((r) => String(r.sessionDate) >= String(fold.trainStart) && String(r.sessionDate) <= String(fold.trainEnd));
    const testRows = rows.filter((r) => String(r.sessionDate) >= String(fold.testStart) && String(r.sessionDate) <= String(fold.testEnd));
    if (trainRows.length < 20 || !testRows.length) throw new Error(`PHASE49_8_FOLD_ROWS_MISSING:${groupName}:${fold.fold}`);
    const trained = trainModel({ rows: trainRows, modelType: selectedModelType });
    const metrics = evaluateModel({ model: trained, rows: testRows, costRate: 0.001 });
    if (!Array.isArray(metrics.probabilities) || metrics.probabilities.length !== testRows.length) {
      throw new Error(`PHASE49_8_PROBABILITY_MISMATCH:${groupName}:${fold.fold}`);
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
  return { predictions, folds };
}

function findPolicy(groupPolicy, policyName) {
  if (policyName === 'baseline') return null;
  const policy = groupPolicy?.policies?.find((p) => (p?.policy?.name ?? p?.name) === policyName) || null;
  if (!policy) throw new Error(`PHASE49_8_POLICY_MISSING:${groupPolicy?.name ?? 'unknown'}:${policyName}`);
  return policy;
}

function intervalDecision(policy, sessionDate) {
  if (!policy) return { matched: true, guardedAllowed: true, reason: 'BASELINE' };
  const decisions = policy?.decisions || [];
  const d = decisions.find((x) => String(sessionDate) >= String(x.testStart) && String(sessionDate) <= String(x.testEnd));
  if (!d) return { matched: false, guardedAllowed: true, reason: 'NO_GUARD_DECISION' };
  const allowed = d.guardedAllowed ?? d.allowed ?? true;
  return { matched: true, guardedAllowed: Boolean(allowed), reason: d.robustnessReason || d.metaReason || d.reason || null };
}

function applyPolicy(predictions, policy) {
  let matched = 0;
  let blocked = 0;
  const guarded = predictions.map((p) => {
    const decision = intervalDecision(policy, p.sessionDate);
    if (decision.matched) matched += 1;
    if (decision.matched && !decision.guardedAllowed) blocked += 1;
    return decision.guardedAllowed ? p : { ...p, probability: -Infinity };
  });
  return { guarded, matched, blocked };
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

function selectionScore(metrics, baseline) {
  const d = deltas(baseline, metrics);
  return d.netReturn + d.sharpe * 0.25 + d.profitFactor * 0.20 - d.maxDrawdown * 0.50;
}

function choosePolicy({ priorPredictions, groupPolicy }) {
  const priorFoldCount = new Set(priorPredictions.map((p) => p.outerFold)).size;
  if (priorFoldCount < MIN_HISTORY_FOLDS) {
    return { name: 'baseline', reason: 'NESTED_POLICY_WARMUP', priorFoldCount, candidates: [] };
  }

  const baselineMetrics = buildPortfolioOosMetrics(priorPredictions, { entryThreshold: null, costRate: 0.001 });
  const candidates = POLICY_NAMES.map((name) => {
    const policy = findPolicy(groupPolicy, name);
    const applied = applyPolicy(priorPredictions, policy);
    if (name !== 'baseline' && !applied.matched) throw new Error(`PHASE49_8_NO_PRIOR_POLICY_MATCH:${groupPolicy.name}:${name}`);
    const metrics = buildPortfolioOosMetrics(applied.guarded, { entryThreshold: null, costRate: 0.001 });
    return {
      name,
      score: name === 'baseline' ? 0 : selectionScore(metrics, baselineMetrics),
      metrics: metricView(metrics),
      blockedPredictionRate: priorPredictions.length ? applied.blocked / priorPredictions.length : 0,
    };
  });

  const best = [...candidates].sort((a, b) => b.score - a.score || a.name.localeCompare(b.name))[0];
  if (best.name === 'baseline' || best.score < MIN_SCORE_ADVANTAGE) {
    return { name: 'baseline', reason: 'NO_CAUSAL_POLICY_ADVANTAGE', priorFoldCount, candidates };
  }
  return { name: best.name, reason: 'CAUSAL_PRIOR_FOLD_ADVANTAGE', priorFoldCount, candidates };
}

const groups = [];
for (const file of fs.readdirSync(robustnessDir).filter((f) => f.endsWith('-model.json')).sort()) {
  const name = file.replace(/-model\.json$/, '');
  const model = JSON.parse(fs.readFileSync(`${robustnessDir}/${file}`, 'utf8'));
  const { selectedModelType, aggregate } = selectedResult(model);
  const { predictions, folds } = reconstructOosPredictions(name, model);
  const groupPolicy = policiesByGroup.get(name);
  if (!groupPolicy) throw new Error(`PHASE49_8_GROUP_POLICY_MISSING:${name}`);

  const baseline = buildPortfolioOosMetrics(predictions, { entryThreshold: null, costRate: 0.001 });
  const source = aggregate?.oos || {};
  const tolerance = 1e-10;
  const reproduction = {
    netReturnDelta: baseline.netReturn - Number(source.netReturn ?? baseline.netReturn),
    profitFactorDelta: baseline.profitFactor - Number(source.profitFactor ?? baseline.profitFactor),
    sharpeDelta: baseline.sharpe - Number(source.sharpe ?? baseline.sharpe),
    maxDrawdownDelta: baseline.maxDrawdown - Number(source.maxDrawdown ?? baseline.maxDrawdown),
  };
  reproduction.matchesCanonicalSource = Object.values(reproduction).every((v) => typeof v !== 'number' || Math.abs(v) <= tolerance);
  if (!reproduction.matchesCanonicalSource) {
    throw new Error(`PHASE49_8_CANONICAL_REPRODUCTION_MISMATCH:${name}:${JSON.stringify(reproduction)}`);
  }

  const nestedPredictions = [];
  const selections = [];
  for (const fold of folds) {
    const current = predictions.filter((p) => p.outerFold === fold.fold);
    const prior = predictions.filter((p) => p.outerFold < fold.fold);
    const selection = choosePolicy({ priorPredictions: prior, groupPolicy });
    const selectedPolicy = findPolicy(groupPolicy, selection.name);
    const applied = applyPolicy(current, selectedPolicy);
    if (selection.name !== 'baseline' && !applied.matched) {
      throw new Error(`PHASE49_8_CURRENT_POLICY_INTERVAL_MISSING:${name}:${fold.fold}:${selection.name}`);
    }
    nestedPredictions.push(...applied.guarded);
    selections.push({
      fold: fold.fold,
      testStart: fold.testStart,
      testEnd: fold.testEnd,
      selectedPolicy: selection.name,
      selectionReason: selection.reason,
      priorFoldCount: selection.priorFoldCount,
      evidenceThroughFold: fold.fold - 1,
      evidenceThroughDate: fold.fold > 1 ? folds.find((f) => f.fold === fold.fold - 1)?.testEnd ?? null : null,
      currentFoldMatchedPredictions: applied.matched,
      currentFoldBlockedPredictions: applied.blocked,
      candidates: selection.candidates,
    });
  }

  const nested = buildPortfolioOosMetrics(nestedPredictions, { entryThreshold: null, costRate: 0.001 });
  const selectedCounts = Object.fromEntries(POLICY_NAMES.map((policy) => [policy, selections.filter((s) => s.selectedPolicy === policy).length]));
  groups.push({
    name,
    selectedModelType,
    canonicalReproduction: reproduction,
    baseline: metricView(baseline),
    nestedPolicyOos: metricView(nested),
    deltas: deltas(baseline, nested),
    selectedPolicyCounts: selectedCounts,
    selections,
    policySelectionMode: 'NESTED_CAUSAL_PRIOR_FOLDS_ONLY',
    retrospectiveBestPolicyUsedForSelection: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
  });
}

const output = {
  phase: 49.8,
  purpose: 'Nested causal guard-policy selection. Each outer fold chooses baseline/strict/balanced/permissive using canonical portfolio metrics from prior outer folds only, then applies that fixed choice to the unseen current fold.',
  minHistoryFolds: MIN_HISTORY_FOLDS,
  minScoreAdvantage: MIN_SCORE_ADVANTAGE,
  groups,
  limitations: [
    'Policy selection is causal with respect to outer folds but still limited to the available historical universe.',
    'No live trading or automatic promotion actions are permitted.',
    'A separate paper/shadow phase is still required before any real-order path can be considered.'
  ],
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
