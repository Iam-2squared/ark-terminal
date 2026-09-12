# Phase57 EXIT v4 - Stage 2 Result-Blind Data Allocation Freeze

## Outcome

Final Gate: **DATA_ALLOCATION_INTEGRITY_BLOCKED**.

Stage 2 could not truthfully freeze session splits. The only broad candidate quantity is the Stage 0 planning band of 300-360 sessions. It has neither exact session dates nor a per-session 13-gate Tier 2 decision and required source lineage. Promoting that range from `UNKNOWN` to `ELIGIBLE` would violate the frozen Stage 1H contract.

No outcome or future label was used. No allocation date, ratio, DEV-A list, split boundary, or purge/embargo length was selected. The three already-exposed Golden sessions remain `DIAGNOSTIC_ONLY`; Protected 180-282 and Fresh reservations remain external and untouched.

## Git baseline

| Item | Result |
|---|---|
| PR | #581 |
| Parent remote head | `3acf65b41234ea06a02c93634aa5329cc13d05aa` |
| Base | `research/phase57-minimal-stateful-hybrid-entry` |
| Draft | YES |
| Parent CI | 4/4 SUCCESS |
| main changed | NO |

## Frozen Tier 2 dependency

| Item | Result |
|---|---|
| Contract version | `1.0.0` |
| Contract status | `FROZEN_NOT_ACTIVATED` |
| Contract SHA-256 | `2aa9fd80596c0f71f2359fb132288a15d563e3fab8e22ecbac54fda308a54a70` |
| Eligibility schema SHA-256 | `f060c654f0d5af5f105f8ba20c47b78950ad433305b735d42f6cbd68f8e2823b` |
| Modified in Stage 2 | NO |

## Pool integrity

| Class | Sessions | Status |
|---|---:|---|
| Metadata-known total | 131 | 3 diagnostic + 103 Protected + 25 Fresh |
| Confirmed Tier 2 eligible | 0 | No session-level eligibility inventory |
| Confirmed blocked | 0 | No unsupported fail classification invented |
| Unknown planning candidates | 300-360 | Planning band only; not allocatable |
| Diagnostic used | 3 | 2025-08-27, 2025-10-09, 2025-11-25 |
| Protected external | 103 | NO NEW ACCESS; not reallocated |
| Fresh external | 25 | NO NEW ACCESS; not reallocated |

The three diagnostic sessions have strong input reconstruction evidence, but the retained evidence is not a complete full-session Tier 2 eligibility record for the large-scale pool. They remain exposed and cannot be promoted to OOS or Future Reserve.

## Integrity blockers

| Blocker | Consequence |
|---|---|
| Exact date-sorted candidate inventory absent | Cannot create time-ordered contiguous blocks |
| Per-session 13-gate decisions absent | UNKNOWN cannot become eligible |
| Per-session source lineage absent for the planning band | Tier 2 contract blocks allocation |
| Protected/Fresh IDs intentionally not read for reuse | Cannot silently absorb them into the new pool |
| No exact boundaries | Purge/embargo need cannot be resolved |

This is an integrity block, not proof that J-Quants capacity is too small. The planning band may be large enough, but availability estimates are not allocation rights.

## Split result

| Split | Sessions | Date boundary | Expected First ENTER C/B/O | Status |
|---|---:|---|---|---|
| DEV-A | 0 | NONE | 0 / 0 / 0 | NOT FROZEN / LOCKED |
| DEV-B | 0 | NONE | 0 / 0 / 0 | NOT FROZEN / LOCKED |
| Validation | 0 | NONE | n/a | NOT FROZEN / LOCKED |
| Historical Holdout | 0 | NONE | n/a | NOT FROZEN / LOCKED |
| Untouched OOS | 0 | NONE | n/a | NOT FROZEN / SEALED |
| Future Reserve | 0 | NONE | n/a | NOT FROZEN / SEALED |
| Purge/Embargo | 0 | NONE | n/a | NOT DETERMINABLE |

For sanity checking only, 300-360 sessions correspond to 600-720 / 870-1,044 / 1,020-1,224 expected First ENTER events under the Stage 0 conservative/base/optimistic assumptions. Those values are not measured frequencies and do not authorize allocation.

## Manifest and conservation

The machine-readable manifest records only the three exact dates already exposed. Each is `UNKNOWN / DIAGNOSTIC_ONLY / DIAGNOSTIC_USED`. The unmanifested 300-360 band remains `UNKNOWN_NOT_ALLOCATED`. Protected 180-282 and the 25 Fresh reservations are represented only as untouched external aggregate ledgers because their content and IDs were not opened for this task.

No session appears in two splits. No exposed session is assigned to OOS. No unknown session is treated as eligible. All eventual allocation classes and minimum reserve rules are encoded in the non-frozen contract for a later retry, but no incomplete contract is described as frozen.

## Stage 3 handoff

The DEV-A handoff is a blocked stub. `devASessions=[]`, `devAUnlockCandidate=false`, and `developmentUnlocked=false`. Stage 3 cannot start. A separate authorization is required even after a future complete Stage 2 freeze.

## Evidence digests

| Artifact | SHA-256 |
|---|---|
| Allocation contract | `b3eb3c438ad2c5ec75d2a2900840570d49e03c483808336b6649f8cf46e150b9` |
| Allocation manifest | `7a3c1fc986eec469b81f6382fc158cc9e54af3c6af24a334432f68a5b868394f` |
| Capacity/eligibility summary | `7227119f2442bf867780f04dfa02c8ab5e964bb1cb389a863d5d02102e5f8252` |
| DEV-A handoff stub | `ab267b0d61a3fc580e50dae5420d6da63a23093087cc4e9da691af6129f9e598` |
| Stage 2 audit | `ec88955c4026a336fe05b3d68f7b323c37d0e0fe6903d40afdabf624a059e1e0` |

## Tests, access, and safety

| Item | Result |
|---|---:|
| New raw sessions | 0 |
| New SEALED sessions | 0 |
| Protected 180-282 access | 0 |
| Fresh Validation/OOS access | 0 |
| EXIT outcomes | 0 |
| Future labels | 0 |
| EXIT invocations | 0 |
| Focused Stage 2 tests | 15/15 PASS |
| Full Predict regression | 2,665/2,665 PASS |
| Checksum evidence | PASS |

Tests enforce outcome/future-field denial, deterministic manifest order, one-session-one-split, Protected/Fresh exclusion, exposed-not-OOS, UNKNOWN-not-eligible, Tier 2 digest pinning, minimum-reserve checks only after a valid freeze, no DEV-A unlock, no EXIT import, and all safety flags false.

## Required answers

1. Freeze with outcome count zero: **outcome count is zero, but allocation was not frozen because integrity prerequisites are absent**.
2. Eligible pool: **0 confirmed sessions**.
3. Blocked/unknown: **0 confirmed blocked; 300-360 planning candidates remain unknown**. Three exact exposed dates are diagnostic-only and also not allocation-eligible.
4. DEV-A 200 events: **not assessable from confirmed allocation; 0/0/0 confirmed capacity**.
5. DEV-B 500 events: **not presently demonstrable**. The broad band suggests potential capacity but is not an eligible pool.
6. Validation: **not allocated; sufficiency unconfirmed**.
7. Historical Holdout: **not allocated, so independence cannot yet be frozen**.
8. Untouched OOS: **no new OOS allocation was created; existing protected data remains sealed**.
9. Future Reserve: **no new reserve allocation could be frozen; existing external protected/fresh data remains untouched**.
10. Protected/Fresh exclusion: **YES, complete; new access 0/0 and reallocation prohibited**.
11. Digests: **the blocked contract, incomplete manifest, summary, audit, and handoff stub are byte-hashed; no valid allocation digest is represented as a completed freeze**.
12. Proceed to Stage 3 DEV-A measurement: **NO**.

## Highest-value next action

With separate authorization, build a date-sorted metadata-only inventory of candidate JST sessions outside Protected/Fresh, attach all 13 frozen Tier 2 gate decisions and required source lineage per session, and rerun Stage 2. Do not access EXIT outcomes or future labels.

## Hard stop

Final Gate: **DATA_ALLOCATION_INTEGRITY_BLOCKED**.

STOP before DEV-A unlock, Stage 3, EXIT measurement, Development outcomes, Validation, Historical Holdout, OOS, or Prospective work.
