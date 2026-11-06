# Phase57 MSH-Entry LONG v1 — First Development evaluation

Date: 2026-09-16 JST. Verdict: **MSH_ENTRY_LONG_V1_DEVELOPMENT_BORDERLINE**. Selected threshold: **none**. Development only; STOP.

## Repository / reproducibility

| Item | Value |
| --- | --- |
| Repository | Iam-2squared/ark-terminal |
| Branch | research/phase57-long-only-cash-equity |
| PR | #587 |
| Verified remote source head | 97617f410a181108ab533632487d05c65f3a9ea8 |
| Latest main at audit | 6b6c4d522cd1863132185463a0aed74bc819be01 |
| Local pre-fit protocol commit | d8539ca38017a0911a90377dd56dfd978313dce4 |
| Remote update | NOT performed; new CI not triggered |
| Fit Contract SHA-256 | 64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938 |
| Model implementation SHA-256 | 9e5910c476c6957aab65cc24490ffb2759084e5e49b36db42fe284674979ae74 |
| Frozen Selector payload SHA-256 | 3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59 |
| Ridge artifact SHA-256 | 994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb |
| Selector / CURRENT Entry / Fit Contract | UNCHANGED; integrity checks PASS |
| Scope | JPX CASH EQUITY LONG-only; project SHORT evaluation = 0 |

The protocol was committed locally before the four fits. GitHub blob/tree/commit objects for that protocol were prepared, but no branch ref was updated. Publication is deferred because the existing full test workflow may contact Yahoo Finance.

Verified source-head CI: Predict Tests run35053207614 SUCCESS; Phase52 Daily Dry-Run Persistence run35053207633 SUCCESS; LONG-only Research Foundation run35053207611 SUCCESS. These are PRIOR source-head checks, not CI of the new results.

## Execution / data integrity

| Metric | Count |
| --- | --- |
| allEvaluationEvents | 3000 |
| allEvaluationSymbolSessions | 2170 |
| events | 3800 |
| labelable | 1828 |
| oofDuplicateIds | 0 |
| oofRows | 1451 |
| oofUniqueSymbolSessions | 1099 |
| sessions | 76 |
| trainingEvaluationSessionOverlap | 0 |
| trainingEvaluationSymbolSessionOverlap | 0 |
| uniqueSymbolSessions | 2743 |
| unlabelable | 1972 |
| warmupOofRows | 0 |

| Unlabelable reason | Rows |
| --- | --- |
| LUNCH_BREAK | 380 |
| PROVIDER_GAP | 1424 |
| SESSION_END | 168 |

Labelable coverage: 1,828 / 3,800 = 48.1053%. Initial 16-session prefix has 377 labelable training rows and NO OOF. Evaluation sessions 17–76 contain 3,000 events / 2,170 symbol-sessions; the labelable OOF subset contains 1,451 events / 1,099 symbol-sessions. Excluded rows are retained in row-ledger.ndjson.gz and never assigned Class 0.

**Denominator limitation:** the 1,099-group evaluation pool is conditioned on future label availability. It is not a causal live availability gate, full-universe coverage, or 1,451 independent trades. Frozen Selector used already exposed Development data, so chronological Entry OOF is not end-to-end OOS.

**Schedule:** saved Frozen Selector evidence has ten decisions/session at 09:30, 10:00, 10:30, 11:00, 11:30, 13:00, 13:30, 14:00, 14:30, 15:00 JST. No five-minute reselections were manufactured.

## Frozen fit / all-fold convergence

Exactly four fits, no retries and no full-76-session refit. Core = Ridge Score + Ridge Rank, optional = none, price = REFERENCE_ONLY. Five-class proportional odds/logit, SUM NLL + 1/2 ||beta||², cutpoints unpenalized, unweighted. L-BFGS-B maxiter=2000, ftol=1e-12, gtol=1e-8. Each training prefix independently supplies population mean/std; no eval data enter scaler estimation.

| Fold | Train sessions | Eval sessions | Train rows | Eval rows | Train classes 0/1/2/3/4 | Eval classes 0/1/2/3/4 | success/status | nit/nfev/njev | Objective |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 16 | 15 | 377 | 362 | 126/88/63/68/32 | 139/85/52/49/37 | true/0 | 10/13/13 | 563.8939 |
| 2 | 31 | 15 | 739 | 365 | 265/173/115/117/69 | 119/91/50/59/46 | true/0 | 11/13/13 | 1087.1669 |
| 3 | 46 | 15 | 1104 | 360 | 384/264/165/176/115 | 118/77/56/53/56 | true/0 | 10/13/13 | 1635.2381 |
| 4 | 61 | 15 | 1464 | 364 | 502/341/221/229/171 | 104/82/50/52/76 | true/0 | 10/13/13 | 2179.6834 |

All ten pre-fit checks passed for every fold. Every optimizer message: CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH. Finite parameters, ordered cutpoints, finite nonnegative probabilities summing to one and exact artifact save/reload checks all passed.

| Fold | Train dates | Eval dates | Mean [score,rank] | Std [score,rank] |
| --- | --- | --- | --- | --- |
| 1 | 2024-09-17 – 2024-10-09 | 2024-10-10 – 2024-10-31 | 54.04266149533535, 2.970822281167109 | 21.88450591042053, 1.4204634102929248 |
| 2 | 2024-09-17 – 2024-10-31 | 2024-11-01 – 2024-11-22 | 55.219712952261084, 2.8646820027063598 | 23.713712671399243, 1.39128750462606 |
| 3 | 2024-09-17 – 2024-11-22 | 2024-11-25 – 2024-12-13 | 58.57711678355806, 2.846014492753623 | 26.070754762210832, 1.398051977976238 |
| 4 | 2024-09-17 – 2024-12-13 | 2024-12-16 – 2025-01-09 | 59.02685601751651, 2.879781420765027 | 26.288357277396333, 1.4052112052848442 |

| Fold | Scaler SHA-256 | Model artifact SHA-256 |
| --- | --- | --- |
| 1 | 21fdba819c8ee3e145e554ba9ae3e79dfae3f916722a854a04734fedb2b3ec20 | 7c9558efc09500a9f476217b7a75c400dbbe3107f07636d541c14898ffbba879 |
| 2 | 6f4067a5d7a7a94bf8ce37452d6a708876761eebf5c61725442c4adc9f7c4e98 | 8517611dfabc29baf7408b84908178ae5a6effc5b0f1073b212751389115ef6b |
| 3 | c1c8241e333be1bb82245797e9294498901bed3f942d89a1d440cc11060788cb | 9686c1eef10170f23a9b3224ed8dbbf9fcc0b4e8e486c557ddc137bbd41d152f |
| 4 | da2e1095090a410bb9c0dc04193ac264f9ecd941455e07ec16ae07b2d8e37001 | 40f56e0db3e4577a34a71434b87b3e71e8d0bd914a8b01ad9b350cd0d53d6439 |

## First-entry primary results — strict 30m HIGH

ENTER means the first eligible event with E[L] ≥ threshold in each symbol-session. Repeated entries are suppressed. Precision uses that ENTER event’s own Decision Price / next complete 30m window. Admission preservation uses first-eligible baseline winners eventually admitted. These are distinct measures. Percentages below are %, throughput is per session (60-session denominator).

| Threshold | ENTER | Coverage % | ENTER/session | +1 precision | +2 precision | +3 precision | +5 precision | Frozen balance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Selector | 1099 | 100 | 18.3167 | 66.4240 | 43.6761 | 29.1174 | 14.1037 | 0.7264 |
| 1.0 | 1086 | 98.8171 | 18.1000 | 66.4825 | 44.0147 | 29.4659 | 14.2726 | 0.7241 |
| 2.0 | 143 | 13.0118 | 2.3833 | 88.8112 | 74.1259 | 53.1469 | 32.8671 | 0.2682 |
| 3.0 | 23 | 2.0928 | 0.3833 | 95.6522 | 82.6087 | 69.5652 | 52.1739 | 0.0889 |

| Threshold | +1 preservation | +2 preservation | +3 preservation | +5 preservation | Preserved +1/day | +2/day | +3/day | +5/day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 98.9041 | 99.5833 | 100 | 100 | 12.0333 | 7.9667 | 5.3333 | 2.5833 |
| 2.0 | 16.8493 | 21.8750 | 25 | 31.6129 | 2.0500 | 1.7500 | 1.3333 | 0.8167 |
| 3.0 | 2.8767 | 3.5417 | 4.3750 | 7.0968 | 0.3500 | 0.2833 | 0.2333 | 0.1833 |

| Threshold | +1 timely | +2 timely | +3 timely | +5 timely | +1 remaining | +2 remaining | +3 remaining | +5 remaining |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 98.7671 | 99.5833 | 100 | 100 | 98.9041 | 99.5833 | 100 | 100 |
| 2.0 | 15.3425 | 20 | 22.5000 | 29.0323 | 16.7123 | 21.2500 | 23.1250 | 30.3226 |
| 3.0 | 2.4658 | 3.1250 | 3.7500 | 5.8065 | 2.8767 | 3.5417 | 4.3750 | 6.4516 |

Timely = admitted strictly before the first baseline 30m window ends. Remaining = first-baseline winner AND ENTER-time threshold hit; this uses a new Entry window, not proof of an executable realized return or proof that the first window’s hit happened after ENTER. Admission alone must not be called economically retained opportunity.

## HIGH vs completed CLOSE supporting diagnostic

| Cohort | HIGH +1 | +2 | +3 | +5 | CLOSE +1 | +2 | +3 | +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Selector | 66.4240 | 43.6761 | 29.1174 | 14.1037 | 53.8672 | 33.3030 | 22.8389 | 11.3740 |
| 1.0 | 66.4825 | 44.0147 | 29.4659 | 14.2726 | 53.8674 | 33.6096 | 23.1123 | 11.5101 |
| 2.0 | 88.8112 | 74.1259 | 53.1469 | 32.8671 | 67.1329 | 51.0490 | 39.1608 | 28.6713 |
| 3.0 | 95.6522 | 82.6087 | 69.5652 | 52.1739 | 73.9130 | 69.5652 | 60.8696 | 47.8261 |

| Threshold | CLOSE preservation +1 | +2 | +3 | +5 |
| --- | --- | --- | --- | --- |
| 1.0 | 98.8176 | 99.7268 | 100 | 100 |
| 2.0 | 16.2162 | 20.2186 | 23.5060 | 33.6000 |
| 3.0 | 2.5338 | 3.8251 | 4.3825 | 8 |

CLOSE is supporting only, never mixed into the HIGH training target. Threshold 2 has HIGH +3 53.15% versus CLOSE +3 39.16%; the touch/confirmation distinction remains material.

## Event-level qualification — not independent trades

| Threshold | OOF events | Qualified events | Qualification % | HIGH +1 precision | +2 | +3 | +5 | HIGH +1 preservation | +2 | +3 | +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 1451 | 1429 | 98.4838 | 67.0399 | 44.1568 | 29.8111 | 14.9055 | 98.6612 | 99.2138 | 99.5327 | 99.0698 |
| 2.0 | 1451 | 168 | 11.5782 | 88.0952 | 74.4048 | 56.5476 | 36.3095 | 15.2420 | 19.6541 | 22.1963 | 28.3721 |
| 3.0 | 1451 | 27 | 1.8608 | 88.8889 | 77.7778 | 66.6667 | 51.8519 | 2.4717 | 3.3019 | 4.2056 | 6.5116 |

## Fold stability — first-entry strict 30m HIGH

| Threshold | Fold | OOF rows | Eligible groups | ENTER | Coverage % | ENTER/day | +1 precision | +2 | +3 | +5 | +1 preservation | +2 | +3 | +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 1 | 362 | 262 | 261 | 99.6183 | 17.4000 | 61.3027 | 39.8467 | 23.7548 | 9.5785 | 99.3789 | 99.0476 | 100 | 100 |
| 1.0 | 2 | 365 | 293 | 290 | 98.9761 | 19.3333 | 67.2414 | 42.4138 | 27.9310 | 12.4138 | 99.4898 | 100 | 100 | 100 |
| 1.0 | 3 | 360 | 276 | 269 | 97.4638 | 17.9333 | 65.7993 | 42.3792 | 29.7398 | 14.4981 | 97.2527 | 99.1304 | 100 | 100 |
| 1.0 | 4 | 364 | 268 | 266 | 99.2537 | 17.7333 | 71.4286 | 51.5038 | 36.4662 | 20.6767 | 99.4764 | 100 | 100 | 100 |
| 2.0 | 1 | 362 | 262 | 24 | 9.1603 | 1.6000 | 91.6667 | 75 | 37.5000 | 20.8333 | 12.4224 | 17.1429 | 16.1290 | 24 |
| 2.0 | 2 | 365 | 293 | 40 | 13.6519 | 2.6667 | 85 | 65 | 47.5000 | 30 | 16.8367 | 19.5122 | 22.2222 | 33.3333 |
| 2.0 | 3 | 360 | 276 | 37 | 13.4058 | 2.4667 | 91.8919 | 81.0811 | 54.0541 | 27.0270 | 18.1319 | 25.2174 | 27.5000 | 25.6410 |
| 2.0 | 4 | 364 | 268 | 42 | 15.6716 | 2.8000 | 88.0952 | 76.1905 | 66.6667 | 47.6190 | 19.3717 | 24.8175 | 30.9278 | 38.1818 |
| 3.0 | 1 | 362 | 262 | 3 | 1.1450 | 0.2000 | 100 | 100 | 100 | 100 | 1.8634 | 2.8571 | 4.8387 | 12 |
| 3.0 | 2 | 365 | 293 | 8 | 2.7304 | 0.5333 | 100 | 87.5000 | 62.5000 | 25 | 4.0816 | 5.6911 | 6.1728 | 8.3333 |
| 3.0 | 3 | 360 | 276 | 3 | 1.0870 | 0.2000 | 100 | 66.6667 | 33.3333 | 0 | 1.6484 | 1.7391 | 1.2500 | 0 |
| 3.0 | 4 | 364 | 268 | 9 | 3.3582 | 0.6000 | 88.8889 | 77.7778 | 77.7778 | 77.7778 | 3.6649 | 3.6496 | 5.1546 | 9.0909 |

| Threshold | Fold | +1 enrichment pp | +2 | +3 | +5 |
| --- | --- | --- | --- | --- | --- |
| 1.0 | 1 | -0.1477 | -0.2296 | 0.0907 | 0.0366 |
| 1.0 | 2 | 0.3472 | 0.4343 | 0.2860 | 0.1271 |
| 1.0 | 3 | -0.1428 | 0.7125 | 0.7543 | 0.3677 |
| 1.0 | 4 | 0.1599 | 0.3844 | 0.2721 | 0.1543 |
| 2.0 | 1 | 30.2163 | 34.9237 | 13.8359 | 11.2913 |
| 2.0 | 2 | 18.1058 | 23.0205 | 19.8549 | 17.7133 |
| 2.0 | 3 | 25.9499 | 39.4144 | 25.0685 | 12.8966 |
| 2.0 | 4 | 16.8266 | 25.0711 | 30.4726 | 27.0967 |
| 3.0 | 1 | 38.5496 | 59.9237 | 76.3359 | 90.4580 |
| 3.0 | 2 | 33.1058 | 45.5205 | 34.8549 | 12.7133 |
| 3.0 | 3 | 34.0580 | 25.0000 | 4.3478 | -14.1304 |
| 3.0 | 4 | 17.6202 | 26.6584 | 41.5837 | 57.2554 |

Threshold 2 has positive HIGH enrichment at all four opportunity levels in all four folds. Threshold 1 is near an identity gate, with small +1/+2 reversals in some folds. Threshold 3 admits only 3/8/3/9 groups per fold and fold 3 has zero +5 hits; aggregate precision is insufficient.

## MFE / true MAE / latency / consumed return

| Threshold | Diagnostic | N | Mean | Median | P25 | P75 | P90 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 30m MFE % | 1086 | 2.6256 | 1.7131 | 0.7380 | 3.3608 | 5.5556 | 0 | 33.5329 |
| 1.0 | Session MFE % (different horizon) | 1086 | 4.2127 | 2.7265 | 1.2920 | 5.2632 | 9.9123 | 0 | 98.0018 |
| 1.0 | Session true MAE % (different horizon) | 1086 | -3.3745 | -2.1713 | -4.5704 | -0.6672 | 0 | -60 | 0 |
| 1.0 | First-eligible to ENTER minutes | 1086 | 0.1657 | 0 | 0 | 0 | 0 | 0 | 180 |
| 1.0 | First-eligible to ENTER consumed bps | 1086 | -0.4977 | 0 | 0 | 0 | 0 | -540.5405 | 0 |
| 1.0 | First-original to ENTER minutes | 1086 | 6.6575 | 0 | 0 | 0 | 0 | 0 | 270 |
| 1.0 | First-original to ENTER consumed bps | 1086 | -10.7346 | 0 | 0 | 0 | 0 | -1250 | 322.5806 |
| 2.0 | 30m MFE % | 143 | 5.2414 | 3.3590 | 1.9053 | 9.3158 | 12.5000 | 0 | 16.2512 |
| 2.0 | Session MFE % (different horizon) | 143 | 7.9061 | 4.6122 | 2.3312 | 12.5000 | 14.2857 | 0 | 98.0018 |
| 2.0 | Session true MAE % (different horizon) | 143 | -5.3266 | -3.6649 | -7.1943 | -0.4079 | 0 | -60 | 0 |
| 2.0 | First-eligible to ENTER minutes | 143 | 14.4755 | 0 | 0 | 0 | 30 | 0 | 270 |
| 2.0 | First-eligible to ENTER consumed bps | 143 | -106.9628 | 0 | 0 | 0 | 0 | -1692.3077 | 0 |
| 2.0 | First-original to ENTER minutes | 143 | 26.8531 | 0 | 0 | 0 | 144.0000 | 0 | 270 |
| 2.0 | First-original to ENTER consumed bps | 143 | -129.2799 | 0 | 0 | 0 | 0 | -1692.3077 | 0 |
| 3.0 | 30m MFE % | 23 | 8.1977 | 5.3150 | 2.4840 | 14.1477 | 14.2857 | 0 | 25 |
| 3.0 | Session MFE % (different horizon) | 23 | 14.8091 | 13.9975 | 4.3598 | 15.8644 | 24.4444 | 0 | 98.0018 |
| 3.0 | Session true MAE % (different horizon) | 23 | -7.7194 | -2.2663 | -8.5158 | -0.4658 | 0 | -50 | 0 |
| 3.0 | First-eligible to ENTER minutes | 23 | 11.7391 | 0 | 0 | 0 | 54.0000 | 0 | 120 |
| 3.0 | First-eligible to ENTER consumed bps | 23 | -195.4964 | 0 | 0 | 0 | 0 | -2000.0000 | 0 |
| 3.0 | First-original to ENTER minutes | 23 | 26.0870 | 0 | 0 | 0 | 108.0000 | 0 | 210 |
| 3.0 | First-original to ENTER consumed bps | 23 | -195.4964 | 0 | 0 | 0 | 0 | -2000.0000 | 0 |

**Strict 30m true MAE: UNAVAILABLE for every candidate.** Future lows are not saved in the reused feasibility ledger. Session true MAE is reported separately and is NOT a replacement. The reused session series includes extreme drawdowns (minimum −60% in thresholds 1/2 and −50% in threshold 3); no cost/risk/profitability claim is made and these extrema were not filtered away.

Same-event Selector→Entry reference latency and consumed return are exactly zero by definition, not measured execution quality. First-original latency additionally includes earlier selections omitted for labelability. Negative consumed return means a lower reference price, not proven beneficial waiting. No fill/slippage, portfolio or EXIT simulation was run.

## Paired CURRENT Entry / Selector comparison

| Metric | Value |
| --- | --- |
| Common eligible symbol-session pool | 1099 |
| CURRENT actual first PASS | 66 |
| CURRENT coverage % | 6.0055 |
| CURRENT PASS/session | 1.1000 |
| CURRENT exact 30m matched PASS | 24 |
| CURRENT 30m unmatched PASS | 42 |
| CURRENT PASS before first eligible event | 2 |
| All60session CURRENT context groups | 2170 |
| All60session CURRENT context PASS | 80 |

Only 24 of the 66 actual CURRENT passes have an exact saved OOF event timestamp AND reference-price match. Other PASS timings are unavailable at strict30m, not Class 0. Therefore the following full-pool comparison uses **session-remaining horizon**, not the primary30m target. CURRENT state/model is unchanged; ALREADY_ENTERED is not counted as a new PASS.

| Cohort | Session +1 precision | +2 | +3 | +5 | Session +1 admission preservation | +2 | +3 | +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Selector | 79.6178 | 62.0564 | 46.3148 | 27.9345 | 100 | 100 | 100 | 100 |
| CURRENT | 89.3939 | 69.6970 | 56.0606 | 37.8788 | 5.8286 | 5.5718 | 5.8939 | 6.8404 |
| 1.0 | 79.7422 | 62.5230 | 46.7772 | 28.1768 | 98.9714 | 99.4135 | 99.6071 | 99.6743 |
| 2.0 | 95.1049 | 81.8182 | 67.8322 | 46.8531 | 15.2000 | 17.0088 | 19.2534 | 22.1498 |
| 3.0 | 95.6522 | 86.9565 | 82.6087 | 65.2174 | 2.4000 | 2.6393 | 3.3399 | 4.5603 |

| Cohort | Session preserved +1/day | +2/day | +3/day | +5/day |
| --- | --- | --- | --- | --- |
| CURRENT | 0.8500 | 0.6333 | 0.5000 | 0.3500 |
| 1.0 | 14.4333 | 11.3000 | 8.4500 | 5.1000 |
| 2.0 | 2.2167 | 1.9333 | 1.6333 | 1.1333 |
| 3.0 | 0.3500 | 0.3000 | 0.2833 | 0.2333 |

| CURRENT exact matched subset ONLY | +1 | +2 | +3 | +5 |
| --- | --- | --- | --- | --- |
| HIGH30 precision | 83.3333 | 45.8333 | 33.3333 | 25 |
| CLOSE30 precision | 54.1667 | 29.1667 | 29.1667 | 25 |

Do not compare formal Selector Development percentages 76.39/61.29/47.26/24.99 directly against the restricted 30m OOF pool. Do not compare historical96/2743 CURRENT coverage directly against1099 groups. Those formal artifacts remain unchanged.

## Verdict / threshold selection

- All four frozen fits converged; all pre-fit and saved-output integrity checks passed.
- Threshold 1 leads the frozen balance scalar but admits 98.82% of the labelable symbol-session pool: it largely reproduces Selector-only rather than establishing a useful incremental Entry filter.
- Threshold 2 enriches every HIGH threshold in every fold and improves session-horizon admission preservation and throughput against cached CURRENT on the same symbol-session pool. It is not selected by overriding the frozen balance objective.
- Threshold 3 has only 23 entries and fails to preserve the +5 enrichment direction in fold 3; high precision alone is insufficient.
- Full paired strict-30m CURRENT outcomes and strict-30m true MAE are unavailable in reused ledgers. Session diagnostics are not replacements for these missing measurements.
- Coverage is conditional on hindsight labelability; Entry OOF is not upstream-Selector OOS or a deployable whole-universe coverage estimate.
- No post-result numeric gates, thresholds, hyperparameters, features, folds, labels or model variants were introduced.

No threshold is promoted. The scalar leader is1.0 (0.724053); Selector-only is0.726408. Threshold2 is promising descriptive evidence, but changing the selection rule to prefer it after seeing its precision is not permitted. This is BORDERLINE, not a finding that the mathematical model failed and not a Validation pass.

## Tests / access / STOP

| Check | Result |
| --- | --- |
| Frozen model synthetic | 18 PASS |
| Evaluation synthetic | 12 PASS |
| Discovery | 26 PASS |
| RSS bridge | 89 PASS |
| Read-only evidence audit | PASS;1451 OOF rows,4353 decisions; max probability error2.220446049250313e-16 |
| Full prediction suite | BLOCKED by safety review; no complete PASS claim |
| New remote CI | NOT run; remote ref unchanged |

The full prediction suite continuation was rejected because it can issue an unapproved Yahoo Finance request. It was not retried or bypassed. Development runner provider requests=0 (saved ledgers only), but the attempted regression suite’s provider-request count is UNVERIFIED, not asserted zero. No newly fetched data were used for model fitting/evaluation.

| Control | Value |
| --- | --- |
| exitAccess | 0 |
| finalAll76SessionRefit | 0 |
| oosNewAccess | 0 |
| projectFitCalls | 4 |
| projectOofRows | 1451 |
| providerRequests | 0 |
| shortEvaluations | 0 |
| validationNewAccess | 0 |

The providerRequests=0 entry above is scoped to the Development experiment, not the blocked general regression suite. Validation new access=0, OOS new access=0, Project EXIT access=0, Project SHORT evaluation=0. Synthetic regression fixture names are not Project Validation/OOS access.

| Safety flag | Value |
| --- | --- |
| automaticPromotionAllowed | false |
| brokerWriteAllowed | false |
| excelOrderWriteAllowed | false |
| executionAllowed | false |
| leverageAllowed | false |
| liveTradingAllowed | false |
| marginAllowed | false |
| paperTradingAllowed | false |
| productionUpdateAllowed | false |
| rssOrderFunctionAllowed | false |
| shortAllowed | false |
| transmitted | false |

**Exact next action: STOP.** Independent review of the Development evidence. Separate permission is needed to make the full regression suite offline-only and publish/run CI safely. Do not retrain, add features/thresholds, alter the contract, or open Validation/OOS.

## Files / hashes

| Ledger | Compressed SHA-256 | Payload SHA-256 |
| --- | --- | --- |
| phase57-long-only-current-entry-transfer-v1-events.ndjson.gz | a36eecfed29aa0e9da50b051839578ca2e8f3a37d500de17bd6c3acfd8ce3a53 | bc5f37822e829308d508ebe3748af0ad2f1dd2e41e8847d5633512f8de850f0d |
| phase57-long-only-entry-filter-recovery-audit-v1-first-opportunities.json.gz | 74ca5797a117df37ec78f7e2f859a52ab634affa088fcdabd2a3a0ec4e16d30a | 03986c60518c25083300cdd13e8de989d17cbfeaef59175bae0c11bc5c7a7d97 |
| phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz | 73e566aba4d1a3f5af33b74be52ae90736c088b1091841f1eb44e93d5476084c | c26309efd129fa3e14b6bfbb2ad898d6be794984303d0371e30276a6d376dbba |

| Output | Rows | File SHA-256 | Payload SHA-256 |
| --- | --- | --- | --- |
| decisions | 4353 | b6538172dd1a73c5480505f311d992fca30ed8193c6a7e69db512fb2f1aec476 | 8d6d4b6f321bfefcdb86dba32c0e8e74e92b83e39e14cb9289fcede5867ca503 |
| exclusions | 3800 | 9f21d5c218ac0adb0de4309353ae27d968cadf8aa287c08634176cbc57dbddd1 | 91ca55ddb718d7e5578e733cbf53b863220ec107aab43e23db5ccca664867828 |
| oof | 1451 | 1428f222b19203bc6736cf4ef3bd3ae18be068f289657e9c2b59ecbe6ec44c34 | 834a9212debb9e5ae8036de4b8cdc3fa8ee332755e556ef11f57ac22c3526248 |

Full-precision metrics and all distributions are in development-report.json; separate final disposition is development-verdict.json. Results were generated once; report generation performs no fit.
