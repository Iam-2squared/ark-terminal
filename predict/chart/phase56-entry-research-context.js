import { analyzeChartSetupContext } from './phase56-setup-context.js';

export const PHASE56_3_SAFETY = Object.freeze({
  mode: 'ENTRY_RESEARCH_CONTEXT_READ_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  paperTradingAllowed: false,
  humanApprovalRequired: true,
});

function finite(value) { return Number.isFinite(Number(value)); }
function avg(values = []) {
  const usable = values.filter(finite).map(Number);
  return usable.length ? usable.reduce((sum, value) => sum + value, 0) / usable.length : null;
}

export function analyzeEntryResearchContext({ bars = [], swingRadius = 2, proximityPct = 0.004 } = {}) {
  const setup = analyzeChartSetupContext({ bars, swingRadius, proximityPct });
  if (setup.status !== 'SETUP_CONTEXT_READY') {
    return Object.freeze({
      phase: '56.3', status: 'OBSERVE', posture: 'WAIT', blockers: ['SETUP_CONTEXT_NOT_READY'], setup,
      recommendationAllowed: false, executionAllowed: false, transmitted: false, safety: PHASE56_3_SAFETY,
    });
  }

  const latest = bars.at(-1) || {};
  const close = Number(latest.close);
  const labels = new Set(setup.labels || []);
  const trend = setup.context?.trend || 'UNKNOWN';
  const support = setup.levels?.nearestSupport?.price;
  const resistance = setup.levels?.nearestResistance?.price;
  const vwap = setup.levels?.vwap;
  const priorHigh = setup.levels?.priorHigh;
  const priorLow = setup.levels?.priorLow;

  const bullishEvidence = [
    trend === 'UPTREND',
    labels.has('RETEST_HOLD_ABOVE'),
    labels.has('UPTREND_PULLBACK_CONTEXT'),
    labels.has('BREAKOUT_ABOVE_LOOKBACK'),
  ].filter(Boolean).length;
  const bearishEvidence = [
    trend === 'DOWNTREND',
    labels.has('RETEST_HOLD_BELOW'),
    labels.has('DOWNTREND_PULLBACK_CONTEXT'),
    labels.has('BREAKDOWN_BELOW_LOOKBACK'),
  ].filter(Boolean).length;

  let posture = 'WAIT';
  if (bullishEvidence >= 2 && bearishEvidence === 0) posture = 'RESEARCH_CANDIDATE_LONG';
  if (bearishEvidence >= 2 && bullishEvidence === 0) posture = 'RESEARCH_CANDIDATE_SHORT';
  if (bullishEvidence > 0 && bearishEvidence > 0) posture = 'AVOID_CONFLICT';

  const longReferences = [support, labels.has('RETEST_HOLD_ABOVE') ? priorHigh : null, labels.has('NEAR_VWAP') ? vwap : null];
  const shortReferences = [resistance, labels.has('RETEST_HOLD_BELOW') ? priorLow : null, labels.has('NEAR_VWAP') ? vwap : null];
  const center = posture === 'RESEARCH_CANDIDATE_LONG'
    ? avg(longReferences)
    : posture === 'RESEARCH_CANDIDATE_SHORT'
      ? avg(shortReferences)
      : null;
  const halfWidth = finite(center) ? Math.abs(Number(center)) * proximityPct : null;
  const researchZone = finite(center)
    ? Object.freeze({ lower: Number(center) - halfWidth, center: Number(center), upper: Number(center) + halfWidth })
    : null;

  const invalidationReference = posture === 'RESEARCH_CANDIDATE_LONG'
    ? (finite(priorLow) ? Number(priorLow) : finite(support) ? Number(support) : null)
    : posture === 'RESEARCH_CANDIDATE_SHORT'
      ? (finite(priorHigh) ? Number(priorHigh) : finite(resistance) ? Number(resistance) : null)
      : null;

  return Object.freeze({
    phase: '56.3', status: 'ENTRY_RESEARCH_CONTEXT_READY', posture,
    bullishEvidence, bearishEvidence, currentPrice: finite(close) ? close : null,
    researchZone, invalidationReference, setup,
    researchOnly: true, recommendationAllowed: false, reviewOnly: true,
    executionAllowed: false, brokerWriteAllowed: false, excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false, liveTradingAllowed: false, automaticPromotionAllowed: false,
    productionUpdateAllowed: false, paperTradingAllowed: false, transmitted: false,
    humanApprovalRequired: true, safety: PHASE56_3_SAFETY,
  });
}
