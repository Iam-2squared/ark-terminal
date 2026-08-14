export const DIRECTION_SETUP_MANAGEMENT_HOLDOUT_UNIVERSE = Object.freeze([
  '1333.T','1721.T','1911.T','1963.T','2501.T','2503.T','2809.T','3038.T','3064.T','3436.T',
  '4021.T','4042.T','4204.T','4503.T','4528.T','4684.T','4902.T','5101.T','5333.T','5706.T',
  '5711.T','5801.T','5803.T','6113.T','6361.T','6479.T','6586.T','6724.T','6963.T','6988.T',
]);

export const DIRECTION_SETUP_MANAGEMENT_HOLDOUT_POLICY = Object.freeze({
  id: 'JP_LARGE_ACTIVE_DIRECTION_SETUP_HOLDOUT_30_V1',
  symbolCount: DIRECTION_SETUP_MANAGEMENT_HOLDOUT_UNIVERSE.length,
  frozenBeforeOutcomeMeasurement: true,
  disjointFromPrior120ChartSymbols: true,
  selectedFromP23_10HOutcomes: false,
  architectureRetuningAllowedAfterOutcomeRetrieval: false,
  purpose: 'Confirmatory cross-symbol OOS validation of direction-asymmetric setup management.',
  caveat: 'Fresh by symbol only; not untouched temporal OOS.',
});
