#!/usr/bin/env node
import fs from 'node:fs';
import { buildPortfolioOosMetrics } from '../predict/models/phase47-walk-forward.js';

const robustnessDir = process.argv[2] || 'data/phase49-robustness';
const guardPath = process.argv[3] || 'data/phase49-guard-robustness/summary.json';
const outDir = process.argv[4] || 'data/phase49-portfolio-guard-oos';
fs.mkdirSync(outDir, { recursive: true });

const guard = JSON.parse(fs.readFileSync(guardPath, 'utf8'));
const policiesByGroup = new Map((guard.groups || []).map((g) => [g.name, g]));

function extractSelected(model) {
  const wf = model.walkForward || {};
  const selectedModelType = wf.selectedModelType;
  const ranked = wf.ranked || [];
  const selected = ranked.find((x) => x.modelType === selectedModelType) || ranked[0];
  if (!selected) throw new Error('PHASE49_6_SELECTED_MODEL_MISSING');
  const predictions = selected.aggregate?.predictions || selected.predictions || selected.oosPredictions || [];
  if (!Array.isArray(predictions) || !predictions.length) {
    throw new Error('PHASE49_6_OOS_PREDICTIONS_MISSING');
  }
  return { selectedModelType, predictions, aggregate: selected.aggregate };
}

function intervalDecision(groupPolicy, sessionDate, policyName = 'balanced') {
  const policy = groupPolicy?.policies?.find((p) => p.name === policyName)
    || groupPolicy?.policyResults?.find((p) => p.name === policyName)
    || groupPolicy?.[policyName]
    || null;
  const decisions = policy?.decisions || groupPolicy?.decisions || [];
  const d = decisions.find((x) => String(sessionDate) >= String(x.testStart) && String(sessionDate) <= String(x.testEnd));
  if (!d) return { guardedAllowed: true, metaActive: false, reason: 'NO_GUARD_DECISION' };
  const allowed = d.guardedAllowed ?? d.allowed ?? true;
  return { guardedAllowed: Boolean(allowed), metaActive: Boolean(d.metaActive), reason: d.metaReason || d.reason || null };
}

const groups = [];
for (const file of fs.readdirSync(robustnessDir).filter((f) => f.endsWith('-model.json')).sort()) {
  const name = file.replace(/-model\.json$/, '');
  const model = JSON.parse(fs.readFileSync(`${robustnessDir}/${file}`, 'utf8'));
  const { selectedModelType, predictions, aggregate } = extractSelected(model);
  const groupPolicy = policiesByGroup.get(name);
  const balancedPredictions = predictions.map((p) => {
    const decision = intervalDecision(groupPolicy, p.sessionDate, 'balanced');
    return decision.guardedAllowed ? p : { ...p, probability: -Infinity };
  });
  const baseline = buildPortfolioOosMetrics(predictions, { costRate: 0.001 });
  const balancedGuard = buildPortfolioOosMetrics(balancedPredictions, { costRate: 0.001 });
  groups.push({
    name,
    selectedModelType,
    sourceAggregate: {
      netReturn: aggregate?.oos?.netReturn ?? null,
      profitFactor: aggregate?.oos?.profitFactor ?? null,
      sharpe: aggregate?.oos?.sharpe ?? null,
      maxDrawdown: aggregate?.oos?.maxDrawdown ?? null,
    },
    baseline: {
      netReturn: baseline.netReturn,
      profitFactor: baseline.profitFactor,
      sharpe: baseline.sharpe,
      maxDrawdown: baseline.maxDrawdown,
      exposure: baseline.exposure,
      positionChanges: baseline.positionChanges,
      sampleCount: baseline.sampleCount,
    },
    balancedGuard: {
      netReturn: balancedGuard.netReturn,
      profitFactor: balancedGuard.profitFactor,
      sharpe: balancedGuard.sharpe,
      maxDrawdown: balancedGuard.maxDrawdown,
      exposure: balancedGuard.exposure,
      positionChanges: balancedGuard.positionChanges,
      sampleCount: balancedGuard.sampleCount,
    },
    deltas: {
      netReturn: balancedGuard.netReturn - baseline.netReturn,
      profitFactor: balancedGuard.profitFactor - baseline.profitFactor,
      sharpe: balancedGuard.sharpe - baseline.sharpe,
      maxDrawdown: balancedGuard.maxDrawdown - baseline.maxDrawdown,
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
  purpose: 'Apples-to-apples portfolio-level OOS comparison using the canonical Phase47 portfolio evaluator. Balanced guard only suppresses exposure for precomputed causal fold intervals.',
  policy: 'balanced',
  limitations: [
    'Guard decisions remain fold-level diagnostics derived only from prior folds.',
    'No live trading or promotion actions are permitted.',
    'This evaluator requires serialized OOS predictions from the selected model output; CI fails closed if unavailable.'
  ],
  groups,
};
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));
