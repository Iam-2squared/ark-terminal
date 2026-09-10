# Phase57 EXIT v4 - Stage 1H Tier 2 Reconstruction Contract Freeze

## Outcome

Final Gate: **TIER2_RECONSTRUCTION_CONTRACT_FROZEN_STAGE2_READY**.

The result-blind Tier 2 Reconstruction Contract is frozen as version `1.0.0`. It defines an `EXIT_DEVELOPMENT_SUBSTRATE / TIER2_RECONSTRUCTED_REPLAY` source class for future, separately authorized paired EXIT Development stress. It is explicitly `DEVELOPMENT_ONLY / NON_PROSPECTIVE` and is not FULL replay, Prospective, Formal OOS, Actual Durable, or Archived Point-in-Time evidence.

The contract is frozen but not activated. Tier 2 sessions remain zero, Development remains locked, Stage 2 allocation has not been executed, and no allocation dates or ratios were selected.

## Git baseline

| Item | Result |
|---|---|
| PR | #581 |
| Parent remote head | `3fb54f2b054f7008a7c5f75cd9d5ba375205419e` |
| Base | `research/phase57-minimal-stateful-hybrid-entry` |
| Draft | YES |
| Parent CI | 4/4 SUCCESS |
| main changed | NO |

## Freeze evidence

| Item | Result |
|---|---|
| Contract | `phase57-exit-v4-tier2-reconstruction-contract-v1.json` |
| Version | `1.0.0` |
| Status | `FROZEN_NOT_ACTIVATED` |
| Contract SHA-256 | `2aa9fd80596c0f71f2359fb132288a15d563e3fab8e22ecbac54fda308a54a70` |
| Eligibility schema | `phase57-exit-v4-tier2-eligibility-schema-v1.json` |
| Schema SHA-256 | `f060c654f0d5af5f105f8ba20c47b78950ad433305b735d42f6cbd68f8e2823b` |
| Stage 1G evidence SHA-256 | `accfa07914c98ab1381351a20e202bd087ae7b4278d750d0556f7b23daa02f4f` |
| Stage 1G matrix SHA-256 | `7fb4dd8e29791deda73710a6539f6c9597a0b2118aff3136a89c2354f522ac86` |

All future evidence that claims this Tier 2 contract must record the contract freeze digest. Any change after Development outcome access requires a new contract version and fresh data separation.

## Classification boundary

| Item | Frozen result |
|---|---|
| Dataset class | `EXIT_DEVELOPMENT_SUBSTRATE` |
| Substrate tier | `TIER2_RECONSTRUCTED_REPLAY` |
| Research use | `DEVELOPMENT_ONLY` |
| Temporality | `NON_PROSPECTIVE` |
| FULL replay claimed | NO |
| Prospective / OOS claimed | NO |
| FULL_REPLAY_ELIGIBLE | 0 |
| Tier 2 activated | 0 |
| Aggregate as Main performance | PROHIBITED |

## Fixed timestamp and PIT contract

| Requirement | Frozen rule |
|---|---|
| Minute label | `BAR_START`, Asia/Tokyo/JST, interval `[Time,Time+1m)` |
| First regular 5m bar | 09:00-09:05; rows 09:00 through 09:04 |
| Replay availability | `availableAt=barEnd` causal bound; no provider latency claim |
| Lunch | No cross-lunch aggregation; afternoon restarts 12:30 |
| Terminal auction | 11:30 and 15:30 excluded from regular 5m bars |
| PIT | Only `barEnd<=decisionTimestamp` data |
| PIT gate | Exactly zero; any violation blocks the event or session |

## Frozen reconstruction requirements

Eligibility requires timestamp/5m PASS, complete source lineage, exact Frozen identifiers, zero comparable Hybrid material mismatches, deterministic MSH feature/state/score reconstruction, strict `>0.60`, unique First ENTER, direction and reference-price closure, and PIT zero. Direct Golden model-applied Entry rows are not required; the Stage 1G `DETERMINISTIC_ENTRY_RECONSTRUCTION` contract is required.

Frozen identifiers remain:

- Selector model digest: `444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2`
- Selector freeze SHA: `a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da`
- Entry threshold: strictly `>0.60`
- Candidate SHA: `f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a`
- Allocation SHA: `7df4cb026d966628c9b3fbc91037eb13704397a700c076e865d817a273df00e6`
- Fit SHA: `e1567951bcc81d50497a42e24411a32112b36638fbc0ff67247a16a6ce80859c`

## Universe, corporate actions, and missing data

| Area | Frozen policy |
|---|---|
| Historical universe | PARTIAL must be disclosed; current-listed backfill cannot be called FULL replay; block if Entry candidate generation is not defensible |
| Corporate actions | PARTIAL; unresolved split/reverse split/merger/code change/delisting conflict blocks or excludes symbol-session |
| Adjustment | Entry and EXIT price bases cannot be mixed; unsafe repair is prohibited |
| Missing reason | Preserve known class when available; unresolved absence remains `UNKNOWN` |
| Missing bar | `NO_OBSERVATION / NO_FINALIZED_BAR`; no EXIT state/streak/MFE/MAE advance and no forced EXIT |
| Fabrication | Forward/backward fill, synthetic OHLCV/volume, and missing-minute inference prohibited |

## Source lineage policy

Every candidate must retain provider, endpoint/file class, fetch timestamp, date range, schema version, source or allowed-derived fingerprint, aggregation contract version, replay code SHA, and all Frozen Hybrid/MSH identifiers. Missing lineage blocks eligibility. J-Quants Historical Minute is the allowed primary source; Ark verified evidence is reference-only. Another provider requires a separate source-specific audit and contract.

## Eligibility and blocking schema

The machine schema contains 13 required gates and 13 blocking reasons. Any critical failure produces `EXCLUDED`, never automatic activation.

| Blocking reason | Treatment |
|---|---|
| `PIT_VIOLATION` | EXCLUDE |
| `SOURCE_LINEAGE_MISSING` | EXCLUDE |
| `TIMESTAMP_AMBIGUOUS` | EXCLUDE |
| `FIVE_MIN_AGGREGATION_FAIL` | EXCLUDE |
| `HISTORICAL_UNIVERSE_BLOCKED` | EXCLUDE |
| `CORPORATE_ACTION_UNRESOLVED` | EXCLUDE |
| `CRITICAL_MISSING_DATA` | EXCLUDE |
| `HYBRID_MATERIAL_MISMATCH` | EXCLUDE |
| `MSH_RECONSTRUCTION_FAIL` | EXCLUDE |
| `ENTRY_EVENT_AMBIGUOUS` | EXCLUDE |
| `REFERENCE_PRICE_AMBIGUOUS` | EXCLUDE |
| `SESSION_INCOMPLETE` | EXCLUDE |
| `UNKNOWN_CRITICAL` | EXCLUDE |

Reason counts are mandatory in future eligibility reports.

## Stage 2 boundary

Stage 2 Data Allocation Freeze may receive only capacity and eligibility metadata: available range, candidate sessions, known USED/EXPOSED/PROTECTED/FRESH classes, Tier 2 eligibility metadata, and conservative/base/optimistic Entry capacity estimates. Stage 1H does not choose Development, Validation, Historical Holdout, Untouched OOS, or Future Reserve dates or ratios.

Stage 2 is ready for a separate authorization, but it has not started. No outcome may be opened before the result-blind allocation contract is frozen.

## Tests, protection, and safety

| Item | Result |
|---|---:|
| Focused Stage 1H tests | 11/11 PASS |
| Full Predict regression | 2683/2683 PASS |
| Contract checksum | PASS |
| Eligibility schema checksum | PASS |
| New raw sessions | 0 |
| New SEALED sessions | 0 |
| Protected 180-282 access | 0 |
| Fresh Validation/OOS access | 0 |
| EXIT outcomes | 0 |
| Future labels | 0 |
| EXIT invocations | 0 |

All safety flags remain false. PR #581 remains Draft. main, merge, Ready, auto-merge, promotion, Stage 2 allocation, Development, Validation, OOS, and Prospective work remain untouched.

## Required answers

1. Tier 2 definition frozen: **YES**, version `1.0.0`, status `FROZEN_NOT_ACTIVATED`.
2. FULL replay separation: **YES**, explicit forbidden labels and separate data classes.
3. PIT zero required: **YES**, any violation blocks.
4. Universe PARTIAL handling: **YES**, mandatory disclosure and defensive exclusion when candidate generation is not defensible.
5. Corporate-action uncertainty: **YES**, unresolved critical conflict blocks or excludes.
6. Missing/no-trade: **YES**, unresolved absence remains UNKNOWN and fails closed without fabrication.
7. Hybrid/MSH/Entry requirements: **YES**, fixed in the contract and eligibility schema.
8. Contract digest frozen: **YES**, contract and schema SHA-256 recorded above.
9. Stage 2 readiness: **YES for separately authorized result-blind allocation design only**; Stage 2 has not started.
10. Highest-value next action: explicitly authorize a result-blind Stage 2 Data Allocation Freeze using capacity/eligibility metadata only. Do not open outcomes.

## Hard stop

Final Gate: **TIER2_RECONSTRUCTION_CONTRACT_FROZEN_STAGE2_READY**.

STOP before Stage 2 execution, Tier 2 activation, Development unlock, EXIT performance measurement, Validation, OOS, or Prospective work.
