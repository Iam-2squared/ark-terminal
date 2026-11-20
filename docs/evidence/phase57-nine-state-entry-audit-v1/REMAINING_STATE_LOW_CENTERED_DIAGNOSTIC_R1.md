# Phase57 9-State Entry — Remaining-State Low-Centered Diagnostic R1

2026-09-24 JST / Development-only / diagnostic-only precommit.

## Purpose

`PROTOCOL_R0.md` remains controlling. The high-support RISE / DROP / PULLBACK causal Low-centered attribution has already been run and their one-shot `CONFIRMED_BUY_PERSISTENCE_V1` candidates are separately precommitted/measured. This diagnostic covers the remaining nonzero-T0 States whose performance-hypothesis slots are still unused or whose support is too small for a justified performance trial: `SHARP_RISE`, `RANGE`, `SHARP_DROP`, `DROP_STOP`.

This is attribution only. It changes no Entry decision and consumes no performance-hypothesis slot.

## Frozen diagnostic contract

For the original fixed T0 cohorts only:

- SHARP_RISE: 7
- RANGE: 57
- SHARP_DROP: 26
- DROP_STOP: 5

Build every State-v3 / frozen-six-signal checkpoint witness using only causally available previous-session + current closed-price prefix before opening the already-exposed Development Oracle Low. Then align the frozen witnesses to evaluator-only Low for attribution.

Report for each State:

1. original cohort N, ONE_MINUTE Fill, EntryPosition mean/median and <=10/15/25/50%;
2. comparable filled cases entering before vs at/after evaluator Low;
3. BUY-state and existing frozen-signal prevalence at Low-10/-5/-3/-1/0/+1/+3/+5/+10 active minutes;
4. delay from Low to first existing BUY State, first frozen Signal, and first either;
5. missing denominators and Oracle-Low-within-decision-window N.

## Causal / integrity gates

The run is valid only if:

- the causal witness object is fully built before Oracle Low is opened;
- all classifier source bars satisfy `maxSourceBarStart < checkpoint minute`;
- `stateFutureViolations == 0`;
- `oracleLowHighDecisionUse == 0` and `futureOutcomeDecisionUse == 0`;
- provider requests and protected-data opens are zero;
- the accepted ONE_MINUTE full-population baseline is exactly `1764 / 2155` fills, `81.85614849187935%` Fill, mean EntryPosition `0.6748679920277816`;
- original State populations match 7 / 57 / 26 / 5 exactly.

## Interpretation / stop rule

No State gets a new performance candidate merely because the evaluator Low reveals a favorable delay. A candidate is permitted only if the causal witness supports a simple rule using the unchanged 9-Pattern classifier and/or existing six frozen Signals, and the cohort has enough support to avoid a tiny-sample claim. No threshold sweep, new Signal, Volume, Dictionary, learned model, State-definition change, or result-driven persistence tuning is allowed.

`SHARP_RISE` and `DROP_STOP` are expected to remain INSUFFICIENT unless the diagnostic reveals a clear software/contract defect; do not manufacture a trial from 7 or 5 T0 observations. `SHARP_DROP` (26) remains limited support and requires especially conservative interpretation. `RANGE` (57) may justify one bounded hypothesis only if the causal mechanism is clear before any candidate replay.

## Safety

Provider requests 0. No Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective access. No EXIT / Capital / Portfolio work. Frozen Selector, 9-Pattern Contract, six Signals and immutable baselines unchanged. All trading/write/promotion flags remain false.
