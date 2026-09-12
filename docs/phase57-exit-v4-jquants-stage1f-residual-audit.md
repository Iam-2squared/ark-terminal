# Phase57 EXIT v4 - Stage 1F Hybrid / Entry Parity Residual Audit

## Outcome

Stage 1F explains the remaining Hybrid and Entry parity gaps without opening any outcome, future label, new raw session, Protected session, Fresh Validation/OOS, or additional SEALED session.

The final gate is **RESIDUALS_EXPLAINED_MORE_EVIDENCE_REQUIRED**. No comparable Hybrid Golden mismatch was observed. Hybrid remains PARTIAL because the evidence does not retain an independently reproducible full historical universe, separate V1/V2 membership inputs, or a full-universe selection digest. Entry feature and state parity remain exact, and the threshold/state decision mapping is deterministic, but empirical Entry-event reconstruction is blocked because the complete hash-verified frozen candidate model bytes are not in committed evidence. A SHA identity and partial coefficient audit do not replace the full model artifact.

`FULL_REPLAY_ELIGIBLE=0`, confirmed Tier 2 remains `0`, and the included Tier 2 contract is a non-active draft only.

## Git baseline

| Item | Result |
|---|---|
| PR | #581 |
| Parent head | `f6314c67f34b7ec551f79f46b99437277d33f674` |
| Base | `research/phase57-minimal-stateful-hybrid-entry` |
| Draft | YES |
| Parent CI | 4/4 SUCCESS |
| main changed | NO |

## Hybrid residual matrix

| Layer | Status | Comparable | Match | Mismatch | Blocked | Exact reason |
|---|---|---:|---:|---:|---:|---|
| A Data input availability | PASS | 787 | 787 | 0 | 0 | Golden B events and their causal input prefixes were available |
| B Historical universe | PARTIAL | 0 | 0 | 0 | 3 sessions | Event-used symbols only; no independent complete PIT universe replay |
| C V1/V2 membership inputs | NOT RECOVERABLE | 0 | 0 | 0 | 787 | Separate V1/V2 membership inputs were not retained |
| D Hybrid score inputs | PARTIAL | 0 | 0 | 0 | 787 | 787 scores retained, but no full-universe independent recomputation |
| E Hybrid membership output | PARTIAL | 198 | 198 | 0 | 0 | Point membership counts match; output was not independently rerun |
| F Hybrid rank output | PARTIAL | 0 | 0 | 0 | 787 | 787 ranks retained and valid, but no independent rerank |
| G Selection timestamp | PASS | 787 | 787 | 0 | 0 | Exact scheduled chronological timestamps, PIT-safe |
| H Duplicate/reselection | PASS | 787 | 787 | 0 | 0 | Exact chronological state reconstruction |

The PARTIAL result is evidence incompleteness, not a hidden mismatch. `Golden missing != mismatch` is enforced by test. The residual taxonomy is `GOLDEN_REFERENCE_INCOMPLETE`, `HISTORICAL_UNIVERSE_PARTIAL`, `SOURCE_INPUT_MISSING`, `MEMBERSHIP_NOT_RETAINED`, and `RANK_NOT_RETAINED`. No `REPLAY_IMPLEMENTATION` failure was observed.

## Entry-event recoverability

| Field | Status | Rows | Note |
|---|---|---:|---|
| symbol | GOLDEN AVAILABLE | 787 | Exact event identity |
| decision timestamp | GOLDEN AVAILABLE | 787 | Exact causal time |
| direction | NOT RETAINED | 0 | Pre-fit decisions are `MODEL_UNAVAILABLE` |
| entry reference price | GOLDEN AVAILABLE | 787 | 630 feature-ready references independently checked |
| ENTER/WATCH decision | NOT RETAINED | 0 | No model-applied Golden row |
| MSH probability/score | NOT RETAINED | 0 | No model-applied Golden row |
| firstSelection timestamp | GOLDEN AVAILABLE | 787 | State parity exact |
| priorSelectionCount | GOLDEN AVAILABLE | 787 | State parity exact |

### Deterministic reconstruction judgment

The decision algorithm is deterministic: use the frozen ten-feature row, frozen scaler/coefficients/intercept, compare the two directional probabilities, apply `maxProbability > 0.60`, and honor the frozen terminal state. The focused tests cover equality at `0.60`, a value immediately above it, direction tie, terminal state, and missing-feature fail-closed behavior.

However, **empirical reconstruction was not executed**. The committed evidence pins candidate SHA-256 `f05def...`, and the robustness audit retains scaled coefficient diagnostics, but the complete candidate bytes - including the exact intercept and byte-level model identity - are absent. Recreating a model from partial diagnostics would violate the frozen-model contract. Therefore this is `ALGORITHM_DETERMINISTIC_EMPIRICAL_RECONSTRUCTION_BLOCKED_PINNED_MODEL_BYTES_REQUIRED`, not direct Golden parity and not a reconstructed Entry-event proof.

## Fixed source limitations

| Item | Result | Tier 2 treatment |
|---|---|---|
| Minute timestamp | PASS, Trust B | Start-labelled half-open minute |
| 1m to 5m | PASS | Completed sparse bars only; no lunch crossing or fill |
| availableAt | CONDITIONAL | Replay bound is `barEnd`; no provider-publication-time claim |
| Missing reason | FAIL | `UNKNOWN -> NO_OBSERVATION / NO_FINALIZED_BAR` |
| Corporate actions | PARTIAL | Unresolved symbol/session conflict blocks |
| Historical universe | PARTIAL | No FULL replay claim; report distribution shift by substrate class |
| PIT violations | 0 | Any future violation blocks Tier 2 |

## Eligibility and Tier 2 draft

| Item | Result |
|---|---|
| FULL_REPLAY_ELIGIBLE | 0 |
| Confirmed Tier 2 | 0 |
| Tier 2 contract | DRAFT_NOT_ACTIVE_BLOCKED |
| Applied to the three pilot sessions | NO |
| Stage 2 allocation | LOCKED |

The draft separates FULL Lane Y fidelity from a causal EXIT Development substrate. It specifies source lineage, timestamp/5m semantics, exact MSH parity, missing fail-closed behavior, corporate-action blocking, partial-universe disclosure, PIT zero, and NON_PROSPECTIVE reporting. It cannot self-activate.

Remaining evidence before a Tier 2 confirmation decision:

1. Make only the non-outcome frozen `candidate-model.json` bytes available under a content allowlist and verify SHA-256 `f05def...`.
2. Run model-applied Entry reconstruction on only the same three authorized Golden inputs, without labels or EXIT outcomes.
3. Separately freeze whether Tier 2 accepts the documented Hybrid partial-universe limitation or requires a separately authorized full-universe Hybrid reference.

No additional SEALED or Fresh session is required for those actions.

## Protection and safety

| Item | Count |
|---|---:|
| New raw downloads | 0 |
| Re-extracted sessions | 0 |
| New SEALED sessions | 0 |
| Protected 180-282 access | 0 |
| Fresh Validation/OOS access | 0 |
| EXIT outcomes | 0 |
| Future labels | 0 |
| EXIT invocations | 0 |

All safety flags remain false. PR #581 remains Draft. main, merge, Ready, auto-merge, promotion, Stage 2, Development, Validation, OOS, and Prospective work remain untouched.

Focused Stage 1F tests: **6/6 PASS**. Full Predict regression: **2,634/2,634 PASS**.

## Required answers

1. Hybrid PARTIAL is caused by missing full-universe/V1/V2/output provenance, not by an observed comparable mismatch.
2. Material comparable Hybrid mismatches: **0**.
3. Entry-event NOT RECOVERABLE is caused by a pre-fit `MODEL_UNAVAILABLE` Golden bundle and absent complete candidate-model bytes.
4. The frozen decision mapping is deterministic; empirical Entry reconstruction is **blocked until exact model bytes are hash-verified**.
5. Direct Golden parity is not inherently required for a Tier 2 method, but current evidence is not yet sufficient to claim model-applied Entry semantics.
6. FULL remains zero because historical universe and complete Hybrid output parity remain partial, availableAt is a replay bound, and missing/corporate-action classification is incomplete.
7. A result-blind Tier 2 draft can be written, but it is blocked and cannot be applied.
8. Additional SEALED/Fresh sessions are not required.
9. Before Stage 2, freeze exact candidate-model access/reconstruction and the accepted Hybrid partial-universe boundary.
10. Highest-value next action: allowlist and hash-verify only the frozen non-outcome candidate-model bytes, then reconstruct decisions on the same three Golden inputs; do not open outcomes.

## Hard stop

Final Gate: **RESIDUALS_EXPLAINED_MORE_EVIDENCE_REQUIRED**.

STOP before Tier 2 activation, Stage 2 allocation, Development, EXIT performance, Validation, OOS, or Prospective work.
