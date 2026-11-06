# MSH-Entry LONG v2 — P0 Architecture Diagnostic
**MSH_ENTRY_LONG_V2_ARCHITECTURE_DIAGNOSTIC_COMPLETE — STOP before learning.**
Historical / Development / IN-SAMPLE / Outcome-exposed。設計要件の診断完了。Entry v2性能やtail予測可能性の証明ではない。新model fit/prediction/feature selection/threshold searchは0。
結論：v1は上昇HIGHのOpportunityを選ぶが、深い逆行や実現利益の質を直接評価していない。89180の利益は7件の1円上昇に集中し、tail10件の半分は1銘柄。既存pullbackに記述的差はあるが分布は重なり、銘柄横断の予測力は未証明。次は最小Risk Veto/Quality案のPre-Development Contractを作る段階。今回は学習せずSTOP。
## Identity / scope

| Item | Value |
| --- | --- |
| Branch | research/phase57-long-only-cash-equity |
| PR | #587 Draft / unmerged |
| Source head | 159e472a4a0ec069c4e433e5d43e2f5dc7003c09 |
| Final head | This report commit; exact final hash in completion message |
| Latest main at start | 8bc850d1bbee4bae4dd3cfaefebab7ef189fc64e |
| selectorFreezeCommit | 565d74b3dea823581fdb32380113aac5913a248d |
| selectorPayloadSHA | 3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59 |
| selectorRidgeSHA | 994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb |
| candidateContractSHA | 4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23 |
| finalModelSHA | b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e |
| finalScalerSHA | 1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b |
| globalBudgetSHA | b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f |
| LONG EXIT | LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1 |
| Allocation | EQUAL_MAX3; V3_0_EQUAL arithmetic |
| Cash ledger | scripts/phase57_long_capital_integration.py (SHA in contract) |
| Period | 2024-09-17–2025-01-09 |
| Sessions / candidate events | 76 / 3800 |
| ENTER / strict30m / paired / actual Equal accepted | 277 /181 /173 /166 |
| strict30m ∩ paired | 158; strict181 is NOT the portfolio173 subset |
| Reference PDF | Named Entry v2 handoff PDF not present; user full specification + repo evidence used |

Entry v1 threshold2.0, features score/rank, model/scaler unchanged. Saved predictions only; no inference rerun. Feature timestamps can be causal while models were fitted on exposed Development: no retrospective real-time performance claim.
## P0 — Tail / winner / joint path

| Metric | strict181 result |
| --- | --- |
| MAE median % | -1.534 |
| MAE p05 % | -10.256 |
| MAE worst % | -35.294 |
| MAE<=−10 | 10/181 (6 symbols;5 events one symbol) |
| MFE median % | 3.333 |
| Later CLOSE reclaim after −10 touch | 2/10 within strict30m; hit-bar order not inferred |
| Intrabar order unknown | 7/181 extrema fall in same bar |


| MAE bucket | LT1 | 1_TO_2 | 2_TO_3 | 3_TO_5 | GE5 | Total |
| --- | --- | --- | --- | --- | --- | --- |
| SAFE_LOW_ADVERSE | 2 | 6 | 12 | 15 | 41 | 76 |
| MILD_ADVERSE | 4 | 4 | 9 | 7 | 7 | 31 |
| MODERATE_ADVERSE | 11 | 9 | 13 | 12 | 5 | 50 |
| SEVERE_ADVERSE | 4 | 3 | 2 | 4 | 1 | 14 |
| EXTREME_FAILURE | 4 | 2 | 1 | 1 | 2 | 10 |

MAE buckets exactly user boundaries: >−1; (−2,−1]; (−5,−2]; (−10,−5]; <=−10. MFE buckets <1;[1,2);[2,3);[3,5);>=5. No retuning. Extreme10 includes2 +5 and3 +3 opportunities: bad-path removal must quantify winner sacrifice. Max HIGH is not sellable PnL.

| Group | 277-side N | strict30m N | Net30 mean % | Net30 median % | Net30 PF | MFE median % | MAE median % | Tail<=−10 N | LONG EXIT N/mean % | Portfolio accepted N/PnL JPY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXTREME_FAILURE | 10 | 10 | -7.263 | -8.497 | 0.132 | 1.243 | -12.087 | 10 | 10/-8.179 | 10/-296,652.15 |
| MILD_ADVERSE | 31 | 31 | 1.412 | 0.729 | 4.688 | 2.707 | -1.576 | 0 | 30/0.811 | 26/86,592.45 |
| MODERATE_ADVERSE | 50 | 50 | -0.198 | -0.571 | 0.822 | 2.293 | -3.164 | 0 | 48/-1.024 | 42/-155,049.15 |
| SAFE_LOW_ADVERSE | 76 | 76 | 3.843 | 1.887 | 172.230 | 5.544 | 0.000 | 0 | 69/2.478 | 63/599,351.95 |
| SEVERE_ADVERSE | 14 | 14 | -2.824 | -4.141 | 0.220 | 1.976 | -5.853 | 0 | 13/-2.676 | 11/-83,285.75 |


| Group | 277-side N | strict30m N | Net30 mean % | Net30 median % | Net30 PF | MFE median % | MAE median % | Tail<=−10 N | LONG EXIT N/mean % | Portfolio accepted N/PnL JPY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1_TO_2 | 24 | 24 | -1.464 | -0.266 | 0.211 | 1.329 | -2.786 | 2 | 23/-1.985 | 18/-161,773.80 |
| 2_TO_3 | 37 | 37 | -0.380 | -0.050 | 0.604 | 2.389 | -1.692 | 1 | 35/-1.429 | 30/-164,030.60 |
| 3_TO_5 | 39 | 39 | 0.931 | 1.512 | 2.462 | 3.810 | -1.626 | 1 | 36/0.487 | 34/105,279.35 |
| GE5 | 56 | 56 | 5.548 | 4.378 | 23.341 | 11.507 | 0.000 | 2 | 52/3.859 | 49/676,296.95 |
| LT1 | 25 | 25 | -3.360 | -1.990 | 0.010 | 0.260 | -3.539 | 4 | 24/-3.874 | 21/-304,814.55 |


| Extreme event | MAE% | MFE% | E[L] | Selector score | Price | Net30% | LONG exit net% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-10-11|2024-10-11T14:00:00+09:00|190A0 | -10.429 | 1.227 | 2.160 | 95.967 | 326 | -9.252 | -4.958 |
| 2024-11-08|2024-11-08T09:30:00+09:00|81070 | -10.256 | 2.564 | 3.193 | 170.874 | 39 | -7.742 | -7.742 |
| 2024-11-14|2024-11-14T10:00:00+09:00|70690 | -11.317 | 0.435 | 2.494 | 120.144 | 919 | -9.734 | -7.341 |
| 2024-11-29|2024-11-29T13:30:00+09:00|57590 | -12.857 | 5.714 | 2.030 | 90.101 | 70 | -11.479 | -2.907 |
| 2024-12-20|2024-12-20T09:30:00+09:00|57590 | -11.111 | 3.704 | 2.820 | 140.516 | 27 | -3.754 | -11.161 |
| 2024-12-20|2024-12-20T13:00:00+09:00|95620 | -12.929 | 1.259 | 2.894 | 146.048 | 1748 | -12.865 | -11.778 |
| 2024-12-24|2024-12-24T09:30:00+09:00|49350 | -13.644 | 0.000 | 2.427 | 113.293 | 2895 | -5.231 | -3.332 |
| 2024-12-25|2024-12-25T09:30:00+09:00|57590 | -35.294 | 0.000 | 3.077 | 160.687 | 17 | -23.579 | -23.579 |
| 2024-12-26|2024-12-26T09:30:00+09:00|57590 | -11.111 | 11.111 | 3.383 | 189.896 | 9 | 11.061 | 11.061 |
| 2024-12-27|2024-12-27T09:30:00+09:00|57590 | -20.000 | 0.000 | 2.333 | 107.105 | 5 | -0.050 | -20.050 |

## P1/P7/P8 — Feature inventory / PIT / descriptive separation
27 fields inventoried:17 conditionally causal-formula fields (includes time, constants and redundant fields; NOT17 selected predictors),8 unavailable numeric snapshots,1 dated Master exact release-clock unknown,1 saved in-sample MSH score. Raw per-feature timestamp vectors are not retained; safety audit combines frozen builder source guards, source pins,3800 decision provenance and prior-selection ordering. This does not prove real-time latency or availability after provider arrival. Frozen L1 cross-section filters feature rows by future label availability; daily eligibility/adjustment metadata release clocks are not serialized. Therefore17 is conditional formula-time causality, not full-pipeline PIT certification. Original minute normalizer also maps missing volume/turnover to0; verify original missing counts before promoting any volume-derived feature.

| Field | Available /277 | Available /181 | PIT status | Preliminary class |
| --- | --- | --- | --- | --- |
| ridgeScore | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | CORE_CANDIDATE |
| ridgeRank | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | CORE_CANDIDATE |
| decisionPrice | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | DIAGNOSTIC_ONLY |
| timeOfDay | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | STATE_ONLY |
| minutesFromOpen | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | STATE_ONLY |
| segment | 277 | 181 | DATED_MASTER_RELEASE_CLOCK_UNPROVEN | DIAGNOSTIC_ONLY |
| liquidityBucket | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | DIAGNOSTIC_ONLY |
| directionalMomentum3Pct | 233 | 168 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | OPTIONAL_CANDIDATE |
| directionalMomentumAccelerationPct | 150 | 100 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | OPTIONAL_CANDIDATE |
| directionalPullback6Pct | 197 | 144 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | OPTIONAL_CANDIDATE |
| relativeVolume5 | 197 | 144 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | OPTIONAL_CANDIDATE |
| directionalReturnFromOpenPct | 202 | 122 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | OPTIONAL_CANDIDATE |
| directionalVwapDistancePct | 108 | 86 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | OPTIONAL_CANDIDATE |
| minutesSinceFirstSelection | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | STATE_ONLY |
| priorSelectionCount | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | STATE_ONLY |
| decisionPriceAgeMinutes | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | STATE_ONLY |
| hybridReciprocalRank | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | REJECT |
| direction | 277 | 181 | CONDITIONAL_HISTORICAL_FORMULA_CAUSAL | REJECT |
| mshScore | 277 | 181 | DIAGNOSTIC_FROZEN_IN_SAMPLE_SCORE | DIAGNOSTIC_ONLY |
| absoluteVolumeState | 0 | 0 | UNKNOWN | UNKNOWN |
| cumulativeTurnover | 0 | 0 | UNKNOWN | UNKNOWN |
| gapFromPriorClose | 0 | 0 | UNKNOWN | UNKNOWN |
| intradayRange | 0 | 0 | UNKNOWN | UNKNOWN |
| recentVolatility | 0 | 0 | UNKNOWN | UNKNOWN |
| spreadProxy | 0 | 0 | UNKNOWN | UNKNOWN |
| recentBarStructure | 0 | 0 | UNKNOWN | UNKNOWN |
| marketWideContext | 0 | 0 | UNKNOWN | UNKNOWN |

Full definitions/source/timestamp/availableAt/lookback/missing/session/previous-session/fill/overlap/leakage/complexity/direction are in feature-inventory.json. No missing fill. VWAP is cumulative HLC3-volume PROXY, not traded-turnover VWAP. Segment is diagnostic-only until Master release semantics verified. Absolute liquidity, spread, gap, volatility and breadth snapshots were not silently reconstructed from outcome paths.

| Fixed descriptive panel | Tail / non-tail available | Median tail / non-tail | Cliff delta | Tail in non-tail range | +3 /+5 winner medians | Delta excluding dominant-tail symbol |
| --- | --- | --- | --- | --- | --- | --- |
| decisionPrice | 10/171 | 54.500/355.000 | -0.246 | 0.900 | 278.000/111.500 | 0.250 |
| directionalMomentum3Pct | 8/160 | -4.410/-3.237 | -0.001 | 0.625 | -3.333/-3.391 | 0.143 |
| directionalPullback6Pct | 8/136 | -19.728/-11.111 | -0.493 | 1.000 | -11.111/-11.111 | -0.251 |
| relativeVolume5 | 8/136 | 0.384/0.521 | -0.270 | 1.000 | 0.388/0.349 | -0.123 |
| directionalVwapDistancePct | 6/80 | -7.822/-6.640 | -0.425 | 0.833 | -6.489/-6.742 | -0.095 |
| decisionPriceAgeMinutes | 10/171 | 0.000/0.000 | 0.026 | 1.000 | 0.000/0.000 | 0.136 |

Six fields were fixed by semantics before new distribution analysis. Delta=P(tail value>non-tail)−P(<), ties0; descriptive only, no cutoff/AUC search. After cohort inspection, dominant-tail-symbol removal was added as an influence diagnostic, not a filter or candidate selection.
Pullback6 has the largest absolute difference among retained market-state panel fields: median−19.73% vs−11.11%, delta−0.493. However all8 observed extreme values lie within non-tail range,5 are57590; removing that symbol leaves only3 extreme observations and delta−0.251. Same-symbol direction agrees for57590 and81070, but only2 symbols support both groups. This is an OPTIONAL hypothesis, not established cross-symbol prediction.
VWAP proxy delta−0.425 falls to−0.095 after dominant-tail removal (only2 tail observations); available only108/277. Relative-volume tail median0.384 is close to +5-winner median0.349: low-volume rejection could remove winners. Momentum delta≈0; freshness nearlyconstant. Price direction flips on removing57590 and89180 has7–8JPY entries: no price threshold or spread conclusion justified. Classifications remain semantic candidates, not performance-selected features.

| Signal | Within-symbol tail/non-tail delta |
| --- | --- |
| decisionPrice | 49350(1/2):1.000; 57590(5/6):-0.467; 81070(1/2):1.000 |
| directionalMomentum3Pct | 57590(5/6):-0.300; 81070(1/2):1.000 |
| directionalPullback6Pct | 57590(5/6):-0.667; 81070(1/2):-1.000 |
| relativeVolume5 | 57590(5/6):-0.200; 81070(1/2):0.000 |
| directionalVwapDistancePct | 57590(4/6):-0.583; 81070(1/2):0.000 |
| decisionPriceAgeMinutes | 49350(1/2):1.000; 57590(5/6):-0.167; 81070(1/2):0.000 |

## P2/P3/P9/P10 — Opportunity, symbol generalization and concentration
89180:61 ENTER in277;21 strict30m;22 portfolio accepted. All21 strict paths have MFE>=5 andMAE0. Of22 selected-exit trades,7 profit and15 gross-flat (cost-only loss). Every profitable exit is7→8JPY or8→9JPY: a1JPY move equals14.29% or12.5%, amplified by many shares under equal-notional sizing. This observed price-scale mechanism explains the large HIGH label/PnL concentration; it does NOT establish tick size, spread, available depth or executable fill.
The remaining39/61 entries for89180 lack selected-exit outcome. Observed successful paths cannot establish quality on all61. Comparisons are descriptive; no symbol rule.

| Net contribution group | Symbols | JPY | Share total net | Share corresponding positive/negative symbol contribution |
| --- | --- | --- | --- | --- |
| Profit top1 | 89180 | 334,449.55 | 1.451 | 0.378 |
| Profit top3 | 89180,90730,38250 | 473,822.10 | 2.055 | 0.536 |
| Profit top5 | 89180,90730,38250,39360,29620 | 548,251.85 | 2.378 | 0.620 |
| Loss top1 | 57590 | -120,721.00 | — | 0.185 |
| Loss top3 | 57590,95620,51310 | -190,102.80 | — | 0.291 |
| Loss top5 | 57590,95620,51310,81070,36640 | -239,826.45 | — | 0.367 |

156 symbols in277;106 accepted symbols, profitable53, losing53. Positive-net-symbol HHI=0.1656; negative-net-symbol HHI=0.0558. HHI squares normalized positive/negative NET SYMBOL contributions separately; it is not trade-level gross profit/loss HHI. Profit concentration is stronger, losses also repeated. 57590 contributes5/10 extreme paths and−120,721JPY net.

| Existing SAME Equal cash replay | Final equity JPY | Return% | DD% |
| --- | --- | --- | --- |
| FULL | 1,230,530.70 | 23.053 | 20.169 |
| EXCLUDE_TOP1_TRADE | 1,133,503.35 | 13.350 | 20.169 |
| EXCLUDE_TOP1_SYMBOL | 921,445.63 | -7.855 | 25.266 |
| EXCLUDE_TOP3_TRADES | 1,053,943.17 | 5.394 | 20.284 |
| EXCLUDE_TOP3_SYMBOLS | 802,946.88 | -19.705 | 27.845 |

For all major top5 symbols, per-symbol PnL/PF/Precision/MAE/MFE/score distribution and fixed-quantity leave-one-out attribution are saved in diagnostic.json.gz. Top1/top3 removal results above are actual existing cash replays; other single-symbol deletions are explicitly additive, NOT self-financing portfolio return.

| PIT field | Top1 median | Top3 median | Other median |
| --- | --- | --- | --- |
| decisionPrice | 7.000 | 7.000 | 433.000 |
| directionalMomentum3Pct | 0.000 | -4.570 | -3.328 |
| directionalPullback6Pct | -12.500 | -12.500 | -10.838 |
| relativeVolume5 | 0.286 | 0.462 | 0.539 |
| directionalVwapDistancePct | -7.674 | -7.687 | -6.860 |
| decisionPriceAgeMinutes | 0.000 | 0.000 | 0.000 |

## P4 — Score calibration
These quartiles use strict181 (46/45/45/45), NOT prior portfolio accepted166 quartiles. Return here is exact+30m CLOSE reference minus0.05pp; frozen LONG EXIT returns and denominators are separate. This diagnostic does not change EXIT.

| Quartile | N | Mean net30% | Median% | PF | Positive% | Mean MFE% | Mean MAE% | MAE<=−10 | +1/+2/+3/+5 hits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | 46 | 0.879 | 0.480 | 1.981 | 56.522 | 3.554 | -1.875 | 1 | 36/31/22/10 |
| Q2 | 45 | 0.689 | 0.409 | 1.838 | 51.111 | 4.867 | -2.135 | 1 | 41/33/21/13 |
| Q3 | 45 | 0.655 | 0.333 | 1.551 | 51.111 | 3.599 | -3.084 | 3 | 36/31/21/11 |
| Q4 | 45 | 2.509 | 0.800 | 2.570 | 57.778 | 7.447 | -3.176 | 5 | 43/37/31/22 |

Return, MFE, MAE and tail safety monotonicity all FALSE. Q4 captures more+5 but also5/45 deep adverse paths. E[L] is expected ordinal HIGH opportunity, NOT expected return/tail probability/size utility. Formal probability-calibration error was not tested; no claim of fitted score being prospectively calibrated.
## P5/P6 — Time / segment / liquidity

| Group | 277-side N | strict30m N | Net30 mean % | Net30 median % | Net30 PF | MFE median % | MAE median % | Tail<=−10 N | LONG EXIT N/mean % | Portfolio accepted N/PnL JPY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFTERNOON | 32 | 25 | 0.526 | 0.912 | 1.385 | 2.679 | -1.692 | 2 | 23/0.587 | 21/43,818.75 |
| AFTERNOON_OPEN | 23 | 16 | 0.815 | 0.878 | 1.526 | 2.163 | -1.232 | 1 | 16/-1.193 | 15/-67,778.00 |
| CLOSE | 40 | 11 | 0.870 | -0.050 | 1.873 | 2.277 | -2.435 | 0 | 12/-0.201 | 3/2,671.20 |
| MORNING | 68 | 54 | 0.993 | 0.371 | 1.838 | 3.340 | -1.240 | 1 | 50/0.811 | 43/202,056.80 |
| OPEN | 72 | 64 | 1.618 | 0.817 | 2.673 | 3.961 | -1.297 | 6 | 63/0.162 | 60/10,085.40 |
| PRE_LUNCH | 42 | 11 | 1.897 | -0.050 | 3.663 | 3.333 | -1.783 | 0 | 28/0.360 | 24/39,676.55 |


| Group | 277-side N | strict30m N | Net30 mean % | Net30 median % | Net30 PF | MFE median % | MAE median % | Tail<=−10 N | LONG EXIT N/mean % | Portfolio accepted N/PnL JPY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GROWTH | 117 | 89 | -0.123 | 0.333 | 0.919 | 2.550 | -2.079 | 8 | 95/-0.951 | 77/-277,226.20 |
| PRIME | 14 | 11 | -0.336 | 0.200 | 0.779 | 0.999 | -1.752 | 0 | 12/0.275 | 10/8,917.40 |
| STANDARD | 146 | 81 | 2.820 | 0.846 | 5.396 | 4.651 | -0.733 | 2 | 85/1.646 | 79/498,839.50 |


| Group | 277-side N | strict30m N | Net30 mean % | Net30 median % | Net30 PF | MFE median % | MAE median % | Tail<=−10 N | LONG EXIT N/mean % | Portfolio accepted N/PnL JPY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HIGH | 252 | 172 | 1.271 | 0.389 | 2.285 | 3.245 | -1.354 | 6 | 182/0.519 | 157/373,563.10 |
| LOW | 4 | 0 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | 0 | 1/-5.313 | 1/-20,391.90 |
| MID | 21 | 9 | -0.544 | 2.172 | 0.853 | 3.795 | -5.556 | 4 | 9/-4.024 | 8/-122,640.50 |

Open has6/64 observed tails; Growth8/89 (5 from57590), Standard2/81. Mid liquidity4/9 versusHigh6/172; Low has0 evaluable out of4 and cannot be called safe. Groups overlap and condition on Selector/Entry/coverage; no independent sector/regime causality, no segment/liquidity/time filter. Within-group score tables retained in compressed diagnostic.
## Coverage minimum and fair comparison
Strict30m missing96:51 absent expected slots,20 session end,25 lunch. PROVIDER_GAP is inherited reason name, not proof whether a missing slot is no-trade or provider loss. Portfolio excluded104:65 missing before LONG EXIT,20 no remaining normal bar,19 another comparison candidate censored. Selected LONG alone resolves192/277, but this is NOT a new portfolio subset or result. Existing173 paired and181 strict overlap158 only. All28 15:00 entries excluded from portfolio; no execution inference from label absence.
15:25-start auction interval after2024-11-05 remains unresolved as regular-bar versus auction representation. No NEW forward fill, future substitution or fabricated liquidation. Inherited future-label-availability membership and raw missing-volume-to-zero handling are disclosed, not certified safe or silently corrected. Exact source clock, calendar/lunch and price reference definitions retained. Full277 portfolio unknown. This does not prevent this descriptive architecture diagnostic, but complete challenger portfolio needs existing-cache path projection for all possible3800 candidate entries.
## P12–P15 — Failure attribution, requirements, architecture questions

| Failure | Verdict | Evidence |
| --- | --- | --- |
| TAIL_FAILURE_NOT_DETECTED | TRUE | 10/181 enter paths have MAE<=−10%;5 are57590. v1 score has no explicit adverse-risk meaning. Detectability before entry remains unproven. |
| OPPORTUNITY_TRADABILITY_CONFUSED | PARTIAL | 2/10 extreme paths also reach+5%;89180 has21/21 +5 HIGH opportunities but only7/22 profitable chosen exits. Target mismatch is established; actual executable fill quality is unmeasured. |
| SCORE_NOT_CALIBRATED_FOR_REALIZED_OUTCOME | TRUE | Strict181 score-quartile return/MFE/MAE/tail directions all nonmonotonic; Q4 tail5/45 vsQ1 1/46. No claim that the ordinal probabilities themselves fail formal probability calibration. |
| CROSS_SYMBOL_GENERALIZATION_WEAK | PARTIAL | Top1/Top3 symbol removal cash replay−7.86%/−19.71%; profit concentration and tail influence material. No held-symbol out-of-sample model evaluation performed. |
| COVERAGE_EXECUTION_SEMANTICS_LIMITATION | TRUE | 96/277 lack strict30m;104 excluded from common173;full277 equity unknown. Upstream L1 membership filters on future-label availability. Same-close reference is not guaranteed execution. |
| OTHER_PRICE_GRANULARITY_AND_DEPENDENCE | PARTIAL | 89180 seven profitable exits are7→8 or8→9 JPY,15 exits gross-flat; loss10 observations cover6 symbols, half one symbol. Tick size/spread and causal fill harm not measured. |


| Priority | Architecture dependency |
| --- | --- |
| 1 | Preserve PIT field/missing semantics and denominator identity |
| 2 | Separate upside opportunity from adverse-path risk meaning |
| 3 | Assess severe/moderate/extreme + winners jointly with symbol influence control |
| 4 | Define calibration target and group/chronological evaluation |
| 5 | Same-downstream throughput/preservation/portfolio robustness trade-off |

**mustPreserve:** Frozen Selector; cash-equity LONG only; same Decision Price reference and PIT timestamps; reasonable throughput with denominator disclosure; +3/+5 opportunity preservation; simple execution state; same-session scope; Frozen EXIT/Equal/cash ledger comparator
**mustImprove:** deep adverse tails and frequency; cross-symbol quality and top1/top3 sensitivity; score interpretation/calibration; portfolio PF/MaxDD/median direction; winner-risk trade-off transparency
**mustNot:** symbol ID predictor/blacklist/symbol model/threshold; 89180 or57590 special rules; post-hoc time/segment/liquidity filter; future MAE/MFE/reclaim/EXIT/PnL feature; feature zoo; Validation/OOS tuning; score-based sizing; silent outcome-selected coverage expansion

| Question | Recommendation, NOT freeze |
| --- | --- |
| Q1 | Prefer a small new risk/quality responsibility alongside frozen opportunity, rather than only changing v1 threshold; architecture not frozen. |
| Q2 | MULTIPLE: opportunity/tradability separation, realized-outcome calibration, tail failure and cross-symbol dependency. |
| Q3 | Non-score market state is justified for investigation; incremental predictive value not yet demonstrated. Six-field fixed descriptive panel only. |
| Q4 | ENTER/SKIP is the initial comparator proposal; no evidence requires WAIT. Final state not frozen. |
| Q5 | Keep risk and opportunity meanings separate; separate outputs do not mandate two independently complex models. |
| Q6 | Retain ordinal opportunity as a preservation benchmark/possible auxiliary; do not let HIGH-touch ordinal alone define tradability. |
| Q7 | Tail auxiliary may be useful, but10 extreme events across6 symbols cannot support a complex tail-only classifier; include severity continuum and censored labels. |
| Q8 | Do not use score for sizing; Equal remains frozen. |
| Q9 | Predeclare symbol-disjoint grouped evaluation plus chronological evaluation with overlapping label-window purge; show symbol-macro and event-micro statistics, top-contributor and dominant-tail influence. All remain Development; Frozen Selector was already outcome-exposed. |
| Q10 | Existing3800 candidates/1828 strict labels and existing feature snapshots support a later Development contract and small experiment; complete whole-universe executable portfolio is not currently established. |


| Family | Disposition | Reason |
| --- | --- | --- |
| C Opportunity Gate + Risk Veto | FIRST_PREDEVELOPMENT_FAMILY_TO_SPECIFY_NOT_SELECTED | Keep Frozen Selector opportunity; test a small independently interpretable adverse-risk gate. No veto threshold chosen. |
| A Single Quality Model | MINIMAL_ALTERNATIVE_FOR_NEXT_CONTRACT | May suffice if a clearly defined net-quality target can balance tail and preservation; no composite weight chosen. |
| B Two-Head | RESERVE_NOT_DEFAULT | Separate risk/quality meanings useful, but only10 extreme events and existing opportunity Selector do not justify duplicating opportunity training or a complex shared model. |
| D Minimal Stateful / WAIT | DEFER_NO_TIMING_COUNTERFACTUAL_EVIDENCE | Waiting changes timestamps/prices and label windows; this diagnostic does not test causal delayed entry. |
| Symbol models / broad feature ensembles / targetless score blending | REJECT_FOR_THIS_DESIGN | Violates symbol-generalization, small-sample simplicity or explicit score meaning. |

C is the first family to specify in the next contract, not a selected architecture. A is a minimal alternative. B is reserve; D WAIT deferred; symbol models/feature zoo rejected. Model family, targets, features, state and numeric gates remain UNFROZEN.
Fair comparator draft: same3800 events/76 sessions/Frozen Selector/reference/0.05% cost/LONG EXIT/Equal/1mJPY/100share/10positions/ledger/event order/missing semantics. Entry alone varies. Each arm has its own causal accepted set; comparing only intersected ENTERs would hide throughput and preservation. Same symbol-session grouped, chronological and held-symbol evaluation plus overlap purge; all still Development, because upstream was outcome-exposed.
**Required entry metrics:** ENTER count/rate/per-session; unique symbols/trades-per-symbol; time/segment/liquidity distribution; feature missingness and censoring by arm
**Required opportunity metrics:** +1/+2/+3/+5 Precision and Preservation against SAME frozen available candidate label denominator; MFE; remaining opportunity at decision
**Required risk metrics:** MAE median/p05/worst; MAE<=−2/−5/−10; first-bar adverse; later observed reclaim with missing flag
**Required calibration metrics:** score quantiles vs net return/PF/MFE/MAE/tail; score definition-specific calibration, not arbitrary score monotonicity only
**Required portfolio metrics:** Final Equity/Return/PF/MaxDD; Median trade/Win rate; cash utilization/accepted/rejected count
**Required robustness metrics:** Top1 trade/symbol andTop3 trades/symbols removed descriptive cash replays; Top5 symbols if support; positive/negative contribution HHI; profitable/losing symbols/median symbol contribution/dispersion; leave-major-symbol-out; dominant-tail-symbol influence
Trade-offs explicit; do not demand every metric improve or invent PF/MAE/DD numerical gates after outcomes. Next Pre-Development Contract must fix score meaning, minimal features/model, missing-state policy, split and quantitative trade-off gates BEFORE Entry v2 fit.
## STOP / counters / artifacts
Frozen components changed0. Entry v2 fit0/prediction0; v1 fit0/prediction0. Fresh0/OOS0/Prospective0; J-Quants0/Yahoo0/other provider0. Global195 sessions untouched, exact budget SHA checked. All9 safety false; no main merge. Historical statement reuse and diagnostic outputs only.
Artifacts: diagnostic.json.gz (all277, per-symbol, calibration, panel distributions, coverage); feature-inventory.json; architecture-decision.json; fair-comparator-draft.json; diagnostic contract/source pins; offline integrity tests and CI. Final head and final-head CI reported in completion message.
