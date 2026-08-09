import { runPredeclaredRealIntradayReplayOos } from './phase57-real-intraday-replay-oos.js';

export const PHASE57_P19_SAFETY = Object.freeze({
  mode: 'PHASE57_P19_REAL_CAPTURE_REPLAY_OOS_RESEARCH_ONLY',
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

function validRealRow(row) {
  return row?.sourceMode === 'MARKETSPEED_II_RSS_READ_ONLY'
    && row?.pointInTimeValid === true
    && Number.isFinite(Number(row?.label))
    && row?.featureCutoff
    && row?.outcomeAt
    && new Date(row.featureCutoff).getTime() < new Date(row.outcomeAt).getTime();
}

export function runRealCaptureReplayOos(datasetArtifact = {}, options = {}) {
  const rows = Array.isArray(datasetArtifact?.rows) ? datasetArtifact.rows.filter(validRealRow) : [];
  const sourceOk = datasetArtifact?.syntheticDataUsed === false
    && datasetArtifact?.futureUsedForFeatures === false
    && datasetArtifact?.futureUsedOnlyForLabels === true;

  if (!sourceOk) {
    return Object.freeze({
      phase: '57.p19',
      status: 'REAL_CAPTURE_REPLAY_BLOCKED_BY_SOURCE_INTEGRITY',
      rowCount: rows.length,
      blockers: Object.freeze(['REAL_SOURCE_INTEGRITY_NOT_PROVEN']),
      nestedReplay: null,
      edgeClaimAllowed: false,
      recommendationAllowed: false,
      executionAllowed: false,
      brokerWriteAllowed: false,
      excelOrderWriteAllowed: false,
      rssOrderFunctionAllowed: false,
      liveTradingAllowed: false,
      paperTradingAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      transmitted: false,
      safety: PHASE57_P19_SAFETY,
    });
  }

  const nestedReplay = runPredeclaredRealIntradayReplayOos(rows, options);
  const measured = nestedReplay.status === 'REAL_INTRADAY_REPLAY_OOS_MEASURED';
  return Object.freeze({
    phase: '57.p19',
    status: measured ? 'REAL_CAPTURE_REPLAY_OOS_MEASURED' : 'REAL_CAPTURE_REPLAY_OOS_BLOCKED_BY_READINESS',
    rowCount: rows.length,
    sourceMode: 'MARKETSPEED_II_RSS_READ_ONLY',
    syntheticDataUsed: false,
    pointInTimeIntegrityRequired: true,
    nestedReplay,
    observed: measured ? nestedReplay.observed : null,
    nextStep: measured ? 'ANALYZE_PREDECLARED_REAL_OOS_ONLY' : 'CONTINUE_READ_ONLY_INTRADAY_CAPTURE',
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    safety: PHASE57_P19_SAFETY,
  });
}

export default runRealCaptureReplayOos;
