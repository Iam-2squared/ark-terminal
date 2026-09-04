import { buildP25ExitPairedDecisionTrace, PHASE57_EXIT_RESEARCH_TRACE_SAFETY } from './phase57-exit-research-decision-trace.js';

export const PHASE57_EXIT_FAILURE_TAXONOMY_VERSION = '2026-09-05.v1';

const signOf = (direction) => direction === 'LONG' || direction === 'UP' || direction === 1 ? 1 : -1;
const directionalReturnPct = (from, to, sign) => (Number(to) / Number(from) - 1) * 100 * sign;
const finiteOrNull = (value) => Number.isFinite(Number(value)) ? Number(value) : null;

function normalizeBars(rows = []) {
  return rows.map((row) => ({
    timestamp: new Date(Date.parse(row.timestamp ?? row.time)).toISOString(),
    close: Number(row.close),
  })).filter((row) => Number.isFinite(row.close) && row.close > 0)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function postExitWindow({ row, summary, horizonBars, roundTripCostPct }) {
  const exitTimestamp = String(summary?.exitTimestamp ?? '');
  const exitPrice = Number(summary?.exitPrice);
  if (!exitTimestamp || !Number.isFinite(exitPrice) || exitPrice <= 0) return null;

  const sign = signOf(row.signalDirection ?? row.direction);
  const laterBars = normalizeBars(row.futureBars ?? []).filter((bar) => bar.timestamp > exitTimestamp);
  if (laterBars.length < horizonBars) return null;

  const target = laterBars[horizonBars - 1];
  const forwardDirectionalReturnPct = directionalReturnPct(exitPrice, target.close, sign);
  return Object.freeze({
    horizonBars,
    targetTimestamp: target.timestamp,
    forwardDirectionalReturnPct,
    postExitRegretPct: Math.max(0, forwardDirectionalReturnPct - Number(roundTripCostPct)),
    additionalLossAvoidedPct: Math.max(0, -forwardDirectionalReturnPct),
  });
}

function classifyModel({ row, modelTrace, roundTripCostPct, horizons }) {
  const summary = modelTrace.summary;
  const cost = Math.max(0, Number(roundTripCostPct));
  const mfePct = finiteOrNull(summary.mfePct) ?? 0;
  const maePct = finiteOrNull(summary.maePct) ?? 0;
  const grossReturnPct = finiteOrNull(summary.grossReturnPct) ?? 0;
  const netReturnPct = finiteOrNull(summary.netReturnPct) ?? 0;
  const givebackPct = Math.max(0, finiteOrNull(summary.givebackPct) ?? 0);
  const captureRatio = finiteOrNull(summary.captureRatio);
  const windows = horizons.map((horizonBars) => postExitWindow({
    row,
    summary,
    horizonBars,
    roundTripCostPct: cost,
  })).filter(Boolean);

  const flags = [];
  if (mfePct > cost && grossReturnPct <= 0) flags.push('WINNER_FLIPPED_TO_NONPROFIT');
  if (mfePct > 0 && givebackPct > cost) flags.push('MATERIAL_PROFIT_GIVEBACK');
  if (windows.some((window) => window.postExitRegretPct > 0)) flags.push('EARLY_EXIT_REGRET');
  if (netReturnPct < 0 && Math.abs(maePct) > cost) flags.push('LOSS_REALIZED');
  if (windows.some((window) => window.additionalLossAvoidedPct > cost)) flags.push('LOSS_AVOIDED_AFTER_EXIT');
  if (String(summary.exitReason ?? '').toUpperCase().includes('SESSION_END')) flags.push('SESSION_END_FALLBACK');

  return Object.freeze({
    model: modelTrace.model,
    exitTimestamp: summary.exitTimestamp,
    exitReason: summary.exitReason,
    barsHeld: summary.barsHeld,
    grossReturnPct,
    netReturnPct,
    mfePct,
    maePct,
    givebackPct,
    captureRatio,
    postExitWindows: Object.freeze(windows),
    flags: Object.freeze(flags),
  });
}

function pairedDelta(v4, v3) {
  const numberDelta = (key) => {
    const left = finiteOrNull(v4[key]);
    const right = finiteOrNull(v3[key]);
    return left === null || right === null ? null : left - right;
  };
  return Object.freeze({
    netReturnPctV4MinusV3: numberDelta('netReturnPct'),
    grossReturnPctV4MinusV3: numberDelta('grossReturnPct'),
    givebackPctV4MinusV3: numberDelta('givebackPct'),
    captureRatioV4MinusV3: numberDelta('captureRatio'),
    barsHeldV4MinusV3: numberDelta('barsHeld'),
  });
}

export function buildP25ExitFailureTaxonomy({
  row,
  analogPool,
  roundTripCostPct = 0.05,
  evaluationHorizons = [1, 3, 6],
} = {}) {
  const horizons = [...new Set((evaluationHorizons ?? []).map(Number)
    .filter((value) => Number.isInteger(value) && value > 0))].sort((a, b) => a - b);
  if (horizons.length === 0) throw new Error('EXIT failure taxonomy requires at least one positive evaluation horizon');

  const paired = buildP25ExitPairedDecisionTrace({ row, analogPool, roundTripCostPct });
  const v3 = classifyModel({ row, modelTrace: paired.v3, roundTripCostPct, horizons });
  const v4 = classifyModel({ row, modelTrace: paired.v4, roundTripCostPct, horizons });

  return Object.freeze({
    version: PHASE57_EXIT_FAILURE_TAXONOMY_VERSION,
    invariant: paired.invariant,
    diagnosticOnly: true,
    outcomeWindowsNeverUsedByDecisionPolicy: true,
    evaluationHorizons: Object.freeze(horizons),
    v3,
    v4,
    pairedDelta: pairedDelta(v4, v3),
    safety: PHASE57_EXIT_RESEARCH_TRACE_SAFETY,
  });
}

export function aggregateP25ExitFailureTaxonomy(records = []) {
  const rows = records.filter(Boolean);
  const models = ['v3', 'v4'];
  const summary = {};

  for (const model of models) {
    const flags = new Map();
    let netReturnPct = 0;
    let givebackPct = 0;
    let barsHeld = 0;
    let captureNumerator = 0;
    let captureCount = 0;

    for (const row of rows) {
      const diag = row[model];
      if (!diag) continue;
      netReturnPct += Number(diag.netReturnPct ?? 0);
      givebackPct += Number(diag.givebackPct ?? 0);
      barsHeld += Number(diag.barsHeld ?? 0);
      if (Number.isFinite(Number(diag.captureRatio))) {
        captureNumerator += Number(diag.captureRatio);
        captureCount += 1;
      }
      for (const flag of diag.flags ?? []) flags.set(flag, (flags.get(flag) ?? 0) + 1);
    }

    summary[model] = Object.freeze({
      count: rows.length,
      totalNetReturnPct: netReturnPct,
      meanGivebackPct: rows.length ? givebackPct / rows.length : null,
      meanBarsHeld: rows.length ? barsHeld / rows.length : null,
      meanCaptureRatio: captureCount ? captureNumerator / captureCount : null,
      flagCounts: Object.freeze(Object.fromEntries([...flags.entries()].sort(([a], [b]) => a.localeCompare(b)))),
    });
  }

  const deltas = rows.map((row) => row.pairedDelta).filter(Boolean);
  const mean = (key) => {
    const values = deltas.map((row) => finiteOrNull(row[key])).filter((value) => value !== null);
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  };

  return Object.freeze({
    version: PHASE57_EXIT_FAILURE_TAXONOMY_VERSION,
    count: rows.length,
    v3: summary.v3,
    v4: summary.v4,
    meanPairedDelta: Object.freeze({
      netReturnPctV4MinusV3: mean('netReturnPctV4MinusV3'),
      givebackPctV4MinusV3: mean('givebackPctV4MinusV3'),
      captureRatioV4MinusV3: mean('captureRatioV4MinusV3'),
      barsHeldV4MinusV3: mean('barsHeldV4MinusV3'),
    }),
    diagnosticOnly: true,
    safety: PHASE57_EXIT_RESEARCH_TRACE_SAFETY,
  });
}

export default {
  PHASE57_EXIT_FAILURE_TAXONOMY_VERSION,
  buildP25ExitFailureTaxonomy,
  aggregateP25ExitFailureTaxonomy,
};
