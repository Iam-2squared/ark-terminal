export const PHASE56_X_SAFETY = Object.freeze({
  mode: 'CHART_INTELLIGENCE_FINAL_REVIEW_ONLY', executionAllowed: false, brokerWriteAllowed: false,
  excelOrderWriteAllowed: false, rssOrderFunctionAllowed: false, liveTradingAllowed: false,
  paperTradingAllowed: false, automaticPromotionAllowed: false, productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const ok = (value, allowed) => allowed.includes(value);

export function evaluatePhase56Finalization({
  chartStructure, priceAction, setupContext, entryResearch, entryOos, patternContext, patternOos, unknownDiscovery,
} = {}) {
  const blockers = [];
  if (!ok(chartStructure?.status, ['CHART_CONTEXT_READY'])) blockers.push('CHART_STRUCTURE_NOT_READY');
  if (!ok(priceAction?.status, ['PRICE_ACTION_FEATURES_READY'])) blockers.push('PRICE_ACTION_NOT_READY');
  if (!ok(setupContext?.status, ['SETUP_CONTEXT_READY'])) blockers.push('SETUP_CONTEXT_NOT_READY');
  if (!ok(entryResearch?.status, ['ENTRY_RESEARCH_READY','RESEARCH_CANDIDATE_LONG','RESEARCH_CANDIDATE_SHORT','WAIT','AVOID_CONFLICT'])) blockers.push('ENTRY_RESEARCH_NOT_READY');
  if (!ok(entryOos?.status, ['ENTRY_OOS_REVIEW_CANDIDATE','OBSERVE'])) blockers.push('ENTRY_OOS_NOT_EVALUATED');
  if (!ok(patternContext?.status, ['PATTERN_CONTEXT_READY','OBSERVE'])) blockers.push('PATTERN_CONTEXT_NOT_EVALUATED');
  if (!ok(patternOos?.status, ['PATTERN_OOS_EVIDENCE_READY','OBSERVE'])) blockers.push('PATTERN_OOS_NOT_EVALUATED');
  if (!ok(unknownDiscovery?.status, ['UNKNOWN_STRUCTURES_FOUND','OBSERVE'])) blockers.push('UNKNOWN_STRUCTURE_DISCOVERY_NOT_EVALUATED');

  const evidenceReady = entryOos?.status === 'ENTRY_OOS_REVIEW_CANDIDATE' || patternOos?.status === 'PATTERN_OOS_EVIDENCE_READY';
  if (!evidenceReady) blockers.push('NO_OOS_EVIDENCE_CANDIDATE');

  const status = blockers.length ? 'OBSERVE' : 'PHASE56_REVIEW_CANDIDATE';
  return Object.freeze({
    phase: '56.x', status, blockers: Object.freeze([...new Set(blockers)]),
    chartIntelligenceCompleteForResearch: status === 'PHASE56_REVIEW_CANDIDATE',
    nextPhase: '57_DAYTRADING_INTELLIGENCE',
    reviewOnly: true, recommendationAllowed: false, paperTradingAllowed: false,
    executionAllowed: false, brokerWriteAllowed: false, excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false, liveTradingAllowed: false, automaticPromotionAllowed: false,
    productionUpdateAllowed: false, transmitted: false, humanApprovalRequired: true,
    safety: PHASE56_X_SAFETY,
  });
}
