# Development robustness / Claude re-review packet

Decision: FRESH_VALIDATION_GO for independent offline validation readiness. STOP BEFORE OPEN. Candidate unchanged.

Source: run34292703804 / artifact10084158820. Candidate SHA: f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a. Audit SHA: f645e959ecc1c60d1bb00b5ff27c1ba9b54d26fdcdb1c628893450367f198646

This is a descriptive post-selection audit, not a new formal significance test or model-selection round. All returns are bps per opportunity; their sum is not portfolio performance.

## Return distribution

| Statistic | Value |
|---|---:|
| n | 84.000000 |
| mean | 120.874378 |
| median | 62.189755 |
| stdSample | 481.543102 |
| min | -1015.101010 |
| max | 1106.111111 |
| p05 | -594.628090 |
| p10 | -465.445014 |
| p25 | -186.061861 |
| p50 | 62.189755 |
| p75 | 426.276297 |
| p90 | 823.522383 |
| p95 | 1020.813449 |
| skewnessMoment | 0.142385 |
| kurtosisExcessMoment | -0.178451 |
| trimmedMean5pctEachTail | 120.891338 |
| winsorizedMean1pctEachTail | 121.414738 |

## Event concentration

| Top k | Sum bps | Share signed net | Share absolute sum | Share positive sum |
|---|---:|---:|---:|---:|
| 1 | 1106.11 | 10.89% | 3.46% | 5.25% |
| 3 | 3318.33 | 32.68% | 10.37% | 15.74% |
| 5 | 5449.81 | 53.67% | 17.02% | 25.85% |
| 10 | 9934.72 | 97.85% | 31.03% | 47.12% |

## Session concentration

| Top k | Sum bps | Share signed net | Share absolute sum | Share positive sum |
|---|---:|---:|---:|---:|
| 1 | 1396.19 | 13.75% | 7.58% | 9.77% |
| 3 | 3978.81 | 39.19% | 21.61% | 27.85% |
| 5 | 6199.61 | 61.06% | 33.67% | 43.40% |

Top5 events removed: mean+59.54bps; Top10 removed:+2.96bps. Top5 sessions account for61.06% of signed net. There is material concentration despite positive robust center estimates.

## Sessions

| Date | ENTER | Valid3 | Mean | Median | Sum |
|---|---:|---:|---:|---:|---:|
| 2025-11-19 | 3 | 2 | -5.00 | -5.00 | -10.00 |
| 2025-11-20 | 0 | 0 | missing | missing | missing |
| 2025-11-25 | 3 | 3 | 294.75 | 324.30 | 884.24 |
| 2025-11-26 | 2 | 0 | missing | missing | missing |
| 2025-11-27 | 6 | 5 | -21.24 | 22.20 | -106.19 |
| 2025-11-28 | 3 | 3 | 312.26 | 429.78 | 936.77 |
| 2025-12-01 | 2 | 2 | -401.51 | -401.51 | -803.03 |
| 2025-12-03 | 2 | 2 | -188.20 | -188.20 | -376.40 |
| 2025-12-04 | 5 | 5 | 202.42 | -71.23 | 1012.10 |
| 2025-12-05 | 2 | 2 | -194.89 | -194.89 | -389.78 |
| 2025-12-08 | 4 | 4 | 300.20 | 353.73 | 1200.79 |
| 2025-12-09 | 2 | 2 | -578.66 | -578.66 | -1157.32 |
| 2025-12-10 | 4 | 3 | 192.28 | 55.24 | 576.84 |
| 2025-12-11 | 3 | 3 | -212.42 | -201.08 | -637.27 |
| 2025-12-15 | 3 | 3 | 256.27 | 623.12 | 768.82 |
| 2025-12-16 | 4 | 4 | -36.00 | -11.55 | -143.99 |
| 2025-12-17 | 4 | 4 | 145.05 | 271.03 | 580.19 |
| 2025-12-18 | 7 | 6 | 169.01 | 142.67 | 1014.09 |
| 2025-12-19 | 3 | 2 | 483.10 | 483.10 | 966.20 |
| 2025-12-22 | 4 | 3 | 79.10 | -266.37 | 237.31 |
| 2025-12-23 | 3 | 3 | 201.60 | -181.06 | 604.79 |
| 2025-12-25 | 2 | 2 | 698.10 | 698.10 | 1396.19 |
| 2025-12-26 | 5 | 5 | 238.45 | 59.94 | 1192.27 |
| 2025-12-29 | 5 | 3 | 167.82 | 173.57 | 503.45 |
| 2025-12-30 | 4 | 3 | 342.84 | 330.20 | 1028.53 |
| 2026-01-05 | 4 | 4 | -11.68 | 34.16 | -46.70 |
| 2026-01-06 | 3 | 3 | -153.42 | -5.00 | -460.26 |
| 2026-01-07 | 3 | 3 | 460.61 | 471.19 | 1381.83 |

16 positive,10 negative,1 zero-ENTER session;2 sessions have no valid+3 labels (not zero returns).

## Fixed threshold sensitivity

| Threshold | ENTER | Coverage | +3 positive | Mean net3 | Median net3 | Adverse1 | Pos/neg sessions | L/S |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 0.5 | 582 | 7.05% | 53.67% | 22.44 | 7.01 | 78.18% | 20/8 | 40/542 |
| 0.55 | 180 | 2.18% | 55.69% | 60.77 | 35.65 | 78.29% | 20/8 | 17/163 |
| 0.6 | 95 | 1.15% | 57.14% | 120.87 | 62.19 | 71.74% | 16/10 | 9/86 |

The three precommitted points show a gradual count-quality tradeoff, not proof of smoothness between points.0.60 remains frozen; coverage halves vs0.55 and session positivity weakens.

## Direction and scaling

Hybrid is direction-neutral. Ready features contain12528 LONG and12528 SHORT rows. OOF means: LONG0.3866,SHORT0.4786; scores>0.60:33/249; after state handling ENTER9/86. Bias is present in model scores before the threshold. Direction coefficient=-0.15298 gives a SHORT-vs-LONG logit difference of+0.30596 holding other inputs fixed; the directional inputs themselves also differ.

| Feature | Coef / training SD | Weighted mean | Weighted SD | Observed min | Observed max |
|---|---:|---:|---:|---:|---:|
| directionalReturnFromOpenPct | 0.009003 | 0.00000 | 7.68089 | -54.05405 | 54.05405 |
| directionalVwapDistancePct | -0.026149 | 0.00000 | 3.09670 | -18.72610 | 18.72610 |
| directionalMomentum3Pct | -0.204571 | 0.00000 | 2.44927 | -28.27362 | 28.27362 |
| directionalMomentumAccelerationPct | 0.020128 | 0.00000 | 2.19074 | -33.48214 | 33.48214 |
| directionalPullback6Pct | -0.024281 | -1.58780 | 2.29484 | -30.55556 | 0.00000 |
| relativeVolume5 | -0.026277 | 2.76825 | 56.19046 | 0.00001 | 3356.76471 |
| minutesSinceFirstSelection | -0.066255 | 46.30807 | 77.60794 | 0.00000 | 325.00000 |
| hybridReciprocalRank | 0.015946 | 0.09689 | 0.13940 | 0.02500 | 1.00000 |
| priorSelectionCount | -0.003426 | 3.14365 | 5.31052 | 0.00000 | 48.00000 |
| direction | -0.152981 | 0.00000 | 1.00000 | -1.00000 | 1.00000 |

Coefficients are log-odds per training weighted SD, not probability changes. Eligible missing rate0 by fail-closed contract. Momentum has the largest standardized coefficient magnitude. Relative volume has a heavy tail(max3356.76,weighted SD56.19); its extreme logit contribution reaches-1.57. Scaling is finite/consistent but not outlier-robust. No scaling or coefficient changes made.

## Feature-ready selection

3864/16392 events blocked(23.57%):2876 opening-bar missing;988 recent-grid gap/stale. Both directions are blocked together.

| JST hour | Ready | Blocked | Block rate |
|---|---:|---:|---:|
| 10 | 3927 | 1124 | 22.25% |
| 11 | 1849 | 566 | 23.44% |
| 13 | 3008 | 817 | 21.36% |
| 14 | 2466 | 723 | 22.67% |
| 15 | 1278 | 634 | 33.16% |

Ready median selection delay50min vs blocked60min; first selections1690 vs439. Late-day missingness is higher. Exact rank/session/persistence distributions are in the JSON. This is not MCAR; validation must retain all-selected denominator and blocked accounting.

## Cluster uncertainty and adverse behavior

Session-cluster bootstrap95% mean interval:[36.368206322602084, 200.60727029696238] bps; positive-rate interval:[0.4659090909090909, 0.6704545454545454]. Seed57060,10000 draws,28 sessions including empty clusters. Conditional on already selected threshold; no correction for threshold selection or common fold training histories. Legacy effective n84 reflects negative ICC clipping and is not proof of independence.

Immediate adverse66/92=71.74%. Among adverse cases depth median152.89bps,p75=282.64,p90=430.99. Across all valid1 cases median79.57bps. Later endpoint net-positive:28/60 at+3,32/53 at+6; missing6/13. First recovery time and within-bar ordering UNKNOWN from saved labels.

## Limits, protection, and judgment

Market regime UNKNOWN; P21 paired reference UNKNOWN. No external source or prior reconstruction started. Original runtime PIT/state/duplicate audit0; artifact and candidate hashes, feature fingerprints and OOF count/mean parity verified. Full raw-source independent audit was not repeated.

FRESH_VALIDATION_GO is justified by the positive robust center and clustered mean estimate, with substantial concentration/coverage/direction/scale caveats. It is not a performance guarantee or permission to open fresh data in this task. Candidate/model/threshold0.60 unchanged. Fresh Validation/OOS/Reserve180–282 new access0; all safety flagsfalse. Existing P21 fallback remains. No Claude message sent.
