export const CHART_QUALITY_HOLDOUT_UNIVERSE = Object.freeze([
  '1605.T','1925.T','2502.T','2802.T','3382.T',
  '3402.T','3659.T','4307.T','4452.T','4568.T',
  '4901.T','5108.T','5401.T','5713.T','5802.T',
  '6146.T','6178.T','6301.T','6326.T','6702.T',
  '6723.T','6981.T','7182.T','7733.T','7751.T',
  '7832.T','8801.T','9020.T','9101.T','9202.T',
]);

export const CHART_QUALITY_HOLDOUT_POLICY = Object.freeze({
  id: 'JP_LARGE_ACTIVE_CROSS_SYMBOL_HOLDOUT_30_V1',
  symbolCount: CHART_QUALITY_HOLDOUT_UNIVERSE.length,
  frozenBeforeOutcomeMeasurement: true,
  disjointFromP23_10Development30: true,
  selectedFromP23_10Outcomes: false,
  qualityScoreRetuningAllowed: false,
  qualityBandRetuningAllowed: false,
  setupRuleRetuningAllowed: false,
  purpose: 'Cross-symbol OOS validation of the already-frozen P23.10D chart setup quality decomposition.',
  caveat: 'This is fresh by symbol, not by time. It must not be described as untouched temporal OOS.',
});
