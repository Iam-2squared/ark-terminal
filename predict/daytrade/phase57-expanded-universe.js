export const EXPANDED_UNIVERSE = Object.freeze([
  '7203.T','6758.T','9984.T','8306.T','8035.T',
  '6501.T','6861.T','6098.T','9432.T','9433.T',
  '9983.T','4063.T','6367.T','6954.T','7011.T',
  '8058.T','8001.T','8316.T','8411.T','8766.T',
  '7741.T','7974.T','6902.T','7267.T','6594.T',
  '4502.T','4519.T','2914.T','4661.T','6273.T',
]);

export const EXPANDED_UNIVERSE_POLICY = Object.freeze({
  id: 'JP_LARGE_LIQUID_FIXED_30_V1',
  symbolCount: EXPANDED_UNIVERSE.length,
  frozenBeforeMeasurement: true,
  selectedFromP23_6Outcomes: false,
  dynamicWinnerFilteringAllowed: false,
  perSymbolExitTuningAllowed: false,
  rationale: 'Pre-registered fixed basket of widely traded large Japanese equities across multiple sectors; frozen before P23.7 measurement to increase sample size without loosening signal or exit thresholds.',
});
