import { evaluateNetExpectancyEvidence } from './phase57-net-expectancy-objective.js';

export const PHASE57_P21_4_REAL_SAFETY = Object.freeze({
  mode: 'PHASE57_REAL_NET_EXPECTANCY_OOS_EVALUATION_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  oosSelectionAllowed: false,
  candidateRankingAllowed: false,
  humanApprovalRequired: true,
});

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));

function requireReplayIntegrity(replay) {
  if (!replay || !Array.isArray(replay.signals)) throw new TypeError('replayResult.signals is required');
  const integrity = replay.selectionIntegrity ?? {};
  for (const key of [
    'horizonSelectedOnInnerOnly',
    'featureFamilySelectedOnInnerOnly',
    'modelFamilySelectedOnInnerOnly',
    'thresholdSelectedOnInnerOnly',
    'outerTestNeverUsedForSelection',
    'outerTestNeverUsedForFit',
    'sameSessionOnly',
    'overnightHoldingForbidden',
  ]) {
    if (integrity[key] !== true) throw new Error(`P21.4 refuses replay without integrity flag: ${key}`);
  }
  if (replay.reconciliation && replay.reconciliation.matches !== true) throw new Error('P21.4 refuses unreconciled adaptive OOS replay');
}

function normalizeReplayObservation(signal, index) {
  if (!finite(signal?.netReturnPct)) return null;
  return Object.freeze({
    id: `${signal?.symbol ?? 'UNKNOWN'}|${signal?.sessionDate ?? ''}|${signal?.featureCutoff ?? index}|${signal?.baseOuterFold ?? ''}`,
    symbol: signal?.symbol ?? 'UNKNOWN',
    fold: signal?.baseOuterFold ?? null,
    featureCutoff: signal?.featureCutoff ?? null,
    netReturnPct: Number(signal.netReturnPct),
    probability: finite(signal?.probability) ? Number(signal.probability) : null,
    label: finite(signal?.label) ? Number(signal.label) : null,
    barsHeld: finite(signal?.horizonBars) ? Number(signal.horizonBars) : null,
  });
}

export function evaluateRealNetExpectancyOos({
  scope = 'COMBINED',
  replayResult,
  researchRowCount = null,
  evidenceOptions = {},
} = {}) {
  requireReplayIntegrity(replayResult);
  const observations = replayResult.signals.map(normalizeReplayObservation).filter(Boolean);
  if (observations.length !== replayResult.signals.length) throw new Error('P21.4 refuses replay signals without finite net return');
  const uniqueSymbols = [...new Set(observations.map(row => row.symbol))];
  const combined = scope === 'COMBINED' || uniqueSymbols.length > 1;
  const gate = evaluateNetExpectancyEvidence(observations, {
    researchRowCount: finite(researchRowCount) ? Number(researchRowCount) : Number(replayResult.commonRowCount ?? 0),
    minSignals: 100,
    minimumNetAverageReturnPct: 0,
    minimumLowerConfidenceBoundPct: 0,
    minimumProfitFactor: 1.2,
    maximumDrawdownPct: 10,
    minimumFoldGroups: 3,
    minimumPositiveFoldFraction: 0.6,
    requireCrossSymbolStability: combined,
    minimumSymbolGroups: combined ? 3 : 1,
    minimumPositiveSymbolFraction: combined ? 0.6 : 0,
    maximumSingleSymbolShare: combined ? 0.6 : 1,
    bootstrap: { iterations: 4000, confidence: 0.95, seed: 57214 },
    ...evidenceOptions,
  });
  const replayDirectionalHitRate = finite(replayResult.hitRate) ? Number(replayResult.hitRate) : null;
  const replayNetAverageReturnPct = finite(replayResult.netAverageReturnPct) ? Number(replayResult.netAverageReturnPct) : null;
  const netMatchesReplay = replayNetAverageReturnPct === null || gate.metrics.netAverageReturnPct === null
    ? replayNetAverageReturnPct === gate.metrics.netAverageReturnPct
    : Math.abs(replayNetAverageReturnPct - gate.metrics.netAverageReturnPct) <= 1e-10;
  if (!netMatchesReplay) throw new Error('P21.4 normalized Net Expectancy does not reconcile with replay summary');

  return Object.freeze({
    phase: '57.p21.4-real',
    status: gate.status,
    scope,
    sourceSignalSet: 'P21_1_NESTED_ADAPTIVE_OUTER_OOS_REPLAY',
    sourceSignalCount: observations.length,
    sourceCommonRowCount: Number(replayResult.commonRowCount ?? 0),
    sourceOuterFoldCount: Number(replayResult.outerFoldCount ?? 0),
    sourceDirectionalHitRate: replayDirectionalHitRate,
    sourceNetAverageReturnPct: replayNetAverageReturnPct,
    evidence: gate,
    diagnosticsOnly: true,
    noPostOosSelection: true,
    candidateRankingAllowed: false,
    recommendationAllowed: false,
    oosSelectionAllowed: false,
    paperTradingAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    safety: PHASE57_P21_4_REAL_SAFETY,
  });
}

export default { evaluateRealNetExpectancyOos };
