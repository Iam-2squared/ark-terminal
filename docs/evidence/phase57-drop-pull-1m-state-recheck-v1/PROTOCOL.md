# Phase57 DROP/PULLBACK 1m State Recheck v1 — Precommitted Protocol

## Scope

This is a policy-layer experiment only. The Frozen LONG Selector, State v3 9-Pattern classifier/contract, T0 BUY states (`RISE`, `SHARP_RISE`, `REBOUND`), all six existing signal definitions, historical Evidence, and all protected datasets remain unchanged.

Target cohort: opportunities whose frozen T0 State v3 classification is `DROP` or `PULLBACK`.

Non-target opportunities use the exact accepted State v3 Entry v1 policy.

## Prior result motivating this one fixed hypothesis

The precommitted `LOWER_WICK`-only policy gate completed with `NO_PROMOTION`: Fill/Capture remained inside the bounded-loss gate, but the primary EntryPosition <=25% rate did not improve and paired Low-to-Entry slightly worsened. The evaluator-only low-centered anatomy showed that State v3 still classifies most target opportunities as `DROP` at the ordered-low boundary, while BUY-state prevalence increases in the following active minutes. This diagnosis is used only to choose the next policy hypothesis; oracle information is prohibited from the decision path.

## Frozen hypothesis before measurement

For initial `DROP` / `PULLBACK` only:

1. Keep the original OR across the six frozen signal families exactly unchanged.
2. Recompute the unchanged State v3 classifier every **1 active minute** instead of every 5 active minutes.
3. The first causal occurrence of either an existing frozen signal or a State v3 BUY state (`RISE`, `SHARP_RISE`, `REBOUND`) creates BUY intent; deterministic same-minute priority remains signal first while preserving all trigger sources.
4. No fixed-time fallback. No new signal, feature, threshold, vocabulary, volume layer, or model.
5. T0 BUY-state behavior remains exactly unchanged.

The hypothesis is that the 5-minute state checkpoint cadence, rather than the 9-Pattern classifier itself, is delaying a material subset of DROP/PULLBACK reversals. A 1-minute causal recheck may catch the earliest BUY-state transition while preserving the Fill/Capture support of the original six-signal OR path.

## Primary evaluation

Evaluator-only EntryPosition:

`EntryPosition = (Entry - ordered Low) / (strictly later High - ordered Low)`

Report <=10%, <=25% (primary), and <=50% rates, plus mean/median EntryPosition and paired Low-to-Entry distance.

The candidate must be compared on the same 2,155 opportunities against Immediate, Entry v1, and State v3 baseline. The DROP/PULLBACK target cohort must also be evaluated separately.

## Precommitted success gate vs State v3 target cohort

- EntryPosition <=25% rate: at least **+2.0 pp**
- paired EntryPosition mean delta: **< 0**
- paired Low-to-Entry distance mean delta: **< 0**
- Fill-rate delta: **>= -2.0 pp**
- +3% Capture delta: **>= -2.0 pp**
- +5% Capture delta: **>= -2.0 pp**
- causality/leakage audit: **PASS required**

Failure of any gate means `NO_PROMOTION`; no within-run threshold tuning is allowed.

## Causality

For each 1-minute State v3 decision at NOW, only previous-session data plus current-session bars with bar start `< NOW` may enter the classifier. Existing signals remain closed-bar causal. Future ordered Low/High, MFE/MAE, outcomes, future pivots, and protected datasets are evaluator-only and cannot enter intent generation.

## Protection / Safety

- Provider requests: 0
- Holdout / Fresh / OOS / Prospective: unopened
- State v3 contract: unchanged
- signal definitions: unchanged
- Volume / Dictionary / new signals: prohibited
- EXIT / Capital / Portfolio / main merge: prohibited
- Safety9: all false

Evidence is append-only. A clear gate PASS stops further automatic tuning; a NO_PROMOTION result permits only one new evidence-based DROP/PULLBACK hypothesis to be precommitted for the next iteration.
