# Sparse Dictionary + Behavior Reader — final REPORT

Gate: **BLOCKED**

Same-as-of: 2025-08-25T15:30:00+09:00. Universe 4080; dated-master listed 3799. No protected payload is used to align dates.
Sample confidence and temporal reliability are separate. Reference scales/peer fits are causal per-snapshot, not reused from later frozen whole-period fits. These counts therefore differ from the archival 2,895/4,080. Historical reconstruction remains NOT PIT / NOT OOS / research-only.

## 1–4. Synchronized sparse coverage and temporal reliability

| lane / trait | H | M | L | insufficient | temporal PASS | dispatchable |
|---|---:|---:|---:|---:|---:|---:|
| daily/inside | 0 | 0 | 3756 | 324 | 0 | 0 |
| daily/gap_fill | 0 | 34 | 2647 | 1399 | 0 | 0 |
| daily/gap_cont | 0 | 18 | 2663 | 1399 | 0 | 0 |
| daily/amihud | 703 | 1532 | 1521 | 324 | 0 | 0 |
| intraday/amihud | 692 | 1530 | 1534 | 324 | 0 | 0 |
| intraday/value_O30 | 619 | 891 | 295 | 2275 | 0 | 0 |
| intraday/value_AM | 370 | 1070 | 365 | 2275 | 0 | 0 |
| intraday/value_PM1 | 182 | 1136 | 486 | 2276 | 0 | 0 |
| intraday/pdh_break | 0 | 133 | 233 | 3714 | 0 | 0 |

Nonempty admitted personality: **0 symbols**. Source H/M without temporal PASS is excluded. Three fixed rolling-origin folds, five exchange-session embargo, future 20 authorized sessions, no threshold tuning. Expanding and recent/long diagnostics retained.

| view | 0 | 1–2 | 3–5 | 6–10 | 11+ |
|---|---:|---:|---:|---:|---:|
| combined | 4080 | 0 | 0 | 0 | 0 |
| daily | 4080 | 0 | 0 | 0 | 0 |
| intraday | 4080 | 0 | 0 | 0 | 0 |

All symbol×trait fields: measurement/06_sparse_profiles.json.gz. Per-symbol eligible fold diagnostics: 07_temporal_symbol_folds.json.gz. Unavailable folds are counted insufficient, not imputed. Snapshot/peer/normalization coefficient provenance: 11_asof_artifacts.json.

## 5. Pullback vNext

Event-bearing symbol-sessions: 1925; confirmed pairs: 3136; paired old/new sessions: 1925.
New ID long_pullback_depth_contiguous_v1. Contiguous same-phase upward impulse then confirmed downward correction only. Unconfirmed terminal legs excluded; ratios above1 retained. Old definition/results unchanged. New result is candidate-only, not retroactive USABLE.
Detailed scalar distributions, paired differences, temporal screen and timestamped examples: measurement/04_pullback_vnext.json.

## 6. Calibration-only WATCH23

| lane / trait | frozen-mapping independent-period candidate |
|---|---|
| daily/body_range | False |
| daily/large_up | False |
| daily/doji | False |
| daily/long_lower | False |
| daily/outside | False |
| daily/trend_day | False |
| daily/range_s | False |
| daily/range_exp | False |
| daily/range_con | False |
| daily/gap_up | False |
| daily/gap_dn | False |
| daily/overnight_var_share | False |
| daily/value_shock | False |
| daily/jump | False |
| intraday/inside | False |
| intraday/trend_day | False |
| intraday/range_con | False |
| intraday/gap_fill | False |
| intraday/overnight_var_share | False |
| intraday/value_shock | False |
| intraday/value_CL | False |
| intraday/range_PM1 | False |
| intraday/volume_CL | False |

OLS fit only on fold1; mapping may be evaluated only at forecast origins on/after its fit-completion date. Fixed fold2 origin predates that completion, so fold2 is NOT_AVAILABLE, never a retroactively corrected forecast. Fold3 can be diagnosed, but the precommitted two-period requirement is not met: no mapping can be promoted by this schedule. Date feasibility was checked before real measurement; schedule and thresholds were not changed. All old WATCH remain WATCH and are excluded from dispatch.

## 7. Shared Chart Reader

Real Development probe outcomes: {"RESEARCH_CONTEXT_AVAILABLE:None": 736, "UNAVAILABLE:MISSING_CURRENT_BAR": 1154}.
Real simultaneous Dictionary+Reader connections: 0/0 fixed code-order probes; full connection payloads in dictionary-reader-integration.json.
History adapter / exact previous exchange day / closed5m / maximum age4min / current-phase expected endpoint / missing/stale/future rejection / lunch reset implemented and contract-tested. VWAP missing-prefix remains null. PDH/PDL, OR, causal Swing/Pullback, breakout/failure, breakdown/reclaim, wick/body, compression/expansion and same-time RVOL/value shock share a single Entry/EXIT context. Probe selection is first3 eligible codes/day, five fixed timestamps; not a whole-market Reader-coverage claim.

## 8–9. Handoff and next step

['NO_USABLE_SAMPLE_HM_AND_TEMPORAL_PASS_SYMBOL_TRAIT', 'NO_NONEMPTY_REAL_SAME_ASOF_DICTIONARY_READER_CONNECTION']
Gate BLOCKED: no NEW Entry/EXIT design or optimization. Do not relax temporal criteria. Fix only evidenced contract/data limitations under a separate precommit.
At actual use, dispatch additionally requires the latest preceding-session snapshot and a fresh Reader; a stored candidate is never an order.

## 10–12. Boundary, verification and provenance

Tests 201; full regression 2949; PASS. Two independently regenerated output manifests match. Raw restoration is allowlisted and every raw page file matches original acquisition measurement hashes. Read ledger intersections with Common Holdout244 and excluded seals are empty. No provider request. Exposure Ledger remains unchanged.
Protocol precommit 43e76dcf8b78aeffb829a41e70e84e65b80c77b3; execution HEAD 6d6e42f485989bc00876a14d680c0a31ad8b7efd; PR587 remains research Draft/unmerged. Evidence preservation commit is a descendant, not the execution HEAD.
Source daily733/intraday144, old registry/Gates/verdicts and prior results preserved. Supplemental daily payloads already acquired for intraday Development are reused causally, not counted as new provider acquisition.
STOP. No Common Holdout/REPORT19/Validation/OOS/Fresh opening, no Entry/EXIT learning, no trading or production promotion.
