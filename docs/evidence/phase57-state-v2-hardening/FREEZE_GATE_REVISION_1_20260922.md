# Phase57 — State v2 Freeze Gate Revision 1

Date: **2026-09-22 JST**  
Repo: `Iam-2squared/ark-terminal`  
Branch: `research/phase57-long-only-cash-equity`  
PR: #587  
User approval: **「進めて」** after review of the two available options.

Status: **GOVERNANCE_REVISION / OLD_G7_FAIL_PRESERVED / STATE_V2_NOT_FROZEN**

## 1. Purpose

This document changes the role of the G7 two-reviewer semantic chart review from a mandatory binary Freeze gate to a **diagnostic falsification gate**.

This revision does **not**:
- rewrite G7 v1 or G7 R2 as PASS;
- delete or relabel either failed run;
- change State v2 market rules, thresholds, Scale, horizon, vocabulary, or Opportunity membership;
- use PnL, Entry/EXIT outcome, future return, Holdout, Fresh, OOS, or Prospective evidence;
- authorize State v2 implementation or 77,214-row generation by itself.

The reason for the revision is that two independent G7 attempts primarily measured review-harness quality and reviewer comprehension in addition to State semantics. After the harness repair, G7 R2 still failed its precommitted mechanical criteria, but adjudication found **no confirmed blocking State-semantic defect, no actual-case future leakage, and no required State-rule change**.

The failed evidence remains first-class evidence.

## 2. Historical results remain immutable

### G7 v1

Disposition remains:

`G7_V1_FAIL / REVIEW_PACKAGE_DEFECT_CONFIRMED`

The first package had a causal display defect: at least some ACTUAL charts included the close of a bar that was not closed at checkpoint t. That run cannot be rehabilitated.

### G7 R2

Disposition remains:

`G7_R2_FORMAL_FAIL / NO_BLOCKING_STATE_SEMANTIC_DEFECT_CONFIRMED`

Recorded results:
- Reviewer A controls: **8/8**
- Reviewer B controls: **7/8**
- clean actual raw agreement: **33/36 = 91.67%**
- Cohen's kappa: **0**
- actual future-leak claims: **0**
- blocking semantic-adequacy cases: **0**
- Reviewer B actual defect calls: **3/36**, all adjudicated as Phase-rule interpretation errors
- State-rule change required by R2: **false**

These values are not converted into a PASS.

## 3. Revised role of G7

G7 becomes **D7 — Independent Semantic Falsification Diagnostic**.

D7 is not a numeric pass/fail prerequisite for State v2 design Freeze.

D7 remains mandatory as a preserved diagnostic record before Freeze and may still create a hard blocker if adjudication confirms any of the following:

1. actual-case future/PnL leakage in State/NOW semantics;
2. a contradiction between the frozen rule package and the State v2 rule specification;
3. a blocking vocabulary gap that cannot be represented by existing axes/descriptors/statuses;
4. an illegal status/value/reason combination in the specification itself;
5. evidence that a State threshold or rule must change for semantic correctness.

Reviewer disagreement, kappa failure, or a missed synthetic control **alone** no longer blocks Freeze after the diagnostic has been completed and adjudicated.

This is a governance change, not a retrospective statistical PASS.

## 4. Current D7 disposition

For the current candidate:

`D7_COMPLETE_WITH_REVIEWER_RELIABILITY_LIMITATIONS / NO_CONFIRMED_STATE_RULE_BLOCKER`

Supporting evidence:
- G7 v1 fail and mechanical adjudication preserved;
- review-harness timing defect repaired and regression-tested;
- G7 R2 run used 36 new Development Opportunities with zero overlap with the first review;
- G7 R2 formal fail preserved;
- no blocking semantic-adequacy concern from either reviewer;
- no actual future-leak claim;
- three Reviewer-B actual defect calls were adjudicated against the pinned mechanical rule as interpretation errors;
- no State class, numeric threshold, Scale rule, horizon, or Opportunity filter was changed.

This disposition does **not** claim semantic completeness of all Japanese-equity price behavior.

## 5. Revised Freeze gates

The original precommit remains historical evidence. From this revision onward, design Freeze requires:

- **F1** Rule-spec completeness and exact source pins
- **F2** Decision log / no outcome tuning
- **F3** Closed status/reason schema and golden vectors
- **F4** PIT/as-of contract
- **F5** Descriptive coverage disclosure
- **F6** NOW/Future/Recognition responsibility separation
- **D7** Independent semantic falsification diagnostic completed and adjudicated; no confirmed State-rule blocker
- **F8** Independent final differential design review returns `SAFE_TO_FREEZE_V2_DESIGN`

Only F8 remains an unresolved design-Freeze decision after this governance revision, subject to the final reviewer also accepting or rejecting this revision itself.

Generation Acceptance gates A1–A12 are unchanged and remain mandatory after implementation.

## 6. Why the revision is bounded

This change is deliberately narrow.

It does not weaken:
- truncation invariance;
- instrumented causal reads;
- timestamp/knownAt checks;
- NOW/Future artifact isolation;
- row conservation;
- canonical replay;
- status/value legality;
- v1→v2 transition audit;
- independent implementation/golden-vector acceptance;
- sealed Holdout/Fresh/OOS/Prospective boundaries.

Those are machine-checkable Acceptance gates and remain hard requirements.

The revision changes only whether two LLM reviewers must achieve a specific control/kappa score before the **design document** can be frozen.

## 7. Anti-post-hoc protections

Because this revision occurs after G7 failure:

- both G7 failures remain visible and immutable;
- the exact reason for changing the gate is recorded;
- no State rule is modified using the G7 outcomes;
- the final independent reviewer is explicitly asked to evaluate whether this governance revision is methodologically acceptable;
- if the final reviewer judges the revision unsafe or identifies a State-rule blocker, State v2 remains NOT_FROZEN.

## 8. STOP boundary

After this revision, do **not** implement or generate State v2 until the final differential reviewer returns a Freeze decision.

Causal Recognition, Signal, BUY/WAIT, Entry, EXIT, Capital and Portfolio remain not started under this revision.

Safety9 remain false.
