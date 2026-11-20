# Phase57 All-Material Entry v1 — Feature Availability & Causality Matrix R1

Status: **PRECOMMITTED BEFORE ALL-MATERIAL PERFORMANCE MEASUREMENT**

This matrix is an append-only research contract for the all-material Entry phase. It does not change the Frozen Selector, the original State-v3 / 9-Pattern Contract, the existing 6 Signals, or any prior Entry evidence.

## Eligibility rule

A feature family is eligible only when all of the following are true at the decision checkpoint:

1. the value is available from the accepted Development substrate or an already-persisted point-in-time source,
2. `knownAt <= decisionTime`,
3. it is derived only from closed observations available at that checkpoint,
4. no future suffix, future State, evaluator-only label, EXIT outcome, PnL, MFE/MAE, future Low/High/Later High, or post-entry observation enters the feature,
5. missingness is not repaired with future backfill/interpolation,
6. the source/coverage/known-at audit is reproducible.

If a family is still CONDITIONAL when model fitting would start, it is frozen as EXCLUDED for All-Material v1 R1. It may not be upgraded after performance results are seen.

## Frozen matrix

| Family | R1 status | Allowed causal content | Required guard / reason |
|---|---|---|---|
| Same-symbol closed OHLC / price prefix | ELIGIBLE | closed Open/High/Low/Close bars through NOW; prefix path | strict closed-bar and session/lunch guard |
| Prefix returns / gap / range | ELIGIBLE | 1/3/5/10-active-minute returns where history exists; opening gap from already-known prior close; rolling ranges | prefix only; missing windows remain missing |
| Prefix realized volatility | ELIGIBLE | rolling return dispersion over 3/5/10 active minutes | train-fold transforms only; no future window |
| Bar shape | ELIGIBLE | body/range, upper/lower wick fractions on closed bars | zero-range handled deterministically |
| Prefix momentum / mean reversion geometry | ELIGIBLE | distance from prefix rolling high/low, drawdown/rebound, monotone return summaries | rolling extrema are prefix extrema, never evaluator future Low/High |
| State-v3 current/past State | ELIGIBLE | current State, prior State(s) available by NOW | original classifier immutable; overlay consumes outputs only |
| State transition / dwell / churn | ELIGIBLE | dwell active minutes, recent transition counts, recent churn | only transitions observed by NOW |
| Existing 6 Signal current/history | ELIGIBLE | current signal states, time since last signal, recent counts | existing causal signal semantics immutable |
| Time/session/lunch context | ELIGIBLE | active-minute index, morning/afternoon, lunch/session boundary flags | exact date identity is not a model feature |
| Price level | ELIGIBLE | point-in-time current/previous known prices and causal transforms | no future corporate-action repair |
| Volume / turnover | CONDITIONAL | only if the accepted replay substrate proves point-in-time closed-bar availability and adequate coverage | source + knownAt + coverage audit required before fitting |
| Market context | CONDITIONAL | only point-in-time market-wide context already persisted and known by NOW | no reconstructed/future aggregate; source audit required |
| Sector context | CONDITIONAL | only point-in-time sector context already persisted and known by NOW | sector identity may be metadata; dynamic context needs knownAt proof |
| Liquidity / tradability / tick-size | CONDITIONAL | only values known by NOW from already-persisted sources | no provider fetch; source/coverage audit required |
| Point-in-time symbol profile | CONDITIONAL | only profile fields whose effective timestamp precedes the decision | static symbol identity is not a direct memorization feature |
| Dictionary-derived descriptors | CONDITIONAL | only descriptors produced from inputs known by NOW with reproducible lineage | Dictionary output cannot conceal future/outcome-derived inputs |
| Other existing Entry-time repo feature | CONDITIONAL | must satisfy the same six eligibility conditions above | explicit source/knownAt/coverage entry required before fitting |
| Symbol ID / exact date ID as direct predictor | EXCLUDED | — | memorization / concentration risk; retained only for audit/grouping |
| Future Low / High / Later High | EXCLUDED AS FEATURE | evaluator/training-label use only where protocol explicitly says so | never decision input |
| Future State / future Signal | EXCLUDED | — | future suffix leak |
| Post-entry OHLC/volume/context | EXCLUDED | — | unavailable at decision time |
| MFE / MAE / Capture / realized PnL / EXIT result | EXCLUDED AS FEATURE | evaluator only | outcome leak |
| Fresh / OOS / Validation / Common Holdout / REPORT19 / Prospective-derived material | EXCLUDED | — | protected partitions remain sealed |
| Future interpolation / backfill / reconstructed missing observations | EXCLUDED | — | violates point-in-time availability |

## Frozen transformations for ELIGIBLE families

No result-driven feature selection is permitted in R1. All final ELIGIBLE families enter the precommitted model protocol together.

- Returns: lagged 1/3/5/10 active-minute close-to-close returns when available.
- Range: rolling 3/5/10 active-minute high-low range normalized by current price.
- Volatility: rolling standard deviation of closed-bar returns over 3/5/10 active minutes.
- Bar shape: body/range and upper/lower wick fractions for the current closed bar.
- Prefix geometry: distance from prefix 3/5/10 rolling high and rolling low; drawdown from prefix high; rebound from prefix low.
- State: current State, previous State, dwell active minutes, transition/churn counts over the last 3/5/10 active minutes.
- Signals: current six-signal vector, active minutes since the most recent occurrence of each signal, and occurrence counts over the last 3/5/10 active minutes.
- Time: active-minute index within the JPX session plus morning/afternoon and lunch-boundary indicators.
- Price: log/current-price transform and causal relative price changes already listed above.

All numeric preprocessing, imputation, scaling, and category handling must be fit on the training fold only. Missing indicators are allowed; future imputation is not.

## Conditional-family closeout rule

Before the first all-material performance measurement, each CONDITIONAL row must receive one immutable disposition:

- `ELIGIBLE` with exact repo source, point-in-time/knownAt proof and coverage summary, or
- `EXCLUDED_R1` with the reason.

There is no post-result upgrade path in All-Material v1 R1.

## Protected boundary

- Provider requests added by this work: **0**.
- Fresh/OOS/Common Holdout/REPORT19/Validation/Prospective opened by this work: **0**.
- Main / production / broker / paper/live trading paths remain untouched.
