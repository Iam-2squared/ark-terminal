export const LEARNING_INTELLIGENCE_V1_VERSION = "learning-intelligence-v1";

function num(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function closedTrades(records = []) {
  return (Array.isArray(records) ? records : []).filter((record) => {
    const action = String(record?.action ?? "").toUpperCase();
    const status = String(record?.status ?? record?.outcome ?? "").toUpperCase();
    return ["BUY", "SELL"].includes(action) && ["WIN", "LOSS", "FLAT", "CLOSED"].includes(status);
  });
}

function summarize(records = []) {
  const wins = records.filter((r) => num(r.returnPercent ?? r.pnlPercent) > 0);
  const losses = records.filter((r) => num(r.returnPercent ?? r.pnlPercent) < 0);
  const avg = records.length
    ? records.reduce((s, r) => s + num(r.returnPercent ?? r.pnlPercent), 0) / records.length
    : null;
  return {
    count: records.length,
    wins: wins.length,
    losses: losses.length,
    winRate: records.length ? (wins.length / records.length) * 100 : null,
    averageReturnPercent: avg,
  };
}

function groupBy(records, selector) {
  const map = new Map();
  for (const record of records) {
    const key = String(selector(record) ?? "UNKNOWN").toUpperCase();
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(record);
  }
  return Object.fromEntries(Array.from(map, ([key, items]) => [key, summarize(items)]));
}

function featureEffects(records) {
  const names = new Set();
  for (const record of records) {
    for (const key of Object.keys(record.features ?? record.technical ?? {})) names.add(key);
  }
  return Array.from(names).map((feature) => {
    const rows = records
      .map((r) => ({ x: num((r.features ?? r.technical ?? {})[feature], NaN), y: num(r.returnPercent ?? r.pnlPercent) }))
      .filter((r) => Number.isFinite(r.x));
    if (rows.length < 2) return { feature, sampleSize: rows.length, directionalEffect: null };
    const meanX = rows.reduce((s, r) => s + r.x, 0) / rows.length;
    const high = rows.filter((r) => r.x >= meanX);
    const low = rows.filter((r) => r.x < meanX);
    const avg = (xs) => xs.length ? xs.reduce((s, r) => s + r.y, 0) / xs.length : 0;
    return {
      feature,
      sampleSize: rows.length,
      threshold: meanX,
      highAverageReturnPercent: avg(high),
      lowAverageReturnPercent: avg(low),
      directionalEffect: avg(high) - avg(low),
    };
  }).sort((a, b) => Math.abs(b.directionalEffect ?? 0) - Math.abs(a.directionalEffect ?? 0));
}

export function analyzeLearningIntelligence(records = []) {
  const trades = closedTrades(records);
  return {
    version: LEARNING_INTELLIGENCE_V1_VERSION,
    generatedAt: new Date().toISOString(),
    sample: summarize(trades),
    byOutcome: {
      winners: summarize(trades.filter((r) => num(r.returnPercent ?? r.pnlPercent) > 0)),
      losers: summarize(trades.filter((r) => num(r.returnPercent ?? r.pnlPercent) < 0)),
    },
    byRegime: groupBy(trades, (r) => r.marketRegime ?? r.regime),
    bySector: groupBy(trades, (r) => r.sector),
    byAction: groupBy(trades, (r) => r.action),
    featureEffects: featureEffects(trades),
    warnings: trades.length < 30 ? ["INSUFFICIENT_TRADE_SAMPLE"] : [],
  };
}

export default analyzeLearningIntelligence;
