# Phase57 LONG-only Candidate v1/v2 Paired Result

Status: **NO IMPROVEMENT — keep Candidate v1; do not freeze Candidate v2**

The fixed Phase-1 question was whether one shallow nonlinear model family could repair Ridge v1's missed-opportunity ranking without changing the 30-minute endpoint target, causal feature universe, Development D rows, decision timestamps, or Top-N policy. It did not.

## Reproducibility

- Comparison contract commit: `6ff9d44bf581f48fe6e75375c66bf7c0b659731b`
- Error-fix/run commit: `a4bac78da1c756a3c5b6b9db44a906004fd0eab8`
- Acquisition run: `34964031692` (20/20 sessions, 7,962,081 Minute rows, 250/300 physical requests)
- Successful paired run: `34969753778`
- Sanitized artifact: `10397346043`
- Report SHA-256: `ead502ba4f6a871b811b20755a983372f8438b47c31156cfa06ae84aa39dbf1e`

## Development data audit

| Use | Sessions | Rows |
|---|---:|---:|
| v2 fit (fixed first half) | 10 | 257,721 |
| v2 model selection (fixed second half) | 10 | 264,271 |
| Ridge v1 fit (Development C) | 20 | 526,930 |
| Paired diagnostic evaluation (Development D) | 20 | 550,181 |

Validation and OOS remained sealed. No J-Quants requests occurred during fit/evaluation.

## Model

Only `HistGradientBoostingRegressor` was considered. Four configurations were fixed before fit. The fixed selection rule chose `HGBR_D3_T80`: depth 3, 80 iterations, learning rate 0.05, minimum leaf size 256, 16 bins, fixed seed 5702.

## Top-5 paired result

| KPI | Ridge v1 | Shallow nonlinear v2 | Delta v2-v1 |
|---|---:|---:|---:|
| 30m mean return | +117.21 bps | +97.81 bps | -19.40 bps |
| 30m median return | +34.69 bps | +42.77 bps | +8.08 bps |
| Positive rate | 53.56% | 54.33% | +0.78 pp |
| Future MFE | +3.36% | +2.34% | -1.02 pp |
| Future MAE | -1.11% | -0.32% | +0.79 pp (smaller drawdown) |
| +50 bps opportunity recall | 0.64% | 0.64% | 0.00 pp |
| +100 bps opportunity recall | 1.50% | 1.36% | -0.14 pp |
| +150 bps opportunity recall | 2.78% | 2.24% | -0.54 pp |
| +200 bps opportunity recall | 4.45% | 3.21% | -1.24 pp |
| Final +5% precision | 12.22% | 5.22% | -7.00 pp |
| Final +5% recall | 0.944% | 0.403% | -0.540 pp |
| Positive sessions | 19/20 | 20/20 | +1 session |
| Global Spearman | 0.1132 | 0.1067 | -0.0066 |

## Capacity curve

| Top N | v1 mean | v2 mean | v1 median | v2 median | v1 +200 recall | v2 +200 recall | v1 MFE / MAE | v2 MFE / MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | +155.18 | +143.54 | +24.07 | +75.70 | 1.10% | 0.83% | +4.98% / -1.82% | +2.87% / -0.00% |
| 3 | +133.11 | +114.43 | +37.19 | +57.09 | 2.90% | 2.12% | +3.96% / -1.29% | +2.52% / -0.29% |
| 5 | +117.21 | +97.81 | +34.69 | +42.77 | 4.45% | 3.21% | +3.36% / -1.11% | +2.34% / -0.32% |
| 10 | +79.29 | +82.12 | +21.75 | +37.40 | 6.77% | 5.36% | +2.52% / -0.99% | +1.92% / -0.34% |
| 20 | +58.48 | +62.62 | +16.07 | +27.10 | 9.92% | 7.80% | +1.93% / -0.80% | +1.54% / -0.36% |
| 30 | +46.96 | +52.75 | +12.77 | +24.04 | 11.88% | 9.92% | +1.64% / -0.73% | +1.36% / -0.38% |
| 50 | +36.92 | +42.80 | +9.49 | +16.89 | 15.11% | 13.55% | +1.36% / -0.65% | +1.20% / -0.41% |

Returns are basis points. v2 becomes stronger on mean/median at Top 10–50 and materially reduces MAE, but it loses the primary upper-tail recall at every capacity.

## Blind-spot repair

The exact evaluation cohort here is v1 rank 101+; therefore its v1 median ranks differ from the earlier broader Top-5-missed summary.

| v1 missed cohort | N | v1 median rank | v2 median rank | Median improvement | v2 rank 101+ | v2 Top20 | v2 Top50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| +100 bps | 21,508 | 1,770.0 | 1,697.0 | +73.0 | 94.22% | 1.54% | 3.13% |
| +200 bps | 5,198 | 2,071.5 | 2,114.5 | -43.0 | 92.61% | 2.50% | 4.54% |

The +100 bps median repair is small and +200 bps becomes slightly worse. More than 92% of both missed cohorts remain below rank 100.

Archetype-level median rank improved most for Pullback Continuation (+100: 1,830→1,053.5; +200: 2,274.5→1,604.5) and Pre-breakout/Volume-led (+200: 904.5→645). It worsened for VWAP-led Weak Price (+100: 1,524→1,937; +200: 1,540.5→1,949) and for Other/Unclassified +200 (2,160.5→2,270.5). Repair is not broad enough to solve the blind spot.

## Distribution and stability

| KPI | Ridge v1 Top5 | v2 Top5 |
|---|---:|---:|
| P1 / P5 / P10 | -714.46 / -329.02 / -184.31 bps | -400.17 / -133.35 / -78.13 bps |
| P25 / P50 / P75 | -15.57 / +34.69 / +284.48 bps | 0.00 / +42.77 / +180.54 bps |
| P90 / P95 / P99 | +526.32 / +555.56 / +1,250.00 bps | +357.32 / +500.96 / +814.66 bps |
| Min / Max | -2,352.94 / +3,313.37 bps | -2,007.72 / +1,428.57 bps |
| Trim top 1% mean | +103.14 bps | +86.23 bps |
| Trim top 5% mean | +72.78 bps | +68.43 bps |
| Top 1% contribution | 13.98% | 12.73% |

v2 is less tail-dependent and has substantially smaller drawdown, but also suppresses valuable upside. It beat v1 on only 9/20 paired sessions; the session-level mean and median differences were -19.40 and -13.87 bps.

## Negative controls and safety

| Control | Top5 mean | +200 recall | Positive sessions |
|---|---:|---:|---:|
| v2 | +97.81 bps | 3.21% | 20/20 |
| Label shuffle | +18.60 bps | 0.96% | 17/20 |
| Random | -0.19 bps | 0.20% | 10/20 |
| Simple momentum | -138.04 bps | 1.36% | 1/20 |

Look-ahead audit passed. Target, Top N, causal feature universe, Entry, EXIT, and allocation were unchanged. SHORT, margin, leverage, and real orders were not introduced.

## Recommendation and stop

Candidate v2 Phase-1 is **not a freeze candidate**. Keep Ridge v1 as `PROMISING BUT INCOMPLETE / DIAGNOSTIC`. The shallow nonlinear family improved median return and downside control, but failed the core goal of repairing +100/+200 bps opportunity ranking and sharply reduced Final +5% precision/recall.

Per protocol, stop here. Do not open Validation/OOS or change Top N, target, features, Entry, EXIT, or allocation without a new user decision.
