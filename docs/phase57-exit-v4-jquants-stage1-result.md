# Phase57 EXIT v4 — J-Quants Stage 1 Quality / Parity Result

As of: 2026-09-10 JST  
Gate: `STOP_DATA_SOURCE_NOT_READY`

The Stage 1 probe stopped before raw Tick download. `/v2/bulk/list` showed that the selected historical Tick transport is month-scoped. Downloading it to inspect only 2025-08-27 would physically access other, unallocated sessions, violating the result-blind one-session precommit. No `/v2/bulk/get` call was made.

No EXIT outcome, MFE/MAE, future label, Protected 180–282, Fresh Validation, or Fresh OOS data was accessed. This is a data-source decision, not an EXIT v4 performance decision.

## F. Pilot classification

| Session | Tier | Timestamp | Timezone | availableAt | 5m | Universe | Adjustment | Missing | Hybrid | MSH | PIT violations | Explicit reason |
|---|---|---|---|---|---|---|---|---|---|---|---:|---|
| 2025-08-27 | BLOCKED | FAIL | CONDITIONAL | FAIL | CONDITIONAL | CONDITIONAL | FAIL | FAIL | NOT RUN | NOT RUN | 0 observed | Tick file was month-scoped; raw download stopped before start |
| 2025-10-09 | BLOCKED | FAIL | CONDITIONAL | FAIL | CONDITIONAL | CONDITIONAL | FAIL | FAIL | NOT RUN | NOT RUN | 0 observed | First-session transport blocker made further probes unauthorized |
| 2025-11-25 | BLOCKED | FAIL | CONDITIONAL | FAIL | CONDITIONAL | CONDITIONAL | FAIL | FAIL | NOT RUN | NOT RUN | 0 observed | First-session transport blocker made further probes unauthorized |

`PIT violations = 0 observed` means no violation was seen because no new raw input was opened. It is not a proof of complete PIT fidelity.

## G. Dataset eligibility

| Classification | Sessions | Status |
|---|---:|---|
| `FULL_REPLAY_ELIGIBLE` | 0 | BLOCKED |
| `EXIT_DEVELOPMENT_SUBSTRATE` | 0 confirmed | 300–360 remain planning candidates only; not unlocked |
| `DIAGNOSTIC_ONLY` | 3 | CONFIRMED existing exposed evidence |
| `SEALED_RESERVE` | 128 known | UNTOUCHED: Protected 103 + Fresh reservations 25 |
| `NOT_USABLE` | 0 | TBD; transport blocker does not prove underlying sessions unusable |

Failure to qualify as FULL replay does not itself make data unusable. However, Tier 2 is also not confirmed because the timestamp boundary and golden input parity remain untested.

## H. Missing / sparse semantics

| Condition | Detectable? | Source | Replay treatment |
|---|---|---|---|
| `NO_TRADE` | PARTIAL | Minute absence plus independently scoped Tick evidence | `NO_OBSERVATION` unless independently resolved |
| `SUSPENDED` | NO | No dedicated suspension-reason source was identified | `UNKNOWN` → `NO_OBSERVATION` |
| `MISSING_PROVIDER` | PARTIAL | Tick present while minute row is absent | Reject affected bar/session |
| `NOT_LISTED` | PARTIAL | Dated issue master | Exclude symbol at session |
| `OUT_OF_UNIVERSE` | PARTIAL | Dated master + frozen market/product filter | Exclude symbol at session |
| `UNKNOWN` | YES | Derived fallback | `NO_OBSERVATION / NO_FINALIZED_BAR`; do not advance state or streak |

No forward fill, backward fill, synthetic OHLCV, or inferred no-trade row is permitted. The structural tests confirm zero rows produce zero bars, missing minutes are not fabricated, and later minutes do not alter an earlier finalized 5m bar.

## I. Corporate action / price continuity

| Item | Availability | Semantics | Replay risk |
|---|---|---|---|
| Stock split | PARTIAL | Daily `AdjFactor` / `ExRT` | MEDIUM |
| Reverse split | PARTIAL | Daily `AdjFactor` / `ExRT` | MEDIUM |
| Merger | NO | Exact lineage unavailable | HIGH |
| Code change | PARTIAL | Snapshot diff; no old/new mapping | HIGH |
| Delisting | PARTIAL | Dated master and daily data during listing period | MEDIUM |
| New listing | PARTIAL | Dated master snapshot diff | MEDIUM |

Minute/Tick schemas provide raw intraday prices, while daily data explicitly distinguishes before/after-adjustment fields. The selected pilot could not perform raw-price parity after the transport stop. Adjustment therefore remains FAIL. Any symbol/session touching an unresolved corporate action must be blocked, not back-adjusted after candidate selection.

## J. Frozen Hybrid replay feasibility

Verdict: `PARTIAL`, not FULL.

| Requirement | Status | Evidence |
|---|---|---|
| Historical universe | CONDITIONAL | Dated master exists; exact merger/code lineage does not |
| Required 5m OHLCV | CONDITIONAL | Existing sparse aggregator and causality tests pass; timestamp proof is missing |
| Timestamp semantics | FAIL | Tick comparison was stopped before raw download |
| PIT completeness | CONDITIONAL | Dated snapshots only |
| Rank reconstruction | CONDITIONAL | Existing source evidence exists; feature-level golden parity not run |
| Membership reconstruction | CONDITIONAL | Existing member-set hashes for three exposed sessions only |
| Missing behavior | CONDITIONAL | No-fill behavior passes; absence reasons remain incomplete |

## K. MSH-Entry replay feasibility

Verdict: `PARTIAL`, not FULL. Threshold remains strictly `> 0.60`.

| Feature | Reconstructable | Golden parity | PIT-safe |
|---|---|---|---|
| directionalReturnFromOpenPct | YES, structurally | 0/3; not run | NO, not proven |
| directionalVwapDistancePct | YES, structurally | 0/3; not run | NO, not proven |
| directionalMomentum3Pct | YES, structurally | 0/3; not run | NO, not proven |
| directionalMomentumAccelerationPct | YES, structurally | 0/3; not run | NO, not proven |
| directionalPullback6Pct | YES, structurally | 0/3; not run | NO, not proven |
| relativeVolume5 | YES, structurally | 0/3; not run | NO, not proven |
| minutesSinceFirstSelection | YES with state replay | 0/3; not run | NO, not proven |
| hybridReciprocalRank | YES with Hybrid replay | 0/3; not run | NO, not proven |
| priorSelectionCount | YES with state replay | 0/3; not run | NO, not proven |
| direction | YES with frozen selector | 0/3; not run | NO, not proven |

No mismatch was rounded away because no golden feature comparison was executed. If a later date-scoped probe runs, mismatch causes are frozen as `DATA_SEMANTICS`, `TIMESTAMP`, `UNIVERSE`, `MISSING_BAR`, `ADJUSTMENT`, `FEATURE_IMPLEMENTATION`, `STATE_REPLAY`, or `UNKNOWN`.

## L. Capacity reassessment

Stage 1 measured no rejection rate or Entry frequency, so Stage 0 estimates remain unchanged.

| Target | Conservative sessions | Base sessions | Optimistic sessions | Feasibility |
|---|---:|---:|---:|---|
| 200 First ENTER | 100 | 69 | 59 | YES as capacity; source gate blocked |
| 500 First ENTER | 250 | 173 | 148 | LIKELY as capacity; source gate blocked |
| 1000 First ENTER | 500 | 345 | 295 | UNCERTAIN |
| 2000 First ENTER | 1000 | 690 | 589 | NO |

## M. Data conservation

| Data class | Sessions | Outcome accessed? | Status |
|---|---:|---|---|
| Existing exposed pilot | 3 | Existing only | USED / DIAGNOSTIC |
| New Stage 1 raw pilot | 0 | NO | QUALITY-ONLY metadata; BLOCKED |
| Development | 0 | NO | LOCKED |
| Validation | 0 | NO | LOCKED |
| Historical Holdout | 0 | NO | LOCKED |
| Untouched OOS | 0 allocated here | NO | SEALED |
| Protected 180–282 | 103 | NO NEW ACCESS | PROTECTED |
| Fresh Validation/OOS | 25 known reservations | NO NEW ACCESS | SEALED |
| Future Reserve | TBD | NO | UNALLOCATED |

New EXIT outcome access: **0**.

## N. Contract / retention

| Item | Result |
|---|---|
| Raw archive during active subscription | CONDITIONAL: private user only, access-controlled/encrypted |
| Raw retention after cancellation | NOT ALLOWED |
| Derived reconstructable retention | NOT ALLOWED |
| Non-reconstructable aggregate retention | CONDITIONAL: private and not distributed |
| Required deletion timing | CONFIRMED at cancellation/downgrade; operational deadline 2026-10-06 |
| Research evidence retention | CONDITIONAL: non-reconstructable evidence only |

Stage 1 did not expand this interpretation. The committed result contains metadata, classifications, counts, and hashes only.

## O. Tests

The Stage 1 contract suite covers CSV/timestamp parsing, Tick-to-minute hypothesis logic, monthly-file scope guard, causal 1m→5m aggregation, future-minute isolation, lunch separation, afternoon restart, missing-minute no-fill, zero-input `NO_FINALIZED_BAR`, adjustment fail-closed status, Frozen Hybrid/MSH contract presence, all ten fixed MSH features, strict `>0.60`, Protected/Fresh guards, outcome guards, and all safety flags false.

## P. Evidence / artifact

| Evidence | Value |
|---|---|
| Workflow run | 34418970782 |
| Probe head | `15e81b176dbd3ad3cb481319c16042974aa39127` |
| Executed | 2026-09-09 23:55:23 UTC / 2026-09-10 08:55:23 JST |
| Metadata endpoint | `/v2/bulk/list` |
| Raw download | Not started |
| Sanitized artifact SHA-256 | `f51f64ea699ccd7f72c11fc1f9da985bc7386e9f9ec24469f17d5f98e0e47150` |
| Precommit SHA-256 | `443f86c8b302f7c3e5a357be23c38a4fecfeccf239413467650921cd9c1411b0` |

## Q. Stage 1 exit gate

`STOP_DATA_SOURCE_NOT_READY`

Timestamp and provider-causal availability remain unresolved, golden input parity did not run, and the only official Tick transport discovered for the historical probe is month-scoped. Tier 2 is not confirmed. This says nothing about whether EXIT v4 is strong or weak.

## R. Hard stop

Development allocation, Development outcomes, EXIT replay measurement, v3/v4 comparison, MFE/MAE analysis, Validation, OOS, and Prospective work remain locked pending a new explicit instruction.

## S. Final summary

| Category | Result |
|---|---|
| Stage | 1 — Minimal Quality / Parity |
| PR | #581 |
| Draft | YES |
| main changed | NO |
| Pilot sessions | 3 precommitted; 0 new raw sessions |
| New sealed sessions opened | 0 |
| EXIT outcomes accessed | 0 |
| Minute timestamp | FAIL |
| availableAt | FAIL |
| 5m aggregation | CONDITIONAL |
| Lunch/session | CONDITIONAL |
| Missing semantics | FAIL |
| Adjustment | FAIL |
| Corporate actions | PARTIAL |
| Historical universe | PARTIAL |
| Hybrid replay | PARTIAL |
| MSH-Entry replay | PARTIAL |
| Golden parity | NOT RUN / BLOCKED |
| FULL_REPLAY_ELIGIBLE | 0 |
| Tier 2 candidates | 0 confirmed |
| PIT violations | 0 observed, not proof |
| Protected access | 0 |
| Fresh access | 0 |
| Safety | ALL FALSE |
| Stage 1 Gate | `STOP_DATA_SOURCE_NOT_READY` |

## T. Direct answers

1. Timestamp semantics: **No**; the required Tick comparison could not be performed within the one-session access contract.
2. 1m→5m semantics: **Structurally yes, empirically conditional**; causality/no-fill/lunch tests pass, but timestamp proof is absent.
3. Frozen Hybrid: **PARTIAL**, not FULL.
4. MSH-Entry v1: **PARTIAL**, not FULL; feature-level golden parity is unrun.
5. FULL replay session: **No, 0**.
6. Tier 2 substrate: **Not yet confirmed**.
7. Stage 2 allocation freeze: **No**.
8. Largest unresolved risk: **timestamp/availability substrate fidelity**, compounded by month-scoped Tick transport.
9. Additional SEALED session needed: **No**.
10. Highest-value next action: obtain provider-confirmed date-scoped Tick access, or locate existing verified Tick evidence for one of the same exposed sessions, then rerun only timestamp and input parity.

Official source basis: J-Quants Minute OHLC, Tick, Bulk List/Get, daily bars/adjustment, issue master, update timing, correction policy, and private-use terms; plus current JPX trading hours.
