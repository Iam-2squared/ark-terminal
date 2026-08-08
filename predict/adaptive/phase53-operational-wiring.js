import { evaluateAdaptiveHorizon } from './phase53-horizon-integration.js';

export const PHASE53_1_SAFETY = Object.freeze({
  mode: 'ADAPTIVE_HORIZON_OPERATIONAL_WIRING_READ_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

export function buildAdaptiveHorizonOperationalView(records = [], options = {}) {
  const gate = evaluateAdaptiveHorizon(records, options);
  const candidate = gate.selectedHorizon ?? gate.candidateHorizon ?? null;

  return Object.freeze({
    phase: 53.1,
    status: gate.status,
    activeForEvaluation: gate.status === 'ADAPTIVE_HORIZON_CANDIDATE',
    selectedHorizon: gate.selectedHorizon,
    candidateHorizon: candidate,
    displayHorizon: candidate,
    blockers: gate.blockers,
    minimumSamples: gate.minimumSamples,
    minimumLead: gate.minimumLead,
    lead: gate.lead,
    eligibleCount: gate.eligibleCount,
    comparison: gate.comparison,
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
    safety: PHASE53_1_SAFETY,
  });
}
