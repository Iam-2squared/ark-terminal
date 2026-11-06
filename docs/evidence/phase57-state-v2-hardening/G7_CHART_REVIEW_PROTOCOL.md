# Phase57 — G7 Two-Reviewer Semantic Chart Review Protocol

Status: **PREREGISTERED / BLINDED_PACKAGE_BUILT / NOT_YET_EXECUTED**

Purpose: test whether the frozen axes and status semantics are intelligible and semantically adequate before State v2 Freeze, without using PnL or future return.

## 1. Source and blinding

Use only the existing Development reference artifact.

For each actual chart show only:
- bars <= checkpoint t
- scheduled missing intervals through t
- Scale value/status available at t
- pivots with `confirmedAt <= t`
- current proposed v2 axis outputs/statuses
- relevant fixed levels set before t

Hide:
- PnL
- future returns
- later High/Low
- future-resolution outcome
- Entry/EXIT result
- future-confirmed pivots

One Opportunity contributes at most one actual checkpoint unless needed for a rare status that cannot otherwise be represented.

## 2. Stratification

The deterministic actual sample is status-cell stratified and contains 36 distinct Opportunities.

Required actual strata:
- DEFINED UP_STRUCTURE
- DEFINED DOWN_STRUCTURE
- DEFINED RANGE_STRUCTURE
- DEFINED NONE with pivotN>=4
- INSUFFICIENT pivotN=0
- INSUFFICIENT pivotN=1
- INSUFFICIENT pivotN=2
- INSUFFICIENT pivotN=3
- current bar not observed
- latest5 incomplete but current bar observed
- Scale unavailable with current bar observed
- rare Scale statuses (PREVIOUS_CONTEXT_UNAVAILABLE, PRICE_BASIS_UNVERIFIED, SCALE_ZERO) when examples exist

Sampling seed:
`phase57-state-v2-g7-status-stratified-20260921`

No sampling by future outcome or profitability.

The built package contains 36 actual cases:
- 3 each for the 11 common strata above except rare Scale
- 1 each for PREVIOUS_CONTEXT_UNAVAILABLE, PRICE_BASIS_UNVERIFIED, SCALE_ZERO
- 36 unique Opportunities
- time-band distribution: OPEN 8 / AM 8 / PM_EARLY 8 / PM_LATE 12
- fixed Selector-price-band distribution: <500 9 / 500-999 8 / 1,000-2,999 10 / 3,000-9,999 7 / >=10,000 2

All actual cases used in the blinded package have `lateConfirmedPivots=0` in the existing G artifact so the displayed pivots are not future-confirmed augmentations.

## 3. Synthetic negative controls

Insert 8 blinded semantic controls randomly among the 36 actual cases.

Controls:
1. UP/DOWN Structure label swapped
2. missing current bar displayed as complete
3. future-confirmed pivot incorrectly shown as NOW-confirmed
4. Scale unavailable row displayed with numeric Scale
5. evaluated no-Structure row displayed as NOT_APPLICABLE rather than DEFINED(NONE)
6. pivotN<4 row displayed as FORMING market state
7. observation and Scale failures collapsed to one exclusive reason
8. overlapping Future censor causes collapsed to one displayed censor flag

Controls test reviewer discrimination, not market error.

## 4. Reviewer rubric

Each case receives zero or more issue tags:
- `SEMANTICS_SUFFICIENT`
- `BOUNDARY_OR_TOLERANCE_SUSPECTED`
- `OBSERVATION_OR_PROVENANCE_PROBLEM`
- `VOCABULARY_GAP_CANDIDATE`
- `STATUS_SEMANTICS_PROBLEM`
- `INDETERMINATE`

Use `SEMANTICS_SUFFICIENT` alone when no issue is present.
Every case requires a short rationale.

Reviewers are not told which cases are controls.

## 5. Independence

Two reviewers inspect the **same blinded package** independently before seeing each other's labels.

A review counts for G7 only if:
- the reviewer is in a fresh session/context that did not author or edit the v2 Freeze Candidate;
- the reviewer has not seen the other reviewer's labels;
- the reviewer has not issued the differential Freeze verdict for this same candidate;
- the reviewer receives the blinded package only, not the sealed control key or sampling truth;
- all case labels are frozen before any adjudication.

Reviewer A: fresh OpenAI session/context independent from the specification-authoring chat.

Reviewer B: fresh Claude session/context independent from the Claude differential Freeze-review session, unless the user explicitly selects another independent reviewer.

The current specification-authoring OpenAI chat does **not** count as Reviewer A.
The Claude session that issued the differential Freeze verdict does **not** count as Reviewer B.

Both reviewers are LLM-based unless the user chooses a human reviewer. Their errors may therefore be correlated. G7 is a semantic falsification check, not proof of objective ground truth. This limitation must be recorded in the final G7 receipt.

## 6. Predeclared pass/fail

Hard fail if:
- either reviewer fails to identify the semantic mismatch in any of the 8 synthetic negative controls; or
- any actual case reveals future/PnL leakage; or
- an unresolved `VOCABULARY_GAP_CANDIDATE` would require changing v2.0 semantics.

Agreement on actual cases:
- derive binary ISSUE = any tag other than SEMANTICS_SUFFICIENT
- Cohen's kappa >= 0.60

If kappa is undefined because one class has zero variance:
- raw agreement >= 85%
- both reviewers detect 8/8 controls

Disagreements may be adjudicated only after both independent label files are frozen.

If a vocabulary gap remains after adjudication, do not patch v2.0 from the same review set. Record it for v2.1 and do not Freeze v2.0 unless the gap is judged non-blocking under this preregistered rubric.

## 7. Package identity

Blinded reviewer ZIP SHA-256:
`303acb5c66b586917b75d1a48bb0e4b0fc848b7d48d86f9d63bb8273283676c1`

Sealed admin-key ZIP SHA-256:
`15e389cbf3638e89e5555e934fe73152b3d4782b5304d4348372ea407d3d932b`

The blinded package contains 44 cases, `INSTRUCTIONS.md`, `RESPONSE_TEMPLATE.csv`, and a public case manifest. It excludes source identity, control identity, outcome data, and the sealed key.

## 8. Relation to old R2

The prior 36/36 single-reviewer R2 result is historical context only. It is not a Freeze Gate and does not count as Reviewer A or B.
