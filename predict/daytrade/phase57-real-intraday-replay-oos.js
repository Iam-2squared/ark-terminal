import { assessIntradayResearchReadiness } from './phase57-intraday-readiness-gate.js';
import { evaluateNestedIntradayModelFamily } from './phase57-intraday-model-family.js';

export const PHASE57_P10_SAFETY = Object.freeze({
  mode: 'PHASE57_REAL_INTRADAY_REPLAY_OOS_RESEARCH_ONLY',
  executionAllowed: false, brokerWriteAllowed: false, excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false, liveTradingAllowed: false, paperTradingAllowed: false,
  automaticPromotionAllowed: false, productionUpdateAllowed: false, humanApprovalRequired: true,
});

export const DEFAULT_P10_PROTOCOL = Object.freeze({
  protocolId: 'PHASE57_P10_V1',
  trainFraction: 0.60,
  testFraction: 0.10,
  minTrainRows: 200,
  innerTrainFraction: 0.60,
  innerTestFraction: 0.15,
  innerMinTrainRows: 100,
  thresholds: Object.freeze([0.55, 0.60, 0.65]),
  minInnerSignals: 20,
  feePercent: 0,
  slippagePercent: 0.05,
  delayCostPercent: 0,
});

export function runPredeclaredRealIntradayReplayOos(rows = [], options = {}) {
  const protocol = Object.freeze({ ...DEFAULT_P10_PROTOCOL, ...(options.protocol ?? {}) });
  const nestedOos = evaluateNestedIntradayModelFamily(rows, protocol);
  const readiness = assessIntradayResearchReadiness({ rows, nestedOos, config: options.readiness });
  const allowed = readiness.status === 'INTRADAY_RESEARCH_EVIDENCE_READY';
  return Object.freeze({
    phase: '57.p10',
    status: allowed ? 'REAL_INTRADAY_REPLAY_OOS_MEASURED' : 'REAL_INTRADAY_REPLAY_OOS_BLOCKED_BY_READINESS',
    protocol,
    readiness,
    nestedOos: allowed ? nestedOos : null,
    observed: allowed ? Object.freeze({
      signalCount: nestedOos.signalCount,
      hitRate: nestedOos.hitRate,
      netAverageReturn: nestedOos.netAverageReturn,
      outerFoldCount: nestedOos.outerResults?.length ?? 0,
    }) : null,
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
    safety: PHASE57_P10_SAFETY,
  });
}

export default runPredeclaredRealIntradayReplayOos;
