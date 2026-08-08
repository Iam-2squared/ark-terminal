import { evaluateAdaptiveHorizonStability } from './phase53-horizon-stability.js';

export const PHASE53_X_SAFETY = Object.freeze({
  mode: 'ADAPTIVE_HORIZON_FINAL_REVIEW_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

export function evaluatePhase53Finalization(records = [], options = {}) {
  const stability = evaluateAdaptiveHorizonStability(records, options);
  const blockers = [...stability.blockers];
  if (stability.status !== 'STABLE_HORIZON_CANDIDATE') blockers.push('STABILITY_NOT_PROVEN');
  if (!Number.isFinite(Number(stability.candidateHorizon))) blockers.push('NO_HORIZON_CANDIDATE');

  const reviewStatus = blockers.length ? 'OBSERVE' : 'REVIEW_CANDIDATE';
  return Object.freeze({
    phase: '53.x',
    reviewStatus,
    candidateHorizon: stability.candidateHorizon,
    stability,
    blockers: [...new Set(blockers)],
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
    safety: PHASE53_X_SAFETY,
  });
}
