# Phase57 Entry UNKNOWN Causal-Coverage Diagnostic v1 — protocol

## Status and single question

Diagnostic-only Development study. The single question is:

> Why are 1,144 / 2,155 Entry-v1 decision states UNKNOWN, and how much of that
> cohort becomes causally DEFINED by T+1/T+2/T+3/T+5/T+10 active minutes?

This study does **not** create Entry v2 and does not change a policy, threshold,
State-v2 definition, Frozen Selector, or any of the six existing Signals.

## Frozen population and sources

- Population: the same 2,155 Opportunities used by State-Conditioned Signal Entry v1.
- Primary cohort: exactly the 1,144 Opportunities whose frozen causal estimator
  returns UNKNOWN at delay 0.
- Causal source: committed `phase57-entry-timing-signal-census-v1/measurement/minute-census` only.
- Entry-v1 causal estimator: unchanged `sign(returnPct[5])`; `None => UNKNOWN`.
- Entry-v1 committed paired records may be opened only after cohort membership and
  the complete causal trajectory table are fixed.
- No provider request and no new market-data acquisition is authorized.
- Common Holdout / Fresh / OOS / Prospective remain unopened.

## Causal measurements

For each initial-UNKNOWN Opportunity:

1. classify the causal reason for `returnPct[5] == None` without future data;
2. record selection minute and half-session age;
3. preserve causal data-availability flags and missingness;
4. evaluate the *same frozen estimator* at exact T+1, T+2, T+3, T+5, T+10 active-minute checkpoints;
5. report exact-offset State, first causal DEFINED delay/State, cumulative DEFINED-by-T+k, and State-transition signatures.

The reason taxonomy is fixed before outcome inspection:

- `INSUFFICIENT_PHASE_HISTORY_FOR_RETURN5`
- `NO_NEW_CLOSED_BAR_AT_ASOF`
- `STRICT_CONTIGUOUS_WINDOW_UNAVAILABLE`

Missing checkpoints are `NO_CHECKPOINT`; they are never imputed or converted to a State.

## Evaluator-only paired anatomy

Only after all causal grouping is complete, the frozen initial-UNKNOWN cohort is
joined to the already-committed Immediate vs Entry-v1 paired record. Report:

- Immediate fill vs WAIT-arm fill;
- intent reason distribution;
- pair status;
- paired price, delay, Low-distance, remaining-upside, EntryPosition,
  Range-Retention, 30m/60m MFE and MAE deltas.

These fields are descriptive evaluator-only anatomy. They must not select a new
rule, threshold, horizon, Signal family, fallback duration, or candidate policy.

## Integrity gates

- 2,155 decision rows exactly.
- 1,144 initial UNKNOWN exactly.
- all minute-census hashes verify against the saved signal-census manifest.
- Entry-v1 input artifacts verify against its saved manifest.
- closed-bar violations = 0.
- outcome/oracle/State-v2 reference inputs are not used to define the cohort or causal trajectories.
- deterministic diagnostic output under identical committed inputs.
- Safety9 remain all false.
- provider requests = 0; protected data opened = 0.

## STOP boundary

When causal coverage, Dynamic State transitions, evaluator-only paired anatomy,
dedicated tests, deterministic evidence artifact, and regression/CI receipts are
available, STOP for human review.

Do not automatically start Entry v2, modify waiting logic, change thresholds,
start EXIT/Capital, open Fresh/OOS/Prospective data, merge to main, paper trade,
or live trade.
