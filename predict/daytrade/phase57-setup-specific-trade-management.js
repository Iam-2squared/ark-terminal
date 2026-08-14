import {
  PHASE57_P23_8D_SAFETY,
  P23_8D_FROZEN_RATCHET_CONFIG,
  simulateFrozenRatchetExit,
} from './phase57-frozen-ratchet-exit.js';

export const P23_10G_SETUP_MANAGEMENT_POLICY = Object.freeze({
  phase: '57.p23.10g',
  id: 'SETUP_STRUCTURAL_INVALIDATION_OVER_FROZEN_RATCHET_V1',
  architectureRole: 'EXIT_ONLY_PAIRED_RESEARCH',
  baselineExitConfigId: P23_8D_FROZEN_RATCHET_CONFIG.configId,
  breakoutInvalidation: 'SIGNAL_TIME_BREAKOUT_LEVEL_CLOSE_BREACH',
  retestInvalidation: 'SIGNAL_TIME_BREAKOUT_LEVEL_CLOSE_BREACH',
  failedBreakoutInvalidation: 'SIGNAL_TIME_BREAKOUT_LEVEL_CLOSE_BREACH',
  pullbackInvalidation: 'SIGNAL_TIME_SCENARIO_INVALIDATION_CLOSE_BREACH',
  momentumInvalidation: 'SIGNAL_TIME_SCENARIO_INVALIDATION_CLOSE_BREACH',
  noAtrMultiplierSearch: true,
  noOutcomeThresholdSearch: true,
  noDirectionSpecificParameterSearch: true,
  noSetupSpecificNumericParameterSearch: true,
  entrySetMustRemainPairedWithBaseline: true,
  outcomeSelectionAllowed: false,
  recommendationAllowed: false,
  edgeClaimAllowed: false,
});

export const PHASE57_P23_10G_SAFETY = Object.freeze({
  ...PHASE57_P23_8D_SAFETY,
  mode: 'PHASE57_P23_10G_SETUP_SPECIFIC_TRADE_MANAGEMENT_READ_ONLY_RESEARCH',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  transmitted: false,
});

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const mean = values => values.length ? values.reduce((sum, value) => sum + Number(value), 0) / values.length : null;
const clamp = (value, lo, hi) => Math.max(lo, Math.min(hi, Number(value)));

function signFromDirection(direction) {
  if (direction === 1 || direction === 'LONG' || direction === 'UP') return 1;
  if (direction === -1 || direction === 0 || direction === 'SHORT' || direction === 'DOWN') return -1;
  throw new TypeError('direction must be LONG/SHORT, UP/DOWN, or +/-1');
}

function directionalReturnPct(entry, price, sign) {
  return (Number(price) / Number(entry) - 1) * 100 * sign;
}

function sameSessionDate(timestamp) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(timestamp));
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function normalizeBars(rows = []) {
  return (Array.isArray(rows) ? rows : []).map(row => ({
    timestamp: new Date(row.timestamp ?? row.time).toISOString(),
    open: Number(row.open), high: Number(row.high), low: Number(row.low), close: Number(row.close),
    volume: finite(row.volume) ? Number(row.volume) : 0,
  })).filter(row => [row.open,row.high,row.low,row.close].every(Number.isFinite) && row.high >= row.low)
    .sort((a,b) => a.timestamp.localeCompare(b.timestamp));
}

export function deriveSetupInvalidationReference({ setup, perception } = {}) {
  const name = String(setup ?? '');
  const tf5 = perception?.timeframes?.['5m'];
  if (!tf5 || tf5.status !== 'CHART_PERCEPTION_READY') {
    return Object.freeze({ reference: null, source: 'NO_READY_5M_CONTEXT', rule: 'BASELINE_ONLY' });
  }
  if (name.startsWith('BREAKOUT_CONTINUATION_')
    || name.startsWith('RETEST_CONTINUATION_')
    || name.startsWith('FAILED_BREAKOUT_REVERSAL_')) {
    const level = Number(tf5?.breakout?.level);
    return Object.freeze({
      reference: finite(level) ? level : null,
      source: 'SIGNAL_TIME_5M_BREAKOUT_LEVEL',
      rule: 'CLOSE_BREACH_INVALIDATES',
    });
  }
  if (name.startsWith('TREND_PULLBACK_') || name.startsWith('MOMENTUM_CONTINUATION_')) {
    const level = Number(tf5?.scenario?.invalidationReference);
    return Object.freeze({
      reference: finite(level) ? level : null,
      source: 'SIGNAL_TIME_5M_SCENARIO_INVALIDATION',
      rule: 'CLOSE_BREACH_INVALIDATES',
    });
  }
  return Object.freeze({ reference: null, source: 'NO_SETUP_SPECIFIC_REFERENCE', rule: 'BASELINE_ONLY' });
}

export function firstSetupInvalidation({ setup, perception, direction, futureBars = [], sessionDate = null } = {}) {
  const sign = signFromDirection(direction);
  const referenceInfo = deriveSetupInvalidationReference({ setup, perception });
  if (!finite(referenceInfo.reference)) return null;
  const reference = Number(referenceInfo.reference);
  const bars = normalizeBars(futureBars);
  for (let index = 0; index < bars.length; index += 1) {
    const bar = bars[index];
    if (sessionDate && sameSessionDate(bar.timestamp) !== String(sessionDate)) break;
    const breached = sign === 1 ? bar.close < reference : bar.close > reference;
    if (breached) {
      return Object.freeze({
        index,
        timestamp: bar.timestamp,
        close: bar.close,
        reference,
        referenceSource: referenceInfo.source,
        rule: referenceInfo.rule,
        causalCloseOnly: true,
      });
    }
  }
  return null;
}

function summarizeStructuralExit({ entryPrice, direction, path, exitBar, roundTripCostPct, setup, invalidation }) {
  const sign = signFromDirection(direction);
  const observed = normalizeBars(path).filter(bar => bar.timestamp <= exitBar.timestamp);
  const grossReturnPct = directionalReturnPct(entryPrice, exitBar.close, sign);
  const netReturnPct = grossReturnPct - Number(roundTripCostPct || 0);
  const favorable = sign === 1
    ? Math.max(Number(entryPrice), ...observed.map(bar => bar.high))
    : Math.min(Number(entryPrice), ...observed.map(bar => bar.low));
  const adverse = sign === 1
    ? Math.min(Number(entryPrice), ...observed.map(bar => bar.low))
    : Math.max(Number(entryPrice), ...observed.map(bar => bar.high));
  const mfePct = Math.max(0, directionalReturnPct(entryPrice, favorable, sign));
  const maePct = Math.min(0, directionalReturnPct(entryPrice, adverse, sign));
  const giveback = Math.max(0, mfePct - grossReturnPct);
  return Object.freeze({
    phase: '57.p23.10g-setup-specific-management',
    status: 'SETUP_STRUCTURAL_INVALIDATION_EXIT',
    setup,
    direction: sign === 1 ? 'LONG' : 'SHORT',
    entryPrice: Number(entryPrice),
    exitPrice: exitBar.close,
    exitReason: 'SETUP_STRUCTURAL_INVALIDATION',
    outcomeAt: exitBar.timestamp,
    barsHeld: observed.length,
    grossReturnPct,
    netReturnPct,
    mfePct,
    maePct,
    profitGivebackPctPoints: giveback,
    captureRatio: mfePct > 0 ? clamp(grossReturnPct / mfePct, -5, 5) : null,
    structuralInvalidationReference: invalidation.reference,
    structuralInvalidationReferenceSource: invalidation.referenceSource,
    structuralInvalidationObservedAtCompletedClose: true,
    baselineRatchetStillPrimaryUntilStructuralBreach: true,
    futureOutcomeUsedForDecision: false,
    recommendationAllowed: false,
    transmitted: false,
    ...PHASE57_P23_10G_SAFETY,
    safety: PHASE57_P23_10G_SAFETY,
  });
}

export function simulateSetupSpecificManagedExit({
  setup,
  perception,
  entryPrice,
  direction,
  contextBars = [],
  futureBars = [],
  sessionDate = null,
} = {}) {
  const bars = normalizeBars(futureBars);
  if (!bars.length || !finite(entryPrice)) return null;
  const baseline = simulateFrozenRatchetExit({
    entryPrice: Number(entryPrice),
    signalDirection: signFromDirection(direction) === 1 ? 'LONG' : 'SHORT',
    contextBars,
    futureBars: bars,
    frozenEntry: true,
    sessionDate,
  });
  if (!baseline) return null;
  const invalidation = firstSetupInvalidation({ setup, perception, direction, futureBars: bars, sessionDate });
  if (!invalidation || String(baseline.outcomeAt) <= String(invalidation.timestamp)) {
    return Object.freeze({
      ...baseline,
      phase: '57.p23.10g-setup-specific-management',
      managerVariant: 'FROZEN_RATCHET_BASELINE_SURVIVED',
      setup,
      structuralInvalidationReference: invalidation?.reference ?? deriveSetupInvalidationReference({ setup, perception }).reference,
      structuralInvalidationTriggeredBeforeBaseline: false,
      setupSpecificNumericParameterSearchUsed: false,
    });
  }
  const exitBar = bars.find(bar => bar.timestamp === invalidation.timestamp);
  if (!exitBar) throw new Error('structural invalidation bar not found in causal path');
  return Object.freeze({
    ...summarizeStructuralExit({
      entryPrice,
      direction,
      path: bars,
      exitBar,
      roundTripCostPct: P23_8D_FROZEN_RATCHET_CONFIG.roundTripCostPct,
      setup,
      invalidation,
    }),
    managerVariant: 'SETUP_STRUCTURAL_INVALIDATION_EARLIER_THAN_RATCHET',
    structuralInvalidationTriggeredBeforeBaseline: true,
    baselineOutcomeAt: baseline.outcomeAt,
    baselineNetReturnPct: baseline.netReturnPct,
    setupSpecificNumericParameterSearchUsed: false,
  });
}

export function summarizePairedExitDelta(pairs = []) {
  const rows = pairs.filter(row => finite(row?.baseline?.netReturnPct) && finite(row?.managed?.netReturnPct));
  const deltas = rows.map(row => Number(row.managed.netReturnPct) - Number(row.baseline.netReturnPct));
  const improved = deltas.filter(value => value > 0).length;
  const worsened = deltas.filter(value => value < 0).length;
  const structural = rows.filter(row => row.managed.structuralInvalidationTriggeredBeforeBaseline === true).length;
  return Object.freeze({
    pairCount: rows.length,
    averageNetDeltaPctPoints: mean(deltas),
    improvedTradeCount: improved,
    worsenedTradeCount: worsened,
    unchangedTradeCount: rows.length - improved - worsened,
    structuralInvalidationEarlierCount: structural,
    structuralInvalidationEarlierRate: rows.length ? structural / rows.length : null,
  });
}

export default {
  P23_10G_SETUP_MANAGEMENT_POLICY,
  PHASE57_P23_10G_SAFETY,
  deriveSetupInvalidationReference,
  firstSetupInvalidation,
  simulateSetupSpecificManagedExit,
  summarizePairedExitDelta,
};
