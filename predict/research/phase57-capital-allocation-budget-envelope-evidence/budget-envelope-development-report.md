# Phase57 Budget Envelope Ablation - Historical Development Diagnosis

Status: **COMPLETE — DEVELOPMENT DIAGNOSIS ONLY**

Only the budget divisor changes: equity/10, equity/5, equity/3. The position limit remains 10 in every arm, so this is a single-variable slotBudget ablation. Selector, MSH Entry, V3_B_RISK, risk definition, Frozen EXIT v4, 100-share lot, costs, cash accounting and event ordering remain fixed.

## Baseline gate

MAX_10 parity: MAX_10_BASELINE_PARITY_PASS; Final Equity ¥1,065,637.505, Return 6.563750%, PF 5.189, MaxDD 2.096278%, Accepted 28/85.

## Experiment 1 — Budget Envelope

| Metric | MAX_10 | MAX_5 | MAX_3 |
| --- | ---: | ---: | ---: |
| Final Equity | ¥1,065,637.505 | ¥1,212,126.265 | ¥1,344,231.6 |
| Net PnL | ¥65,637.505 | ¥212,126.265 | ¥344,231.6 |
| Return | 6.563750% | 21.212626% | 34.423160% |
| Portfolio PF | 5.189 | 3.901 | 2.74 |
| MaxDD | 2.096278% | 4.273109% | 6.379147% |
| Worst Day | 2026-06-24 -0.054684% | 2026-07-24 -0.874888% | 2026-07-24 -2.549371% |
| Accepted count | 28/85 | 49/85 | 63/85 |
| Below-lot skip | 56 | 36 | 19 |
| Cash-insufficient skip | 1 | 0 | 3 |
| Position-limit skip | 0 | 0 | 0 |
| Avg capital utilization | 3.73% | 10.05% | 18.66% |
| Max capital utilization | 22.24% | 54.30% | 93.33% |
| Avg gross exposure | ¥38,476.79 | ¥111,537.832 | ¥222,028.947 |
| Max gross exposure | ¥224,300 | ¥567,200 | ¥1,213,950 |
| Avg abs net exposure | ¥38,476.79 | ¥111,308.4 | ¥219,261.15 |
| Max abs net exposure | ¥224,300 | ¥567,200 | ¥1,115,700 |
| Win rate | 50.00% | 48.98% | 46.03% |
| Avg trade PnL | ¥2,344.197 | ¥4,329.107 | ¥5,463.994 |
| Median trade PnL | ¥356.8 | ¥-92.5 | ¥-185 |
| Avg win | ¥5,807.664 | ¥11,885.604 | ¥18,692.977 |
| Avg loss | ¥-1,119.271 | ¥-2,925.129 | ¥-5,819.551 |
| Avg Win / Avg Loss | 5.189 | 4.063 | 3.212 |
| Largest winner contribution | 5240.T 14.07% | 5240.T 9.62% | 5240.T 9.28% |
| Top1 symbol profit contribution | 8918.T 34.23% | 8918.T 22.06% | 8918.T 21.19% |
| Top3 symbol profit contribution | 60.35% | 41.58% | 41.38% |
| Top symbol capital concentration | 8918.T 26.83% | 8918.T 16.54% | 8918.T 12.57% |
| Top3 capital concentration | 48.00% | 33.49% | 27.25% |
| LONG capital share | 11.11% | 10.47% | 10.17% |
| SHORT capital share | 88.89% | 89.53% | 89.83% |
| Max concurrent positions | 2 | 3 | 4 |

## Attribution

Cash Recycling is a mutually exclusive descriptive cash-path component in the recomposition below; it is not added twice to the execution-set total.

| Comparison | Total | Position Size | New Trade | Cash Recycling | Other execution-set |
| --- | ---: | ---: | ---: | ---: | ---: |
| V3_B_RISK__FROZEN_EXIT_V4__MAX_10 → V3_B_RISK__FROZEN_EXIT_V4__MAX_5 | ¥146,488.76 | ¥80,846.81 (28) | ¥65,641.95 (21) | ¥0 (0) | ¥0 (0) |
| V3_B_RISK__FROZEN_EXIT_V4__MAX_10 → V3_B_RISK__FROZEN_EXIT_V4__MAX_3 | ¥278,594.095 | ¥197,481.87 (28) | ¥81,112.225 (35) | ¥0 (0) | ¥0 (0) |

## Experiment 2 — Fractional-share theoretical diagnostic

| Metric | 100-share MAX_10 | Fractional MAX_10 | Difference |
| --- | ---: | ---: | ---: |
| Accepted | 28 | 85 | 57 |
| Return | 6.563750% | 11.013795% | 4.450045% |
| PF | 5.189 | 2.247 | - |
| MaxDD | 2.096278% | 2.471520% | 0.375242% |
| Avg utilization | 3.73% | 7.59% | 3.86% |
| Fractional-only trade contribution | - | ¥37,100.914 | ¥37,100.914 |
| Total PnL difference | - | - | ¥44,500.449 |

This fractional arm is theoretical diagnostics only: it is not executable, not a validation candidate and not eligible for main/promotion.

## Accepted vs below-lot outcome diagnosis

| Group | N | MSH mean / median | Price mean / median | v4 mean net | v4 win rate | LONG / SHORT | Theoretical 100-share PnL sum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| accepted | 28 | 0.658 / 0.639 | ¥218.496 / ¥179 | 2.242000% | 50.00% | 3 / 25 | ¥5,774.105 |
| belowLot | 56 | 0.651 / 0.633 | ¥3,247.08 / ¥2,744.25 | 0.620823% | 44.64% | 7 / 49 | ¥116,808.175 |

High-price rows and full symbol concentration are retained in the JSON evidence. These outcome diagnostics are explanatory only and were not used to retune MSH.

## Experiment 3 — v5 reappearance

| Budget arm | bar5-defensive accepted | v4 PnL | v5 PnL | v5-v4 | Earlier-release additions |
| --- | ---: | ---: | ---: | ---: | ---: |
| MAX_5 | 6 | ¥212,126.265 | ¥214,425.715 | ¥2,299.45 | 0 |
| MAX_3 | 9 | ¥344,231.6 | ¥350,919.8 | ¥6,688.2 | 1 |

## Development diagnosis

- MAX_10 is a material deployment constraint in this exposed sample: MAX_5/MAX_3 accept 21/35 additional trades, and the fractional diagnostic accepts all 85.
- The PnL increase is not only added trades. Relative to MAX_10, the common-trade size effect is ¥80,846.81 for MAX_5 and ¥197,481.87 for MAX_3; new-trade effects are ¥65,641.95 and ¥81,112.225.
- Deployment expansion weakens quality/risk metrics: PF declines and MaxDD rises as the divisor falls; below-lot trades have lower mean net return and a negative median despite positive aggregate contribution.
- Capital concentration falls rather than rises, while the naturally observed SHORT-heavy direction mix remains unchanged.
- Therefore the bottleneck diagnosis is supported for this Development set, but a smaller divisor is not selected or validated.

## Interpretation lock

This exposed-data result diagnoses whether the MAX_10 budget envelope limits capital deployment. It does not select MAX_5/MAX_3 as a winner, freeze Risk as a winner, validate EXIT v5, open fresh/OOS data, authorize execution, or permit main merge/promotion. Independent-review packet prepared; review not claimed.
