# Phase57 DROP/PULLBACK Lower-Wick Gate v1 — Precommitted Protocol

Status: `LOCKED_BEFORE_MEASUREMENT`. Base HEAD: `281f215fa3d86c9ef2dffebce8fd211425b6817c`.

## Scope

This is a Development-only Entry Timing experiment on the same 2,155 Opportunities. The frozen State v3 9-Pattern classifier, Frozen Selector, T0 BUY rule for `RISE / SHARP_RISE / REBOUND`, all six existing signal definitions, and every existing Evidence namespace stay unchanged.

Only opportunities whose T0 State v3 state is `DROP` or `PULLBACK` are changed. For those two initial states, a signal may create a BUY intent only when the existing `LOWER_WICK` signal is true. The existing five-active-minute State-v3 recheck remains intact and still buys on transition to `RISE / SHARP_RISE / REBOUND`. Signal/State same-timestamp ties retain `SIGNAL_TRIGGER` priority. There is no fixed-time fallback.

All other T0 states use the exact State v3 Entry v1 policy.

## Why this single hypothesis

Evaluator-only anatomy of the frozen State v3 result showed that `DROP_STOP` is rare around the eventual Low and `REBOUND` becomes common only after the Low. Family-isolated diagnostics on existing State v3 signal-triggered DROP/PULLBACK rows identified `LOWER_WICK` as the only existing signal family with a favorable paired direction versus Immediate on price, EntryPosition, and Low→Entry distance. This protocol therefore tests one minimal aggregation change; it does not tune or redefine any signal threshold.

## Primary evaluation

`EntryPosition = (Entry - Low) / (LaterHigh - Low)` remains evaluator-only. Report `<=10%`, `<=25%` (Primary), and `<=50%` rates, paired mean EntryPosition, paired Low→Entry distance, Fill, +1/+2/+3/+5 Capture, and 30m/60m MFE/MAE.

The candidate is a clear improvement only if, on the T0 DROP/PULLBACK cohort versus frozen State v3: `<=25%` rate improves by at least +2.0pp; paired mean EntryPosition and Low→Entry both improve (<0 deltas); Fill rate, +3 Capture and +5 Capture each worsen by no more than 2.0pp; and causality/leakage audit passes. All gates are conjunctive.

## Causality

Causal minute-census rows and committed frozen State-v3 checkpoints are read first. All 2,155 intents are frozen and SHA-256 hashed before opportunity Oracle anatomy, raw evaluator paths, fill labels, MFE/MAE, outcomes, or other future fields are opened. Future data is evaluation-only and cannot alter an intent.

## Low-centered diagnostic

After intents are frozen, report evaluator-only State/Signal anatomy around the regular-bar Oracle Low at `Low−10/−5/−3/−1/0/+1/+3/+5/+10` active minutes where observable. This diagnostic may explain the result but may not modify this v1 policy.

## Protection / STOP

Provider requests = 0. Holdout/Fresh/OOS/Prospective remain unopened. Safety9 stays false. No Volume, Dictionary, new Signal, State vocabulary/contract change, EXIT, Capital, main merge, paper/live trading, or automatic promotion is allowed. The trial is replayed twice and byte-compared. If the gate fails, preserve the result as negative Evidence and STOP this hypothesis; a later run may precommit one different minimal hypothesis.
