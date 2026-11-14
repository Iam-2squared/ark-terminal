# Phase57 9-State Entry Audit — PROGRESS R2

2026-09-23 JST / PR #587 / research/phase57-long-only-cash-equity

## Scope

R0 protocol remains controlling. This receipt records the final infrastructure gate before REBOUND semantic review. It does not claim REBOUND classification accuracy, Entry improvement, Fresh/OOS evidence, or promotion.

## Git / CI identity

- Source HEAD re-read before this append-only receipt: `e3c09172761dce9b8ac762c5c11be9970211eaa9`
- R0 protocol commit: `f2f5312312f9265ac6ee6c607bb1ca04e5567b6e`
- Successful blind-packet implementation head: `5c08a0944763846f960c413e82c949a5ed471693`
- Successful packet run: `35833003690`
- Trigger-hygiene head: `e3c09172761dce9b8ac762c5c11be9970211eaa9`
- Trigger-hygiene verification run: `35834283517`
- Verification conclusion: `success`

The trigger-hygiene change only removes `docs/evidence/phase57-nine-state-entry-audit-v1/**` from the packet workflow path trigger. It prevents append-only progress receipts from rebuilding the 34-case packet. It does not change the packet builder, sample definition, classifier, State definitions, Signals, Entry policy, evaluator, or data scope.

## Frozen REBOUND contract notes for blind review

The semantic review must apply the existing contract exactly; no new threshold is introduced here.

For a causally available T0 prefix:

1. `unit = max(log(1.001), 0.5 * median(abs(adjacent previous-session 1m close log returns)))` when previous-session adjacent returns exist; otherwise the fixed floor applies.
2. The recent window uses available current-session points in the latest phase within at most 10 active minutes ending at the latest available point. Lunch is removed by the existing active-minute coordinate.
3. `recentDir = sign_at_unit(recentReturn, unit)`.
4. Prior direction is taken from sufficiently determined earlier-today prefix (`earlierTransitions >= 2` and `abs(earlierReturn) >= unit`); otherwise it falls back to previous-session context.
5. `priorDir = sign_at_unit(priorReturn, unit)`.
6. When `priorDir=-1` and `recentDir=+1`, the contract distinguishes:
   - `REBOUND` when `abs(recentReturn) < abs(priorReturn)` (opposing-direction partial recovery),
   - `RISE` when `abs(recentReturn) >= abs(priorReturn)` (opposing-direction full recovery).
7. The blind packet intentionally mixes 24 frozen-T0 REBOUND cases with the 10 available full-recovery RISE comparators satisfying the fixed comparator predicate. The public packet withholds baseline State and Opportunity identity.

The public review witness may show prefix-only classifier inputs such as as-of minute, data quality, classifier confidence, unit, prior/recent direction signs and returns, coverage and transition counts. Future suffix, fill, ordered Low/Later High, MFE/MAE, Capture and outcome are excluded by the packet guard.

## Required review record before opening sealed mapping

Every `RBV1-001` ... `RBV1-034` row must be fixed with:

- `chartInspected=YES` only after the SVG was actually viewed,
- `semanticState` equal to one of the frozen nine State names,
- `contractAmbiguous=YES` only when the fixed contract cannot be applied from the packet without inventing a rule,
- concise prefix-only witness notes.

No sealed-map lookup, baseline-label lookup, evaluator anatomy or profit/outcome inspection is permitted before all 34 blind judgments are fixed. The sample is a deterministic semantic stress audit, not an unbiased population-accuracy estimate.

## Current review state

- blind packet generation: COMPLETE
- packet dedicated CI: PASS
- trigger-hygiene CI: PASS (`35834283517`)
- public packet artifact from the successful build: `10738260743`
- sealed mapping artifact: `10738275641`
- visual chart inspection claimed in repository evidence: `0 / 34`
- blind semantic judgments fixed: NO
- sealed-map comparison: NOT STARTED
- REBOUND Low/High + Entry anatomy: NOT STARTED
- REBOUND performance hypothesis consumed: `0 / 1`
- classifier/Entry logic change: NONE

In this continuation, the public artifact was retrieved through the connected GitHub tool, but the current analysis runtime did not successfully expose/render the ZIP members for visual inspection. Therefore no chart was falsely marked inspected and no semantic verdict was written. This is an execution-tooling blocker for this turn, not evidence about REBOUND.

## Next valid action

Render and actually inspect all 34 public SVG charts, freeze the blind review CSV, then and only then open/compare the sealed mapping. After that, attach evaluator-only Low/High and Entry anatomy for the original fixed T0 cohorts and decide whether the problem is classifier semantics, Entry timing, support insufficiency, or no supported issue.

## Safety / research boundary

Provider requests 0. No new Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective access. No EXIT / Capital / Portfolio / main merge / production work. Trading/write/promotion flags remain false by R0 protocol.