# Phase57 G7 R2 — Two-Reviewer Result and Adjudication

Recorded: **2026-09-22 13:46 JST**  
Branch: `research/phase57-long-only-cash-equity`  
PR: #587

## Disposition

**G7_R2_FORMAL_FAIL / NO_BLOCKING_STATE_SEMANTIC_DEFECT_CONFIRMED / STATE_V2_NOT_FROZEN**

The precommitted R2 gate is not passed. This is not rewritten into a PASS.

Reasons:
1. Reviewer B detected **7/8** pinned target controls; G7R2-016 (`REQUIRED_REASON_OMITTED`) was missed.
2. On the 36 clean actual cases, raw representation-defect agreement was **33/36 = 91.67%**, but Cohen's kappa is **0** because Reviewer A marked all 36 clean actuals NO while Reviewer B marked 3 YES. The precommitted protocol only permits raw-agreement fallback when kappa is mathematically undefined, so the agreement gate fails.
3. Reviewer B did not visually inspect the charts (`chartCasesInspected=0`), which is preserved as an attested review limitation rather than silently repaired.

No actual-case future leakage or blocking semantic-adequacy concern was claimed by either reviewer.

## Submission integrity

| Item | Reviewer A | Reviewer B |
|---|---|---|
| Submission ZIP SHA-256 | `1b09d8b704870a3b505b2af37e4ffac885d1f5b00bfcc43fcc743ee75af8b245` | `32e6ff0f0510a0b03d7be1f479f62058fc5c361d1b1240db726b97359e41f824` |
| RESPONSE.csv SHA-256 | `440a4d91576f18af739db46de9a9cb59c382c5d1df4b698a1410a873e001bbe1` | `158fdd4a82f4545297b672766f02efd4b43305be10a975b1673349e46bfced48` |
| Frozen PASS1 SHA-256 | `e514bb14df899ae797a1262ec2136476e29bb7664e363894b6df7c5d24b907b5` | `0e881954c6de3401435ac864139eb06007a1b448b81289bf04278f9ae9dd2ca9` |
| Rows | 46/46 | 46/46 |
| Fresh-session attestation | true | true |
| Other reviewer labels seen | false | false |
| PASS1 locked before Pass2 | true | true |
| Pending IDs | 0 | 0 |
| Numeric cases inspected | 46 | 46 |
| Chart cases inspected | 43 | **0** |

Both locked PASS1 files are byte-consistent with their PASS1_LOCK hashes.

## Target-control scoring

Pinned controls: G7R2-008 / 012 / 016 / 022 / 029 / 040 / 041 / 045.

| Target | A | B |
|---|---|---|
| OBSERVATION_STATUS_MISMATCH | PASS | PASS |
| NEGATIVE_FINDING_STATUS_MISMATCH | PASS | PASS |
| REQUIRED_REASON_OMITTED | PASS | **MISS** |
| UNDEFINED_STATE_VALUE | PASS | PASS |
| CENSOR_CAUSE_OMITTED | PASS | PASS |
| SCALE_STATUS_VALUE_MISMATCH | PASS | PASS |
| STRUCTURE_RULE_MISMATCH | PASS | PASS |
| FUTURE_PIVOT_IN_NOW | PASS | PASS |
| **Total** | **8/8** | **7/8** |

Reviewer B's G7R2-016 rationale matched only the axis statuses and did not identify that Structure omitted the concurrent `SCALE_ZERO` reason while both current-bar and Scale prerequisites failed.

## First-pass accuracy versus pinned operator expectations

Reviewer A: **46/46 cases, all four PASS1 fields matched**.

Reviewer B: all fields matched except Phase on exactly three actual cases:
- G7R2-001: expected `RECOVERY|RESTRUCTURING`, B expected EMPTY.
- G7R2-009: expected `RECOVERY`, B expected EMPTY.
- G7R2-018: expected `RECOVERY|RESTRUCTURING`, B expected EMPTY.

These same three IDs are the **only** clean actual cases Reviewer B marked as representation defects.

## Adjudication of the three Reviewer-B actual claims

The fixed rule brief and pinned mechanical-v1 semantics do **not** require an active UP/DOWN/RANGE Structure for RECOVERY. An unclosed confirmed HIGH→LOW episode with leg=UP and L<C<H emits RECOVERY.

RESTRUCTURING also does not require the literal event name `STRUCTURE_INVALIDATED` only; an active Range close-exit can invalidate the active Range and leave restructuring true when no later active structure exists.

Therefore:
- **G7R2-001**: Reviewer B's PHASE_RULE_MISMATCH is a reviewer rule-interpretation error.
- **G7R2-009**: Reviewer B's PHASE_RULE_MISMATCH is a reviewer rule-interpretation error.
- **G7R2-018**: Reviewer B's PHASE_RULE_MISMATCH is a reviewer rule-interpretation error.

Reviewer A's PASS1 agrees with the pinned operator expectation on all three.

This adjudication does **not** rewrite Reviewer B's frozen response, does not change kappa, and does not convert the formal R2 gate to PASS.

## Actual-case review

- Reviewer A actual representation defects: **0/36**.
- Reviewer B actual representation defects: **3/36**, all three adjudicated above as reviewer interpretation errors.
- Raw A/B actual agreement: **33/36 = 91.67%**.
- Cohen's kappa: **0** under the precommitted scorer.
- Actual future-leak claims: **0**.
- Blocking or indeterminate semantic-adequacy cases: **0**.
- Both correct EVALUATOR_ONLY controls (G7R2-023, G7R2-028): NO defect from both reviewers.

The zero kappa is a prevalence effect in this deliberately clean actual set: A has zero positive actual-defect calls and B has three. The metric's behavior is recorded, not post-hoc replaced.

## Research interpretation

R2 did **not** identify evidence requiring:
- a new State class,
- a market-rule threshold change,
- a Scale change,
- an Opportunity filter,
- or a causal-label change.

It did identify reviewer reliability / rule-comprehension limitations. The formal gate nevertheless remains FAIL under its precommitted criteria.

## Guards

No State thresholds changed. No State v2 implementation or full-cohort generation started. No Causal Recognition, Signal, BUY/WAIT, Entry, or EXIT started. No new market provider request. No protected data opened. PnL/future-return remain unused for State design. Safety9 remain false.
