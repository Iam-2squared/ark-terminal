# Phase57 EXIT v4 - Stage 1C Minute-Only Golden Input Parity

As of: 2026-09-10 JST  
PR: #581  
Parent head: `87587f301806cf7ae262bf901ffcd3bad4c59dbe`  
Gate: `GOLDEN_PARITY_NOT_RECOVERABLE`

Stage 1C stopped at Gate 1, before replay or parity execution. Existing Actions metadata proves that labels-free, pre-outcome row-level feature bundles were created for all three authorized sessions. None is packaged as a single-session artifact: each target shares a ZIP with eight or nine out-of-scope sessions. Downloading those ZIPs would physically acquire inputs for sessions outside the three-session Stage 1C authorization. No artifact ZIP was downloaded and no provider call was made.

The safely accessible committed evidence is Golden C: dates, counts, source fingerprints and workflow/artifact lineage. Golden C can support consistency checks but not formal row-level Hybrid/MSH/Entry parity. No PASS was inferred from counts, aggregate metrics or later outcomes.

## A. Golden recoverability

| Session | Accessible Golden | Candidate pre-outcome bundle | Hybrid rows | MSH rows | Entry rows | Verdict |
|---|---|---|---:|---:|---:|---|
| 2025-08-27 | C | B candidate: run `34355199082`, artifact `10106663226`, 10 sessions | 0 accessible | 0 accessible | 0 accessible | NOT RECOVERABLE - target co-packaged with 9 out-of-scope sessions |
| 2025-10-09 | C | B candidate: run `34292703804`, artifact `10082689099`, 10 sessions | 0 accessible | 0 accessible | 0 accessible | NOT RECOVERABLE - target co-packaged with 9 out-of-scope sessions |
| 2025-11-25 | C | B candidate: run `34292703804`, artifact `10084152060`, 9 sessions | 0 accessible | 0 accessible | 0 accessible | NOT RECOVERABLE - target co-packaged with 8 out-of-scope sessions |

The candidate bundles were created before labels in their workflows. Their builders write per-session `features.json.gz`, `bars.json.gz`, manifest and access ledger members. This is strong provenance, but provenance alone does not authorize retrieval of the surrounding sessions.

No Golden D material was used. Existing measurement artifacts and outcome-derived packets were deliberately not downloaded or inspected.

## B. Data bar parity

| Session | Eligible symbols | 1m rows | Sparse 5m bars | Source-parity lineage | Row-level comparison | Verdict |
|---|---:|---:|---:|---|---|---|
| 2025-08-27 | 3,768 | 466,427 | 167,291 | run `34343070520`, artifact `10101335949` | 0 rows | PARTIAL |
| 2025-10-09 | 3,758 | 459,257 | 165,051 | run `34279996111`, artifact `10078072448` | 0 rows | PARTIAL |
| 2025-11-25 | 3,765 | 466,095 | 166,978 | run `34279996111`, artifact `10079662326` | 0 rows | PARTIAL |

The Stage 1B source contract remains fixed: Minute `Time` is BAR_START, interval `[Time,Time+1m)`, timezone Asia/Tokyo, regular 09:00-09:05 uses rows 09:00 through 09:04, and the reconstructed decision/availability time is 09:05. Lunch is not crossed, 12:30 starts a new grid, 11:30/15:30 terminal-auction Minute events are excluded from regular continuous 5m bars, and absent minutes are not filled.

These contracts and counts do not establish equality of individual 5m rows against an independent Ark golden dataset. Data-bar parity is therefore PARTIAL, not PASS.

## C. Frozen Hybrid parity

| Session | Golden selections | Replay selections | Membership | Rank | Timestamp | Result |
|---|---:|---:|---|---|---|---|
| 2025-08-27 | 0 accessible | NOT RUN | NOT RECOVERABLE | NOT RECOVERABLE | NOT RECOVERABLE | BLOCKED |
| 2025-10-09 | 0 accessible | NOT RUN | NOT RECOVERABLE | NOT RECOVERABLE | NOT RECOVERABLE | BLOCKED |
| 2025-11-25 | 0 accessible | NOT RUN | NOT RECOVERABLE | NOT RECOVERABLE | NOT RECOVERABLE | BLOCKED |

Frozen Minimal Hybrid v1 identifiers remain unchanged:

- model digest `444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2`
- freeze SHA-256 `a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da`

No old DYNAMIC_30/40/50 selector output was substituted.

## D. MSH feature parity

| Feature | Comparable rows | Exact/tolerance match | Mismatch | Blocked |
|---|---:|---:|---:|---:|
| directionalReturnFromOpenPct | 0 | 0 | 0 | 3 sessions |
| directionalVwapDistancePct | 0 | 0 | 0 | 3 sessions |
| directionalMomentum3Pct | 0 | 0 | 0 | 3 sessions |
| directionalMomentumAccelerationPct | 0 | 0 | 0 | 3 sessions |
| directionalPullback6Pct | 0 | 0 | 0 | 3 sessions |
| relativeVolume5 | 0 | 0 | 0 | 3 sessions |
| minutesSinceFirstSelection | 0 | 0 | 0 | 3 sessions |
| hybridReciprocalRank | 0 | 0 | 0 | 3 sessions |
| priorSelectionCount | 0 | 0 | 0 | 3 sessions |
| direction | 0 | 0 | 0 | 3 sessions |

No tolerance was selected because no Golden A/B value was opened. MSH threshold remains strictly `> 0.60`; candidate, allocation and fit SHA-256 identifiers remain unchanged.

## E. State parity

| Session | Comparable transitions | Match | Mismatch | Unknown | Result |
|---|---:|---:|---:|---:|---|
| 2025-08-27 | 0 | 0 | 0 | all | NOT RECOVERABLE |
| 2025-10-09 | 0 | 0 | 0 | all | NOT RECOVERABLE |
| 2025-11-25 | 0 | 0 | 0 | all | NOT RECOVERABLE |

The implementation contract for UNSEEN/WATCHING/ENTERED/EXPIRED, no same-session re-entry, complete-snapshot expiry and unknown-snapshot fail-closed behavior remains structurally tested. It was not compared with a recovered chronological Golden ledger for these dates.

## F. Entry event parity

| Session | Golden First ENTER | Replay First ENTER | Symbol | Timestamp | Direction | Reference price |
|---|---:|---:|---|---|---|---|
| 2025-08-27 | 0 accessible | NOT RUN | NOT RECOVERABLE | NOT RECOVERABLE | NOT RECOVERABLE | NOT RECOVERABLE |
| 2025-10-09 | 0 accessible | NOT RUN | NOT RECOVERABLE | NOT RECOVERABLE | NOT RECOVERABLE | NOT RECOVERABLE |
| 2025-11-25 | 0 accessible | NOT RUN | NOT RECOVERABLE | NOT RECOVERABLE | NOT RECOVERABLE | NOT RECOVERABLE |

No future return, EXIT result, MFE/MAE, PF, Win Rate or winner/loser field was used to reconstruct an Entry event.

## G. PIT, universe and missing audit

| Item | Result | Boundary |
|---|---|---|
| PIT violations | 0 observed | Parity did not start; this is not full PIT proof |
| Completed-bar guard | PASS structurally | `barEnd <= decisionTimestamp` |
| Historical universe | PARTIAL | Dated master exists; complete suspension and corporate lineage do not |
| Corporate actions | PARTIAL | Critical unresolved event must block symbol/session |
| Missing reason | FAIL | Absence cannot be uniquely classified |
| Sparse treatment | PASS | `UNKNOWN -> NO_OBSERVATION / NO_FINALIZED_BAR`; no state advance |

## H. Data protection

| Item | Result |
|---|---:|
| New J-Quants bulk downloads | 0 |
| New `/v2/bulk/get` calls | 0 |
| New Tick downloads | 0 |
| New Minute API calls | 0 |
| New raw sessions accessed | 0 |
| New SEALED sessions accessed | 0 |
| Out-of-scope artifact sessions accessed | 0 |
| Protected 180-282 access | 0 |
| Fresh Validation/OOS access | 0 |
| EXIT outcome access | 0 |
| Future labels generated | 0 |
| EXIT v3/v4 invocations | 0 |
| Raw persistence | 0 |

All nine safety flags remain false. No broker, MarketSpeed order, RSS order, paper-trading, live-trading, promotion or production path was enabled.

## I. Mismatch taxonomy

The frozen taxonomy remains `DATA_SEMANTICS`, `TIMESTAMP`, `UNIVERSE`, `MISSING_BAR`, `CORPORATE_ACTION`, `HYBRID_IMPLEMENTATION`, `RANK`, `MSH_FEATURE`, `MSH_STATE`, `PRICE_REFERENCE`, `DIRECTION`, `GOLDEN_REFERENCE_INCOMPLETE`, and `UNKNOWN`.

No material mismatch was observed because zero row-level comparisons were authorized. The gate is an incomplete-reference gate, not a parity failure.

## J. Stage 1C gate

`GOLDEN_PARITY_NOT_RECOVERABLE`

Golden B candidates physically exist, but cannot be recovered under the current three-session-only access contract because the Actions archive boundary is broader than the research access boundary. Accessible Golden C evidence is insufficient for row-level parity. FULL replay and Tier 2 remain unconfirmed.

The highest-value next action is to precommit a read-only extraction workflow that operates against the three existing pre-outcome feature artifacts but emits only the three authorized session members as hash-locked, non-outcome Golden B bundles. The workflow must prove zero output and zero inspection for every non-authorized member and stop before any replay, provider call, allocation or outcome access. This is a proposal only and was not implemented or run in Stage 1C.

## K. Final summary

| Category | Result |
|---|---|
| Stage | 1C - Minute-Only Golden Input Parity |
| PR | #581 |
| Parent head | `87587f301806cf7ae262bf901ffcd3bad4c59dbe` |
| Draft | YES |
| main changed | NO |
| Pilot sessions | 2025-08-27 / 2025-10-09 / 2025-11-25 only |
| Golden A/B recoverable | NO within current artifact boundary |
| Data bar parity | PARTIAL |
| Hybrid input parity | NOT RECOVERABLE |
| Hybrid output parity | NOT RECOVERABLE |
| MSH feature parity | NOT RECOVERABLE |
| MSH state parity | NOT RECOVERABLE |
| Entry event parity | NOT RECOVERABLE |
| Historical universe | PARTIAL |
| Corporate actions | PARTIAL |
| Missing semantics | FAIL |
| PIT violations | 0 observed, not complete proof |
| FULL_REPLAY_ELIGIBLE | 0 |
| Tier 2 confirmed | 0 |
| New bulk/raw/SEALED access | 0 |
| Protected/Fresh access | 0 |
| EXIT outcome/future labels | 0 |
| Stage 1C contract tests | 6/6 PASS |
| Full Predict tests | 2,607/2,607 PASS |
| GitHub CI | Verify on committed head; reported externally to avoid a self-referential CI commit |
| Final Gate | `GOLDEN_PARITY_NOT_RECOVERABLE` |
| Hard Stop | ACTIVE |

## L. Direct answers

1. Golden A/B recoverable: **No under the current artifact access boundary**. Three Golden B candidates exist but each is co-packaged with unauthorized sessions.
2. Data-bar parity: **PARTIAL**. Timestamp, causal aggregation, counts and fingerprints are known; zero independent row-level comparisons were possible.
3. Hybrid input/output parity: **NOT RECOVERABLE**.
4. MSH ten-feature/state parity: **NOT RECOVERABLE**, zero comparable rows.
5. Entry event parity: **NOT RECOVERABLE**, zero comparable events.
6. PIT violations: **0 observed**, because parity did not execute; this is not full proof.
7. FULL_REPLAY_ELIGIBLE at least one: **No; 0**.
8. Tier 2 confirmation: **No; 0**.
9. New SEALED session required: **No**.
10. Highest-value action: **separately precommit a server-side/session-isolated extraction of only the three existing pre-outcome Golden members, then stop before replay**.

HARD STOP: Stage 2 allocation, Development, EXIT measurement, Validation, OOS and Prospective work remain locked.
