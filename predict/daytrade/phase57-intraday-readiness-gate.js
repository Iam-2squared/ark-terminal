export const PHASE57_P9_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_READINESS_RESEARCH_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
const ratio = (n,d) => d > 0 ? n / d : 0;

function unique(values){ return [...new Set(values.filter(Boolean))]; }

export function assessIntradayResearchReadiness({ rows = [], nestedOos = null, config = {} } = {}) {
  const list = Array.isArray(rows) ? rows : [];
  const valid = list.filter(r => r?.pointInTimeValid !== false && r?.featureCutoff && r?.outcomeAt && Date.parse(r.featureCutoff) < Date.parse(r.outcomeAt));
  const sessions = unique(valid.map(r => r.sessionDate));
  const symbols = unique(valid.map(r => r.symbol));
  const has = key => valid.filter(r => finite(r?.features?.[key])).length;
  const microFields = ['spreadBps','bookImbalance','depthImbalance','aggressiveBuyRatio','tradeIntensity'];
  const microCoverage = Object.fromEntries(microFields.map(k => [k, ratio(has(k), valid.length)]));
  const thresholds = {
    minRows: config.minRows ?? 1000,
    minSessions: config.minSessions ?? 20,
    minSymbols: config.minSymbols ?? 3,
    minMicroCoverage: config.minMicroCoverage ?? 0.8,
    minOuterSignals: config.minOuterSignals ?? 200,
    minOuterFolds: config.minOuterFolds ?? 3,
  };
  const outerSignals = Number(nestedOos?.signalCount ?? nestedOos?.outerSignals ?? 0);
  const outerFolds = Number(nestedOos?.outerFoldCount ?? nestedOos?.foldCount ?? 0);
  const outerUntouched = nestedOos?.selectionIntegrity?.outerTestNeverUsedForSelection === true || nestedOos?.outerTestUntouchedBySelection === true;
  const outerNotFit = nestedOos?.selectionIntegrity?.outerTestNeverUsedForFit === true || nestedOos?.outerTestNeverUsedForFit === true;
  const blockers = [];
  if (valid.length < thresholds.minRows) blockers.push('INSUFFICIENT_POINT_IN_TIME_ROWS');
  if (sessions.length < thresholds.minSessions) blockers.push('INSUFFICIENT_SESSIONS');
  if (symbols.length < thresholds.minSymbols) blockers.push('INSUFFICIENT_SYMBOL_DIVERSITY');
  for (const [k,v] of Object.entries(microCoverage)) if (v < thresholds.minMicroCoverage) blockers.push(`LOW_${k.toUpperCase()}_COVERAGE`);
  if (outerSignals < thresholds.minOuterSignals) blockers.push('INSUFFICIENT_OUTER_SIGNALS');
  if (outerFolds < thresholds.minOuterFolds) blockers.push('INSUFFICIENT_OUTER_FOLDS');
  if (!outerUntouched) blockers.push('OUTER_SELECTION_INTEGRITY_NOT_PROVEN');
  if (!outerNotFit) blockers.push('OUTER_FIT_INTEGRITY_NOT_PROVEN');

  return Object.freeze({
    phase: '57.p9',
    status: blockers.length ? 'INTRADAY_RESEARCH_DATA_NOT_READY' : 'INTRADAY_RESEARCH_EVIDENCE_READY',
    blockers: Object.freeze(blockers),
    counts: Object.freeze({ rows: list.length, pointInTimeRows: valid.length, sessions: sessions.length, symbols: symbols.length, outerSignals, outerFolds }),
    microCoverage: Object.freeze(microCoverage),
    thresholds: Object.freeze(thresholds),
    evidence: Object.freeze({ outerTestUntouchedBySelection: outerUntouched, outerTestNeverUsedForFit: outerNotFit }),
    nextStep: blockers.length ? 'CONTINUE_READ_ONLY_INTRADAY_CAPTURE' : 'RUN_PREDECLARED_REAL_REPLAY_OOS',
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    paperTradingAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    humanApprovalRequired: true,
    safety: PHASE57_P9_SAFETY,
  });
}

export default assessIntradayResearchReadiness;
