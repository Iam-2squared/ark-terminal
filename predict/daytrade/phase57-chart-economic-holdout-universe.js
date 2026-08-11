import { EXPANDED_UNIVERSE } from './phase57-expanded-universe.js';
import { CHART_QUALITY_HOLDOUT_UNIVERSE } from './phase57-chart-quality-holdout-universe.js';

export const CHART_ECONOMIC_HOLDOUT_UNIVERSE = Object.freeze([
  '1801.T','1802.T','1803.T','1808.T','1812.T',
  '2269.T','2282.T','2413.T','2587.T','2768.T',
  '3092.T','4188.T','5020.T','5201.T','5332.T',
  '5411.T','6503.T','6504.T','6506.T','6508.T',
  '6701.T','6703.T','6752.T','6753.T','6762.T',
  '6841.T','6857.T','6920.T','6971.T','7012.T',
]);

const prior = new Set([...EXPANDED_UNIVERSE, ...CHART_QUALITY_HOLDOUT_UNIVERSE]);
const overlap = CHART_ECONOMIC_HOLDOUT_UNIVERSE.filter(symbol => prior.has(symbol));
if (overlap.length) throw new Error(`P23.10F economic holdout overlaps prior chart universes: ${overlap.join(',')}`);
if (new Set(CHART_ECONOMIC_HOLDOUT_UNIVERSE).size !== CHART_ECONOMIC_HOLDOUT_UNIVERSE.length) {
  throw new Error('P23.10F economic holdout must contain unique symbols');
}

export const CHART_ECONOMIC_HOLDOUT_POLICY = Object.freeze({
  id: 'JP_LARGE_ACTIVE_ECONOMIC_HOLDOUT_30_V1',
  symbolCount: CHART_ECONOMIC_HOLDOUT_UNIVERSE.length,
  frozenBeforeOutcomeMeasurement: true,
  disjointFromP23_10Development30: true,
  disjointFromP23_10ECrossSymbol30: true,
  selectedFromP23_10EOutcomes: false,
  setupRuleRetuningAllowed: false,
  qualityScoreRetuningAllowed: false,
  q4ThresholdRetuningAllowed: false,
  exitRetuningAllowed: false,
  purpose: 'Confirmatory cross-symbol economic validation of frozen P23.10D Q4 chart quality with the frozen P23.8D ratchet exit.',
  caveat: 'Fresh by symbol only. The recent historical time window can overlap prior development and is not untouched temporal OOS.',
});
