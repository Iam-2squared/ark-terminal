# Phase57 EXIT v4 - Stage 1G Entry Event Evidence Closure

## Outcome

The final gate is **ENTRY_EVENT_EVIDENCE_CLOSED_TIER2_FREEZE_READY**.

The complete non-outcome Frozen MSH candidate was recovered from the existing GitHub Actions First Development Fit artifact and verified byte-for-byte against SHA-256 `f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a`. Only `candidate-model.json` and its checksum were inspected from that artifact. No training rows, development report, label, return, MFE/MAE, or EXIT outcome was read.

On the three already-approved Golden sessions, all 1,260 retained direction-feature rows were scored deterministically. The 787 chronological selection events reconstructed 10 unique First ENTER events. All 630 feature-ready reference-price comparisons matched the last completed 5-minute close, PIT violations were zero, and repeat Entry violations were zero.

This is **DETERMINISTIC_ENTRY_RECONSTRUCTION**, not direct Golden Entry parity: the pre-fit Golden bundles retain `MODEL_UNAVAILABLE` rather than model-applied Entry rows. Golden absence is not counted as a mismatch.

Stage 1G does not confirm Tier 2, activate the draft contract, allocate Development data, or change `FULL_REPLAY_ELIGIBLE=0`.

## Git baseline

| Item | Result |
|---|---|
| PR | #581 |
| Parent remote head | `4699600e03308ecad1a5c48bbb3446cebd132594` |
| Base | `research/phase57-minimal-stateful-hybrid-entry` |
| Draft | YES |
| Parent CI | 4/4 SUCCESS |
| main changed | NO |

## Frozen model closure

| Item | Result |
|---|---|
| Source run | `34292703804` |
| Source artifact | `10084158820` / `entry58-development-measurement-34292703804` |
| Artifact container SHA-256 | `aa4fa5f9f5530132263f33a7dcbf9153bff4d7b44f2f574b4f3a213f122b9058` |
| Allowed member | `candidate-model.json` |
| Candidate SHA-256 | `f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a` PASS |
| Parameter SHA-256 | `9f116aee99fb3ffa7047b787d1ad8b1c41addf17eb753349e4b67157e101df14` |
| Feature contract SHA-256 | `cc70b1eb07c0719f72c4a8caa0f165a2812aec4af0b2fdeae42ef3ff400c4115` |
| Features | Exact frozen 10-feature order PASS |
| Coefficients / means / scales / intercept | Complete, finite, fixed |
| Threshold | strictly `> 0.60` |
| Validation opened in candidate | false |
| Candidate bytes committed | NO |

## Reconstruction pipeline

1. Read only the three allowlisted pre-outcome Golden feature/bar subsets.
2. Verify exact feature SHA, contract SHA, selector digest, selector freeze, feature order, and candidate SHA.
3. Recalculate both LONG and SHORT logits/probabilities for every retained pair.
4. Apply the frozen strict `> 0.60` comparison.
5. Replay `UNSEEN / WATCHING / ENTERED / EXPIRED` chronologically with `repeatEntryAllowed=false`.
6. Select the first ENTER per symbol-session.
7. Bind `entryReferencePrice` to the last completed 5-minute bar close whose `availableAt <= decisionTimestamp`.

No future field or outcome family is accepted by the runner.

## Session evidence

| Session | Golden events | Score rows | State rows | First ENTER | Ref comparisons | Ref mismatch | PIT | Repeat Entry |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-08-27 | 236 | 324 | 236 | 5 | 162 | 0 | 0 | 0 |
| 2025-10-09 | 226 | 342 | 226 | 2 | 171 | 0 | 0 | 0 |
| 2025-11-25 | 325 | 594 | 325 | 3 | 297 | 0 | 0 | 0 |
| **Total** | **787** | **1,260** | **787** | **10** | **630** | **0** | **0** | **0** |

The individual pre-outcome reconstructed First ENTER rows, including symbol, direction, timestamps, probabilities, states, and reference-price lineage, are retained in the machine-readable audit. No post-entry price or outcome is present.

## Evidence distinction

| Evidence | Status | Meaning |
|---|---|---|
| Direct Golden feature parity | PASS | Stage 1E exact 1,260/1,260 numerical parity, tolerance zero |
| Direct Golden state foundation | PASS | Stage 1E exact 787/787 pre-fit chronological parity |
| Direct Golden score parity | NOT AVAILABLE | Pre-fit bundle did not retain model-applied scores |
| Direct Golden Entry parity | NOT AVAILABLE | Pre-fit decisions are `MODEL_UNAVAILABLE` |
| Deterministic score reconstruction | PASS | Full hash-verified model applied to all 1,260 rows |
| Deterministic Entry reconstruction | PASS | Frozen threshold and state rules produce 10 unique First ENTER rows |
| Deterministic reference-price reconstruction | PASS | 630/630 feature-ready inputs and all reconstructed Entry rows close exactly |

## Critical closure matrix summary

| Critical field | Evidence | Status |
|---|---|---|
| symbol | DIRECT_GOLDEN | PASS |
| direction | DETERMINISTIC | PASS |
| decisionTimestamp | DIRECT_GOLDEN | PASS |
| threshold decision | DETERMINISTIC | PASS |
| state transition | DETERMINISTIC on exact Golden state foundation | PASS |
| First ENTER uniqueness | DETERMINISTIC | PASS, 0 violations |
| entryReferencePrice semantics | DETERMINISTIC | PASS, 0 mismatches |

Critical ambiguous: **0**. Critical mismatch: **0**. Critical blocked: **0**. Hybrid material comparable mismatch remains **0**.

## Tier 2 readiness and retained limits

| Item | Result |
|---|---|
| Timestamp contract | PASS |
| 5-minute causal aggregation | PASS |
| PIT violations | 0 |
| MSH feature parity | PASS |
| MSH state parity foundation | PASS |
| Entry deterministic reconstruction | PASS |
| Reference-price semantics | PASS |
| Missing behavior | Fail-closed to `NO_OBSERVATION / NO_FINALIZED_BAR` |
| Corporate actions | PARTIAL; unresolved conflict blocks symbol-session |
| Historical universe | PARTIAL; no FULL Lane Y claim |
| FULL_REPLAY_ELIGIBLE | 0 |
| Tier 2 confirmed | 0 |
| Tier 2 contract | `DRAFT_NOT_ACTIVE_BLOCKED` |
| Tier 2 freeze readiness | READY FOR SEPARATELY AUTHORIZED FREEZE |

The Hybrid residual is a documented full-universe/V1/V2 retention limitation. It did not create a comparable material mismatch in these Entry inputs, but acceptance of that limitation must be frozen separately before Tier 2 can be confirmed.

## Data conservation and safety

| Item | Count / status |
|---|---:|
| Existing GitHub artifacts temporarily downloaded | 4 |
| Approved Golden sessions re-extracted | 3 |
| Unapproved content reads | 0 |
| New raw session access | 0 |
| New SEALED sessions | 0 |
| Protected 180-282 access | 0 |
| Fresh Validation/OOS access | 0 |
| EXIT outcomes | 0 |
| Future labels | 0 |
| EXIT invocations | 0 |

The four temporary artifacts were the three already-approved Golden input artifacts plus the non-outcome model artifact. Temporary ZIPs, extracted subsets, and candidate bytes were deleted after evidence generation and were not committed.

All safety flags remain false. PR #581 remains Draft. main, merge, Ready, auto-merge, automatic promotion, Tier 2 confirmation, Stage 2 allocation, Development, Validation, OOS, and Prospective work remain untouched.

## Required answers

1. Frozen MSH features can be scored uniquely: **YES**, 1,260 rows deterministically reconstructed.
2. Strict threshold `>0.60` is fully reproduced: **YES**; exactly `0.60` remains WATCH.
3. First ENTER is uniquely determined from state: **YES**, 10 events and zero repeat violations.
4. Symbol, timestamp, and direction are closed: **YES**, by direct Golden identity plus deterministic model application.
5. Reference price is uniquely reconstructed: **YES**, last completed 5-minute close; 630/630 comparisons match.
6. Direct Golden remains absent for model-applied score, direction, ENTER/WATCH, and First ENTER rows. These are closed as deterministic evidence, not relabelled as direct parity.
7. Material mismatch: **NO**. Hybrid comparable mismatch, reference-price mismatch, critical Entry mismatch, and PIT violation are all zero.
8. PIT violations: **0**.
9. Tier 2 Contract Freeze readiness: **YES**, but only as the next separately authorized action; Tier 2 itself remains unconfirmed.
10. Highest-value next action: explicitly authorize and freeze the Tier 2 Reconstruction Contract, including the accepted partial-universe boundary and blocking/exclusion rules. Do not allocate data yet.

## Hard stop

Final Gate: **ENTRY_EVENT_EVIDENCE_CLOSED_TIER2_FREEZE_READY**.

STOP before Tier 2 confirmation, Stage 2 Data Allocation, Development, EXIT performance measurement, Validation, OOS, or Prospective work.
