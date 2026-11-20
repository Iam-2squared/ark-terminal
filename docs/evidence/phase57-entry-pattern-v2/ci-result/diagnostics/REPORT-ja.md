# Entry Pattern v2 — report supplement

Selection-fixed primary: `RIDGE_FULL_QUALITY_1m`. No refit or evaluation winner selection.

## Pattern sample / good-bad anatomy

| Split | Samples | Complete30 | Good | Bad |
|---|---:|---:|---:|---:|
| evaluation | 65312 | 34213 | 5139 | 20663 |
| fit | 60253 | 26471 | 3494 | 16895 |
| selection | 24335 | 9257 | 1369 | 5478 |

Good: complete30, return>0, MFE>=2%, MAE>−1%. Bad: observed return<0 or MAE<=−2%. Fixed before training; labels are anatomy only, not decision features.

## Full1m coverage

- previous: {'MISSING': 1406, 'PARTIAL_OBSERVED': 155790, 'FULL_SLOTS': 3412}
- today: {'PARTIAL_OBSERVED': 149860, 'FULL_SLOTS': 10748}

FULL_SLOTS means every expected continuous-minute slot is present; PARTIAL_OBSERVED is preserved without interpolation. Source record absence is not proof of no trade.

## Cadence-matched retry comparison

| Cadence | BUY model / baseline | +3 Capture model / baseline | +3 delta pp | +5 delta pp | Model decision evaluations |
|---|---:|---:|---:|---:|---:|
| 1m | 1020 / 1963 | 40.736 / 85.283 | -44.547 | -45.588 | 40003 |
| 5m | 784 / 1802 | 32.326 / 79.763 | -47.438 | -49.510 | 10690 |

## Proposal noise / fresh-turning outcome proxy

Adjacent model BUY/WAIT proposal flips are measured only until actual BUY or expiry, on available quotes. Fresh turning = STRUCT/turningUp=1 and swingAge=0. Nonpositive return30 after that BUY is a descriptive adverse-outcome proxy, not an objective false-pattern label.

- {'cadence': 1, 'turnFeaturesAvailable': True, 'proposalAdjacentPairsUntilEntryOrExpiry': 30418, 'proposalFlips': 837, 'flipPct': 2.75166020119666, 'BUYAtFreshConfirmedSwingLow': 76, 'nonpositiveReturn30AfterFreshSwingLowBUY': 35, 'unknownReturn30AfterFreshSwingLowBUY': 9}
- {'cadence': 5, 'turnFeaturesAvailable': True, 'proposalAdjacentPairsUntilEntryOrExpiry': 6880, 'proposalFlips': 504, 'flipPct': 7.325581395348837, 'BUYAtFreshConfirmedSwingLow': 108, 'nonpositiveReturn30AfterFreshSwingLowBUY': 49, 'unknownReturn30AfterFreshSwingLowBUY': 20}

## Selected-model attribution

Training-only coefficients/gains. Correlated features and availability masks prevent a causal interpretation.

- {'absoluteBuyUtilityWeight': 3.336357341004925, 'feature': 'PREV_AM/value'}
- {'absoluteBuyUtilityWeight': 3.234237510114379, 'feature': 'RECENT/position_low'}
- {'absoluteBuyUtilityWeight': 3.2342375101137217, 'feature': 'SIGNAL/PDLdistance'}
- {'absoluteBuyUtilityWeight': 3.206237622949296, 'feature': 'RECENT/position_close'}
- {'absoluteBuyUtilityWeight': 2.982693815375348, 'feature': 'PREV/lower'}
- {'absoluteBuyUtilityWeight': 2.7216122546381367, 'feature': 'RECENT/lower_wick'}
- {'absoluteBuyUtilityWeight': 2.290967738511995, 'feature': 'PREV_AM/volume'}
- {'absoluteBuyUtilityWeight': 1.9869465892880815, 'feature': 'PREV_PM/body'}
- {'absoluteBuyUtilityWeight': 1.8804608274716685, 'feature': 'LOCAL60/return'}
- {'absoluteBuyUtilityWeight': 1.8719736452312035, 'feature': 'PREV/value'}
- {'absoluteBuyUtilityWeight': 1.822958372231698, 'feature': 'LOCAL30/timeHigh'}
- {'absoluteBuyUtilityWeight': 1.7963060644860036, 'feature': 'LOCAL60/timeHigh'}
- {'absoluteBuyUtilityWeight': 1.7280193015518783, 'feature': 'PREV_PM/return'}
- {'absoluteBuyUtilityWeight': 1.7209192690774362, 'feature': 'RECENT/body'}
- {'absoluteBuyUtilityWeight': 1.672884465689499, 'feature': 'PREV_PM/volume'}

No formal event-level false-turning precision is claimed: turning state persists, so a negative-return BUY is a bad-BUY diagnostic, not proof that a newly detected turning signal was false.
