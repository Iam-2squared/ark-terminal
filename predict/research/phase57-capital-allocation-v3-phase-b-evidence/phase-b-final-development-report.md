# Phase57 Capital Allocation Phase B - Historical Integrated Development

Status: **COMPLETE - DEVELOPMENT ONLY, NOT VALIDATION OR PROMOTION**

## Fixed accounting contract

- Initial capital: JPY 1,000,000 (existing Lane C source default)
- Base profile: MAX_10; maximum 10 concurrent positions
- Lot: 100 shares; 0.05% round-trip cost; baseline slippage 0
- Order: price update -> EXIT -> cash release -> Entry -> mark-to-market
- SHORT: fully cash collateralized; proceeds never become reusable buying power
- V3 set budget bridge (explicit Development assumption): current equity / 10 x candidate count, capped by open slots; policy weights divide that same timestamp budget
- Adaptive v2: INCOMPATIBLE_INPUT_SCHEMA / NOT_MEASURED

## Parity and PIT gates

- A: 51/51 exact per-trade net/classification parity; net 72.529078066275 pt
- B: 34/34 exact per-trade net/classification parity; net 29.920959194621 pt
- MSH replay: 91 total First ENTER, 85 exact eligible joins; threshold strictly > 0.60
- Risk: exact last seven completed closes at decision time -> six log returns -> population SD
- Future bars after bar5 read by adapter: false

## Six-arm portfolio comparison

All arms start with JPY 1,000,000. Realized PnL equals final Net PnL and unrealized PnL is zero because all accepted intraday positions close.

| Arm | Final equity JPY | Net PnL JPY | Return % | Realized / unrealized JPY | PF | MaxDD % | Worst day | Accepted / candidates | Win % | Avg PnL JPY | Median PnL JPY | Avg hold min | Max pos | Avg / max util % | Cash / limit / below-lot skips |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V3_0_EQUAL__FROZEN_EXIT_V4 | 1,058,638.605 | 58,638.605 | 5.864 | 58,638.605 / 0 | 4.408261 | 2.225 | 2026-06-24 -0.055% | 29/85 | 48.28 | 2,022.021 | -37 | 201.4 | 2 | 3.62 / 19.72 | 1 / 0 / 55 |
| V3_0_EQUAL__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 1,058,638.605 | 58,638.605 | 5.864 | 58,638.605 / 0 | 4.408261 | 2.225 | 2026-06-24 -0.055% | 29/85 | 48.28 | 2,022.021 | -37 | 201.4 | 2 | 3.62 / 19.72 | 1 / 0 / 55 |
| V3_A_RANK__FROZEN_EXIT_V4 | 1,051,084.205 | 51,084.205 | 5.108 | 51,084.205 / 0 | 3.969521 | 2.356 | 2026-06-29 -0.181% | 29/85 | 48.28 | 1,761.524 | -37 | 201.4 | 2 | 3.47 / 19.77 | 1 / 0 / 55 |
| V3_A_RANK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 1,051,084.205 | 51,084.205 | 5.108 | 51,084.205 / 0 | 3.969521 | 2.356 | 2026-06-29 -0.181% | 29/85 | 48.28 | 1,761.524 | -37 | 201.4 | 2 | 3.47 / 19.77 | 1 / 0 / 55 |
| V3_B_RISK__FROZEN_EXIT_V4 | 1,065,637.505 | 65,637.505 | 6.564 | 65,637.505 / 0 | 5.188792 | 2.096 | 2026-06-24 -0.055% | 28/85 | 50.00 | 2,344.197 | 356.8 | 207.9 | 2 | 3.73 / 22.24 | 1 / 0 / 56 |
| V3_B_RISK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 1,065,637.505 | 65,637.505 | 6.564 | 65,637.505 / 0 | 5.188792 | 2.096 | 2026-06-24 -0.055% | 28/85 | 50.00 | 2,344.197 | 356.8 | 207.9 | 2 | 3.73 / 22.24 | 1 / 0 / 56 |

The v4 and v5 cash-ledger arms are identical because none of the 11 bar5-defensive trades passed the fixed MAX_10/100-share execution gate in any arm. Therefore v5 released no capital from an actually held position and added no subsequent trade. The dominant rejection is target budget below one 100-share lot (55 Equal/Rank, 56 Risk), so this exposed result is highly sensitive to the already-fixed lot/profile feasibility and must not be interpreted as evidence that the two EXIT policies are generally equivalent.

## Exposure and concentration

| Arm | Avg / max gross JPY | Avg / max abs net JPY | LONG / SHORT capital % | Top symbol | Top3 symbol share | Top1 positive profit | Top3 positive profit share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V3_0_EQUAL__FROZEN_EXIT_V4 | 37,195.419 / 198,900 | -27,400.336 / 198,900 | 11.04 / 88.96 | 8918.T 26.70% | 46.94% | 8918.T 36.57% | 57.88% |
| V3_0_EQUAL__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 37,195.419 / 198,900 | -27,400.336 / 198,900 | 11.04 / 88.96 | 8918.T 26.70% | 46.94% | 8918.T 36.57% | 57.88% |
| V3_A_RANK__FROZEN_EXIT_V4 | 35,482.78 / 198,900 | -25,702.656 / 198,900 | 11.40 / 88.60 | 8918.T 27.48% | 48.35% | 8918.T 40.34% | 58.96% |
| V3_A_RANK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 35,482.78 / 198,900 | -25,702.656 / 198,900 | 11.40 / 88.60 | 8918.T 27.48% | 48.35% | 8918.T 40.34% | 58.96% |
| V3_B_RISK__FROZEN_EXIT_V4 | 38,476.79 / 224,300 | -28,621.181 / 224,300 | 11.11 / 88.89 | 8918.T 26.83% | 48.00% | 8918.T 34.23% | 60.35% |
| V3_B_RISK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 38,476.79 / 224,300 | -28,621.181 / 224,300 | 11.11 / 88.89 | 8918.T 26.83% | 48.00% | 8918.T 34.23% | 60.35% |

## EXIT effect: same allocation, v4 -> v5 bar5

| Pair | Total delta JPY | Common N / delta | v4-only N / contribution | v5-only N / contribution | Earlier-release additions N / PnL |
| --- | ---: | ---: | ---: | ---: | ---: |
| V3_0_EQUAL__FROZEN_EXIT_V4 → V3_0_EQUAL__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 0 | 29 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| V3_A_RANK__FROZEN_EXIT_V4 → V3_A_RANK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 0 | 29 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| V3_B_RISK__FROZEN_EXIT_V4 → V3_B_RISK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 0 | 28 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

## Allocation effect: same EXIT

| Pair | Total delta JPY | Common N / delta | left-only N / contribution | right-only N / contribution | Earlier-release additions N / PnL |
| --- | ---: | ---: | ---: | ---: | ---: |
| V3_0_EQUAL__FROZEN_EXIT_V4 → V3_A_RANK__FROZEN_EXIT_V4 | -7,554.4 | 29 / -7,554.4 | 0 / 0 | 0 / 0 | 0 / 0 |
| V3_0_EQUAL__FROZEN_EXIT_V4 → V3_B_RISK__FROZEN_EXIT_V4 | 6,998.9 | 28 / 4,349.7 | 1 / 2,649.2 | 0 / 0 | 0 / 0 |
| V3_A_RANK__FROZEN_EXIT_V4 → V3_B_RISK__FROZEN_EXIT_V4 | 14,553.3 | 28 / 11,904.1 | 1 / 2,649.2 | 0 / 0 | 0 / 0 |
| V3_0_EQUAL__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 → V3_A_RANK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | -7,554.4 | 29 / -7,554.4 | 0 / 0 | 0 / 0 | 0 / 0 |
| V3_0_EQUAL__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 → V3_B_RISK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 6,998.9 | 28 / 4,349.7 | 1 / 2,649.2 | 0 / 0 | 0 / 0 |
| V3_A_RANK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 → V3_B_RISK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | 14,553.3 | 28 / 11,904.1 | 1 / 2,649.2 | 0 / 0 | 0 / 0 |

## EXIT reason distribution

| Arm | Reason | N | PnL JPY |
| --- | --- | ---: | ---: |
| V3_0_EQUAL__FROZEN_EXIT_V4 | SESSION_END | 21 | 70,105.555 |
| V3_0_EQUAL__FROZEN_EXIT_V4 | V4_CONFIRMED_DOWNSIDE_TRAJECTORY | 6 | -10,467.6 |
| V3_0_EQUAL__FROZEN_EXIT_V4 | V4_EMERGENCY_STRUCTURAL_DOWNSIDE | 1 | -2,649.2 |
| V3_0_EQUAL__FROZEN_EXIT_V4 | V4_WINNER_GIVEBACK_CONFIRMED | 1 | 1,649.85 |
| V3_0_EQUAL__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | SESSION_END | 21 | 70,105.555 |
| V3_0_EQUAL__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | V4_CONFIRMED_DOWNSIDE_TRAJECTORY | 6 | -10,467.6 |
| V3_0_EQUAL__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | V4_EMERGENCY_STRUCTURAL_DOWNSIDE | 1 | -2,649.2 |
| V3_0_EQUAL__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | V4_WINNER_GIVEBACK_CONFIRMED | 1 | 1,649.85 |
| V3_A_RANK__FROZEN_EXIT_V4 | SESSION_END | 21 | 62,551.155 |
| V3_A_RANK__FROZEN_EXIT_V4 | V4_CONFIRMED_DOWNSIDE_TRAJECTORY | 6 | -10,467.6 |
| V3_A_RANK__FROZEN_EXIT_V4 | V4_EMERGENCY_STRUCTURAL_DOWNSIDE | 1 | -2,649.2 |
| V3_A_RANK__FROZEN_EXIT_V4 | V4_WINNER_GIVEBACK_CONFIRMED | 1 | 1,649.85 |
| V3_A_RANK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | SESSION_END | 21 | 62,551.155 |
| V3_A_RANK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | V4_CONFIRMED_DOWNSIDE_TRAJECTORY | 6 | -10,467.6 |
| V3_A_RANK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | V4_EMERGENCY_STRUCTURAL_DOWNSIDE | 1 | -2,649.2 |
| V3_A_RANK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | V4_WINNER_GIVEBACK_CONFIRMED | 1 | 1,649.85 |
| V3_B_RISK__FROZEN_EXIT_V4 | SESSION_END | 21 | 75,567.905 |
| V3_B_RISK__FROZEN_EXIT_V4 | V4_CONFIRMED_DOWNSIDE_TRAJECTORY | 6 | -11,580.25 |
| V3_B_RISK__FROZEN_EXIT_V4 | V4_WINNER_GIVEBACK_CONFIRMED | 1 | 1,649.85 |
| V3_B_RISK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | SESSION_END | 21 | 75,567.905 |
| V3_B_RISK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | V4_CONFIRMED_DOWNSIDE_TRAJECTORY | 6 | -11,580.25 |
| V3_B_RISK__EXIT_V5_DYNAMIC_RECLAIM_BAR_5 | V4_WINNER_GIVEBACK_CONFIRMED | 1 | 1,649.85 |

## Interpretation lock

This is exposed Historical Development evidence. It measures cash-ledger interactions but does not validate EXIT v5, select an allocation winner, authorize live/paper trading, or permit merge/promotion. The independent-review packet is prepared; no external review is claimed.
