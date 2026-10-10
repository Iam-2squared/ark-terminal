# Phase57 MSH-Entry LONG v2.1 Development — BLOCKED

**MSH_ENTRY_LONG_V2_1_DEVELOPMENT_BLOCKED**. The immutable experiment completed all24 inner fits and96 fixed-threshold evaluations. No threshold passed every precommitted inner condition in any unit. Contract requires stopping each replica before outer refit; no selected OOF or candidate Portfolio exists. This is not an implementation exception, a completed OOF FAIL, or evidence that all Risk refinement architectures fail.

| Item | Result |
|---|---|
| Verdict | MSH_ENTRY_LONG_V2_1_DEVELOPMENT_BLOCKED |
| Contract SHA | 82c17234b482118919b092df4af56c0e6a60d792de5ce3a551a509bcc3d293c7 |
| Branch | research/phase57-long-only-cash-equity |
| PR | https://github.com/Iam-2squared/ark-terminal/pull/587 (Draft/unmerged) |
| Source / freeze head | a575f27731e879c1c1d5ed90d42f3c0bade3d996 |
| Latest main at start | c48be22db7deef286b0bb5dc1951964431145908 |
| Final head / CI | Containing research commit; exact final head and completed GitHub checks reported with delivery. No main merge. |
| Dataset | 2024-09-17..2025-01-09; 76 Historical / Development / IN-SAMPLE / Outcome-exposed sessions |
| Conditional universe | 3,800 events / 760 timestamps; 353 raw-qualified / 277 v1 anchors / 181 labelable / 96 unknown |
| Primary outer scope | 60 sessions / 3,000 candidate IDs / 232 v1 anchors / 159 labelable; warmup16 excluded in both arms |
| Project fits | 24 inner attempted / 24 success / 0 outer |
| Risk predictions | 825 numeric inner-calibration records across repeated folds/groups; not 825 independent trades |
| Threshold evaluations | 96 = 24 units × {1,2,5,10} |
| Selection | NONE in all24 units |
| Selected OOF | 0 numerical predictions / 0 decisions; 3,000 UNAVAILABLE status records per scope, not fabricated SKIPs |
| v2.1 selected ENTER / Portfolio | UNKNOWN / NOT_AVAILABLE; not 0 trades or 0% return |
| Prefit tests | 48 PASS before the single Project run; tests are synthetic/static only |
| Budget SHA | b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f |

## What the fixed thresholds did

These are **chronological INNER calibration** results, not outer OOF. Windows overlap across expanding folds; do not sum them as independent evidence. Threshold5 and10 reproduce every baseline anchor in all24 units and therefore provide0% mean-D30 improvement. Threshold1 produces no labelable accepted observations in all24 units. Threshold2 either removes too many anchors/winners or fails another frozen condition. No new threshold was tried.

| Fold | Threshold | v1→v2.1 ENTER | strict N | Mean D30 | D30 improvement | +1 Precision | +2 Precision | +3 retention | +5 retention | Throughput | Non-PASS gates |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 12→0 | 0 | UNKNOWN | UNKNOWN% | UNKNOWN | UNKNOWN | 0.00% | 0.00% | 0.00% | precision1RatioMin:INCONCLUSIVE;precision2RatioMin:INCONCLUSIVE;winnerRetention3Min:FAIL;winnerRetention5Min:FAIL;adverseMeanRatioMax:INCONCLUSIVE;adverseES95RatioMax:INCONCLUSIVE;throughputRatioMin:FAIL;absoluteStrictLabelCoverageGapMax:INCONCLUSIVE |
| 1 | 2 | 12→9 | 3 | 1.2424 | 18.83% | 66.67% | 66.67% | 100.00% | 100.00% | 75.00% | precision1RatioMin:FAIL;throughputRatioMin:FAIL;absoluteStrictLabelCoverageGapMax:FAIL |
| 1 | 5 | 12→12 | 5 | 1.5306 | 0.00% | 80.00% | 60.00% | 100.00% | 100.00% | 100.00% | adverseMeanRatioMax:FAIL |
| 1 | 10 | 12→12 | 5 | 1.5306 | 0.00% | 80.00% | 60.00% | 100.00% | 100.00% | 100.00% | adverseMeanRatioMax:FAIL |
| 2 | 1 | 25→0 | 0 | UNKNOWN | UNKNOWN% | UNKNOWN | UNKNOWN | 0.00% | 0.00% | 0.00% | precision1RatioMin:INCONCLUSIVE;precision2RatioMin:INCONCLUSIVE;winnerRetention3Min:FAIL;winnerRetention5Min:FAIL;adverseMeanRatioMax:INCONCLUSIVE;adverseES95RatioMax:INCONCLUSIVE;throughputRatioMin:FAIL;absoluteStrictLabelCoverageGapMax:INCONCLUSIVE |
| 2 | 2 | 25→2 | 0 | UNKNOWN | UNKNOWN% | UNKNOWN | UNKNOWN | 0.00% | 0.00% | 8.00% | precision1RatioMin:INCONCLUSIVE;precision2RatioMin:INCONCLUSIVE;winnerRetention3Min:FAIL;winnerRetention5Min:FAIL;adverseMeanRatioMax:INCONCLUSIVE;adverseES95RatioMax:INCONCLUSIVE;throughputRatioMin:FAIL;absoluteStrictLabelCoverageGapMax:FAIL |
| 2 | 5 | 25→25 | 16 | 2.2437 | 0.00% | 81.25% | 75.00% | 100.00% | 100.00% | 100.00% | adverseMeanRatioMax:FAIL |
| 2 | 10 | 25→25 | 16 | 2.2437 | 0.00% | 81.25% | 75.00% | 100.00% | 100.00% | 100.00% | adverseMeanRatioMax:FAIL |
| 3 | 1 | 65→0 | 0 | UNKNOWN | UNKNOWN% | UNKNOWN | UNKNOWN | 0.00% | 0.00% | 0.00% | precision1RatioMin:INCONCLUSIVE;precision2RatioMin:INCONCLUSIVE;winnerRetention3Min:FAIL;winnerRetention5Min:FAIL;adverseMeanRatioMax:INCONCLUSIVE;adverseES95RatioMax:INCONCLUSIVE;throughputRatioMin:FAIL;absoluteStrictLabelCoverageGapMax:INCONCLUSIVE |
| 3 | 2 | 65→0 | 0 | UNKNOWN | UNKNOWN% | UNKNOWN | UNKNOWN | 0.00% | 0.00% | 0.00% | precision1RatioMin:INCONCLUSIVE;precision2RatioMin:INCONCLUSIVE;winnerRetention3Min:FAIL;winnerRetention5Min:FAIL;adverseMeanRatioMax:INCONCLUSIVE;adverseES95RatioMax:INCONCLUSIVE;throughputRatioMin:FAIL;absoluteStrictLabelCoverageGapMax:INCONCLUSIVE |
| 3 | 5 | 65→65 | 45 | 2.3558 | 0.00% | 84.44% | 66.67% | 100.00% | 100.00% | 100.00% | adverseMeanRatioMax:FAIL |
| 3 | 10 | 65→65 | 45 | 2.3558 | 0.00% | 84.44% | 66.67% | 100.00% | 100.00% | 100.00% | adverseMeanRatioMax:FAIL |
| 4 | 1 | 63→0 | 0 | UNKNOWN | UNKNOWN% | UNKNOWN | UNKNOWN | 0.00% | 0.00% | 0.00% | precision1RatioMin:INCONCLUSIVE;precision2RatioMin:INCONCLUSIVE;winnerRetention3Min:FAIL;winnerRetention5Min:FAIL;adverseMeanRatioMax:INCONCLUSIVE;adverseES95RatioMax:INCONCLUSIVE;throughputRatioMin:FAIL;absoluteStrictLabelCoverageGapMax:INCONCLUSIVE |
| 4 | 2 | 63→0 | 0 | UNKNOWN | UNKNOWN% | UNKNOWN | UNKNOWN | 0.00% | 0.00% | 0.00% | precision1RatioMin:INCONCLUSIVE;precision2RatioMin:INCONCLUSIVE;winnerRetention3Min:FAIL;winnerRetention5Min:FAIL;adverseMeanRatioMax:INCONCLUSIVE;adverseES95RatioMax:INCONCLUSIVE;throughputRatioMin:FAIL;absoluteStrictLabelCoverageGapMax:INCONCLUSIVE |
| 4 | 5 | 63→63 | 46 | 1.8353 | 0.00% | 84.78% | 78.26% | 100.00% | 100.00% | 100.00% | adverseMeanRatioMax:FAIL |
| 4 | 10 | 63→63 | 46 | 1.8353 | 0.00% | 84.78% | 78.26% | 100.00% | 100.00% | 100.00% | adverseMeanRatioMax:FAIL |

F1 threshold2 improves meanD30 by18.83%, but +1 precision is66.67% versus80%, throughput75% versus required80%, and strict-label coverage gap8.33pp exceeds5pp. +3/+5 retention is100% in that small calibration sample (two winners each). F2 threshold2 accepts2 anchors but neither has a strict30m label; F3/F4 accept none. Unknown outcomes are not labelled safe.

All96 results, precision/preservation1/2/3/5, D30/MAE/MFE distributions, tail counts, symbols and attribution: [all-threshold-metrics.csv](all-threshold-metrics.csv). Every numeric inner and final gate: [all-frozen-gates.csv](all-frozen-gates.csv).

## All fixed selection units

| Unit | Fit labels / anchors | Calibration labels / anchors | Threshold | Outer status |
|---|---|---|---|---|
| chrono-1 | 17/33 | 5/12 | NONE | NONE_NO_OUTER_MODEL |
| chrono-2 | 30/63 | 16/25 | NONE | NONE_NO_OUTER_MODEL |
| chrono-3 | 50/96 | 45/65 | NONE | NONE_NO_OUTER_MODEL |
| chrono-4 | 91/157 | 46/63 | NONE | NONE_NO_OUTER_MODEL |
| symbol-0-fold-1 | 10/24 | 5/11 | NONE | NONE_NO_OUTER_MODEL |
| symbol-0-fold-2 | 19/46 | 14/20 | NONE | NONE_NO_OUTER_MODEL |
| symbol-0-fold-3 | 37/74 | 40/57 | NONE | NONE_NO_OUTER_MODEL |
| symbol-0-fold-4 | 74/128 | 36/51 | NONE | NONE_NO_OUTER_MODEL |
| symbol-1-fold-1 | 12/19 | 4/8 | NONE | NONE_NO_OUTER_MODEL |
| symbol-1-fold-2 | 24/41 | 11/15 | NONE | NONE_NO_OUTER_MODEL |
| symbol-1-fold-3 | 38/60 | 37/51 | NONE | NONE_NO_OUTER_MODEL |
| symbol-1-fold-4 | 72/108 | 30/35 | NONE | NONE_NO_OUTER_MODEL |
| symbol-2-fold-1 | 15/29 | 3/9 | NONE | NONE_NO_OUTER_MODEL |
| symbol-2-fold-2 | 26/55 | 14/22 | NONE | NONE_NO_OUTER_MODEL |
| symbol-2-fold-3 | 44/85 | 33/51 | NONE | NONE_NO_OUTER_MODEL |
| symbol-2-fold-4 | 74/133 | 40/57 | NONE | NONE_NO_OUTER_MODEL |
| symbol-3-fold-1 | 16/31 | 5/11 | NONE | NONE_NO_OUTER_MODEL |
| symbol-3-fold-2 | 28/59 | 12/21 | NONE | NONE_NO_OUTER_MODEL |
| symbol-3-fold-3 | 42/85 | 31/48 | NONE | NONE_NO_OUTER_MODEL |
| symbol-3-fold-4 | 69/129 | 38/53 | NONE | NONE_NO_OUTER_MODEL |
| symbol-4-fold-1 | 15/29 | 3/9 | NONE | NONE_NO_OUTER_MODEL |
| symbol-4-fold-2 | 23/51 | 13/22 | NONE | NONE_NO_OUTER_MODEL |
| symbol-4-fold-3 | 39/80 | 39/53 | NONE | NONE_NO_OUTER_MODEL |
| symbol-4-fold-4 | 75/130 | 40/56 | NONE | NONE_NO_OUTER_MODEL |

Chronological4 and hash-complement20 models use the same family. Held groups are excluded from fitting, imputation/scaling and calibration. No new split, sparse-group rebalance, symbol-specific exception or outer fallback. Actual session/symbol leakage0. Outer OOF duplicates0; OOF performance is unmeasurable because no selected model exists. Final chronological/symbol gates are INCONCLUSIVE; the blocker is the absent admissible inner threshold, not Portfolio coverage.

## Frozen model, training and state

Risk model `MSH_ENTRY_LONG_V2_1_V1_ANCHOR_D30_RIDGE_V1`: continuous D30=max(0,-strict30m MAE), weighted Linear Ridge λ1, unpenalized intercept, numpy.linalg.solve, float64, Python3.12 / NumPy2.3.5 / threads1. All four coefficients are penalized. Output max(0,raw); raw and contributions retained. Models are serialized and hash-checked on reload.

Input order: directionalMomentum3Pct, directionalPullback6Pct, momentum3Missing, pullback6Missing. Selector Score/Rank and v1 score/probabilities are excluded from the Risk matrix. Only the first two inputs are scaled; indicators remain0/1. Fold-only observed weighted median; no global/future/zero/time fill.

Eligible FIT anchors only receive w=1/(S×d_s×n_sd). All symbols have equal total weight, no manual exception. Labelability controls supervised loss only; every calibration anchor, including unknown labels, is causally scored. Original source statuses and both missing indicators are preserved.

v1 E[L]>=2 and original shadow state are unchanged. Risk rejects consume the original symbol-session eligibility. No later timestamp replacement, WAIT, re-entry, new v1-SKIP entry, delayed price or score sizing. Frozen277 identities remain intact.

| Chronological inner | Fit labels | Momentum missing | Pullback missing | Both | Weighted medians M/P | Intercept | β M/P/mM/mP | Largest symbol weight |
|---|---|---|---|---|---|---|---|---|
| chrono-1-inner | 17 | 2 | 4 | 2 | -2.4561/-11.2000 | 1.7536 | 0.2638/-0.4689/0.0282/0.1408 | 7.69% |
| chrono-2-inner | 30 | 2 | 5 | 2 | -3.0303/-11.4754 | 2.3986 | 0.0494/-0.1871/-0.0178/0.0215 | 4.17% |
| chrono-3-inner | 50 | 5 | 11 | 5 | -3.0303/-11.2000 | 2.7331 | 0.0095/-0.1660/0.0190/-0.0478 | 2.63% |
| chrono-4-inner | 91 | 9 | 20 | 9 | -3.0675/-11.1975 | 2.4990 | 0.0998/-0.1137/0.0546/0.0301 | 1.43% |

All24 model SHAs, coefficients, medians, means/stds, missing counts, observed support, weight shares, objectives and residuals: [all-models-medians-weights.csv](all-models-medians-weights.csv). Exact FIT eligible/excluded IDs, per-event weights, symbols and sessions: run/models/*.json and run/fit-manifest.json.

## Baseline scope and unavailable selected challenger

| Metric | v1 full76 inventory | v1 common60 outer scope | Selected v2.1 |
|---|---|---|---|
| ENTER | 277.0000 | 232.0000 | UNKNOWN / no selected OOF |
| ENTER/session | 3.6447 | 3.8667 | UNKNOWN / no selected OOF |
| Unique symbols | 156.0000 | 135.0000 | UNKNOWN / no selected OOF |
| Strict30m | 181.0000 | 159.0000 | UNKNOWN / no selected OOF |
| Mean D30 | 2.5637 | 2.6776 | UNKNOWN / no selected OOF |
| D30 ES95 | 14.8949 | 16.0329 | UNKNOWN / no selected OOF |
| Entry-count Symbol HHI | 0.0550 | 0.0476 | UNKNOWN / no selected OOF |
| +1 Precision | 86.19% | 86.16% | UNKNOWN |
| +2 Precision | 72.93% | 72.96% | UNKNOWN |
| +3 Precision | 52.49% | 51.57% | UNKNOWN |
| +5 Precision | 30.94% | 29.56% | UNKNOWN |
| +1 Anchor Preservation | 100% | 100% | UNKNOWN |
| +2 Anchor Preservation | 100% | 100% | UNKNOWN |
| +3 Anchor Preservation | 100% | 100% | UNKNOWN |
| +5 Anchor Preservation | 100% | 100% | UNKNOWN |
| D30 median | 1.5337 | 1.6260 | UNKNOWN |
| D30 p90 | 5.6042 | 5.7055 | UNKNOWN |
| D30 p95 | 10.2564 | 10.4976 | UNKNOWN |
| MAE median | -1.5337 | -1.6260 | UNKNOWN |
| MAE p05 | -10.2564 | -10.4976 | UNKNOWN |
| MAE worst | -35.2941 | -35.2941 | UNKNOWN |
| MAE<=-2 count | 74 | 66 | UNKNOWN |
| MAE<=-5 count | 24 | 23 | UNKNOWN |
| MAE<=-10 count | 10 | 10 | UNKNOWN |
| MFE median | 3.3333 | 3.2362 | UNKNOWN |

96 full76 unknown labels:51 PROVIDER_GAP,25 LUNCH_BREAK,20 SESSION_END. Common60 has73 unknown labels. The saved strict30m six-bar low values agree on all181 anchors. No D30=0 substitution. No live-universe PIT claim: source3800 membership and frozen upstream are outcome-exposed; source field arrival clocks were not serialized.

## Risk decisions and winner cost

Diagnostics use nonexclusive labels: correct rejection = direct veto with observed D30>=5; false risk acceptance = ENTER with observed D30>=5; good acceptance = ENTER with MFE>=1 and D30<5. Rejected +1/+2/+3/+5 counts are separately retained even when the same path also has high adverse risk. Unknown and unsupported-input cases remain separate. These labels do not replace Gates.

| Inner fold / τ2 | Direct veto | Correct reject D30≥5 | False rejects +1/+2/+3/+5 | False accept D30≥5 | Good accept | Censored anchors |
|---|---|---|---|---|---|---|
| 1 | 3 | 0 | 2/1/0/0 | 0 | 2 | 7 |
| 2 | 23 | 2 | 13/12/6/4 | 0 | 0 | 9 |
| 3 | 65 | 7 | 38/30/22/14 | 0 | 0 | 20 |
| 4 | 63 | 2 | 39/36/23/10 | 0 | 0 | 17 |

Risk accepted/rejected D30 distributions and missingness strata are in each persisted unit. Complete per-anchor diagnostic records for all96 evaluations: risk-decisions-diagnostic.ndjson.gz. Overlapping calibration rows must not be treated as independent counts. No selected outer false-rejection/acceptance rate can be claimed.

## Secondary Portfolio and execution uncertainty

| Item | Frozen v1 common60 reference | Selected v2.1 |
|---|---|---|
| Entry anchors / EXIT-resolvable | 232 / 171 | UNKNOWN |
| Purchased / closed / unresolved | 6 / 5 / 1 | UNKNOWN |
| Initial equity | 1,000,000 JPY | 1,000,000 JPY contract only |
| Locked purchase notional | 335,300 JPY | UNKNOWN |
| Cash balance | 671,699.925 JPY | UNKNOWN |
| Final equity / Return / MaxDD | UNKNOWN: MISSING_BEFORE_EXIT | NOT_AVAILABLE: no selected OOF |
| Closed-only PF / median JPY / win rate | 1.167640 / -7369.20 / 20.00% | UNKNOWN |
| Closed-only worst / p05 JPY | -16163.00 / -15524.80 | UNKNOWN |
| Capital utilization / idle cash | UNKNOWN with unpriced exposure | UNKNOWN |
| Closed-only symbol positive / negative HHI | 1.000000 / 0.406545 | UNKNOWN |
| Closed-only effective positive / negative contributors | 1.000000 / 2.459751 | UNKNOWN |
| Closed-only profitable / losing symbols | 1 / 3 | UNKNOWN |
| Top1 / Top3 positive symbol contributions | 39360 +36,367.50 JPY; only1 net positive symbol | UNKNOWN |
| Top1 / Top3 symbol exclusion | Return and MaxDD still UNKNOWN; only1 positive symbol available | NOT_AVAILABLE |

Locked position:89180, 2024-10-15 10:30 JST,47,900shares,335,300JPY purchase notional; first missing bar before EXIT at10:50 JST. No liquidation, carry-forward mark or invented cash release. Existing +23.05% complete-case173-trade reference is a different scope and is not substituted here.

Comparator unchanged: LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1, Equal/EQUAL_MAX3, initial1mJPY,100share lots,max10concurrent,budgetdivisor3,0.05% round-trip entry-notional cost, EXIT/cash release before new Entry. Score-free Equal matches original frozen277 weighting exactly. Engine and source hashes unchanged.

Execution MFE-versus-frozen-EXIT records are stored for all232 baseline outer anchors. 89180 low-price one-JPY movement uncertainty remains; no book/spread/depth/fill observation or new price/tick/symbol gate. No executable-quality claim.

## Gates, identity, integrity and STOP

All7 inner Primary conditions and5pp coverage gap were applied before selection. Final mean-D30/ES95/precision/retention/throughput, coverage, HHI≤1.1×baseline,3/4 chronological stability, direct-risk separation and3/5 symbol stability remain INCONCLUSIVE without selected OOF. Portfolio uncertainty neither fails nor relaxes Entry gates. No BORDERLINE reinterpretation.

The detailed contract definition of macro-symbol D30 is per-arm observed accepted-symbol means without imputation. The shorter applicationScopes phrase says fixed baseline symbols; the explicit metric definition is authoritative. No macro gate was reached in this run; this prose inconsistency has no effect on NONE or the verdict.

| Identity | SHA |
|---|---|
| selectorFreezeCommit | 565d74b3dea823581fdb32380113aac5913a248d |
| selectorPayloadSHA | 3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59 |
| selectorRidgeSHA | 994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb |
| v1CandidateSHA | 4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23 |
| v1ModelSHA | b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e |
| v1ScalerSHA | 1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b |
| v1EnterIdentitySHA | 72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236 |
| p0DiagnosticSHA | 91019d3550bcfbf38e64cbc00e0f30b1cbefe44681152c82ed0b09bb3053c29d |
| globalBudgetSHA | b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f |
| v2ContractSHA | 18818ffd1157c7ba15c93eb4723c3e28945c238e0e2f6a2440bee98c7ad1267f |
| v2DevelopmentEvidenceSHA | 35cec58faedcebfd09190ed5c404e2e874647eca90b92e12bc9021ff80385a75 |
| rootCauseEvidenceSHA | 5e6f10fb978b06efb0bfdc842570c75d6a277c1515ee3b5ffca1e02e170dbe71 |
| eventIdentitySHA | 103ae204ad93ec32a772f0bd966cab3c9072d9509bb78c5a243aea200bbe57fd |
| frozenPredictionSHA | a11313909248d2c8aa1c39bac807f8a5c476c19c0be75a0e15dde41690cdb8be |

| Implementation / evidence source | SHA-256 |
|---|---|
| predict/research/phase57_msh_entry_long_v2_1_d30.py | 033e29996cde836b4f5a9c12eeac6132a047fa0faeaaa535158696f58debc5e2 |
| scripts/phase57_msh_entry_v2_1_evaluation.py | 8760101fbd86656e6433e424032d8669368726250d7762341cd49a88c2b7b182 |
| scripts/phase57_msh_entry_v2_1_development.py | 445f525062d831356f4321448bd27b883d3d199c963cbda1bab344c3e14b9585 |

Contract deviations0; Risk feature changes0; Opportunity/Selector/EXIT/Allocation/ledger changes0; model tuning0; threshold additions0; Gate changes0; retries/retimed entries0. All existing100 source pins verify.

Fresh Validation0; Entry OOS0; EXIT OOS0; Prospective0; J-Quants0; Yahoo0; other price provider0; SHORT0. The Project runner and tests ran under inherited kernel network denial. Global Fresh budget195 remains untouched. All9 Safety flags false. main unmerged.

Evidence content seal: manifest.json + manifest.sha256 (includes source implementation/test/workflow pins). Prefit48 tests PASS; delivery tests additionally verify stored model hashes/weights, all96 gate calculations, saved predictions, exact anchor subsets, no outer fallback and locked-cash accounting without new Project fit/prediction. Final GitHub CI is checked at the published head.

**STOP.** Exact next action requires a separate instruction: blocker-resolution / v2.1 Root Cause Review using this saved evidence, followed only then by a separately frozen architecture decision. No threshold interpolation, Gate relaxation, v2.2 implementation, full76 candidate refit or Fresh/OOS in this work.
