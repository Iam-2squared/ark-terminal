# NEW LONG Entry — 5m Timing-only FAST-FAIL / 2026-09-17

Status: MEASUREMENT_COMPLETE_TWO_TIMING_POLICIES_KILLED. 1m research PAUSED per user instruction. Frozen LONG Selector is unchanged. Immediate remains a comparator, not an accepted profitable Entry.

This commit adds this research record only. The executable experiment, full ledgers, tests and local logs are delivered in the conversation bundle `Ark_Terminal_5m_Timing_Only_FAST_FAIL_2026-09-17.zip`. No runtime, workflow, Selector, existing Entry, EXIT, allocation, cash ledger, or main changes.

## Fixed experiment

Existing exposed Historical Development only: 76 sessions / 3,800 selection events / 2,743 first symbol-session anchors. No old E[L]>=2.0 gate and no restriction to old 277 ENTER anchors. The primary panel has 878 complete continuous 60-minute 5m paths, 430 symbols and 76 days. The full 2,743-candidate ledger is retained.

Three predefined policies:

- IMMEDIATE: intent at selection, reference OPEN of the 5m interval starting at selection. This is an optimistic zero-latency/queue reference, not a fill at the already-observed selection CLOSE.
- WAIT5: schedule reference Entry at selection+5m OPEN, without quality filtering.
- DIP_CLOSE_FALLBACK10: after the first completed 5m bar, if CLOSE is below pinned selection price, reference Entry at +5m OPEN. Otherwise reference Entry at +10m OPEN regardless of price. No rebound confirmation, no retrospective immediate fallback, no parameter sweep.

All 3 policies enter 878/878 in the primary panel. This is NOT full-population coverage. Required missing inputs/opens remain UNKNOWN and are not replaced by later bars. Entry cannot cross lunch/session boundaries. No intrabar LOW fills, 1m interpolation, future bottom features, new data acquisition or decryption.

## Same 878 candidates

| Metric | IMMEDIATE | WAIT5 | DIP_CLOSE_FALLBACK10 |
|---|---:|---:|---:|
| Reference entries | 878 | 878 | 878 |
| +3 capture | 267/267, 100% | 192/267, 71.91% | 174/267, 65.17% |
| +5 capture | 123/123, 100% | 86/123, 69.92% | 78/123, 63.41% |
| Mean buy-price improvement, positive=cheaper | 0% | -0.02870% | -0.01619% |
| Mean D30 after each actual reference Entry | 2.1258% | 2.0449% | 1.9835% |
| Mean D30 improvement | 0% | 3.81% | 6.70% |
| D30 ES95 | 10.4559% | 9.5048% | 9.1122% |
| D30>=10% cases | 19 | 16 | 13 |
| Mean common selection+60m CLOSE net | -0.2656% | -0.2883% | -0.2703% |
| Mean each-Entry+30m CLOSE net | +0.0250% | -0.1605% | -0.1102% |

D30 is a positive adverse magnitude; smaller is better. All risk windows are the same 30 wall-clock minutes AFTER each Entry. Capture is HIGH touch from each new buy to a common selection+60m endpoint, among immediate-reference winners. It is not realized profit. The earlier Selector Census used decisionPrice, not this next-OPEN reference; its HIGH-hit counts and D30 must not be substituted here.

## Frozen LONG EXIT paired replay

Policy `LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1` is unchanged. Source `predict/long-only/phase57_long_exit_continuation_v1.py` was read at `2b0fb733654576d3e5b3ffcad6583484ca35c8c6`; remote/local Git blob matches `f4fc4fc49943332122840a5442163bec26f0c97f`. Original saved EXIT outcomes matched 3,800/3,800 before new-Entry replay. The adapter only rebases returns to the reference buy, renumbers the remaining regular slots, and updates elapsed time.

On the same 865 primary-panel anchors where all 3 EXIT outcomes are observable:

| Metric | IMMEDIATE | WAIT5 | DIP_CLOSE_FALLBACK10 |
|---|---:|---:|---:|
| Mean net/reference trade | -0.2561% | -0.3731% | -0.2858% |
| Win rate | 36.30% | 32.83% | 30.98% |
| Profit Factor | 0.7740 | 0.6638 | 0.7334 |

Round-trip reference cost 0.05%. EXIT uses its existing completed-CLOSE reference marks, NOT demonstrated executable sells. No spread/depth/quantity/queue validation. Thirteen primary anchors are not fully EXIT-paired, including needed post-60m missing bars after delayed Entry; do not fill their results. Capital/Portfolio replay=0, portfolio return/MaxDD=NULL. Immediate is less bad than these two challengers, but itself has negative mean and PF<1 with this Frozen EXIT. It is not a completed good Entry.

## Keep these lessons, not the losing policy

The predeclared FIRST_CLOSED_DIP branch occurs in 328 primary anchors, 236 symbols, 74 days. On these same candidates, waiting improves mean buy by 1.1184%; mean D30 2.8980% -> 1.8911% (-34.74%); +3 capture 56/59 (94.92%), +5 capture 21/21. However its paired 326 Frozen EXIT outcomes remain negative: mean -0.3170%, PF0.6990, versus immediate mean -1.2605%. This is relative loss reduction, not a profitable sub-strategy. The 21 +5 winners are small, and avoiding the already-observed initial decline partly explains the benefit; this is not bottom prediction.

The no-dip BOUNDED_FALLBACK_10M branch has 550 primary anchors. Mean buy is 0.6928% worse, D30 1.6654% -> 2.0385%, +3/+5 capture 56.73%/55.88%. In its 539 paired EXIT cases, mean net changes from immediate +0.3515% to delayed -0.2670%. Waiting for a dip which does not arrive consumes the upside.

The no-dip label becomes known only after the first completed bar. Buying that subgroup retrospectively at t0 would be future leakage. Neither branch is adopted by selecting after the outcomes. Preserve code, causal comparisons and all bad results; stop these exact complete timing policies without threshold tweaks.

## Gates and sensitivity

Pre-evaluation engineering screen: +3/+5 capture>=90%, throughput>=80%, mean D30 improvement>=10%, ES95 nonworse, mean buy nonworse, common-deadline net nonworse; nonworse D30 in >=3/4 chronological blocks and >=3/5 deterministic symbol groups. Both challengers fail capture, mean-risk improvement, mean buy and common net. They pass throughput, ES95 and D30 stability (4/4 time blocks, 4/5 symbol groups). No gate relaxation.

Complete-underlying-minute-count sensitivity has 249 anchors: capture insufficiency and negative Frozen EXIT net remain. Removing prior dominant symbols 89180/57590 leaves 849 primary anchors with the capture failures remaining; this is diagnostic, not a blacklist. Complete 40m panel=1,021 for equal-30m risk; common60 capture still uses 878. Extra +5m execution latency for every policy is separately reported, not used to retune.

Full-population reference fills / UNKNOWN / EXPIRED: immediate 1907/483/353; WAIT5 1865/525/353; dip/fallback 1656/734/353. Incomplete minute/no-trade semantics and actual fill quality remain limitations. This is outcome-exposed Development, not Fresh/OOS or production evidence.

## Verification and identities

35 unit tests PASS. 34 independent checks PASS, including 8,229 intents, 5,428 reference fills, 18,210 absolute-price outcome fields and 3,621 resolved EXIT outcomes. These are software/arithmetic checks, not independent market validation. Source ZIP, 12 pins, 76 sessions and 2,743 first-anchor identity verified.

Source ZIP SHA256: `043dc99ad42ac3036ff280cb139de3fa6740f5386d0829a4cbaf13e360507505`.
Protocol SHA256: `49ffaed67d99314ae87f99b2f999529ebf139b44bd811ee0d1fb9e0e3e8c365f`.
Result SHA256: `f4326b87e2813342ba9e964ee38477f5300a0c41703cb490b67aba07eee4dfdf`.

1m replay / new provider requests / fit / model prediction / Fresh/OOS / Capital/Portfolio / main merge = 0. All 9 trading/write/promotion flags false. CI for this documentation-only commit is not asserted. Existing 1m files are preserved and paused. New experiment code and complete result ledger remain in the conversation bundle.
