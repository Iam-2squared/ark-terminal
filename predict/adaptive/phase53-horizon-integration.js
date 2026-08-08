import { compareHorizonPerformance } from '../analysis/horizon-performance.js';

export const PHASE53_HORIZON_SAFETY = Object.freeze({
  mode: 'ADAPTIVE_HORIZON_REVIEW_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function integer(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.floor(n) : fallback;
}

export function evaluateAdaptiveHorizon(records = [], {
  minimumSamples = 10,
  minimumLead = 0.25,
} = {}) {
  const comparison = compareHorizonPerformance(records, { minimumSamples });
  const eligible = comparison.horizons
    .filter((row) => row.eligible && Number.isFinite(row.qualityScore))
    .sort((a, b) => b.qualityScore - a.qualityScore);

  const best = eligible[0] || null;
  const second = eligible[1] || null;
  const lead = best && second ? best.qualityScore - second.qualityScore : null;
  const blockers = [];

  if (comparison.status !== 'COMPARABLE' || !best) blockers.push('INSUFFICIENT_HORIZON_OOS');
  if (best && second && lead < minimumLead) blockers.push('HORIZON_LEAD_TOO_SMALL');

  const status = blockers.length ? 'OBSERVE' : 'ADAPTIVE_HORIZON_CANDIDATE';

  return Object.freeze({
    phase: 53.0,
    status,
    selectedHorizon: blockers.length ? null : best?.horizon ?? null,
    candidateHorizon: best?.horizon ?? null,
    bestQualityScore: best?.qualityScore ?? null,
    secondBestQualityScore: second?.qualityScore ?? null,
    lead,
    eligibleCount: eligible.length,
    minimumSamples: Math.max(1, integer(minimumSamples, 10)),
    minimumLead,
    blockers,
    comparison,
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
    safety: PHASE53_HORIZON_SAFETY,
  });
}
