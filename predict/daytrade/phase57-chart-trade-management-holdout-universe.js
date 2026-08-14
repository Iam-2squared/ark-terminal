export const CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE = Object.freeze([
  '1332.T','2002.T','2267.T','2801.T','2871.T',
  '3086.T','3289.T','3626.T','3861.T','4005.T',
  '4091.T','4151.T','4324.T','4523.T','4543.T',
  '4578.T','4689.T','4751.T','4755.T','4911.T',
  '5019.T','5406.T','5631.T','5831.T','5838.T',
  '6471.T','6472.T','6473.T','6645.T','6674.T',
]);

export const CHART_TRADE_MANAGEMENT_HOLDOUT_POLICY = Object.freeze({
  id: 'JP_ACTIVE_SETUP_MANAGEMENT_HOLDOUT_30_V1',
  symbolCount: CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE.length,
  frozenBeforeOutcomeMeasurement: true,
  disjointFromP23_10Development30: true,
  disjointFromP23_10ECrossSymbol30: true,
  disjointFromP23_10FEconomic30: true,
  selectedFromPriorTradeOutcomes: false,
  setupRuleRetuningAllowed: false,
  qualityRuleRetuningAllowed: false,
  exitNumericParameterRetuningAllowed: false,
  purpose: 'Paired cross-symbol OOS comparison of frozen P23.8D ratchet versus pre-registered setup-specific structural invalidation.',
  caveat: 'Fresh by symbol only. This is not untouched temporal OOS.',
});
