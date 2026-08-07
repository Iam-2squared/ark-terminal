import fs from 'node:fs';

const datasetPath = process.argv[2] || 'data/training/phase49-expanded.json';
const diagnosticsPath = process.argv[3] || 'data/phase49-diagnostics/summary.json';
const outDir = process.argv[4] || 'data/phase49-regime-gate-walkforward';
fs.mkdirSync(outDir, { recursive: true });

const dataset = JSON.parse(fs.readFileSync(datasetPath, 'utf8'));
const rows = dataset.rows || dataset.dataset || dataset;
const diagnostics = JSON.parse(fs.readFileSync(diagnosticsPath, 'utf8'));
if (!Array.isArray(rows)) throw new Error('PHASE49_3_DATASET_ROWS_MISSING');

const GROUPS = {
  all: null,
  core5: ['7203.T','6758.T','9984.T','8306.T','8035.T'],
  banks: ['8306.T','8316.T','8411.T'],
  autos: ['7203.T','7267.T','7201.T'],
  electronics: ['6758.T','8035.T','6501.T','6954.T'],
  trading: ['8058.T','8001.T','8031.T'],
};
const FEATURES = ['ma20Gap','ma50Gap','ma75Gap','return5','return20','vwapGap20','bollingerZ20','regimeTrend','regimeVolatility','volatility20','atr14','volumeRatio20'];
const finite = (x) => Number.isFinite(Number(x)) ? Number(x) : null;
const mean = (xs) => xs.length ? xs.reduce((a,b)=>a+b,0)/xs.length : null;
const std = (xs) => {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  return Math.sqrt(xs.reduce((s,x)=>s+(x-m)**2,0)/xs.length);
};

function snapshot(groupName, testStart) {
  const symbols = GROUPS[groupName];
  const eligible = rows.filter((r) => (!symbols || symbols.includes(r.symbol)) && String(r.sessionDate) < String(testStart));
  const latestBySymbol = new Map();
  for (const row of eligible) {
    const prev = latestBySymbol.get(row.symbol);
    if (!prev || String(row.sessionDate) > String(prev.sessionDate)) latestBySymbol.set(row.symbol, row);
  }
  const latest = [...latestBySymbol.values()];
  const out = {};
  for (const feature of FEATURES) {
    const values = latest.map((r) => finite(r.features?.[feature] ?? r[feature])).filter((v) => v !== null);
    out[feature] = mean(values);
  }
  return { asOf: latest.map((r)=>r.sessionDate).sort().at(-1) ?? null, symbolCount: latest.length, features: out };
}

function trainGate(history) {
  if (history.length < 4) return null;
  const winners = history.filter((x) => (x.netReturn ?? 0) > 0);
  const losers = history.filter((x) => (x.netReturn ?? 0) <= 0);
  if (winners.length < 2 || losers.length < 2) return null;
  let best = null;
  for (const feature of FEATURES) {
    const w = winners.map((x)=>finite(x.snapshot.features[feature])).filter((v)=>v!==null);
    const l = losers.map((x)=>finite(x.snapshot.features[feature])).filter((v)=>v!==null);
    if (!w.length || !l.length) continue;
    const wm = mean(w), lm = mean(l);
    if (wm === lm) continue;
    const direction = wm > lm ? 'gte' : 'lte';
    const threshold = (wm + lm) / 2;
    let tp=0, fn=0, tn=0, fp=0;
    for (const item of history) {
      const value = finite(item.snapshot.features[feature]);
      if (value === null) continue;
      const allow = direction === 'gte' ? value >= threshold : value <= threshold;
      const positive = (item.netReturn ?? 0) > 0;
      if (positive && allow) tp++; else if (positive) fn++; else if (!allow) tn++; else fp++;
    }
    const tpr = tp + fn ? tp/(tp+fn) : 0;
    const tnr = tn + fp ? tn/(tn+fp) : 0;
    const balancedAccuracy = (tpr + tnr) / 2;
    const separation = Math.abs(wm-lm) / Math.max(1e-9, Math.abs(lm));
    const candidate = { feature, direction, threshold, winnerMean: wm, loserMean: lm, balancedAccuracy, separation };
    if (!best || balancedAccuracy > best.balancedAccuracy || (balancedAccuracy === best.balancedAccuracy && separation > best.separation)) best = candidate;
  }
  return best;
}

function summarize(returns) {
  let equity = 1, peak = 1, maxDrawdown = 0;
  for (const r of returns) {
    equity *= Math.max(0, 1 + r);
    peak = Math.max(peak, equity);
    if (peak > 0) maxDrawdown = Math.max(maxDrawdown, 1 - equity/peak);
  }
  const s = std(returns);
  return {
    netReturn: equity - 1,
    maxDrawdown,
    sharpeQuarterlyApprox: s > 0 ? (mean(returns)/s)*2 : 0,
    positiveFoldRate: returns.length ? returns.filter((r)=>r>0).length/returns.length : null,
  };
}

const groups = [];
for (const group of diagnostics.groups || []) {
  const history = [];
  const decisions = [];
  for (const fold of group.folds || []) {
    const snap = snapshot(group.name, fold.testStart);
    const gate = trainGate(history);
    let allowed = true;
    let reason = 'WARMUP_ALLOW';
    if (gate) {
      const value = finite(snap.features[gate.feature]);
      allowed = value !== null && (gate.direction === 'gte' ? value >= gate.threshold : value <= gate.threshold);
      reason = allowed ? 'GATE_ALLOW' : 'GATE_BLOCK';
    }
    const netReturn = finite(fold.netReturn) ?? 0;
    decisions.push({ fold: fold.fold, testStart: fold.testStart, testEnd: fold.testEnd, snapshot: snap, gate, allowed, reason, rawNetReturn: netReturn, gatedNetReturn: allowed ? netReturn : 0 });
    history.push({ netReturn, snapshot: snap });
  }
  const evaluated = decisions.filter((d)=>d.gate);
  const rawReturns = evaluated.map((d)=>d.rawNetReturn);
  const gatedReturns = evaluated.map((d)=>d.gatedNetReturn);
  groups.push({
    name: group.name,
    selectedModelType: group.selectedModelType,
    warmupFolds: decisions.length - evaluated.length,
    evaluatedFoldCount: evaluated.length,
    exposureFoldRate: evaluated.length ? evaluated.filter((d)=>d.allowed).length/evaluated.length : null,
    blockedLosingFoldRate: evaluated.filter((d)=>d.rawNetReturn<=0).length ? evaluated.filter((d)=>d.rawNetReturn<=0 && !d.allowed).length/evaluated.filter((d)=>d.rawNetReturn<=0).length : null,
    blockedWinningFoldRate: evaluated.filter((d)=>d.rawNetReturn>0).length ? evaluated.filter((d)=>d.rawNetReturn>0 && !d.allowed).length/evaluated.filter((d)=>d.rawNetReturn>0).length : null,
    baseline: summarize(rawReturns),
    gated: summarize(gatedReturns),
    decisions,
    safety: { brokerWrites: 0, excelOrderWrites: 0, rssOrderCalls: 0, liveOrders: 0, automaticPromotionAllowed: false, productionUpdateAllowed: false },
  });
}

const output = {
  phase: 49.3,
  purpose: 'Causal fold-start regime gate walk-forward diagnostic. Gate parameters use prior OOS folds only; current fold snapshot is strictly before testStart. Diagnostic only.',
  limitations: ['Fold-level gate, not row-level execution backtest', 'Profit factor is intentionally not reported here', 'Promotion remains blocked regardless of diagnostic result'],
  groups,
};
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));