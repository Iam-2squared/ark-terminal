# Phase57 MSH-Entry LONG v1 Pre-Implementation Feasibility Audit

**Verdict: MSH_ENTRY_LONG_V1_FEASIBLE_WITH_CONTRACT_CHANGES**

Same already-opened 76 Development sessions only. No model was fit, no predictions or performance metrics were produced, and no threshold, class weight, L2 value, feature importance, or CV performance was searched.

## Identity and training rows

- Candidate rows: 3,800 Frozen Selector Top5 events
- Unique symbol-sessions: 2,743
- Repeats per symbol-session: median 1, P90 2, max 6
- Selector score / rank / Decision Price availability: 100.00% / 100.00% / 100.00%

## Existing feature intrinsic availability

| Feature | All | Open Early | Dependency |
|---|---:|---:|---|
| directionalReturnFromOpenPct | 76.03% | 71.05% | exact 09:00 open plus latest completed close; session-open dependent, intervening gaps not used by the formula |
| directionalVwapDistancePct | 31.39% | 61.84% | complete observed session-to-date 5m grid beginning 09:00 and positive volume; session-open and grid dependent |
| directionalMomentum3Pct | 65.16% | 83.68% | 4 completed same-session 5m bars; latest close / close 3 completed bars earlier; lunch boundary skips scheduled recess; no prior session and no fill |
| directionalMomentumAccelerationPct | 49.34% | 0.00% | 7 completed same-session 5m bars; Momentum3 minus Momentum6; no prior session and no fill |
| directionalPullback6Pct | 58.16% | 61.84% | 6 completed same-session 5m bars including High; no prior session and no fill |
| relativeVolume5 | 58.16% | 61.84% | 6 completed same-session 5m bars and positive prior-five mean volume |
| minutesSinceFirstSelection | 100.00% | 100.00% | selector event lineage only; wall-clock elapsed time |
| hybridReciprocalRank | 100.00% | 100.00% | selector rank only; 1/rank |
| priorSelectionCount | 100.00% | 100.00% | earlier Top5 events for the same symbol-session |
| direction | 100.00% | 100.00% | constant LONG=1; semantically redundant in a LONG-only model |

## Strict wall-clock 30m ordinal label

- Labelable: 1,828 / 3,800 (48.11%)
- HIGH availability: 1,828; CLOSE availability: 1,828

| Class | Count | Meaning |
|---:|---:|---|
| 0 | 606 | below +1% |
| 1 | 423 | +1% to below +2% |
| 2 | 271 | +2% to below +3% |
| 3 | 281 | +3% to below +5% |
| 4 | 247 | +5% or more |

## Core scoreability

| Core | Features | All | Open Early |
|---|---|---:|---:|
| A | selectorScore | 100.00% | 100.00% |
| B | selectorScore, ridgeRank | 100.00% | 100.00% |
| C | selectorScore, directionalMomentum3Pct | 65.16% | 83.68% |
| D | selectorScore, ridgeRank, directionalMomentum3Pct | 65.16% | 83.68% |

## Contract recommendations

- **trainingRowUnit:** One frozen Top5 selection event. Repeats remain correlated observations, never independent trades.
- **primaryLabelSemantics:** Candidate ordinal 0..4 from maximum future continuous 5m HIGH over a complete strict +30 wall-clock-minute same-session path; unlabelable rows excluded, never class 0. Freeze only after independent review.
- **supportingLabelDiagnostic:** Completed 5m CLOSE ordinal confirmation from the identical complete 30m path, stored separately from the primary HIGH-touch label.
- **coreFeatures:** Mandatory v1 core: frozen Selector Ridge score and rank. Both are complete Selector outputs and require no market-bar imputation.
- **optionalFeatures:** Momentum3 is intrinsically available for 65.16% overall and 83.68% Open Early; treat it and other bar-derived features as optional until a missing contract is frozen. Raw Decision Price is reference-only; LONG direction is constant and should not be a model feature.
- **missingStrategy:** Do not use raw missing=0. Keep mandatory core fully observed. If an optional feature is admitted later, use an explicit missing indicator plus training-only standardized neutral value; otherwise omit it from v1. No forward-fill or previous-session substitution.
- **state:** Stateless ENTER or SKIP_THIS_DECISION at each frozen selection event. Re-evaluate only on a later explicit Frozen Selector reselection; do not inherit WATCH/WAIT/terminal-expiry semantics. Position/re-entry safety remains external.
- **cvSplit:** SESSION-grouped expanding-window chronological split. All events from a JST session stay in one fold, which also keeps every symbol-session together. Fold count remains unfrozen; ordinary stratified K-fold is prohibited.
- **developmentAllocation:** The same 76 already outcome-exposed sessions may be reused only as MSH-Entry LONG v1 Development. They cannot become Validation/OOS. Preserve all sealed Validation/OOS/EXIT/integration/allocation/portfolio data.

STOP: ISSUE_FEASIBILITY_VERDICT_AND_CONTRACT_RECOMMENDATIONS_THEN_STOP_BEFORE_IMPLEMENTATION_OR_TRAINING
