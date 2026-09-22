# Phase57 — State v2 Rule-Spec Hardening Evidence Pack

Status: **HARDENING_COMPLETE / NOT_FROZEN**


---

# Claude independent review disposition

# Claude Independent Review — State Definition v2 Design Draft

Received: **2026-09-21 JST**  
Recorded into GitHub hardening evidence: **2026-09-22 00:39 JST**

## Verdict

`APPROVE_WITH_REQUIRED_CHANGES`

Final Freeze decision from reviewer:

`NOT_SAFE_TO_FREEZE_V2_DESIGN`

The reviewer judged the architecture direction sound but found the draft to be a taxonomy rather than a Freeze-level rule specification.

## Blocking findings carried into hardening

### C1 — Rule specification incomplete
Freeze requires exact observation prerequisites, inherited rule IDs/hashes, closed enums, deterministic reason handling, golden vectors, and spec/code/input hashes.

### C2 — Single-reason masking repeats the R3 problem
Use multi-valued `reasonCodes[]` and display-only `primaryReason`. Future censoring must use overlapping flags rather than exclusive causal labels.

### C3 — Status semantics
- evaluated absence must not be `NOT_APPLICABLE`
- remove or mechanically define AMBIGUOUS
- distinguish `INSUFFICIENT` from `NOT_EVALUATED`
- do not treat low pivot count as a market state

### C4 — Truncation replay is necessary but not sufficient for PIT
Timestamp convention, known-at, price adjustment, data vintage, dataset-wide parameters, pivot confirmation delay, stateful carry-over, calendar provenance, and Future→NOW isolation require separate tests.

### C5 — R1 cannot justify vocabulary
R1 is descriptive future-confirmation context. The conservative no-FORMING decision must rest on the frozen evidence requirement, not future resolution rates.

### C6 — Missingness / selection bias disclosure
Current reference coverage is systematically incomplete. Pre-Freeze descriptive coverage must be reported by time, price, and Opportunity without using the report to retune State rules.

### C7 — Old R2 36/36 is non-gating
A new two-reviewer, blinded, status-stratified chart protocol with synthetic negative controls is required.

### C8 — Ground Truth naming / Recognition responsibility
NOW should be a causal rule-based State Descriptor/Reference, Future a future-assisted descriptive reference. Recognition must predict delayed-confirmation axes rather than trivially reproduce deterministic NOW descriptors.

## Reviewer-requested gate changes

- split design Freeze gates from generated-artifact Acceptance gates
- preserve truncation invariance as a hard Acceptance check
- add timestamp/as-of/vintage audit
- add golden vectors and independent reimplementation
- add deterministic replay under processing-order changes
- add future perturbation isolation
- add full v1→v2 transition audit
- add descriptive coverage report
- require two independent semantic reviewers

## Hardening disposition

The new Freeze Candidate addresses C1–C8 by:
- pinning mechanical-v1 exactly
- defining v2 status/value/reason semantics
- defining multi-reason/censor flags
- separating NOW and Future artifacts
- defining PIT/provenance requirements
- adding coverage disclosure
- adding golden vectors
- pre-registering G7
- splitting Freeze and Acceptance gates

It remains **NOT FROZEN** until:
1. G7 two-reviewer review passes, and
2. Claude differential review returns `SAFE_TO_FREEZE_V2_DESIGN`.


---

# Decision log

# Phase57 — State v2 Hardening Decision Log

Status: **PRE-FREEZE / OUTCOME FIREWALL ACTIVE**

| Decision | Classification | Basis | Outcome use |
|---|---|---|---|
| Keep mechanical-v1 numeric rules unchanged | DEFINITIONAL | Already adopted and source-locked | none |
| Rename NOW from Ground Truth to `now_state_reference_v2` | DEFINITIONAL | NOW is a causal rule-based descriptor | none |
| Separate `future_resolution_v2` | DEFINITIONAL / PIT | Prevent delayed confirmation from contaminating NOW | none |
| Remove common `AMBIGUOUS` status | DEFINITIONAL | No frozen axis had a mechanical AMBIGUOUS trigger | none |
| Use `DEFINED(NONE/[])` for evaluated negative findings | DEFINITIONAL | Separate negative finding from masking | none |
| Define `INSUFFICIENT` vs `NOT_EVALUATED` | DEFINITIONAL | Evidence-count shortage vs prerequisite failure | none |
| Store `reasonCodes[]` plus display-only `primaryReason` | OBSERVATION_DRIVEN | R3 showed nested/overlapping missing causes | no PnL/return |
| Keep Structure non-mandatory | OBSERVATION_DRIVEN | Scale/observation availability is incomplete; do not erase independent axes | no PnL/return |
| Keep `INSUFFICIENT_PIVOTS(k)` without FORMING state | DEFINITIONAL | Frozen Structure evidence requirement is four confirmed pivots | R1 is descriptive only |
| H=10 active minutes | PREEXISTING_DEFINITION | Inherited mechanical-v1 `ORACLE_HORIZON=10` | R1 did not reselect H |
| R1 rates | OUTCOME_INFORMED_CONTEXT_ONLY | Describes future confirmation / censoring | cannot choose vocabulary |
| R2 36/36 | NON-GATING_CONTEXT | Single-reviewer sample cannot prove completeness | not a Freeze basis |
| Add status-cell coverage report | OBSERVATION_DRIVEN | Detect systematic missingness / selection bias | non-gating |
| Fixed Selector-price bands in coverage report | REPORTING_ONLY | `<500`, `500-999`, `1,000-2,999`, `3,000-9,999`, `>=10,000` | cannot affect State rules |
| Time bands in coverage report | REPORTING_ONLY | OPEN, AM, PM_EARLY, PM_LATE fixed clock bands | cannot affect State rules |
| Add tick/daily-limit metadata without changing rules | PIT/AUDIT_ONLY | Diagnose exact-equality and no-trade contexts | cannot affect v2.0 labels |
| Keep ScaleSpec unchanged | DEFINITIONAL | Avoid result-driven repair | missingness is disclosed, not optimized |
| Causal Recognition target = future-adjudicated delayed-confirmation axes | RESPONSIBILITY_SEPARATION | Avoid trivial prediction of deterministic NOW descriptors | no PnL/return |

## R1 disposition

R1 is not allowed to justify “FORMING is bad” or to select a vocabulary.

The rule is simpler: if the frozen Structure rule has not produced enough confirmed evidence, v2 reports evidence insufficiency rather than inventing a new market state.

H=10 remains only because it existed in the source-locked mechanical-v1 package before the R1 result was observed.

## Sealed-data statement

This hardening task opens no Common Holdout, Fresh, OOS, or Prospective data and performs no new provider requests.

## Future evaluation North Star — not a State-definition input

The user’s final integrated Entry+EXIT evaluation objective is recorded separately from State design:

- Oracle opportunity range = Selector-after Low → later High, future-assisted and evaluation-only
- Entry quality = distance from realized Entry to Oracle Low
- EXIT quality = distance from realized EXIT to Oracle later High
- integrated realized return
- Oracle capture ratio
- opportunity-weighted Oracle capture

These metrics must not influence State v2 rule definition or Causal Recognition label construction.


---

# Pre-Freeze coverage disclosure

# Phase57 — Pre-Freeze State Coverage Disclosure

Status: **DESCRIPTIVE ONLY / NON-GATING / NO THRESHOLD CHANGES**

Source: GitHub Actions artifact `phase57-five-minute-reference-g-20ebb47323b7c1aca4e4579c7783fc9f48c75792`  
Artifact digest: `sha256:cc921c476af1079344975daa78e89fe03ee0dfc20ee62333170199178ade795e`  
Measurement manifest SHA-256: `4e11b8eb576dcdd0552f2461c699f57bdabc1db37d8e4c2be9a389a80748d6d1`  
Rows: **77,214 checkpoints / 2,155 Opportunities**

This report describes the existing mechanical-v1 Development reference artifact. It is not v2 output and may not be used to retune State rules.

## Overall checkpoint coverage

| Metric | N | Rate |
| --- | ---: | ---: |
| Latest5 complete / Direction defined | 28,474 | 36.88% |
| Scale AVAILABLE | 39,282 | 50.87% |
| Structure defined | 8,809 | 11.41% |
| Phase non-empty | 11,621 | 15.05% |
| Attributes non-empty | 18,257 | 23.64% |

## Missingness association

Scale unavailable among checkpoints with current bar missing: **74.60%**  
Scale unavailable among checkpoints with current bar observed: **32.05%**

This is descriptive association, not a causal claim. It supports carrying Observation/Scale status into downstream denominators rather than evaluating only the defined subset.

## Time-band coverage

Fixed bands, chosen for reporting only:

- `OPEN_0900_1000`: 09:00 ≤ t < 10:00
- `AM_1000_1130`: 10:00 ≤ t ≤ 11:30
- `PM_EARLY_1230_1400`: 12:30 ≤ t < 14:00
- `PM_LATE_1400_CLOSE`: 14:00 ≤ t ≤ close

| Time band | N | Direction defined | Structure defined | Phase non-empty | Scale available |
| --- | ---: | ---: | ---: | ---: | ---: |
| OPEN_0900_1000 | 1,740 | 63.97% | 22.41% | 27.64% | 62.07% |
| AM_1000_1130 | 15,474 | 42.83% | 16.34% | 20.29% | 56.11% |
| PM_EARLY_1230_1400 | 24,402 | 36.69% | 9.98% | 14.47% | 51.19% |
| PM_LATE_1400_CLOSE | 35,598 | 33.09% | 9.71% | 12.55% | 47.83% |

## Fixed Selector-price-band coverage

Price bands are fixed reporting bins and have no role in State rules:

`<500`, `500-999`, `1,000-2,999`, `3,000-9,999`, `>=10,000`.

| Selector price band | Checkpoint N | Direction defined | Structure defined | Phase non-empty | Scale available |
| --- | ---: | ---: | ---: | ---: | ---: |
| <500 | 25,992 | 40.91% | 12.22% | 14.92% | 57.83% |
| 500-999 | 16,098 | 31.28% | 7.31% | 10.80% | 40.59% |
| 1,000-2,999 | 25,422 | 36.06% | 12.69% | 17.21% | 48.45% |
| 3,000-9,999 | 8,802 | 37.23% | 12.33% | 16.45% | 53.44% |
| >=10,000 | 900 | 40.22% | 16.00% | 20.44% | 77.33% |

## Opportunity-level coverage

| Opportunity-level metric | N / 2,155 | Rate |
| --- | ---: | ---: |
| Any Direction defined | 1,509 | 70.02% |
| Any Structure defined | 604 | 28.03% |
| Any Phase non-empty | 712 | 33.04% |
| Any Attributes non-empty | 1,246 | 57.82% |
| Scale AVAILABLE | 1,005 | 46.64% |

Distribution of within-Opportunity checkpoint coverage:

| Opportunity checkpoint coverage | P25 | Median | P75 |
| --- | ---: | ---: | ---: |
| Direction | 0.00% | 19.44% | 70.83% |
| Structure | 0.00% | 0.00% | 5.00% |
| Phase non-empty | 0.00% | 0.00% | 11.79% |
| Attributes non-empty | 0.00% | 6.67% | 45.00% |

## Existing source limitations

The source artifact already declares:

- `INHERITED_RAW_PRICE_BASIS`
- `INHERITED_SAME_DAY_METADATA_NOT_INDEPENDENT_PIT`
- `CURRENT_ACTION_RAW_NOT_REAUDITED`
- `SOURCE_ALREADY_FILTERED_INVALID_ROWS_CAUSE_NOT_ALWAYS_RECOVERABLE`

Therefore this report is historical Development coverage, not prospective availability proof.

## Disposition

No threshold, Scale rule, State class, horizon, or Opportunity membership is changed because of these values.


---

# Freeze and Acceptance gates

# Phase57 — State v2 Freeze Gates and Generation Acceptance Gates

Status: **PRECOMMITTED / FREEZE_NOT_YET_GRANTED**

This document separates design Freeze from generated-artifact Acceptance.

## A. Freeze gates — before implementation

### F1 — Rule-spec completeness and pins
PASS requires:
- `STATE_DEFINITION_v2_FREEZE_CANDIDATE.md` exists
- inherited mechanical-v1 source commit and SHA-256 pins are recorded
- all axis statuses, negative values, prerequisites, reason semantics, and evaluation order are specified
- spec SHA-256 is recorded in the candidate manifest

### F2 — Decision log / no outcome tuning
PASS requires:
- every material v2 design decision classified as `DEFINITIONAL`, `OBSERVATION_DRIVEN`, or `OUTCOME_INFORMED_CONTEXT_ONLY`
- PnL/future return not used
- Common Holdout / Fresh / OOS / Prospective remain unopened
- H=10 explicitly treated as inherited, not reselected from R1

### F3 — Status/reason schema and golden vectors
PASS requires:
- closed status enum
- closed core reason-code enum
- deterministic primaryReason precedence
- illegal status/value combinations specified
- synthetic golden vectors cover multi-reason, negative finding, insufficient pivots, censor overlap, and future-isolation cases

### F4 — PIT contract
PASS requires specification of:
- provider timestamp normalization
- event-time and known-at checks
- historical availability qualification
- corporate-action / price-basis as-of handling
- source vintage hashes
- pivot confirmation timing
- stateful carry-over prohibition
- injected calendar provenance

Known historical source limitations may remain, but they must be explicit and may not be promoted to prospective parity.

### F5 — Coverage disclosure
PASS requires a descriptive coverage report from the existing Development reference artifact:
- overall checkpoint coverage
- time-band coverage
- fixed Selector-price-band coverage
- Opportunity-level coverage
- missingness association
The report is non-gating and may not be used to change v2 thresholds.

### F6 — Naming and Recognition responsibility
PASS requires:
- NOW artifact called `now_state_reference_v2`
- Future artifact called `future_resolution_v2`
- “Ground Truth” removed from current v2 naming
- Causal Recognition target responsibility documented

### F7 — Two-reviewer semantic chart review
PASS requires the preregistered `G7_CHART_REVIEW_PROTOCOL.md` to be executed:
- bars<=t only
- PnL/future return hidden
- status-cell stratification with rare-cell oversampling
- two independent reviewers
- blinded synthetic negative controls
- preregistered agreement / failure criteria

The previous single-reviewer 36/36 R2 is non-gating.

**Current state: PENDING.**

### F8 — External differential design review
PASS requires Claude (or another explicitly independent reviewer chosen by the user) to review only the hardening delta and return:
- `SAFE_TO_FREEZE_V2_DESIGN`

**Current state: PENDING.**

Only after F1–F8 PASS may the candidate be marked `FROZEN`.

---

## B. Generation Acceptance gates — after implementation

### A1 — Row conservation
- source Opportunities = 2,155
- source checkpoints = 77,214
- duplicate keys = 0
- dropped Opportunities = 0
- silent refilter = 0

### A2 — Determinism
Run the same frozen input twice and vary processing order / allowed parallelism.
- canonical output hash must match
- input hashes/runtime identity recorded

### A3 — Causal read enforcement / truncation invariance
Instrument every NOW primitive read.
- any source timestamp > t → hard fail
- if knownAt exists, knownAt > t → hard fail
- recompute every NOW row from prefix through t
- 77,214 / 77,214 canonical NOW rows must match saved output

A3 is necessary but not sufficient for PIT correctness.

### A4 — Status/value legality
Hard fail if:
- status is outside closed enum
- reason code is outside closed enum
- DEFINED lacks legal value
- non-DEFINED status lacks required reasonCodes
- illegal status/value pair exists
- reasonless null exists

Report `OBS_NOT_OBSERVED_CAUSE_UNKNOWN` frequency; do not hide it.

### A5 — Provenance completeness
Validate required provenance fields by schema plus an independently recomputed sample from raw inputs.

### A6 — NOW/Future mechanical isolation
Require:
- separate module/schema/hash
- NOW module cannot import Future module
- Future suffix perturbation/removal leaves NOW hash unchanged
- join key between artifacts is only the checkpoint identity contract

### A7 — v1→v2 transition audit
- every changed row has closed `changeReasonCodes[]`
- change predicate can be recomputed from row fields
- unexplained residual = 0
- full status cross-tabs and concentration reports saved

### A8 — Timestamp / as-of / vintage audit
Hand-audit provider samples for:
- bar-start vs bar-end convention
- availability semantics
- corporate-action as-of
- exact source vintage

A consistent off-by-one that passes truncation replay is still a failure here.

### A9 — Golden vectors + independent implementation
- frozen synthetic vectors all pass
- second minimal implementation written from the spec, not copied from primary code, matches expected canonical outputs

### A10 — Coverage report
Regenerate v2 descriptive coverage by:
- time band
- fixed Selector-price band
- Opportunity
- Scale status
- Observation status

Coverage values do not pass/fail the model and may not trigger v2.0 threshold changes.

### A11 — Safety / contamination
- Safety9 all false
- protected data opened = 0
- provider requests = 0 unless separately authorized
- PnL/future return not used for State-definition acceptance
- Common Holdout / Fresh / OOS / Prospective remain sealed

### A12 — Acceptance disposition
Only if A1–A11 pass:
`STATE_REFERENCE_V2_ACCEPTED_FOR_CAUSAL_RECOGNITION_RESEARCH`

Acceptance does not authorize Signal, BUY/WAIT, Entry, EXIT, or trading.


---

# G7 two-reviewer semantic chart review protocol

# Phase57 — G7 Two-Reviewer Semantic Chart Review Protocol

Status: **PREREGISTERED / NOT_YET_EXECUTED**

Purpose: test whether the frozen axes and status semantics are intelligible and semantically adequate before State v2 Freeze, without using PnL or future return.

## 1. Source and blinding

Use only the existing Development reference artifact.

For each actual chart show only:

- bars <= checkpoint t
- scheduled missing intervals through t
- Scale value/status available at t
- pivots with `confirmedAt <= t`
- current NOW axis outputs/statuses
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

The deterministic sample must oversample status cells rather than only pivotSignature.

Required actual strata include:

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
- rare Scale statuses (`PREVIOUS_CONTEXT_UNAVAILABLE`, `PRICE_BASIS_UNVERIFIED`, `SCALE_ZERO`) when examples exist

Within strata, spread across the fixed time bands and Selector-price bands where possible.

Selection seed:

`phase57-state-v2-g7-status-stratified-20260921`

No sampling by future outcome or profitability.

## 3. Synthetic negative controls

Insert blinded synthetic controls that intentionally contain known semantic violations.

Minimum controls:

1. UP/DOWN Structure label swapped
2. missing current bar displayed as complete
3. future-confirmed pivot incorrectly shown as NOW-confirmed
4. Scale unavailable row displayed with numeric Scale
5. evaluated no-Structure row displayed as NOT_APPLICABLE rather than DEFINED(NONE)
6. pivotN<4 row displayed as FORMING market state
7. observation and Scale failures collapsed to one exclusive reason
8. Future censor flags collapsed so only one overlapping cause is visible

Controls are not used to estimate market error; they test reviewer discrimination.

## 4. Reviewer rubric

Each actual chart receives zero or more issue tags:

- `SEMANTICS_SUFFICIENT`
- `BOUNDARY_OR_TOLERANCE_SUSPECTED`
- `OBSERVATION_OR_PROVENANCE_PROBLEM`
- `VOCABULARY_GAP_CANDIDATE`
- `STATUS_SEMANTICS_PROBLEM`
- `INDETERMINATE`

Each control also requires:

- `CONTROL_MISMATCH_DETECTED = true|false`

Reviewers must provide one short rationale.

## 5. Independence

Two reviewers inspect the blinded package independently before seeing each other’s labels.

Reviewer A: OpenAI  
Reviewer B: Claude, unless the user explicitly selects another independent reviewer.

## 6. Predeclared pass/fail

Hard fail if:

- either reviewer misses any of the 8 synthetic negative controls, or
- any actual chart reveals future/PnL leakage, or
- an unresolved `VOCABULARY_GAP_CANDIDATE` would require changing v2.0 semantics.

Agreement requirement on actual charts:

- compute binary `ISSUE` = any tag other than SEMANTICS_SUFFICIENT
- Cohen’s kappa >= 0.60

If kappa is undefined because one class has zero variance, require raw agreement >= 85% plus 8/8 control detection by both reviewers.

Disagreements may be adjudicated only after independent labels are frozen.

If a vocabulary gap remains after adjudication, do not patch v2.0 from the same review set. Record it for v2.1 and do not Freeze v2.0 unless the gap is judged non-blocking under the predeclared rubric.

## 7. Relation to old R2

The prior 36/36 single-reviewer R2 result is preserved as historical context only. It is not a Freeze Gate and does not count as Reviewer A or B for this protocol unless the exact new blinded package is independently rescored.

