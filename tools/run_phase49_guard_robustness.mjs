import fs from 'node:fs';

const inputPath = process.argv[2] || 'data/phase49-regime-gate-walkforward/summary.json';
const outDir = process.argv[3] || 'data/phase49-guard-robustness';
fs.mkdirSync(outDir, { recursive: true });

const input = JSON.parse(fs.readFileSync(inputPath, 'utf8'));

function summarize(returns) {
  if (!returns.length) return { netReturn: 0, maxDrawdown: 0, sharpeQuarterlyApprox: 0, positiveFoldRate: null };
  let equity = 1, peak = 1, maxDrawdown = 0;
  const mean = returns.reduce((a,b)=>a+b,0)/returns.length;
  const variance = returns.length > 1 ? returns.reduce((s,x)=>s+(x-mean)**2,0)/returns.length : 0;
  const std = Math.sqrt(variance);
  for (const r of returns) {
    equity *= Math.max(0, 1 + r);
    peak = Math.max(peak, equity);
    if (peak > 0) maxDrawdown = Math.max(maxDrawdown, 1 - equity/peak);
  }
  return {
    netReturn: equity - 1,
    maxDrawdown,
    sharpeQuarterlyApprox: std > 0 ? (mean/std)*2 : 0,
    positiveFoldRate: returns.filter((r)=>r>0).length/returns.length,
  };
}

const POLICIES = [
  { name: 'strict', minHistory: 6, minMetricWins: 2, minNetRatio: 1.00, maxBlockedWinningRate: 0.35, minExposure: 0.35 },
  { name: 'balanced', minHistory: 5, minMetricWins: 2, minNetRatio: 0.98, maxBlockedWinningRate: 0.40, minExposure: 0.30 },
  { name: 'permissive', minHistory: 4, minMetricWins: 2, minNetRatio: 0.95, maxBlockedWinningRate: 0.50, minExposure: 0.25 },
];

function evaluateHistory(history, policy) {
  if (history.length < policy.minHistory) return { active: false, reason: 'ROBUSTNESS_WARMUP' };
  const raw = summarize(history.map((d)=>d.rawNetReturn));
  const gated = summarize(history.map((d)=>d.gatedNetReturn));
  const metricWins = [
    gated.netReturn > raw.netReturn,
    gated.maxDrawdown < raw.maxDrawdown,
    gated.sharpeQuarterlyApprox > raw.sharpeQuarterlyApprox,
  ].filter(Boolean).length;
  const losing = history.filter((d)=>d.rawNetReturn <= 0);
  const winning = history.filter((d)=>d.rawNetReturn > 0);
  const blockedLosingRate = losing.length ? losing.filter((d)=>!d.allowed).length/losing.length : 0;
  const blockedWinningRate = winning.length ? winning.filter((d)=>!d.allowed).length/winning.length : 0;
  const exposure = history.length ? history.filter((d)=>d.allowed).length/history.length : 1;
  const rawBase = Math.max(1e-9, 1 + raw.netReturn);
  const gatedBase = Math.max(0, 1 + gated.netReturn);
  const netRatio = gatedBase / rawBase;
  const active = metricWins >= policy.minMetricWins
    && netRatio >= policy.minNetRatio
    && blockedWinningRate <= policy.maxBlockedWinningRate
    && exposure >= policy.minExposure;
  return {
    active,
    reason: active ? 'ROBUSTNESS_GATE_ACTIVE' : 'ROBUSTNESS_GATE_BYPASS',
    evidence: { raw, gated, metricWins, netRatio, blockedLosingRate, blockedWinningRate, exposure },
  };
}

const groups = [];
for (const group of input.groups || []) {
  const policyResults = [];
  for (const policy of POLICIES) {
    const history = [];
    const decisions = [];
    for (const d of group.decisions || []) {
      if (!d.gate) {
        decisions.push({ ...d, robustnessActive: false, robustnessReason: 'BASE_GATE_WARMUP', guardedAllowed: true, guardedNetReturn: d.rawNetReturn });
        continue;
      }
      const meta = evaluateHistory(history, policy);
      const guardedAllowed = meta.active ? d.allowed : true;
      decisions.push({
        ...d,
        robustnessActive: meta.active,
        robustnessReason: meta.reason,
        robustnessEvidence: meta.evidence ?? null,
        guardedAllowed,
        guardedNetReturn: guardedAllowed ? d.rawNetReturn : 0,
      });
      history.push(d);
    }
    const evaluated = decisions.filter((d)=>d.gate);
    const rawReturns = evaluated.map((d)=>d.rawNetReturn);
    const guardedReturns = evaluated.map((d)=>d.guardedNetReturn);
    policyResults.push({
      policy,
      evaluatedFoldCount: evaluated.length,
      activeFoldRate: evaluated.length ? evaluated.filter((d)=>d.robustnessActive).length/evaluated.length : null,
      guardedExposureFoldRate: evaluated.length ? evaluated.filter((d)=>d.guardedAllowed).length/evaluated.length : null,
      baseline: summarize(rawReturns),
      guarded: summarize(guardedReturns),
      decisions,
    });
  }
  groups.push({
    name: group.name,
    selectedModelType: group.selectedModelType,
    policies: policyResults,
    safety: { brokerWrites: 0, excelOrderWrites: 0, rssOrderCalls: 0, liveOrders: 0, automaticPromotionAllowed: false, productionUpdateAllowed: false },
  });
}

const output = {
  phase: 49.5,
  purpose: 'Robustness evaluation for causal regime-gate promotion policies using only prior fold evidence. Diagnostic only.',
  policies: POLICIES,
  limitations: ['Fold-level diagnostic only', 'No live trading actions', 'Promotion remains blocked'],
  groups,
};
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));
