#!/usr/bin/env node
import fs from 'node:fs';
import { buildPortfolioOosMetrics } from '../predict/models/phase47-walk-forward.js';
import { evaluateModel, normalizeTrainingRows, trainModel } from '../predict/models/phase47-real-training.js';

const robustnessDir = process.argv[2] || 'data/phase49-robustness';
const guardPath = process.argv[3] || 'data/phase49-guard-robustness/summary.json';
const outDir = process.argv[4] || 'data/phase49-promotion-demotion';
const POLICY_NAMES = ['baseline', 'strict', 'balanced', 'permissive'];
const MIN_HISTORY_FOLDS = 4;
const PROMOTE_SCORE_ADVANTAGE = 0.01;
const DEMOTE_SCORE_FLOOR = -0.005;
const DEMOTE_CONFIRM_FOLDS = 2;
fs.mkdirSync(outDir, { recursive: true });

const guard = JSON.parse(fs.readFileSync(guardPath, 'utf8'));
const policiesByGroup = new Map((guard.groups || []).map((g) => [g.name, g]));

function selectedResult(model) {
  const wf = model.walkForward || {};
  const selectedModelType = wf.selectedModelType;
  const ranked = wf.ranked || [];
  const selected = ranked.find((x) => x.modelType === selectedModelType) || ranked[0];
  if (!selected) throw new Error('PHASE49_9_SELECTED_MODEL_MISSING');
  return { selectedModelType: selected.modelType, selected, aggregate: selected.aggregate };
}

function reconstructOosPredictions(groupName, model) {
  const datasetPath = `${robustnessDir}/${groupName}.json`;
  if (!fs.existsSync(datasetPath)) throw new Error(`PHASE49_9_DATASET_MISSING:${groupName}`);
  const dataset = JSON.parse(fs.readFileSync(datasetPath, 'utf8'));
  const rawRows = Array.isArray(dataset) ? dataset : (dataset.rows || dataset.dataset?.rows || []);
  const rows = normalizeTrainingRows(rawRows);
  const { selectedModelType, selected } = selectedResult(model);
  const folds = selected.folds || [];
  if (!folds.length) throw new Error(`PHASE49_9_FOLDS_MISSING:${groupName}`);

  const predictions = [];
  for (const fold of folds) {
    const trainRows = rows.filter((r) => String(r.sessionDate) >= String(fold.trainStart) && String(r.sessionDate) <= String(fold.trainEnd));
    const testRows = rows.filter((r) => String(r.sessionDate) >= String(fold.testStart) && String(r.sessionDate) <= String(fold.testEnd));
    if (trainRows.length < 20 || !testRows.length) throw new Error(`PHASE49_9_FOLD_ROWS_MISSING:${groupName}:${fold.fold}`);
    const trained = trainModel({ rows: trainRows, modelType: selectedModelType });
    const metrics = evaluateModel({ model: trained, rows: testRows, costRate: 0.001 });
    if (!Array.isArray(metrics.probabilities) || metrics.probabilities.length !== testRows.length) {
      throw new Error(`PHASE49_9_PROBABILITY_MISMATCH:${groupName}:${fold.fold}`);
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
  if (!policy) throw new Error(`PHASE49_9_POLICY_MISSING:${groupPolicy?.name ?? 'unknown'}:${policyName}`);
  return policy;
}

function intervalDecision(policy, sessionDate) {
  if (!policy) return { matched: true, guardedAllowed: true };
  const d = (policy.decisions || []).find((x) => String(sessionDate) >= String(x.testStart) && String(sessionDate) <= String(x.testEnd));
  if (!d) return { matched: false, guardedAllowed: true };
  return { matched: true, guardedAllowed: Boolean(d.guardedAllowed ?? d.allowed ?? true) };
}

function applyPolicy(predictions, policy) {
  let matched = 0;
  let blocked = 0;
  const guarded = predictions.map((p) => {
    const d = intervalDecision(policy, p.sessionDate);
    if (d.matched) matched += 1;
    if (d.matched && !d.guardedAllowed) blocked += 1;
    return d.guardedAllowed ? p : { ...p, probability: -Infinity };
  });
  return { guarded, matched, blocked };
}

function metricView(m) {
  return {
    netReturn: m.netReturn,
    profitFactor: m.profitFactor,
    sharpe: m.sharpe,
    maxDrawdown: m.maxDrawdown,
    cagr: m.cagr,
    exposure: m.exposure,
    positionChanges: m.positionChanges,
    sampleCount: m.sampleCount,
    portfolioDays: m.portfolioDays,
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

function score(metrics, baseline) {
  const d = deltas(baseline, metrics);
  return d.netReturn + d.sharpe * 0.25 + d.profitFactor * 0.20 - d.maxDrawdown * 0.50;
}

function evaluateCandidates(priorPredictions, groupPolicy) {
  const baselineMetrics = buildPortfolioOosMetrics(priorPredictions, { entryThreshold: null, costRate: 0.001 });
  return POLICY_NAMES.map((name) => {
    const policy = findPolicy(groupPolicy, name);
    const applied = applyPolicy(priorPredictions, policy);
    if (name !== 'baseline' && !applied.matched) throw new Error(`PHASE49_9_NO_PRIOR_POLICY_MATCH:${groupPolicy.name}:${name}`);
    const metrics = buildPortfolioOosMetrics(applied.guarded, { entryThreshold: null, costRate: 0.001 });
    return {
      name,
      score: name === 'baseline' ? 0 : score(metrics, baselineMetrics),
      metrics: metricView(metrics),
      blockedPredictionRate: priorPredictions.length ? applied.blocked / priorPredictions.length : 0,
    };
  });
}

const groups = [];
for (const file of fs.readdirSync(robustnessDir).filter((f) => f.endsWith('-model.json')).sort()) {
  const name = file.replace(/-model\.json$/, '');
  const model = JSON.parse(fs.readFileSync(`${robustnessDir}/${file}`, 'utf8'));
  const { selectedModelType, aggregate } = selectedResult(model);
  const { predictions, folds } = reconstructOosPredictions(name, model);
  const groupPolicy = policiesByGroup.get(name);
  if (!groupPolicy) throw new Error(`PHASE49_9_GROUP_POLICY_MISSING:${name}`);

  const baseline = buildPortfolioOosMetrics(predictions, { entryThreshold: null, costRate: 0.001 });
  const source = aggregate?.oos || {};
  const reproduction = {
    netReturnDelta: baseline.netReturn - Number(source.netReturn ?? baseline.netReturn),
    profitFactorDelta: baseline.profitFactor - Number(source.profitFactor ?? baseline.profitFactor),
    sharpeDelta: baseline.sharpe - Number(source.sharpe ?? baseline.sharpe),
    maxDrawdownDelta: baseline.maxDrawdown - Number(source.maxDrawdown ?? baseline.maxDrawdown),
  };
  reproduction.matchesCanonicalSource = Object.values(reproduction).every((v) => typeof v !== 'number' || Math.abs(v) <= 1e-10);
  if (!reproduction.matchesCanonicalSource) throw new Error(`PHASE49_9_CANONICAL_REPRODUCTION_MISMATCH:${name}`);

  const finalPredictions = [];
  const selections = [];
  let activePolicy = 'baseline';
  let consecutiveDemotionSignals = 0;

  for (const fold of folds) {
    const prior = predictions.filter((p) => p.outerFold < fold.fold);
    const current = predictions.filter((p) => p.outerFold === fold.fold);
    const priorFoldCount = new Set(prior.map((p) => p.outerFold)).size;
    let candidates = [];
    let reason = 'WARMUP_BASELINE';

    if (priorFoldCount >= MIN_HISTORY_FOLDS) {
      candidates = evaluateCandidates(prior, groupPolicy);
      const byName = Object.fromEntries(candidates.map((c) => [c.name, c]));
      const currentScore = byName[activePolicy]?.score ?? 0;

      if (activePolicy !== 'baseline') {
        if (currentScore < DEMOTE_SCORE_FLOOR) consecutiveDemotionSignals += 1;
        else consecutiveDemotionSignals = 0;
        if (consecutiveDemotionSignals >= DEMOTE_CONFIRM_FOLDS) {
          activePolicy = 'baseline';
          consecutiveDemotionSignals = 0;
          reason = 'CAUSAL_DEMOTION_TO_BASELINE';
        }
      }

      if (activePolicy === 'baseline') {
        const best = [...candidates].sort((a, b) => b.score - a.score || a.name.localeCompare(b.name))[0];
        if (best.name !== 'baseline' && best.score >= PROMOTE_SCORE_ADVANTAGE) {
          activePolicy = best.name;
          reason = 'CAUSAL_PROMOTION_FROM_BASELINE';
        } else if (reason !== 'CAUSAL_DEMOTION_TO_BASELINE') {
          reason = 'NO_CAUSAL_PROMOTION_ADVANTAGE';
        }
      } else if (reason !== 'CAUSAL_DEMOTION_TO_BASELINE') {
        reason = 'KEEP_ACTIVE_POLICY';
      }
    }

    const selectedPolicy = findPolicy(groupPolicy, activePolicy);
    const applied = applyPolicy(current, selectedPolicy);
    if (activePolicy !== 'baseline' && !applied.matched) throw new Error(`PHASE49_9_CURRENT_POLICY_INTERVAL_MISSING:${name}:${fold.fold}:${activePolicy}`);
    finalPredictions.push(...applied.guarded);
    selections.push({
      fold: fold.fold,
      testStart: fold.testStart,
      testEnd: fold.testEnd,
      selectedPolicy: activePolicy,
      reason,
      priorFoldCount,
      consecutiveDemotionSignals,
      currentFoldMatchedPredictions: applied.matched,
      currentFoldBlockedPredictions: applied.blocked,
      candidates,
    });
  }

  const adaptive = buildPortfolioOosMetrics(finalPredictions, { entryThreshold: null, costRate: 0.001 });
  const selectedPolicyCounts = Object.fromEntries(POLICY_NAMES.map((p) => [p, selections.filter((s) => s.selectedPolicy === p).length]));
  groups.push({
    name,
    selectedModelType,
    canonicalReproduction: reproduction,
    baseline: metricView(baseline),
    adaptivePromotionDemotionOos: metricView(adaptive),
    deltas: deltas(baseline, adaptive),
    selectedPolicyCounts,
    selections,
    policySelectionMode: 'CAUSAL_PROMOTION_DEMOTION_PRIOR_FOLDS_ONLY',
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
  });
}

const output = {
  phase: 49.9,
  purpose: 'Final causal promotion/demotion validation. Policies may be promoted from baseline or demoted back to baseline using only prior outer-fold evidence; no same-fold or future evidence is used.',
  config: { MIN_HISTORY_FOLDS, PROMOTE_SCORE_ADVANTAGE, DEMOTE_SCORE_FLOOR, DEMOTE_CONFIRM_FOLDS },
  groups,
  limitations: [
    'Historical-universe validation only; paper/shadow validation remains required before any real-order path.',
    'Promotion/demotion here is research-state selection only, not live deployment or automatic trading.',
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
