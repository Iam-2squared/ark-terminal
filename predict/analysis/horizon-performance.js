import { summarizePerformance } from '../backtest/engine.js';

export const ARK_HORIZONS = Object.freeze([1, 3, 5, 10, 20]);

function normalizedPeriod(record) {
  const value = Number(record?.period ?? record?.horizon ?? record?.predictionHorizon);
  return Number.isFinite(value) ? value : null;
}

function qualityScore(metrics) {
  const sampleCount = Number(metrics?.sampleCount || 0);
  const winRate = Number(metrics?.winRate || 0);
  const profitFactor = Number(metrics?.profitFactor);
  const sharpe = Number(metrics?.sharpe || 0);
  const drawdown = Math.abs(Number(metrics?.maximumDrawdown || 0));

  if (sampleCount <= 0) return null;

  const sampleWeight = Math.min(1, sampleCount / 30);
  const pf = Number.isFinite(profitFactor) ? Math.min(3, Math.max(0, profitFactor)) : 3;
  return Number((sampleWeight * (winRate * 0.45 + pf * 10 * 0.25 + sharpe * 10 * 0.2 - drawdown * 0.1)).toFixed(3));
}

export function compareHorizonPerformance(records = [], { minimumSamples = 5 } = {}) {
  const resolved = Array.isArray(records)
    ? records.filter((record) => record?.status === 'resolved')
    : [];

  const rows = ARK_HORIZONS.map((horizon) => {
    const items = resolved.filter((record) => normalizedPeriod(record) === horizon);
    const metrics = summarizePerformance(items);
    const score = qualityScore(metrics);
    return {
      horizon,
      sampleCount: Number(metrics.sampleCount || 0),
      winRate: metrics.winRate,
      averageReturn: metrics.averageReturn,
      profitFactor: metrics.profitFactor,
      sharpe: metrics.sharpe,
      maximumDrawdown: metrics.maximumDrawdown,
      qualityScore: score,
      eligible: Number(metrics.sampleCount || 0) >= minimumSamples,
    };
  });

  const eligible = rows
    .filter((row) => row.eligible && row.qualityScore !== null)
    .sort((a, b) => b.qualityScore - a.qualityScore);

  return Object.freeze({
    horizons: rows,
    bestHorizon: eligible[0]?.horizon ?? null,
    bestQualityScore: eligible[0]?.qualityScore ?? null,
    minimumSamples,
    totalResolved: resolved.length,
    status: eligible.length ? 'COMPARABLE' : 'INSUFFICIENT_DATA',
  });
}
