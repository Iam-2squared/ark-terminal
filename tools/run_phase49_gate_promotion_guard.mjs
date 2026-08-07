import fs from 'node:fs';

const inputPath = process.argv[2] || 'data/phase49-regime-gate-walkforward/summary.json';
const outDir = process.argv[3] || 'data/phase49-gate-promotion-guard';
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

function shouldActivate(history) {
  if (history.length < 4) return { active: false, reason: 'META_WARMUP' };
  const raw = summarize(history.map((d)=>d.rawNetReturn));
  const gated = summarize(history.map((d)=>d.gatedNetReturn));
  const wins = [
    gated.netReturn > raw.netReturn,
    gated.maxDrawdown < raw.maxDrawdown,
    gated.sharpeQuarterlyApprox > raw.sharpeQuarterlyApprox,
  ].filter(Boolean).length;
  const active = wins >= 2 && gated.netReturn >= raw.netReturn * 0.95;
  return { active, reason: active ? 'META_GATE_ACTIVE' : 'META_GATE_BYPASS', evidence: { raw, gated, improvedMetricCount: wins } };
}

const groups = [];
for (const group of input.groups || []) {
  const evaluatedHistory = [];
  const decisions = [];
  for (const d of group.decisions || []) {
    if (!d.gate) {
      decisions.push({ ...d, metaActive: false, metaReason: 'BASE_GATE_WARMUP', guardedNetReturn: d.rawNetReturn });
      continue;
    }
    const meta = shouldActivate(evaluatedHistory);
    const guardedAllowed = meta.active ? d.allowed : true;
    const guardedNetReturn = guardedAllowed ? d.rawNetReturn : 0;
    decisions.push({ ...d, metaActive: meta.active, metaReason: meta.reason, metaEvidence: meta.evidence ?? null, guardedAllowed, guardedNetReturn });
    evaluatedHistory.push(d);
  }
  const evaluated = decisions.filter((d)=>d.gate);
  const rawReturns = evaluated.map((d)=>d.rawNetReturn);
  const baseGatedReturns = evaluated.map((d)=>d.gatedNetReturn);
  const guardedReturns = evaluated.map((d)=>d.guardedNetReturn);
  groups.push({
    name: group.name,
    selectedModelType: group.selectedModelType,
    evaluatedFoldCount: evaluated.length,
    metaActiveFoldRate: evaluated.length ? evaluated.filter((d)=>d.metaActive).length/evaluated.length : null,
    guardedExposureFoldRate: evaluated.length ? evaluated.filter((d)=>d.guardedAllowed).length/evaluated.length : null,
    baseline: summarize(rawReturns),
    baseGate: summarize(baseGatedReturns),
    guardedGate: summarize(guardedReturns),
    decisions,
    safety: { brokerWrites: 0, excelOrderWrites: 0, rssOrderCalls: 0, liveOrders: 0, automaticPromotionAllowed: false, productionUpdateAllowed: false },
  });
}

const output = {
  phase: 49.4,
  purpose: 'Causal meta-promotion guard for Phase49.3 regime gate. The gate is only activated after prior gate decisions show improvement on at least two of net return, drawdown, and Sharpe. Diagnostic only.',
  limitations: ['Fold-level diagnostic only', 'No live trading actions', 'Promotion remains blocked'],
  groups,
};
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));
