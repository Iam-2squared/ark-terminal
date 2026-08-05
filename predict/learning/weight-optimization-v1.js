export const WEIGHT_OPTIMIZATION_V1_VERSION = "weight-optimization-v1";

function num(v, fallback = 0) { const n = Number(v); return Number.isFinite(n) ? n : fallback; }
function closed(records = []) { return (Array.isArray(records) ? records : []).filter((r) => ["BUY", "SELL"].includes(String(r?.action ?? "").toUpperCase()) && ["WIN", "LOSS", "FLAT", "CLOSED"].includes(String(r?.status ?? r?.outcome ?? "").toUpperCase())); }
function avg(xs) { return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0; }

function importance(records) {
  const names = new Set(records.flatMap((r) => Object.keys(r.features ?? r.technical ?? {})));
  return Array.from(names).map((feature) => {
    const rows = records.map((r) => ({ x: num((r.features ?? r.technical ?? {})[feature], NaN), y: num(r.returnPercent ?? r.pnlPercent) })).filter((r) => Number.isFinite(r.x));
    if (rows.length < 2) return { feature, score: 0, sampleSize: rows.length };
    const mx = avg(rows.map((r) => r.x));
    const my = avg(rows.map((r) => r.y));
    const cov = rows.reduce((s, r) => s + (r.x - mx) * (r.y - my), 0);
    const vx = Math.sqrt(rows.reduce((s, r) => s + (r.x - mx) ** 2, 0));
    const vy = Math.sqrt(rows.reduce((s, r) => s + (r.y - my) ** 2, 0));
    return { feature, score: vx && vy ? Math.abs(cov / (vx * vy)) : 0, sampleSize: rows.length };
  }).sort((a, b) => b.score - a.score);
}

function normalizedWeights(items) {
  const total = items.reduce((s, x) => s + x.score, 0);
  return Object.fromEntries(items.map((x) => [x.feature, total > 0 ? x.score / total : 0]));
}

export function analyzeWeightOptimization(records = [], { evaluator = null } = {}) {
  const trades = closed(records);
  const featureImportance = importance(trades);
  const permutationImportance = typeof evaluator === "function"
    ? featureImportance.map(({ feature }) => ({ feature, scoreDrop: num(evaluator({ records: trades, permutedFeature: feature })) })).sort((a, b) => b.scoreDrop - a.scoreDrop)
    : [];
  const byRegime = {};
  const bySector = {};
  for (const regime of new Set(trades.map((r) => String(r.marketRegime ?? r.regime ?? "UNKNOWN").toUpperCase()))) {
    const subset = trades.filter((r) => String(r.marketRegime ?? r.regime ?? "UNKNOWN").toUpperCase() === regime);
    byRegime[regime] = normalizedWeights(importance(subset));
  }
  for (const sector of new Set(trades.map((r) => String(r.sector ?? "UNKNOWN").toUpperCase()))) {
    const subset = trades.filter((r) => String(r.sector ?? "UNKNOWN").toUpperCase() === sector);
    bySector[sector] = normalizedWeights(importance(subset));
  }
  return {
    version: WEIGHT_OPTIMIZATION_V1_VERSION,
    sampleSize: trades.length,
    featureImportance,
    permutationImportance,
    proposedWeights: normalizedWeights(featureImportance),
    byRegime,
    bySector,
    outOfSampleRequired: true,
    productionUpdateAllowed: false,
  };
}

export default analyzeWeightOptimization;
