import { evaluateSelectiveSignal } from './phase56-selective-signal.js';
import { regimeSignalPolicy } from './phase56-regime-horizon.js';

export const PHASE56_FUSION_SAFETY = Object.freeze({
  mode: 'OOS_ADAPTIVE_FUSION_RESEARCH_ONLY',
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

function finite(v){ return Number.isFinite(Number(v)); }
function directionName(signal){ return signal === 1 ? 'BULLISH' : signal === -1 ? 'BEARISH' : 'NEUTRAL'; }
function patternEvidencePass({patternOosEvidence=[], symbol, timeframe, regime, horizon, signal}={}){
  const direction = directionName(signal);
  return patternOosEvidence.some(e =>
    e?.status === 'OOS_EDGE_CANDIDATE' &&
    (!symbol || !e.market || e.market === symbol || e.market === 'JP') &&
    (!timeframe || e.timeframe === timeframe || e.timeframe === 'UNKNOWN') &&
    (!regime || e.regime === regime || e.regime === 'UNKNOWN') &&
    (!horizon || String(e.horizon) === String(horizon) || e.horizon === 'UNKNOWN') &&
    (!e.direction || e.direction === direction)
  );
}

export function evaluateOosAdaptiveFusion({
  bars = [], horizon = 1, minimumScore = 5, minimumMargin = 2,
  patternOosEvidence = [], symbol = null, timeframe = '1d', requirePatternEvidence = false,
} = {}) {
  const base = evaluateSelectiveSignal({ bars, minimumScore, minimumMargin });
  if (base.signal !== 1 && base.signal !== -1) {
    return Object.freeze({ phase:'56.precision.fusion', status:'ABSTAIN', signal:0, reason:'BASE_SIGNAL_ABSTAIN', base, reviewOnly:true, recommendationAllowed:false, paperTradingAllowed:false, executionAllowed:false, transmitted:false, safety:PHASE56_FUSION_SAFETY });
  }

  const regime = regimeSignalPolicy({ bars, horizon, baseSignal: base.signal });
  if (!regime.allow) {
    return Object.freeze({ phase:'56.precision.fusion', status:'ABSTAIN', signal:0, reason:'REGIME_BLOCK', base, regime, reviewOnly:true, recommendationAllowed:false, paperTradingAllowed:false, executionAllowed:false, transmitted:false, safety:PHASE56_FUSION_SAFETY });
  }

  const evidencePass = patternEvidencePass({ patternOosEvidence, symbol, timeframe, regime: regime.regime, horizon, signal: base.signal });
  if (requirePatternEvidence && !evidencePass) {
    return Object.freeze({ phase:'56.precision.fusion', status:'ABSTAIN', signal:0, reason:'PATTERN_OOS_EVIDENCE_MISSING', base, regime, evidencePass:false, reviewOnly:true, recommendationAllowed:false, paperTradingAllowed:false, executionAllowed:false, transmitted:false, safety:PHASE56_FUSION_SAFETY });
  }

  const weightedScore = Math.max(Number(base.longScore)||0, Number(base.shortScore)||0) * (finite(regime.weight) ? Number(regime.weight) : 1);
  return Object.freeze({
    phase:'56.precision.fusion', status:'FUSION_REVIEW_CANDIDATE', signal:base.signal,
    direction:directionName(base.signal), horizon, regime:regime.regime, regimeWeight:regime.weight,
    weightedScore, evidencePass, base,
    reviewOnly:true, recommendationAllowed:false, paperTradingAllowed:false,
    executionAllowed:false, brokerWriteAllowed:false, excelOrderWriteAllowed:false,
    rssOrderFunctionAllowed:false, liveTradingAllowed:false, automaticPromotionAllowed:false,
    productionUpdateAllowed:false, transmitted:false, humanApprovalRequired:true,
    safety:PHASE56_FUSION_SAFETY,
  });
}
