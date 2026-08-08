import fs from 'node:fs';

const input = process.argv[2] || 'data/training/phase49-expanded.json';
const diagnosticsPath = process.argv[3] || 'data/phase49-diagnostics/summary.json';
const outDir = process.argv[4] || 'data/phase49-regime-gate';
fs.mkdirSync(outDir, { recursive: true });

const parsed = JSON.parse(fs.readFileSync(input, 'utf8'));
const rows = parsed.rows || parsed.dataset || parsed;
if (!Array.isArray(rows)) throw new Error('PHASE49_REGIME_INPUT_ROWS_MISSING');
const diagnostics = JSON.parse(fs.readFileSync(diagnosticsPath, 'utf8'));

const finite = (v) => Number.isFinite(Number(v)) ? Number(v) : null;
const mean = (xs) => {
  const ys = xs.filter(Number.isFinite);
  return ys.length ? ys.reduce((a,b)=>a+b,0)/ys.length : null;
};
const FEATURES = [
  'regimeTrend','regimeAdx','regimeVolatility','regimeAtr',
  'adx14Approx','volatility20','atr14','volumeRatio20',
  'return5','return20','ma20Gap','ma50Gap','ma75Gap','vwapGap20','bollingerZ20'
];

const rowsByDate = new Map();
for (const row of rows) {
  const d = row.sessionDate;
  if (!d) continue;
  if (!rowsByDate.has(d)) rowsByDate.set(d, []);
  rowsByDate.get(d).push(row);
}

const periodFeatureMeans = (start, end) => {
  const bucket = [];
  for (const [date, rs] of rowsByDate.entries()) {
    if (date >= start && date <= end) bucket.push(...rs);
  }
  const out = {};
  for (const key of FEATURES) {
    out[key] = mean(bucket.map((row) => finite(row.features?.[key] ?? row[key])).filter(Number.isFinite));
  }
  return out;
};

const groups = [];
for (const group of diagnostics.groups || []) {
  const folds = (group.folds || []).map((fold) => ({
    ...fold,
    regime: periodFeatureMeans(fold.testStart, fold.testEnd),
    isWinner: (fold.netReturn ?? 0) > 0,
  }));
  const winners = folds.filter((f) => f.isWinner);
  const losers = folds.filter((f) => !f.isWinner);
  const featureDiffs = FEATURES.map((key) => {
    const w = mean(winners.map((f) => f.regime[key]).filter(Number.isFinite));
    const l = mean(losers.map((f) => f.regime[key]).filter(Number.isFinite));
    const denom = Math.max(Math.abs(l ?? 0), 1e-9);
    return { feature: key, winnerMean: w, loserMean: l, relativeDifference: w == null || l == null ? null : (w-l)/denom };
  }).sort((a,b)=>Math.abs(b.relativeDifference ?? 0)-Math.abs(a.relativeDifference ?? 0));

  groups.push({
    name: group.name,
    selectedModelType: group.selectedModelType,
    foldCount: folds.length,
    winningFoldCount: winners.length,
    losingFoldCount: losers.length,
    featureDiffs,
    candidateGateSignals: featureDiffs.slice(0, 5),
    folds,
    safety: group.safety,
  });
}

const output = {
  phase: 49.2,
  purpose: 'Diagnostic-only comparison of winning vs losing OOS market regimes; no execution or automatic promotion',
  groups,
};
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));
