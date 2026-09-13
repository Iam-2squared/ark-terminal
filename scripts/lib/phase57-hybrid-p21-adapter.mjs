import { buildProspectiveP21FeatureFeed } from '../../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import { MODEL_DIGEST, FREEZE_DIGEST, SAFETY, sessionOf, timeBucket } from './phase57-hybrid-p21-baseline.mjs';

// Exact policy values from PHASE58_P13_FROZEN_POLICY at the pinned main SHA.
// The parity test pins its source blob and checks this projection. No overrides.
export const P21_OPTIONS = Object.freeze({
  innerTrainFraction: 0.6, innerTestFraction: 0.15, innerMinTrainRows: 200,
  thresholds: Object.freeze([0.55, 0.60, 0.65]), minInnerSignals: 50,
  minimumInnerNetReturnPct: 0, roundTripCostPct: 0.05,
});
export const P21_HORIZONS = Object.freeze([1, 3, 6, 12, 24]);
const ms = value => {
  if (typeof value !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) throw new Error('EXPLICIT_TIMESTAMP_REQUIRED');
  return Date.parse(value);
};
const number = value => typeof value === 'number' && Number.isFinite(value);
const forbidden = new Set(['outcome', 'outcomes', 'outcomeAt', 'label', 'labels', 'futureBars', 'futureReturn', 'actualReturnPct', 'grossReturnPct', 'netReturnPct', 'mfePct', 'maePct', 'realizedReturn', 'hit', 'target']);
function rejectOutcomes(value) {
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    if (forbidden.has(key)) throw new Error('CURRENT_INPUT_HAS_OUTCOME');
    rejectOutcomes(child);
  }
}

/** Input mapping only. Does not load archives, score P21, fit, or calculate labels.
 * Historical callers must pass all admission gates before scoring this input.
 * The legacy P21 featureCutoff is a BAR-OPEN key. Never relabel it as decision T.
 */
export function buildHybridP21Input({ selection, symbol, sessionDate, decisionTimestamp, contextBars, selectorFreezeSHA, sourceClass } = {}) {
  rejectOutcomes(selection); rejectOutcomes(contextBars);
  const t = ms(decisionTimestamp);
  timeBucket(decisionTimestamp);
  if (t % 300000 !== 0 || sessionOf(decisionTimestamp) !== sessionDate) throw new Error('INVALID_DECISION_TIMESTAMP');
  if (sessionDate < '2026-08-13') throw new Error('CURRENT_P21_BEFORE_SAFE_FORWARD_BOUNDARY');
  if (!['HISTORICAL_RECONSTRUCTION_LATER_FETCHED', 'SYNTHETIC_CONTRACT_TEST'].includes(sourceClass)) throw new Error('SOURCE_CLASS_REQUIRED');
  if (selectorFreezeSHA !== FREEZE_DIGEST || selection?.modelDigest !== MODEL_DIGEST) throw new Error('FROZEN_SELECTOR_MISMATCH');
  if (ms(selection.featureCutoff) !== t) throw new Error('SELECTION_DECISION_TIME_MISMATCH');
  if (!/^[0-9A-Z]{4}\.T$/.test(symbol) || !Array.isArray(selection.selected)) throw new Error('INVALID_SELECTED_SYMBOL');
  const selected = selection.selected;
  if (new Set(selected.map(x => x.symbol)).size !== selected.length) throw new Error('DUPLICATE_SELECTED_SYMBOL');
  const candidate = selected.find(x => x.symbol === symbol);
  if (!candidate) throw new Error('NOT_A_HYBRID_SELECTED_EVENT');
  if (!Number.isInteger(candidate.hybridRank) || candidate.hybridRank < 1 || !number(candidate.hybridScore) || !number(candidate.currentPrice) || candidate.currentPrice <= 0) throw new Error('INVALID_HYBRID_LINEAGE');
  if (!Array.isArray(contextBars) || contextBars.length < 6) throw new Error('INSUFFICIENT_COMPLETED_PREFIX');
  let previous = -Infinity;
  const bars5m = contextBars.map(bar => {
    const start = ms(bar.timestamp), available = ms(bar.availableAt);
    if (start <= previous || start % 300000 !== 0) throw new Error('UNSORTED_OR_DUPLICATE_BARS');
    previous = start;
    if (sessionOf(bar.timestamp) !== sessionDate || (bar.symbol != null && bar.symbol !== symbol)) throw new Error('CROSS_SESSION_OR_SYMBOL_BAR');
    if (start + 300000 > t || available < start + 300000 || available > t) throw new Error('BAR_NOT_COMPLETED_AND_AVAILABLE');
    if (!['open', 'high', 'low', 'close', 'volume'].every(k => number(bar[k])) || bar.low <= 0 || bar.volume < 0 || bar.high < Math.max(bar.open, bar.close, bar.low) || bar.low > Math.min(bar.open, bar.close)) throw new Error('INVALID_OHLCV_NO_IMPUTATION');
    return { timestamp: bar.timestamp, open: bar.open, high: bar.high, low: bar.low, close: bar.close, volume: bar.volume };
  });
  if (candidate.currentPrice !== bars5m.at(-1).close) throw new Error('SELECTOR_P21_PRICE_REFERENCE_MISMATCH');
  const feed = buildProspectiveP21FeatureFeed({ symbol, sessionDate, bars5m, horizons: P21_HORIZONS, latestBarClosed: true });
  if (!feed.complete) throw new Error('EXISTING_P21_FEATURE_FEED_BLOCKED');
  return Object.freeze({
    currentRowsByHorizon: feed.currentRowsByHorizon,
    options: P21_OPTIONS,
    lineage: Object.freeze({
      symbol, sessionDate, selectionTimestamp: selection.featureCutoff, decisionTimestamp,
      p21LegacyFeatureCutoff: feed.featureCutoff,
      contextAvailableAt: new Date(Math.max(...contextBars.map(b => ms(b.availableAt)))).toISOString(),
      priceReference: candidate.currentPrice, priceBasis: 'LAST_COMPLETED_5M_CLOSE',
      hybridRank: candidate.hybridRank, hybridScore: candidate.hybridScore, selectionCount: selected.length,
      selectorModelDigest: MODEL_DIGEST, selectorFreezeSHA: FREEZE_DIGEST, sourceClass,
      legacySourceModeIsNotProspectiveEvidence: true,
    }),
    safety: SAFETY,
  });
}
