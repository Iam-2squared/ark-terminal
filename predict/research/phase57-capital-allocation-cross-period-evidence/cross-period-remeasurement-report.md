# Phase57 Historical Re-measurement / Cross-Period Robustness

Status: **HISTORICAL_REMEASUREMENT_COMPLETE — USED/EXPOSED DATA, NOT OOS OR VALIDATION**

The frozen integrated system was replayed without parameter changes. No reserved 2026-09-10 through 2026-10-21 session was accessed.

## Main comparison

| Block | Sessions | Arm | Return | PF | MaxDD | Worst day | Accepted | Eligible | Avg util | Max util |
| --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| A | 30 | MAX_5_V5 | 16.935817% | 4.233 | 4.273109% | 2026-07-24 -0.874888% | 34 | 51 | 9.92% | 54.30% |
| A | 30 | MAX_10_V5 | 5.329555% | 4.413 | 2.096278% | 2026-06-24 -0.054684% | 25 | 51 | 3.99% | 22.24% |
| A | 30 | MAX_3_V5 | 27.477280% | 3.34 | 6.379147% | 2026-07-24 -2.549371% | 39 | 51 | 17.19% | 90.36% |
| A | 30 | MAX_5_V4 | 16.935817% | 4.233 | 4.273109% | 2026-07-24 -0.874888% | 34 | 51 | 9.92% | 54.30% |
| B | 8 | MAX_5_V5 | 2.613570% | 2.793 | 2.392236% | 2026-08-04 -0.403858% | 14 | 34 | 8.85% | 36.95% |
| B | 8 | MAX_10_V5 | 1.155275% | 231.824 | 1.252314% | 2026-08-06 -0.004961% | 3 | 34 | 2.68% | 9.92% |
| B | 8 | MAX_3_V5 | 4.574855% | 1.765 | 3.499304% | 2026-08-05 -1.699423% | 23 | 34 | 20.25% | 84.02% |
| B | 8 | MAX_5_V4 | 2.223625% | 2.204 | 2.581152% | 2026-08-04 -0.644526% | 14 | 34 | 9.72% | 47.00% |
| OLD20 | 20 | MAX_5_V5 | 22.538840% | 3.711 | 5.436598% | 2026-08-27 -1.698039% | 27 | 35 | 9.18% | 72.45% |
| OLD20 | 20 | MAX_10_V5 | 5.413440% | 3.143 | 2.279582% | 2026-08-27 -0.581467% | 17 | 35 | 3.11% | 29.59% |
| OLD20 | 20 | MAX_3_V5 | 41.521440% | 3.956 | 8.778544% | 2026-08-27 -2.821382% | 28 | 35 | 14.93% | 99.09% |
| OLD20 | 20 | MAX_5_V4 | 21.358890% | 3.252 | 5.724065% | 2026-08-27 -1.991788% | 27 | 35 | 9.76% | 72.65% |
| A+B | 38 | MAX_5_V5 | 21.442571% | 4.027 | 4.273109% | 2026-07-24 -0.874888% | 49 | 85 | 9.89% | 54.30% |
| A+B | 38 | MAX_10_V5 | 6.563750% | 5.189 | 2.096278% | 2026-06-24 -0.054684% | 28 | 85 | 3.73% | 22.24% |
| A+B | 38 | MAX_3_V5 | 35.091980% | 2.833 | 6.379147% | 2026-07-24 -2.549371% | 64 | 85 | 18.20% | 92.24% |
| A+B | 38 | MAX_5_V4 | 21.212626% | 3.901 | 4.273109% | 2026-07-24 -0.874888% | 49 | 85 | 10.05% | 54.30% |

## Cross-period summary

| Dataset | Role | Sessions | MAX_5 v5 Return | PF | MaxDD | MAX_10 Return | MAX_3 Return |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | REPLAYABLE_DEVELOPMENT_BLOCK_A | 30 | 16.935817% | 4.233 | 4.273109% | 5.329555% | 27.477280% |
| B | REPLAYABLE_DEVELOPMENT_BLOCK_B | 8 | 2.613570% | 2.793 | 2.392236% | 1.155275% | 4.574855% |
| OLD20 | REPLAYABLE_EXPOSED_DIAGNOSTIC | 20 | 22.538840% | 3.711 | 5.436598% | 5.413440% | 41.521440% |
| A+B | REPLAYABLE_DEVELOPMENT | 38 | 21.442571% | 4.027 | 4.273109% | 6.563750% | 35.091980% |

## Budget attribution

| Block | Comparison | Total | Common size | New trade | Cash recycling | Other set |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A | MAX_10_TO_MAX_5 | ¥116,062.61 | ¥65,739.66 (25) | ¥50,322.95 (9) | ¥0 (0) | ¥0 (0) |
| A | MAX_5_TO_MAX_3 | ¥105,414.635 | ¥114,799.31 (34) | ¥-9,384.675 (5) | ¥0 (0) | ¥0 (0) |
| B | MAX_10_TO_MAX_5 | ¥14,582.95 | ¥11,945.8 (3) | ¥2,637.15 (11) | ¥0 (0) | ¥0 (0) |
| B | MAX_5_TO_MAX_3 | ¥19,612.85 | ¥4,044.95 (14) | ¥15,567.9 (9) | ¥0 (0) | ¥0 (0) |
| OLD20 | MAX_10_TO_MAX_5 | ¥171,254 | ¥60,566.85 (17) | ¥110,687.15 (10) | ¥0 (0) | ¥0 (0) |
| OLD20 | MAX_5_TO_MAX_3 | ¥189,826 | ¥168,972.25 (27) | ¥20,853.75 (1) | ¥0 (0) | ¥0 (0) |
| A+B | MAX_10_TO_MAX_5 | ¥148,788.21 | ¥80,846.26 (28) | ¥67,941.95 (21) | ¥0 (0) | ¥0 (0) |
| A+B | MAX_5_TO_MAX_3 | ¥136,494.085 | ¥140,161.96 (49) | ¥-3,667.875 (15) | ¥0 (0) | ¥0 (0) |

## Frozen EXIT comparison at MAX_5

| Block | v4 Return | v5 Return | PnL delta | Defensive accepted | Changed outcomes | Earlier exits | Recycling additions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 16.935817% | 16.935817% | ¥0 | 2 | 0 | 0 | 0 / ¥0 |
| B | 2.223625% | 2.613570% | ¥3,899.45 | 4 | 5 | 4 | 0 / ¥0 |
| OLD20 | 21.358890% | 22.538840% | ¥11,799.5 | 4 | 5 | 4 | 0 / ¥0 |
| A+B | 21.212626% | 21.442571% | ¥2,299.45 | 6 | 5 | 4 | 0 / ¥0 |

## Interpretation

- Positive MAX_5 return in every replayable block: true
- PF above 1 in every replayable block: true
- MAX_5 return above MAX_10 in every block: true
- MAX_3 return above MAX_5 in every block: true
- SHORT capital share above 50% in every block: true
- v5 PnL above v4 in every block: false

Exact arm metrics, symbol/day concentration, all attributions, ledger audits, and descriptive leave-one-block combinations are preserved in the JSON evidence. This diagnostic does not reopen Development, promote MAX_3, validate the candidate, or authorize execution.
