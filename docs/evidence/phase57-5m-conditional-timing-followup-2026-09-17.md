# 5m Timing-only conditional follow-up / 2026-09-17

Status: **FAST_FAIL_KILL_THIS_CONDITIONAL_WAIT_RULE**. Frozen LONG Selector unchanged. 1m research remains PAUSED. This commit adds this report only; the executable experiment, full ledgers and verification logs are delivered in `Ark_Terminal_5m_Conditional_Timing_Result_2026-09-17.zip` in the conversation. No accepted new Entry, no production integration or main merge.

## Correct the causal interpretation

The previous chat description suggested immediate Entry except when the first post-selection 5m bar declines. That decline is not known at selection. A policy buying the eventual no-dip subgroup at t0 is lookahead and is not implemented or adopted.

One additional executable rule was fixed before its measurement: **OBSERVE5_DELAY_DIP10**. Every active candidate waits for the first completed 5m close. If that close is below the pinned selection decisionPrice, schedule reference Entry at +10m OPEN; otherwise enter at +5m OPEN. No t0 fallback, no rebound check, no new score, no quality filtering, no threshold sweep. The ten-minute bound is inherited from the prior experiment. The original IMMEDIATE / WAIT5 / DIP_CLOSE_FALLBACK10 policies were rerun as parity comparators, not new candidates.

## Data and reference semantics

Pinned exposed Historical Development: 76 sessions, 3,800 selection events, 2,743 first symbol-session anchors. Primary complete-60m panel: 878 anchors, 430 symbols, 76 days. All candidates stay in the ledger. Future path availability is used only by the evaluator, not the decision kernel.

Reference buy is the OPEN of the scheduled 5m interval, not the already-observed decision CLOSE. Actual queue, spread, quantity and first-trade timestamp inside a partly observed 5m interval are not known. Equal D30 windows cover 30 wall-clock minutes AFTER each Entry. Capture measures immediate HIGH winners retained from the new buy to common selection+60m, not realized PnL.

| Same 878 anchors | IMMEDIATE | WAIT5 | Prior DIP_CLOSE_FALLBACK10 | New OBSERVE5_DELAY_DIP10 |
|---|---:|---:|---:|---:|
| Reference entries | 878 | 878 | 878 | 878 |
| +3 capture | 267/267 (100%) | 192/267 (71.91%) | 174/267 (65.17%) | 186/267 (69.66%) |
| +5 capture | 123/123 (100%) | 86/123 (69.92%) | 78/123 (63.41%) | 86/123 (69.92%) |
| Mean buy improvement, positive=cheaper | 0% | -0.02870% | -0.01619% | -0.04819% |
| Mean D30 | 2.12584% | 2.04490% | 1.98348% | 2.03945% |
| D30 relative improvement | 0% | 3.81% | 6.70% | 4.06% |
| D30 ES95 | 10.45592% | 9.50478% | 9.11216% | 9.62000% |
| D30 >=10% | 19 | 16 | 13 | 17 |
| Common selection+60m mean CLOSE net | -0.2656% | -0.2883% | -0.2703% | -0.3087% |
| Each Entry+30m mean CLOSE net | +0.0250% | -0.1605% | -0.1102% | -0.1979% |

All entries firing in the primary panel does not mean all original candidates are covered. Full 2,743 anchor reference fills / UNKNOWN / EXPIRED are: IMMEDIATE 1907/483/353, WAIT5 1865/525/353, prior dip/fallback 1656/734/353, new conditional 1681/709/353.

## Actual Frozen LONG EXIT replay

Unchanged policy: LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1. Source module Git blob `f4fc4fc49943332122840a5442163bec26f0c97f`, read at `e7a3f7c3a17a8490a13298119d206c339b657b11`. Thin adapter rebases returns to the new reference buy, renumbers remaining normal slots and updates elapsed time. Original saved EXIT outcomes matched 3,800/3,800 after explicitly normalizing 160 censored records whose absent netPct means null. The first input check stopped on that serialization difference; the comparator was corrected without changing any timing rule, EXIT or gate. First-failure log preserved.

Same 865 anchors where all four EXIT outcomes are observable:

| Metric | IMMEDIATE | WAIT5 | Prior dip/fallback | New conditional |
|---|---:|---:|---:|---:|
| Mean net/reference trade | -0.25607% | -0.37306% | -0.28583% | -0.39158% |
| Profit Factor | 0.77401 | 0.66382 | 0.73343 | 0.65030 |
| Win rate | 36.30% | 32.83% | 30.98% | 33.06% |

Round-trip cost 0.05%. Frozen EXIT uses completed-CLOSE reference marks, not demonstrated executable sells. Thirteen primary anchors remain not fully EXIT-paired. Capital/Portfolio replay=0; account return and MaxDD remain null. Immediate is only the comparator and is itself negative with this Frozen EXIT, not an adopted profitable Entry.

## What is retained and what is killed

FIRST_CLOSED_DIP: 328 anchors / 236 symbols / 74 days. Waiting until +5 rather than buying at t0 has relative loss reduction, but extending this to +10 is not supported. On those same anchors, +3 capture drops 56/59 -> 50/59, mean buy improvement drops 1.11841% -> 1.06623%, D30 changes only 1.89114% -> 1.87656%. On the same 326 EXIT-paired cases mean net changes -0.31699% -> -0.36613% and PF 0.69904 -> 0.66097. +5 capture remains 21/21, a small sample, not a profitable branch proof.

NO_FIRST_CLOSED_DIP: 550 anchors. At +5 the mean buy is 0.71279% higher than immediate. On 539 paired EXIT cases immediate mean is +0.35147% versus +5 mean -0.40697%. The subgroup label is known only at +5, so its good t0 outcome cannot become a causal t0 Entry rule.

Keep immutable upstream joins, prefix-only decision logic, next-OPEN references, equal risk windows, full denominators, missing UNKNOWN, and unchanged EXIT adapters. Archive all results. Kill this exact additional-wait rule and any retrospective no-dip/t0 interpretation. Do not rescue the full failure by selecting favorable realized subgroups. This experiment does not establish that all OHLCV timing is impossible or that 1m is necessary.

## Gates, robustness and verification

Inherited engineering gates: capture3/capture5 >=90%, throughput >=80%, mean D30 reduction >=10%, nonworse ES95/buy/common net, D30 nonworse in >=3/4 chronological blocks and >=3/5 symbol groups. New rule fails capture, mean-risk improvement, mean buy and common net. It passes throughput, ES95, chronological 3/4 and symbol 4/5. Gates unchanged.

Full underlying-minute-count subset has 249 anchors: new capture3 60/88=68.18%, capture5 34/40=85%, EXIT mean -0.46398%, PF0.64685. Excluding previously identified 89180/57590 gives 849 anchors: capture3 176/250=70.40%, capture5 79/109=72.48%. No blacklist. Extra +5m latency for all policies gives some better relative EXIT differences, but new capture3 164/234=70.09%, capture5 76/102=74.51%, EXIT mean -0.27412%, PF0.74010; no positive edge certified and no execution-assumption retuning.

Date-cluster bootstrap, 1,000 resamples / seed57, gives new-minus-immediate D30 mean difference 95% interval -0.20424 to +0.02209 pp and EXIT net difference -0.32608 to +0.02532 pp. Descriptive exposed-Development uncertainty only, not independent validation.

36 unit tests PASS. 24 independent checks PASS, including 10,972 causal intents, 35,957 absolute-price numerical comparisons and 7,109 independent EXIT evaluations. Previous three-policy capture/D30/EXIT mean/PF values reproduced. Code/test success is not performance success.

Source ZIP SHA: `043dc99ad42ac3036ff280cb139de3fa6740f5386d0829a4cbaf13e360507505`.
Anchor SHA: `985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121`.
Protocol SHA: `2b2d6764b1ae4dc24e8ae59a469866f654c5a4cac7cda411a4e93807fb5fe448`.
Result SHA: `efe67d59992a0e457dfd0a8e934c3e74154ae6450d5dba9bff73d2a7f39a8246`.
Ledger SHA: `52cd81a4dc128800423c0fa7ecdec5e8286cc50a4206bc3e47d3c1d61078786f`.

Selector / old Entry / 1m Entry / EXIT / allocation / cash ledger / workflow modifications=0. One-minute replay, new market data, fits, model predictions, Fresh/OOS, Capital/Portfolio and main merge=0. All nine trading/write/promotion flags false. No final-head CI claim is made for this documentation-only change. This exact study is closed with preserved evidence, not queued for automatic retuning.
