# Phase57 LONG-only EXIT v3 / v4 / v5: Historical diagnostic and paired-replay feasibility

2026-09-16 JST. Verdict: **EXIT_ARCHITECTURE_INCONCLUSIVE**. No LONG EXIT foundation selected. This is direct Entry Development / IN-SAMPLE historical reuse, not Fresh Validation, OOS, Prospective, final PASS or production readiness.

Repo Iam-2squared/ark-terminal; branch research/phase57-long-only-cash-equity; PR #587 remains open, no main merge. Start upstream head e2a2f8752d859365187a2798bd840689146dcf2e. Preregistered computation head 13e5aa84ac7e4b39200662b9c71435ba4c62ac24. Main branch API at start/end evidence preparation: b7801ce2c13772cbc3f5b51506819c119fe868ea. The PR response separately returned base SHA f43abbbb41718e513d46c69c81b2efcf6653ab07; it is not substituted for the main branch reference. Final result commit and final-head CI are reported in the task handoff/GitHub history.

## Completion and blockers

| Task | Result |
| --- | --- |
| v3/v4/v5 lineage | Recovered source, candidate contract, commit and SHA |
| Fixed 277 identity | 277 retained; no regeneration or trade replacement |
| Post-entry diagnostic | Completed on available horizons with missingness disclosed |
| Fixed / Session-End | 41 common path-complete pairs only; not 277-pair success |
| v3 / v4 / v5 paired replay | NOT EXECUTED: causal analog input unavailable; metrics null |
| Foundation selection | INCONCLUSIVE; neither reuse nor new EXIT justified by unmeasured arms |

The recovered v3/v4 continuation uses a pinned 56-day analog snapshot ending 2026-08-12. Every such analog is later than the latest target Entry on 2025-01-09. The unchanged scorer requires earlier session AND fully realized analog before query time, with at least 30 neighbors. This frozen pool therefore provides zero causal neighbors for every target Entry. The snapshot itself was not opened. No alternative frozen pre-Entry pool was identified in the recovered lineage. A synthetic test of the unchanged scorer confirms rejection of later analogs. This is a causal input-artifact mismatch, not evidence that v3/v4/v5 performance failed.

Additional blockers: incomplete session-end paths, and v5 final bar5 versus old bar6 runtime / truncated-v4-trace fallback semantics. Future analogs, newly fitted pools, missing-data HOLD, bar6 substitution and fabricated performance are not used. No additional market acquisition was attempted because filling price paths would not fix the frozen analog chronology.

## Frozen upstream and identity

Selector freeze commit 565d74b3dea823581fdb32380113aac5913a248d; payload 3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59; Ridge 994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb. Candidate Threshold 2.0, score P1+2P2+3P3+4P4, features frozenSelectorRidgeScore and frozenSelectorRidgeRank, no optional feature, no WAIT/expiry; no repeated ENTER for a symbol-session. Upstream status remains MSH_ENTRY_LONG_V1_FROZEN_FOR_EXIT_RESEARCH; Historical BORDERLINE; Fresh Validation PENDING.

| Artifact | Verified SHA-256 |
| --- | --- |
| predict/research/phase57-long-only-global-data-budget-v1.json | b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f |
| predict/research/phase57-msh-entry-long-v1-validation-candidate-v1.json | 4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23 |
| docs/evidence/phase57-msh-entry-long-v1-final-validation-model/final-model.json | b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e |
| docs/evidence/phase57-msh-entry-long-v1-final-validation-model/final-scaler.json | 1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b |
| docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/manifest.json | b1755d173e25267f00c9ab89f2ab3f2cfb82bbaf841d2d88dc6ad19421284a32 |
| docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/historical-enter-identities.json | 72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236 |

Dataset 2024-09-17–2025-01-09, 76 Development sessions, saved 277 ENTER. Entry timestamp/reference is copied exactly from the existing ledger: causally available closed Decision Price; no prediction, re-ranking or Entry timestamp regeneration. All source pin checks passed. The Global Budget remains 195; Fresh consumption = 0.

## Existing EXIT lineage / LONG compatibility

| Arm | Identity / semantics | Compatibility |
| --- | --- | --- |
| Fixed | Inherited future.slice(0,12), completed close, regular-session end cap, cost 0.05% | Reference only |
| Session-End | Last regular-session completed close; same cost | Reference only |
| v3 | Dual gate state-conditioned; prior analog 1/3/6-bar forecasts, min30 neighbors; loser1bar, winner2 confirmations | LONG branch exists; causal input mismatch |
| v4 | Structural risk trajectory; v3/v2 analog dependency; loser trajectory/emergency, winner giveback, neutral loss persistence | LONG branch exists; causal input mismatch |
| v5 | EXIT_V5_DYNAMIC_RECLAIM_BAR_5; DEVELOPMENT_FINAL_SELECTED_NOT_VALIDATED; frozen v4 continuation | Causal input mismatch and adapter parity unresolved |

v5 authoritative branch research/phase57-exit-v4-hybrid-msh-large-scale at ea15a594103bd6c9146f19a4aebafb83067d869b. Final candidate commit 417ad9d6dc92c3110e680cdc4a6c8dcf94b4ee5e; final sweep implementation commit aaa99030295ffb447de273881b16aad1eab1a7e9. First completed bar non-adverse continues v4; adverse enters DEFENSIVE; completed-close reclaim >=0 by bar5 continues v4; no reclaim exits at bar5. Older dynamic-state module asserts horizon6 and is NOT the selected bar5 implementation. The selected sweep simulator consumes truncated v4 management decisions and falls back to v4 if horizon is absent. Early v4 exit and missing-horizon behavior must be explicitly mapped before claiming a faithful online mechanical adapter. No sweep was executed. The other v5 research-baseline branch contains different continuation/GBM experiments, not the requested final candidate. Mixed-direction old development does not establish LONG-only suitability.

| Source | SHA-256 | Last change |
| --- | --- | --- |
| predict/research/phase57-exit-v5-development-final-candidate-v1.json | a597ea41f277ef10ab4bb4a763d2a1eb87dc45bed7bd32709798d4d77a44c7af | 417ad9d6dc92c3110e680cdc4a6c8dcf94b4ee5e |
| scripts/phase57-exit-v5-development-final-sweep.mjs | 209f2857a62c1cb7e655417d2769b952b4b9fa3ce4e3c2e99e4c228d6c9664f7 | aaa99030295ffb447de273881b16aad1eab1a7e9 |
| scripts/lib/phase57-exit-v5-dynamic-state.mjs | ed46c5b9af98b92c070ebdf24c42d3af8c4acc77314e11db7784e0f74b5cd871 | 0fd66d266c8a9f2ce57d56455ef4ff537e19b944 |
| scripts/phase57-exit-block-a-recover.mjs | 6694efe6a4aa98c7d31176ccc3f7a463d427431f74ff3aaffb94d1b2791667f4 | 47d4d767841a2eb382f81d1bcd7233cd608141fc |
| scripts/phase57-exit-v5-block-b-measure.mjs | 579423f93e3056706fc29d5c5271114252575d599973c6a3abb1882fc1861299 | f7c89a90ce7be0a7312d67ee5c13c4b80e4647d4 |
| predict/daytrade/phase57-p25-exit-v3-dual-gate.js | db4c52836509c471a9c5c96a471c07d4a787cca348a998fee5fc7cf33921017b | 56132c22368d1abdaa8deaa782a29ba7d1a6ab3e |
| predict/daytrade/phase57-p25-exit-v4-structural-risk.js | 393e9c6ee5201699ad8ea1cb8843fc57b6d91ef055fadee1ee88905190fd0405 | e78c25a1ed1ec254076cbf40388a372da808c5be |
| predict/daytrade/phase57-p25-exit-v2-state-conditioned.js | 72c19d2ad5977fcc0d27de3ba9e1a28cf223844c2b5d7a8acd9fc471946a2b41 | 15ab0c037175201b422af976c5e2439de3c864ca |
| predict/daytrade/phase57-p25-2k-pinned-history-bridge.js | 574e0177106824a85c474d4fdb40fda5b291fc52970d9061c8b75aa5e8a17e54 | 5dea11e214f6f93f6944014fd85c24e894d48488 |

## Provenance and measurement semantics

New authorized workflow run 35091141862 succeeded at preregistered head13e5aa84. Artifact10443914414 ZIP SHA72df35b601c94a6931791a924846b1449492dd2361572570937d9f4b7750b647. Original encrypted Development checkpoint runs34926225832 / 34936002178 / 34964031692 were recovered and checked; prior EXIT diagnostic run35087975004 remained unopened/unused. Raw page SHA, normalized SHA and source audits are in paths.json.gz. Transient decrypted raw cache was deleted by the workflow; original encrypted checkpoints remain.

Five-minute bars reuse the frozen normalizer, without forward-fill/interpolation/substitution. Same-day raw OHLC/reference basis, LONG only, no overnight and no corporate-action adjustment added. Completed-bar timestamps determine observability. Strict 30m excludes lunch/session-end crossing. Session-End excludes auction-only bars; regular close15:00 before2024-11-05,15:30 thereafter. Sparse observed-minute bars are disclosed, not imputed. PROVIDER_GAP means an absent expected 5m slot: it does NOT prove an outage rather than no trade. No absent interval is silently assumed flat. Returns are reference-price diagnostics, not broker-realized fills; liquidity/slippage and auction execution remain unproven.

MFE=max(0,future HIGH/reference−1); MAE=min(0,future LOW/reference−1). Extremum times use completed-bar ends, not known intrabar times. Same-bar extrema order is UNKNOWN_INTRABAR_ORDER. All percent returns use percentage units; net=gross−0.05 percentage point. Future paths are evaluation only. Missing entries remain in the 277 identity inventory; each metric states its availability denominator.

| Horizon | Available /277 | Missing reasons | MAE median /p05 /worst % | MFE mean /median /P25 /P75 /P90 % | Close return mean /median % | Sparse paths |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | 225/277 (81.2274%) | {"SESSION_END": 20, "LUNCH_BREAK": 25, "PROVIDER_GAP": 7} | -0.1729/-4.1659/-20.0000 | 3.5638/1.6279/0.3781/4.4304/12.5000 | 1.9052/0.3236 | 79 |
| 10 | 212/277 (76.5343%) | {"SESSION_END": 20, "LUNCH_BREAK": 25, "PROVIDER_GAP": 20} | -0.5847/-5.4095/-20.0000 | 4.1867/2.2005/0.9692/4.9552/12.5000 | 1.6010/0.4389 | 78 |
| 15 | 206/277 (74.3682%) | {"PROVIDER_GAP": 26, "SESSION_END": 20, "LUNCH_BREAK": 25} | -0.8836/-5.9750/-35.2941 | 4.5265/2.5568/1.2347/5.6583/12.5000 | 1.2452/0.1902 | 85 |
| 30 | 181/277 (65.3430%) | {"PROVIDER_GAP": 51, "SESSION_END": 20, "LUNCH_BREAK": 25} | -1.5337/-10.2564/-35.2941 | 4.8594/3.3333/1.8349/6.5274/12.5000 | 1.2312/0.5587 | 97 |
| SESSION_END | 41/277 (14.8014%) | {"PROVIDER_GAP": 216, "NO_REMAINING_REGULAR_BAR": 20} | -4.7872/-10.7817/-15.3488 | 5.9699/3.5117/1.9054/6.9144/14.2857 | -0.7464/-1.4038 | 32 |

The 181 strict30m results reproduce the already frozen Entry reference (MAE median−1.533742%, p05−10.256410%, worst−35.294118%). This is identity/measurement parity, not independent validation. Only41/277 have every expected remaining regular 5m slot; all41 are in2024-09-18–2024-11-01. This coverage-selected subset cannot stand for all277 or all76 sessions.

Important session-boundary limitation: all187 entries dated2024-11-05 or later lack the expected15:25-start final slot in the recovered normalized paths. This systematic absence may reflect closing-auction/no-trade representation rather than random provider loss; the current expected-slot checker does not establish which. Therefore41 is completeness under this preregistered conservative slot policy, not proof that only41 original market paths can ever be reconstructed. No final close is imputed, no auction is silently substituted, and the pre-result slot rule is not retroactively changed. Auction/session-end semantics must be resolved explicitly before full-session replay. This is an additional DATA_REQUIREMENT_MISMATCH, not a reason to buy missing bars blindly. The strict30m reference parity is unaffected.

## Adverse, recovery, opportunity, timing and path types

Immediate first5m completed-close adverse: 52/225 (23.1111%); first5m LOW adverse: 124/225 (55.1111%). These are different definitions.

### 30

| MAE bucket | Count/rate | Later completed-close reclaim | Recovery median clock min | Later +1/+2/+3/+5 counts | Horizon-close median % |
| --- | --- | --- | --- | --- | --- |
| -1 | 105/181 (58.0110%) | 63/105 (60.0000%) | 5.0000 | 50/40/30/12 | -0.5236 |
| -2 | 74/181 (40.8840%) | 37/74 (50.0000%) | 5.0000 | 28/22/17/7 | -1.1569 |
| -3 | 50/181 (27.6243%) | 17/50 (34.0000%) | 10.0000 | 12/9/8/3 | -2.9614 |
| -5 | 24/181 (13.2597%) | 6/24 (25.0000%) | 5.0000 | 4/3/3/2 | -5.0216 |
| -10 | 10/181 (5.5249%) | 2/10 (20.0000%) | 15.0000 | 1/1/1/1 | -8.4474 |

| MFE at least | Count/rate |
| --- | --- |
| 1 | 156/181 (86.1878%) |
| 2 | 132/181 (72.9282%) |
| 3 | 95/181 (52.4862%) |
| 5 | 56/181 (30.9392%) |

| Ordering | Count | Rate % |
| --- | --- | --- |
| MAE_FIRST | 66 | 36.4641 |
| MFE_FIRST | 57 | 31.4917 |
| NO_TWO_SIDED_EXCURSION | 51 | 28.1768 |
| UNKNOWN_INTRABAR_ORDER | 7 | 3.8674 |

| Time to | <=5m | 5–10m | 10–15m | 15–30m | >30m | Median min |
| --- | --- | --- | --- | --- | --- | --- |
| MFE | 69 | 35 | 22 | 47 | 0 | 10.0000 |
| MAE | 53 | 23 | 19 | 43 | 0 | 10.0000 |

### SESSION_END

| MAE bucket | Count/rate | Later completed-close reclaim | Recovery median clock min | Later +1/+2/+3/+5 counts | Horizon-close median % |
| --- | --- | --- | --- | --- | --- |
| -1 | 31/41 (75.6098%) | 22/31 (70.9677%) | 10.0000 | 18/14/13/6 | -3.1915 |
| -2 | 30/41 (73.1707%) | 19/30 (63.3333%) | 20.0000 | 16/11/11/4 | -3.3714 |
| -3 | 25/41 (60.9756%) | 13/25 (52.0000%) | 50.0000 | 11/8/8/3 | -3.8889 |
| -5 | 20/41 (48.7805%) | 6/20 (30.0000%) | 57.5000 | 5/5/5/1 | -6.0979 |
| -10 | 5/41 (12.1951%) | 0/5 (0.0000%) | N/A | 0/0/0/0 | -7.6110 |

| MFE at least | Count/rate |
| --- | --- |
| 1 | 36/41 (87.8049%) |
| 2 | 29/41 (70.7317%) |
| 3 | 24/41 (58.5366%) |
| 5 | 15/41 (36.5854%) |

| Ordering | Count | Rate % |
| --- | --- | --- |
| MFE_FIRST | 20 | 48.7805 |
| NO_TWO_SIDED_EXCURSION | 7 | 17.0732 |
| MAE_FIRST | 13 | 31.7073 |
| UNKNOWN_INTRABAR_ORDER | 1 | 2.4390 |

| Time to | <=5m | 5–10m | 10–15m | 15–30m | >30m | Median min |
| --- | --- | --- | --- | --- | --- | --- |
| MFE | 14 | 0 | 1 | 2 | 22 | 45.0000 |
| MAE | 3 | 2 | 4 | 2 | 25 | 55.0000 |

Recovery excludes the first adverse bar because its intrabar ordering is unknown. Later completed CLOSE>=Entry defines reclaim, not a profitable final outcome. Later opportunity counts exclude entries with no later observation. Adverse cohorts and their complete available denominators are not statistically independent. Detailed first-adverse depth/time and later path are retained per entry in paths.json.gz.

| Exclusive descriptive class | Count /277 |
| --- | --- |
| A_EARLY_ADVERSE_THEN_RECOVERY | 11 |
| B_EARLY_FAILURE | 6 |
| C_FAST_WINNER | 10 |
| D_WINNER_THEN_GIVEBACK | 5 |
| E_SLOW_WINNER | 0 |
| F_CHOP_NO_EDGE | 2 |
| G_UNKNOWN | 243 |

Classes were fixed before path results: first ±1% touch, early<=15m, fast<=30m, final close sign; same-bar first touch is UNKNOWN. These labels are descriptive, not live rules, causal structural labels or an EXIT threshold search. 243 UNKNOWN =236 incomplete session paths +7 ambiguous same-bar first ±1% touches. Slow winner0 is not evidence of absence in the full277.

## Paired reference results — NOT a five-arm comparison

| Metric | FIXED_12 | SESSION_END |
| --- | --- | --- |
| N | 41 | 41 |
| Gross sum (percentage points) | -9.0944 | -30.6042 |
| Net sum (percentage points) | -11.1444 | -32.6542 |
| Average / median net % | -0.2718 / -0.0500 | -0.7964 / -1.4538 |
| Win rate | 20/41 (48.7805%) | 14/41 (34.1463%) |
| Profit factor | 0.8651 | 0.7216 |
| DD trade-order proxy (pp) | -40.9675 | -71.6877 |
| Mean / median loss % | -3.9349 / -3.9389 | -4.3440 / -3.7537 |
| Worst / p05 net % | -9.8660 / -6.5717 | -11.6779 / -7.7681 |
| Mean / median holding bars | 11.5610 / 12.0000 | 37.3171 / 42.0000 |
| Holding clock buckets | {"<=5m": 0, "5-10m": 0, "10-15m": 0, "15-30m": 3, ">30m": 38} | {"<=5m": 0, "5-10m": 0, "10-15m": 0, "15-30m": 3, ">30m": 38} |
| Pre-exit MAE mean / median % | -3.5111 / -3.3445 | -4.8660 / -4.7872 |
| Gross MFE capture mean / median | -2.7289 / 0.0417 | -2.9529 / -0.2000 |
| Giveback mean / median pp | 6.1917 / 5.3908 | 6.7163 / 5.7143 |
| Session-end exposure | 8/41 (19.5122%) | 41/41 (100.0000%) |
| Recovered-cohort net winner preserved | 5/10 (50.0000%) | 2/10 (20.0000%) |
| False early exit before later close reclaim | 0 | 0 |
| Mean loss reduction vs end on end-losers (pp) | 1.7503 | 0.0000 |
| End-losers held to end | 4 | 27 |
| Positive profit Top1/3/5 shares | 19.9135%/59.7404%/71.0241% | 16.8201%/50.4604%/74.8225% |

| Realized net loss bucket | FIXED_12 | SESSION_END |
| --- | --- | --- |
| -1 | 19/41 (46.3415%) | 22/41 (53.6585%) |
| -2 | 15/41 (36.5854%) | 20/41 (48.7805%) |
| -3 | 13/41 (31.7073%) | 16/41 (39.0244%) |
| -5 | 9/41 (21.9512%) | 12/41 (29.2683%) |
| -10 | 0/41 (0.0000%) | 1/41 (2.4390%) |

| Available MFE >= 1% | Net realization count/rate | Exit before later first touch | Winner net mean /median % |
| --- | --- | --- | --- |
| FIXED_12 | 14/36 (38.8889%) | 2/36 (5.5556%) | 0.4373 / 0.2569 |
| SESSION_END | 13/36 (36.1111%) | 0/36 (0.0000%) | -0.1334 / -0.7607 |

| Available MFE >= 2% | Net realization count/rate | Exit before later first touch | Winner net mean /median % |
| --- | --- | --- | --- |
| FIXED_12 | 10/29 (34.4828%) | 3/29 (10.3448%) | 1.3785 / 0.5789 |
| SESSION_END | 9/29 (31.0345%) | 0/29 (0.0000%) | 0.8685 / -0.0500 |

| Available MFE >= 3% | Net realization count/rate | Exit before later first touch | Winner net mean /median % |
| --- | --- | --- | --- |
| FIXED_12 | 6/24 (25.0000%) | 5/24 (20.8333%) | 2.0698 / 0.9395 |
| SESSION_END | 8/24 (33.3333%) | 0/24 (0.0000%) | 1.8344 / 0.0548 |

| Available MFE >= 5% | Net realization count/rate | Exit before later first touch | Winner net mean /median % |
| --- | --- | --- | --- |
| FIXED_12 | 3/15 (20.0000%) | 3/15 (20.0000%) | 3.7111 / 2.2436 |
| SESSION_END | 5/15 (33.3333%) | 0/15 (0.0000%) | 3.6504 / 2.1083 |

Gross/net sums are sums of unweighted per-trade percentage returns, not portfolio ROI. DD is an Entry-time/symbol/ID-ordered additive closed-trade proxy, not execution-time equity, mark-to-market or capital-allocation drawdown. MFE capture uses same full-session available MFE, is unbounded below, and excludes2 MFE<=0 denominators; net capture is separately stored. Giveback here includes opportunity AFTER exit, not only already-earned upside. Premature means exit before first later level touch, not all possible winner impairment. End-loss cohorts are hindsight diagnostic labels. Both references share the same41 identities, cost and path; Fixed standalone availability173 is not mixed into this table.

### FIXED_12 concentration (absolute return share; top5 groups)

| symbol | Trades | Net sum pp | Absolute share % |
| --- | --- | --- | --- |
| 89180 | 4 | 42.6571 | 27.7427 |
| 190A0 | 1 | -9.8660 | 6.4015 |
| 45060 | 1 | -7.2304 | 4.6914 |
| 65520 | 2 | -7.0837 | 4.5962 |
| 76890 | 2 | -6.9786 | 4.5280 |

| sessionDate | Trades | Net sum pp | Absolute share % |
| --- | --- | --- | --- |
| 2024-10-29 | 2 | 10.9652 | 11.3588 |
| 2024-09-19 | 2 | 14.8546 | 9.6383 |
| 2024-09-25 | 1 | 14.2357 | 9.2368 |
| 2024-10-11 | 2 | -8.5206 | 7.2744 |
| 2024-10-02 | 3 | -2.2489 | 7.2398 |

### SESSION_END concentration (absolute return share; top5 groups)

| symbol | Trades | Net sum pp | Absolute share % |
| --- | --- | --- | --- |
| 89180 | 4 | 42.6571 | 21.1748 |
| 143A0 | 1 | 13.6137 | 6.7420 |
| 39360 | 1 | -11.6779 | 5.7833 |
| 190A0 | 1 | -9.8660 | 4.8860 |
| 39080 | 2 | -8.6444 | 4.2810 |

| sessionDate | Trades | Net sum pp | Absolute share % |
| --- | --- | --- | --- |
| 2024-10-02 | 3 | -0.1325 | 13.5495 |
| 2024-10-11 | 2 | -21.5439 | 10.6693 |
| 2024-09-19 | 2 | 12.0118 | 8.1514 |
| 2024-10-29 | 2 | 12.7819 | 7.7700 |
| 2024-10-22 | 3 | -12.1158 | 7.2482 |

| Requested arm | Replayed trades | Return/risk/capture/holding metrics | Selection |
| --- | --- | --- | --- |
| v3 | 0 | NULL — not measured, not zero performance | No ranking |
| v4 | 0 | NULL — not measured, not zero performance | No ranking |
| v5 | 0 | NULL — not measured, not zero performance | No ranking |

## Interpretation and exact next action

Tail and recovery coexist: at30m,10/181 paths reach MAE<=−10%, and2/10 later reclaim Entry at a completed close;63/105 of the <=−1% cohort reclaim. Thus an immediate adverse print alone does not establish structural failure. Conversely,41 complete session paths show substantial giveback and concentration; simply holding longer is not uniformly better. In the shared reference subset Fixed realizes +3/+5 on6/24 and3/15, versus Session-End8/24 and5/15, but Session-End has worse average net and lower-tail realized return. These are diagnostics, not sufficient evidence for choosing v3/v4/v5 or designing optimal stops.

Biggest remaining risk: causal EXIT forecasting inputs and full-path coverage are not reproducible for the fixed277. Next action requires a genuinely pre-Entry frozen analog pool with artifact SHA and adequate neighbors, or explicit authorization for a separately versioned causal LONG Development pool (which changes the old frozen evidence context). Also specify final bar5 early-v4-exit/missing-horizon parity and resolve missing-path/no-trade coverage without filling or replacing the277. Do not call a new pool an unchanged frozen replay. Do not silently acquire another period. No new LONG EXIT design/training/tuning is performed until that responsibility is resolved.

## Tests, safety and stop

Offline regression2886 PASS (Predict2702, Discovery26, Foundation39, Python30, RSS89). Additional focused tests20 PASS: path/causal6, aggregation4, artifact/summary integrity3, upstream7. One initial unittest module-import error was fixed; all final focused tests pass. New path workflow35091141862 SUCCESS. Final-head CI is checked after publication; a green CI does not unblock scientific replay. Integrity rerenders aggregates from saved derived paths only, never predicts Entry or replays v3/v4/v5.

| Counter | Value |
| --- | --- |
| entryPredictions | 0 |
| modelFit | 0 |
| scalerFit | 0 |
| exitFit | 0 |
| exitSweep | 0 |
| v3Replay | 0 |
| v4Replay | 0 |
| v5Replay | 0 |
| completeFiveArmPairs | 0 |
| providerRequests | 0 |
| freshAccess | 0 |
| oosAccess | 0 |
| shortEvaluation | 0 |
| forwardFill | 0 |
| interpolation | 0 |
| futureSubstitution | 0 |
| priorExitResultAccess | 0 |
| Selector logic changes | 0 |
| Entry logic changes | 0 |
| Existing EXIT strategy changes | 0 |
| Fresh budget consumed | 0 |

| Safety flag | Value |
| --- | --- |
| executionAllowed | false |
| brokerWriteAllowed | false |
| excelOrderWriteAllowed | false |
| rssOrderFunctionAllowed | false |
| liveTradingAllowed | false |
| paperTradingAllowed | false |
| automaticPromotionAllowed | false |
| productionUpdateAllowed | false |
| transmitted | false |

STOP: EXIT_ARCHITECTURE_INCONCLUSIVE. Frozen upstream remains unchanged. No official LONG EXIT validation, OOS PASS or production readiness claim.

## Evidence checksums

| Artifact | SHA-256 |
| --- | --- |
| contract.json | b0bcbce912786d6d3a6ca62b413a85a6e3e332dba93e975d02dd0ce14e5f071b |
| entry-path-classification.json | ec5b2c8e401c3f787a7dab734d00b3c16fbd55dbf3d83eea7bda1a60dd8b7ec6 |
| lineage-audit.json | 1e67a95a8649a68becc1ec5cf1fc90e15c568484584b482fb6ea6e0ba971eae4 |
| offline-regression.json | 6822d8d0e088b64434188c55109c38d3ab1b0382abb43a4d9364d743474561a0 |
| paths.json.gz | 1ffd7e5e3d650a676e06507faf26226ad236ec4de4a0c0446873ee16f7408959 |
| paths.json.sha256 | d531d3f0d3ee394f1b1a655ef9c10a76ec9e303a83d7205fd6688083bd8f7e95 |
| summary.json | 6adba2e2c8d90e757988c4457d4c00fe4add19e881eb8bb739fedafd6688350e |

