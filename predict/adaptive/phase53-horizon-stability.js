import { compareHorizonPerformance } from '../analysis/horizon-performance.js';

export const PHASE53_2_SAFETY = Object.freeze({
  mode: 'ADAPTIVE_HORIZON_STABILITY_REVIEW_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function timestamp(record) {
  const value = record?.resolvedAt || record?.createdAt || record?.analysisTime;
  const parsed = value == null ? NaN : new Date(value).getTime();
  return Number.isFinite(parsed) ? parsed : 0;
}

function integer(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.max(1, Math.floor(number)) : fallback;
}

export function evaluateAdaptiveHorizonStability(records = [], {
  windowSize = 30,
  minimumSamples = 5,
  minimumComparableWindows = 3,
  minimumDominance = 0.6,
  maximumSwitches = 2,
} = {}) {
  const ordered = (Array.isArray(records) ? records : [])
    .filter((record) => record?.status === 'resolved')
    .sort((a, b) => timestamp(a) - timestamp(b));

  const size = integer(windowSize, 30);
  const windows = [];
  for (let start = 0; start + size <= ordered.length; start += size) {
    const slice = ordered.slice(start, start + size);
    const comparison = compareHorizonPerformance(slice, { minimumSamples });
    windows.push(Object.freeze({
      index: windows.length,
      start,
      end: start + slice.length - 1,
      sampleCount: slice.length,
      status: comparison.status,
      bestHorizon: comparison.bestHorizon,
      bestQualityScore: comparison.bestQualityScore,
      comparison,
    }));
  }

  const comparable = windows.filter((window) =>
    window.status === 'COMPARABLE' && Number.isFinite(Number(window.bestHorizon)),
  );
  const counts = new Map();
  comparable.forEach((window) => {
    const horizon = Number(window.bestHorizon);
    counts.set(horizon, (counts.get(horizon) || 0) + 1);
  });
  const ranked = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0]);
  const dominantHorizon = ranked[0]?.[0] ?? null;
  const dominantCount = ranked[0]?.[1] ?? 0;
  const dominance = comparable.length ? dominantCount / comparable.length : 0;

  let switches = 0;
  for (let index = 1; index < comparable.length; index += 1) {
    if (comparable[index].bestHorizon !== comparable[index - 1].bestHorizon) switches += 1;
  }

  const blockers = [];
  if (comparable.length < minimumComparableWindows) blockers.push('INSUFFICIENT_STABILITY_WINDOWS');
  if (comparable.length >= minimumComparableWindows && dominance < minimumDominance) blockers.push('HORIZON_DOMINANCE_TOO_LOW');
  if (comparable.length >= minimumComparableWindows && switches > maximumSwitches) blockers.push('HORIZON_SWITCHING_TOO_HIGH');

  const status = blockers.length ? 'OBSERVE' : 'STABLE_HORIZON_CANDIDATE';

  return Object.freeze({
    phase: 53.2,
    status,
    dominantHorizon: status === 'STABLE_HORIZON_CANDIDATE' ? dominantHorizon : null,
    candidateHorizon: dominantHorizon,
    dominance,
    switches,
    comparableWindowCount: comparable.length,
    totalWindowCount: windows.length,
    minimumComparableWindows,
    minimumDominance,
    maximumSwitches,
    windowSize: size,
    minimumSamples,
    blockers,
    windows,
    reviewOnly: true,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    transmitted: false,
    safety: PHASE53_2_SAFETY,
  });
}
