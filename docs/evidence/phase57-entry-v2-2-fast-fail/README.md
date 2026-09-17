# Phase57 Entry v2.2 FAST-FAIL — FAST_FAIL_KILL

Historical / Development / outcome-exposed only. Protocol was published in commit `ab6fa75fa778b2790165781e7c7749cb596d4741` before Project target computation, fit or prediction. No full Development or new Portfolio replay was performed.

**Stop this hypothesis.** A positive-return score has a small descriptive signal, but the fixed breakeven screen worsens adverse paths and loses too many frozen v1 winners. No new thresholds, targets, inputs or model settings were tried after this finding.

| Precommitted requirement | Observed | Result |
|---|---:|---|
| Chronological positive rank direction ≥3/4 | 3/4 | PASS |
| Held-symbol positive rank direction ≥3/5 | 3/5 | PASS |
| Chronological MSE improvement over train-only constant >0 | 0.2504% | PASS, small |
| Held-symbol MSE improvement >0 | 0.4532% | PASS, small |
| Positive-band mean D30 no worse | 1.6867% → 2.0410% (+21.00%) | FAIL |
| Retain ≥90% of v1 +3 winners | 67/82 = 81.7073% | FAIL |
| Retain ≥90% of v1 +5 winners | 36/47 = 76.5957% | FAIL |
| Retain ≥80% of v1 anchor count in score band | 206/232 = 88.7931% | PASS |

These are **score-band diagnostics**, not executable ENTER counts or cash Portfolio returns. D30 comparison in this table uses all held candidates versus the positive-score band; winner-retention denominators use exact frozen v1 anchors on the same held timestamps. The two denominators must not be conflated.

## Hypothesis and scope

One signed continuous target: frozen LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1 net reference return, `Q = 100*(exitReference/decisionPrice - 1) - 0.05`. This rewards retained upside and penalizes realized-reference loss under a fixed downstream exit. It does not itself penalize an adverse excursion followed by recovery; D30 is therefore a separate evaluation check. Reference closes are not verified executable fills.

Exact inputs: Selector Ridge Score, Momentum3, Pullback6, Momentum missing, Pullback missing. Selector score supplies upside context to a signed-quality target; this is not labelled an independent risk model. No symbol, price, time, liquidity, rank, future label, new feature or execution proxy enters the prediction. Training-fold weighted medians and weighted raw mean/std only; unscaled missing indicators. Weighted Ridge λ=1, numpy.linalg.solve, signed linear output, no clipping, weight 1/(S*d_s*n_sd), unpenalized intercept.

The only diagnostic cut is predicted Q>0 (net economic breakeven). No cut was selected by performance. No Entry state, timing replacement, sizing or Portfolio implementation was built. Prior D30 threshold-veto failures remain immutable evidence.

## Bounded evaluation

Four expanding chronological windows: 16→15, 31→15, 46→15 and 61→15 sessions. Five fixed-hash held-symbol groups use only the last chronological evaluation window. All train/eval session and symbol-session intersections are zero; held-symbol intersections are zero in the five group tests. All label endpoints precede the next held block. No alternative split, inner threshold calibration or extra fit was used.

| Unit | Training / target available | Held / target available | Spearman | MSE skill |
|---|---:|---:|---:|---:|
| chrono-1 | 800/380 | 750/380 | -0.015573 | 0.1143% |
| chrono-2 | 1550/760 | 750/378 | 0.078319 | 0.0289% |
| chrono-3 | 2300/1138 | 750/380 | 0.122875 | 0.4645% |
| chrono-4 | 3050/1518 | 750/379 | 0.068117 | 0.3052% |
| symbol-0 | 2381/1218 | 169/80 | 0.245643 | 0.2876% |
| symbol-1 | 2315/1191 | 226/106 | 0.004828 | -0.0551% |
| symbol-2 | 2505/1246 | 112/56 | 0.190035 | 1.0553% |
| symbol-3 | 2531/1205 | 125/79 | -0.000645 | 1.2974% |
| symbol-4 | 2468/1212 | 118/58 | -0.171832 | -0.1745% |

Exactly 9/9 Project fits succeeded and 3,750 numerical predictions were saved: 3,000 chronological records plus 750 separate last-window held-symbol records. Duplicate IDs within each scope=0. The 750 held-symbol records overlap the chronological scope by design and must not be counted as new observations. The first16 sessions are training warm-up only.

MSE skill compares each trained model with its training-fold symbol-weighted constant mean; evaluation error is symbol/session/event balanced within a unit and units are pooled equally. Spearman is event-level with average tied ranks. Repeated observations are not independent statistical evidence; no significance or p-value claim is made.

## Winner and adverse-path coexistence

| Held chronological score band | All scores | Q prediction >0 |
|---|---:|---:|
| Candidate events | 3000 | 927 |
| Target-evaluable events | 1517 | 494 |
| Mean frozen-exit net reference return | -0.072950% | -0.000236% |
| Reference-return PF (not Portfolio PF) | 0.929371 | 0.999807 |
| Strict30m evaluable | 1451 | 492 |
| Mean D30 | 1.686699% | 2.040966% |
| D30 ES95 | 9.216446% | 11.756784% |
| D30 ≥10 count / strict30m N | 18/1451 | 11/492 |
| Median MFE | 1.709402% | 2.372742% |

The positive-score band increases upside opportunity but also selects more adverse paths. Its mean net reference return is still approximately zero after the frozen cost. Among v1 anchors alone, mean D30 moves 2.677622%→2.558126% (4.46% reduction), while +3 and +5 winner retention falls below90%. This supporting subset does not replace the preregistered Full Replacement screen or its gates.

Top-two reference-contribution symbol removal (89180, 67400; ranked by repeated-event net return sums, **not Portfolio contribution**) leaves Spearman 0.020969 and MSE skill 0.1463%. Direction remains slightly positive; this experiment does not establish that two-symbol dependency is the primary cause of failure. No symbol was excluded from fitting or runtime scoring.

## Coverage, PIT and Portfolio limits

Shared universe: 76 sessions, 2024-09-17–2025-01-09, 760 decision timestamps, 3,800 Top5 events. Frozen v1: 353 raw qualified, 277 state-constrained anchors, 181 strict30m labelable and96 unlabelable. The new fixed-exit target is observable for1,897/3,800;1,903 are unknown (1,743 missing before EXIT;160 no remaining regular bar). Strict D30 is observable for1,828 of3,800. Censored outcomes are excluded from training loss/metrics only and remain NULL in the ledger. All3,750 held candidate records were scored before evaluator-side label joins.

Positive-band target coverage differs by2.7235pp and D30 coverage by4.7078pp from all chronological scores, both inside the precommitted5pp screen. This does not prove missingness is random. Results are conditional on available labels. No fill, interpolation, substitution or missing-as-zero was used.

Existing feature code enforces completed-bar availableAt<=decision. Saved rows do not serialize every raw arrival clock. The inherited3800 membership and Frozen Selector/v1 training are outcome-exposed; this is not a clean full-stack OOS experiment. The new model alone uses chronological or held-symbol train/eval isolation.

Portfolio evidence is reused: full-stream unresolved position1, locked cash335,300 JPY. Final Equity/MaxDD remain UNKNOWN. The prior+23.05% belongs to173 complete-case trades. No new Portfolio replay, synthetic liquidation, cash release, engine change, or execution quality filter was introduced. Low-price/tick/spread/depth/fill uncertainty remains diagnostic.

## Decision and one next proposal

Kill this signed-mean-reference-return / five-input Ridge / economic-breakeven hypothesis; not every possible Entry Quality target.

ONE minimal joint-success classifier: probability of a positive frozen-EXIT net reference result AND an independently specified acceptable adverse path. Predefine the path budget from the objective, not this result; use one low-capacity model. This replaces the signed-mean objective rather than changing its cut or adding a D30 veto.

Predictability is unproven. Requires a separate minimal preregistered screen; no numeric target boundary chosen here.

**STOP.** No full Development contract or candidate freeze is warranted for this screen. The next proposal is not implemented or evaluated. Do not rescue the failed mean-return score through a different cutoff, feature expansion, stronger model or Fresh data.

## Integrity and artifacts

- Branch: `research/phase57-long-only-cash-equity`; PR#587 remains Draft/unmerged.
- Starting head: `e9c0f64674bd759bae369085c179522136992898`; latest-main-at-start: `c48be22db7deef286b0bb5dc1951964431145908`.
- Protocol SHA: `5349d28259b0764385a8de3b29038464eb8d639c992427df76a3fceb671ee5c6`.
- Source pins:107 verified, including Selector/v1/EXIT/Allocation/ledger and both failure lineages.
- Prefit:15 synthetic/contract/leakage tests PASS. Postfit:20 tests PASS using saved evidence; no Project refit/prediction during verification.
- Fits9, predictions3750, target candidates1, models1, threshold searches0, retuning0, Fresh/OOS/Prospective/provider requests0, SHORT0. All nine safety flags false.
- Global budget SHA: `b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f`; Fresh195 unchanged.
- Full exact metrics/gates/per-symbol bands: `result.json`; per-unit summary: `units.csv`; all gates: `screen-gates.csv`.
- Exact fitted coefficients, weighted medians/scales, training IDs/weight audits/model SHAs: `models.json.gz`; causal predictions and separate evaluation labels: `predictions.json.gz`.
- All3800 target identities/censor reasons/frozen EXIT results: `target-ledger.json.gz`.
- Precommit source pins, prefit receipt/log, execution log and manifest preserve run order. The final commit is the commit containing this evidence manifest; verify its exact-head CI through GitHub, not a prior commit status.

### Frozen identity references

| Identity | SHA |
|---|---|
| eventIdentitySHA | `103ae204ad93ec32a772f0bd966cab3c9072d9509bb78c5a243aea200bbe57fd` |
| frozenPredictionSHA | `a11313909248d2c8aa1c39bac807f8a5c476c19c0be75a0e15dde41690cdb8be` |
| globalBudgetSHA | `b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f` |
| p0DiagnosticSHA | `91019d3550bcfbf38e64cbc00e0f30b1cbefe44681152c82ed0b09bb3053c29d` |
| p0Head | `13148321d7ef586975ab973a04392e2af73b6503` |
| p0Verdict | `MSH_ENTRY_LONG_V2_ARCHITECTURE_DIAGNOSTIC_COMPLETE` |
| rootCauseEvidenceSHA | `5e6f10fb978b06efb0bfdc842570c75d6a277c1515ee3b5ffca1e02e170dbe71` |
| rootCauseHead | `0ffdd8056489d7df7a9690df8047986a428eda4d` |
| selectorFreezeCommit | `565d74b3dea823581fdb32380113aac5913a248d` |
| selectorPayloadSHA | `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59` |
| selectorRidgeSHA | `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb` |
| v1CandidateSHA | `4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23` |
| v1EnterIdentitySHA | `72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236` |
| v1Features | `['frozenSelectorRidgeScore', 'frozenSelectorRidgeRank']` |
| v1ModelSHA | `b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e` |
| v1ScalerSHA | `1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b` |
| v1Status | `MSH_ENTRY_LONG_V1_FROZEN_FOR_EXIT_RESEARCH` |
| v1Threshold | `2.0` |
| v21ContractSHA | `82c17234b482118919b092df4af56c0e6a60d792de5ce3a551a509bcc3d293c7` |
| v21EvidenceSHA | `c1c257a54ff733828135c248fa1b9b9713b737836ee2b369017b68b8639ace12` |
| v2ContractSHA | `18818ffd1157c7ba15c93eb4723c3e28945c238e0e2f6a2440bee98c7ad1267f` |
| v2DevelopmentEvidenceSHA | `35cec58faedcebfd09190ed5c404e2e874647eca90b92e12bc9021ff80385a75` |
