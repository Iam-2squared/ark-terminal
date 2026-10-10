# Phase57 — 5-Minute State Definition v2 FREEZE CANDIDATE

Status: **FREEZE_CANDIDATE / NOT_FROZEN / NOT_IMPLEMENTED / PENDING_CLAUDE_DIFFERENTIAL_REVIEW / PENDING_G7_SECOND_REVIEW**

Source branch: `research/phase57-long-only-cash-equity`  
Source HEAD before hardening: `52370348bab598de24cf3a2e6c2df8bde27a8f94`

## 0. Purpose

This specification converts the v2 design taxonomy into an implementation-level rule contract.

The purpose is not to optimize PnL, reduce UNKNOWN, or maximize Structure identification. The purpose is to define one deterministic, auditable reference representation for the 5-minute state of a Selector opportunity so that later causal recognition, Signal analysis, BUY NOW / WAIT, Entry, and EXIT can be evaluated without silently changing label semantics.

No PnL, future return, Holdout, Fresh, OOS, or Prospective data is used to choose rules in this specification.

## 1. Immutable inherited rule package

v2.0 does **not** change the numeric market rules of the adopted mechanical-v1 package. It inherits them by exact source pin.

- rule family: `five-minute-state-mechanical-v1`
- adopted source commit: `9a764e27086bf6bb1133c304b73c0027d1275760`
- source directory: `docs/phase57-five-minute-entry-state/mechanical-v1`
- `SPEC-ja.md` SHA-256: `f640e0b6bd04bd1a3f65130d64d904607064e34227e99467fc46b96b48988f70`
- `contract.json` SHA-256: `f00134b85218eba4dad8409a00ce7f1076d1a3abdc02d8a4cb7e2e2b3511279e`
- `reference.py` SHA-256: `e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d`
- `test_reference.py` SHA-256: `eed192e39e957a97229e8bdfc4b75e0c79dc393a70d150ca0b714eab31907ec6`
- `verify.py` SHA-256: `bda692eab389f7802c1d8f13d4100febe313174b06df8b48fa74b348c8f74e95`

If this v2 document and the pinned mechanical-v1 package disagree on a numeric market rule, the pinned mechanical-v1 package is authoritative and the disagreement is a specification defect. Numeric thresholds may not be repaired by looking at v2 output.

The inherited rules include:

- 5 active-minute evaluation cycle
- Scale S = actual previous session complete non-overlapping 5-minute True Range median
- minimum 6 complete Scale blocks, no fallback
- close-based 1S directional-change pivots
- strict HH/HL or LH/LL 4-pivot Structure
- strict close protected-level invalidation
- 30 continuous 1m Range rule
- fixed CHOP / expansion / compression rules
- fixed recovery episode semantics
- fixed close-cross / reclaim / persistence semantics
- future confirmation horizon H = 10 active minutes, same session

## 2. Naming and responsibility separation

### 2.1 NOW artifact

Name: `now_state_reference_v2`

Meaning: deterministic, rule-based causal descriptors that can be computed from information admissible at checkpoint `t`.

It is **not** called Ground Truth.

### 2.2 Future artifact

Name: `future_resolution_v2`

Meaning: future-assisted descriptive adjudication of delayed-confirmation facts about the state at `t`, using the already frozen H=10 active-minute rule.

It may confirm a pivot whose `effectiveAt <= t` and `confirmedAt > t`. It may not import a pivot whose `effectiveAt > t` into the state at `t`.

It contains no PnL and no future-return target.

### 2.3 Causal Recognition target

Causal Recognition is not an identity mapping of NOW fields.

When the Recognition stage begins, the supervised target is limited to delayed-confirmation state axes in `future_resolution_v2`, primarily the adjudicated `StructureAtT` and `PhaseAtT`. Deterministic NOW fields such as 5-minute Direction are causal descriptors/features, not prediction labels.

The exact target vector and scoring metric must be precommitted before model fitting. It may not be selected using PnL, Entry outcomes, or future returns.

## 3. Row identity and time contract

Every row is uniquely keyed by:

`opportunityId + checkpointAsOf`

Required identity fields:

- `opportunityId`
- `sessionDate`
- `securityId`
- `selectorAt`
- `checkpointAsOf`
- `elapsedActiveMinutesFromSelector`
- `activeMinutesSinceOpen`
- `sessionSegment`
- `definitionVersion = state-reference-v2.0`
- `inheritedRuleVersion = five-minute-state-mechanical-v1`

`checkpointAsOf` means the end time of the current scheduled closed 1m interval.

Active-minute arithmetic uses the injected trading calendar. Lunch/recess is not counted as active minutes. Missing bars are still scheduled active minutes and must not shift checkpoints.

## 4. ObservationQuality — Layer 0

ObservationQuality is a meta-layer. It is not a market State.

Required fields:

- `currentBarObserved`
- `scheduled5N`
- `latest5ObservedK`
- `latest5Complete`
- `density5`
- `density15`
- `density30`
- `densityToday`
- `lastObservedAgeActiveMinutes`
- `consecutiveMissingRun`
- `missingFlags[]`
- `missingCauseCodes[]`
- `evidenceSource`
- `availabilityEvidence`
- `maxSourceTimestamp`
- `maxKnownAt`
- `sourceVintageId`
- `sourceHashes`

### 4.1 Density

For N in {5,15,30}:

`densityN = observed scheduled bars / scheduled active bars in trailing N active minutes ending at t`.

If fewer than N scheduled active minutes exist since the current segment/session began, use the available scheduled count as the denominator **and** emit the relevant SHORT_HISTORY flag. A density of 1.0 does not erase a short-history flag.

`densityToday` uses scheduled active minutes from session open through `t`.

### 4.2 latest5Complete

`latest5Complete=true` only when the inherited mechanical-v1 `window` contract is COMPLETE:

- exactly 5 scheduled active 1m ends are expected,
- all 5 are observed,
- current scheduled bar is observed,
- the 5 bars do not cross a discontinuous session boundary/recess.

No forward-fill, bar retiming, or collection of “the latest five existing rows” is permitted.

### 4.3 Missing flags

Closed core flags:

- `OBS_CURRENT_BAR_NOT_OBSERVED`
- `OBS_LATEST5_INCOMPLETE`
- `OBS_MISSING_SCHEDULED_BAR`
- `OBS_SHORT_SESSION_HISTORY`
- `OBS_SESSION_BOUNDARY`
- `OBS_NOT_OBSERVED_CAUSE_UNKNOWN`

`missingFlags[]` is multi-valued. A primary display reason must never replace these flags.

No-trade, halt, or provider loss may not be inferred without independent evidence.

## 5. ScaleSpec

Scale remains separate from State vocabulary.

`scaleSpecId = PREVIOUS_SESSION_COMPLETE_5M_TR_MEDIAN_V1`

Exact semantics are inherited from the pinned mechanical-v1 package:

- actual previous session only
- complete non-overlapping 5m blocks on scheduled stamps
- True Range median in common raw price units, zeros included
- minimum 6 complete blocks
- current-day fixed
- no fallback

Required Scale fields:

- `scaleSpecId`
- `scaleStatus`
- `scaleValue`
- `scaleSourceDay`
- `previousComplete5mBlockN`
- `scaleSource`
- `scaleProvenance`

Closed `scaleStatus`:

- `AVAILABLE`
- `PREVIOUS_CONTEXT_UNAVAILABLE`
- `PRICE_BASIS_UNVERIFIED`
- `SCALE_INSUFFICIENT`
- `SCALE_ZERO`

`scaleValue` exists only when `scaleStatus=AVAILABLE`.

The v2 State specification hash includes `scaleSpecId`. Any ScaleSpec change creates a new State version for every Scale-dependent axis.

## 6. Common axis contract

The v2.0 common status enum is:

- `DEFINED`
- `INSUFFICIENT`
- `NOT_EVALUATED`
- `NOT_APPLICABLE`

`AMBIGUOUS` is removed from v2.0 because no axis had a frozen mechanical trigger for it. Ambiguity that is itself observed, such as intrabar order uncertainty, is stored as an explicit event/flag, not an undefined status.

### 6.1 Semantics

`DEFINED`  
All hard input prerequisites were available and the rule was evaluated. A negative finding is still DEFINED.

`INSUFFICIENT`  
Hard inputs were valid and the computation ran, but a predeclared evidence-count requirement was not met.

`NOT_EVALUATED`  
At least one hard prerequisite was unavailable, untrusted, or not admissible.

`NOT_APPLICABLE`  
Only for a conditional sub-evaluation whose trigger does not exist. Example: two-close persistence when no close-cross event occurred.

### 6.2 Explicit negative values

Absence after a valid evaluation is not masking.

Examples:

- Structure: `DEFINED(value=NONE)`
- Phase: `DEFINED(value=[])`
- Attribute family: `DEFINED(value=NONE)`
- Event family: `DEFINED(value=[])`

### 6.3 reasonCodes[] and primaryReason

Every non-DEFINED status contains `reasonCodes[]`. All applicable failed prerequisites are retained.

`primaryReason` is display-only and is chosen deterministically from this precedence:

1. `OBS_CURRENT_BAR_NOT_OBSERVED`
2. `OBS_SESSION_BOUNDARY`
3. `OBS_SHORT_SESSION_HISTORY`
4. `OBS_MISSING_SCHEDULED_BAR`
5. `OBS_LATEST5_INCOMPLETE`
6. `SCALE_PREVIOUS_CONTEXT_UNAVAILABLE`
7. `SCALE_PRICE_BASIS_UNVERIFIED`
8. `SCALE_INSUFFICIENT_BLOCKS`
9. `SCALE_ZERO`
10. `PIVOT_INSUFFICIENT_COUNT`
11. context/activity-specific reasons

Downstream analysis must use `reasonCodes[]`, not `primaryReason`, for causal interpretation.

## 7. NOW axes

## 7.1 Direction

Prerequisite: inherited latest-5 window COMPLETE.

Rule:

`move = close(t) - open(first bar of latest 5 scheduled active 1m bars)`

- move > 0 → `UP`
- move < 0 → `DOWN`
- move = 0 → `UNCHANGED`

`return5Pct` is retained as the exact inherited continuous descriptor.

Scale is not required.

If latest5 is not complete:

- status = `NOT_EVALUATED`
- value = null
- include every relevant observation reason code

## 7.2 Structure

Possible values:

- `UP_STRUCTURE`
- `DOWN_STRUCTURE`
- `RANGE_STRUCTURE`
- `NONE`

The actual market rules are exactly the pinned mechanical-v1 Structure and Range rules.

Evaluation order:

1. If the inherited rule returns an active UP/DOWN/RANGE Structure, return `DEFINED(value=<structure>)`.
2. Else if a hard input prerequisite is unavailable, return `NOT_EVALUATED`.
3. Else if the pivot engine ran, no active Structure/Range exists, and confirmed pivot count is <4, return `INSUFFICIENT`, reason `PIVOT_INSUFFICIENT_COUNT`, and store `pivotN`.
4. Else return `DEFINED(value=NONE)`.

`PIVOT_INSUFFICIENT_COUNT` is an evidence-status finding, not a market state called “forming”. It must be accompanied by `activeMinutesSinceOpen`, `sessionSegment`, ObservationQuality, and `pivotN`.

R1 future-resolution rates are not used to choose this rule.

## 7.3 Phase

The Phase set is exactly the pinned mechanical-v1 set:

- `PROGRESSION`
- `CORRECTION`
- `RECOVERY`
- `BALANCE`
- `RESTRUCTURING`

Multiple values may coexist where allowed by the inherited rule. This is not AMBIGUOUS.

- if the inherited phase engine can be evaluated, status=`DEFINED`; an empty phase set is `DEFINED(value=[])`
- if hard inputs required by the engine are unavailable, status=`NOT_EVALUATED`

Allowed/forbidden combinations are those emitted by the pinned reference implementation. v2 does not add combinations by prose interpretation.

## 7.4 pivotSignature

This is a descriptor, not a Structure class.

When the Scale-dependent pivot engine is evaluable and there are at least four relevant confirmed alternating pivots, compare the latest two HIGH pivots and latest two LOW pivots using exact price equality:

HIGH relation: `H_UP | H_EQ | H_DOWN`  
LOW relation: `L_UP | L_EQ | L_DOWN`

Store the 3×3 pair.

If the pivot engine is not evaluable → `NOT_EVALUATED`.

If the pivot engine is evaluable but fewer than four relevant confirmed pivots exist → `INSUFFICIENT`, reason `PIVOT_INSUFFICIENT_COUNT`.

No tolerance is introduced in v2.0.

Also store raw differences:

- `highDiffRaw`
- `lowDiffRaw`
- `highDiffTicks` when tickSize is available
- `lowDiffTicks` when tickSize is available
- `highDiffScale` when Scale is available
- `lowDiffScale` when Scale is available

These are descriptors only and do not alter the 3×3 class.

## 7.5 Attributes

Each attribute family has its own status/value/evidence.

### Choppiness

Exact inherited rule. Requires latest5 COMPLETE and Scale AVAILABLE.

Value: `CHOPPINESS | NONE`.

### Range expansion/compression

Exact inherited ratio rule between current and prior valid 5-minute windows.

Value: `EXPANSION | COMPRESSION | NONE`.

If prior/current window is not comparable or denominator is zero → `NOT_EVALUATED` with reason.

### Volume expansion/compression

Exact inherited ratio rule.

If volume is unavailable or denominator is zero → `NOT_EVALUATED`.

### Trading-value expansion/compression

Exact inherited ratio rule.

If value is unavailable or denominator is zero → `NOT_EVALUATED`.

Failure of one attribute family may not erase another family.

## 7.6 Events

Static fixed-level events and moving VWAP relation events remain separate families.

For an evaluable family, no event is `DEFINED(value=[])`.

Intrabar high/low ordering uncertainty is an explicit event flag such as `INTRABAR_ORDER_UNRESOLVED`; it does not make the entire axis AMBIGUOUS.

Persistence confirmation after a cross is a conditional sub-evaluation:

- cross exists → evaluate
- no cross exists → `NOT_APPLICABLE(reason=NO_TRIGGER_EVENT)`

VWAP cross uses only the admissible prefix through `t`. A partial observed VWAP may be retained as a descriptor but cannot be promoted to a complete VWAP cross.

## 7.7 Context

Context is not one all-or-nothing status.

Store separately:

- `recentDaily.D5 ... D1`
- `previousObservedSession`
- `todayOpenToNow`

Each lag/primitive has its own status and provenance.

Cross-day comparisons requiring common price basis or corporate-action handling are `NOT_EVALUATED` when that basis is not independently admissible. Missing context must not erase valid same-day Direction.

## 8. Causal metadata

The following metadata must be stored even though v2.0 does not use them to change State rules:

- `activeMinutesSinceOpen`
- `sessionSegment`
- `tickSize`
- `tickSizeStatus`
- `tickSizeSource`
- `atDailyLimit`
- `dailyLimitStatus`
- `dailyLimitSource`
- `maxSourceTimestamp`
- `maxKnownAt`
- `availabilityEvidence`
- `sourceVintageId`

If tick size or daily-limit status is not independently available, store null plus an explicit status. Do not infer it.

## 9. PIT / as-of contract

### 9.1 Intraday bars

A bar may enter NOW only if its event/end timestamp is <= `checkpointAsOf`.

If a trustworthy `knownAt` exists, it must also be <= `checkpointAsOf`.

If historical source data lacks independent received/known-at evidence, mark:

`availabilityEvidence = HISTORICAL_CLOSED_RECONSTRUCTION`

and do not claim prospective latency parity.

### 9.2 Timestamp convention

The implementation must record whether each provider timestamp denotes interval start or interval end and normalize once into `barEndTimestamp`.

A hand-audited raw sample is required before Acceptance. Truncation replay alone cannot detect a consistently wrong off-by-one convention.

### 9.3 Corporate actions and price basis

Cross-day Scale/Daily comparisons may only use a common price basis whose as-of semantics are proven.

The current historical G artifact explicitly carries inherited limitations including:

- `INHERITED_RAW_PRICE_BASIS`
- `INHERITED_SAME_DAY_METADATA_NOT_INDEPENDENT_PIT`
- `CURRENT_ACTION_RAW_NOT_REAUDITED`
- `SOURCE_ALREADY_FILTERED_INVALID_ROWS_CAUSE_NOT_ALWAYS_RECOVERABLE`

These limitations are not silently cured by v2.

### 9.4 Data vintage

Store exact source hashes/artifact digest and a `sourceVintageId`. Later provider corrections may not overwrite the evidence identity of an existing reference artifact.

### 9.5 Dataset-level parameters

No feature threshold, normalization constant, quantile, or scale may be computed from the full dataset unless explicitly listed in the frozen rule package and causally admissible at each row.

### 9.6 Pivot confirmation delay

NOW may use only pivots with `confirmedAt <= t`.

`effectiveAt` and `confirmedAt` remain separate.

### 9.7 Stateful carry-over

Acceptance replay must be able to recompute each checkpoint from a fresh prefix/context. Hidden state carried from future or later checkpoints is prohibited.

### 9.8 Calendar

Regular-session schedule and recess boundaries are injected inputs with provenance. A post-hoc calendar correction must create a new source vintage.

## 10. Future Resolution

`future_resolution_v2` is a separate schema, module, artifact, and hash.

Fixed horizon:

`H = 10 active minutes, same session`

This is inherited from mechanical-v1 and is not justified by R1 outcome rates.

Required fields:

- `opportunityId`
- `checkpointAsOf`
- `horizonActiveMinutes=10`
- `adjudicatedStructureAtT`
- `adjudicatedPhaseAtT`
- `lateConfirmedPivotN`
- `resolutionStatus`
- `resolutionType`
- `resolutionActiveMinutes`
- `censorFlags[]`
- `futureMaxSourceTimestamp`
- `futureSourceHashes`

Closed `resolutionStatus`:

- `RESOLVED_WITHIN_H`
- `NOT_RESOLVED_WITHIN_H`
- `CENSORED`

Closed Structure `resolutionType` when relevant:

- `UP_STRUCTURE`
- `DOWN_STRUCTURE`
- `RANGE_STRUCTURE`

Independent censor flags:

- `OBSERVATION_CENSORED_BEFORE_H`
- `SESSION_CENSORED_BEFORE_H`

Both may be true. They are never collapsed into one causal explanation.

Future suffix modification must not change the canonical hash of `now_state_reference_v2`.

## 11. R1 / R2 disposition

R1 is descriptive context only.

The decision not to create PRE_STRUCTURE / FORMING is definitional: the frozen rule has not produced sufficient evidence for an active Structure. R1 future resolution rates do not justify the vocabulary.

The existing single-reviewer R2 36/36 result is non-gating and may not be cited as proof of vocabulary completeness.

A new preregistered two-reviewer G7 protocol is required before Freeze.

## 12. v1 → v2 transition

v1 artifacts are immutable.

For every one of the 77,214 source checkpoints, transition output must retain:

- v1 key/value/status
- v2 value/status
- `changeReasonCodes[]`

Required audits:

- row conservation = 77,214
- unique key violations = 0
- missing rows = 0
- all v1 DEFINED → v2 non-DEFINED rows enumerated
- all v1 value ≠ v2 value changes enumerated
- status cross-tab complete
- symbol/session/opportunity concentration reported
- axis coverage gain/loss reported
- unexplained change rows = 0

Transition review may not use PnL or future return.

## 13. Canonical serialization and determinism

The v2 implementation must define canonical serialization before generation:

- UTF-8
- stable key ordering
- deterministic array ordering
- exact rational/decimal representation for rule-critical price comparisons
- explicit nulls where schema requires them
- no non-finite numeric values

Input snapshot hash, spec hash, code commit, dependency/runtime identity, and output hash are stored together.

Processing order and allowed parallelism changes must not change the canonical output hash.

## 14. Coverage disclosure

Coverage is descriptive, not a pass/fail threshold and not a reason to change rules.

Before Freeze, retain the existing v1 descriptive coverage report. After v2 generation, regenerate the same report with v2 statuses by:

- time band
- fixed Selector-price band
- Opportunity unit
- Scale status
- observation status

The report may not be used to retune thresholds inside v2.0.

## 15. Freeze / Acceptance gates

The authoritative gate split is:

`docs/evidence/phase57-state-v2-hardening/GATES_v2.md`

No implementation starts until the Freeze gates are explicitly satisfied.

## 16. Non-goals / STOP boundary

This candidate does not authorize:

- v2 implementation
- 77,214-row v2 generation
- Scale alternative search
- Causal Recognition model fitting
- Signal research
- State × Signal
- BUY NOW / WAIT
- Entry Timing
- Entry vNext
- EXIT
- Common Holdout / Fresh / OOS / Prospective opening
- new provider acquisition

Safety9 remain false.
