# Phase57 State-Conditioned Signal Entry v1 — locked protocol

## Scope

- Population: the frozen 2,155 LONG Opportunities.
- Start HEAD: `c7dfb8e18747e8a263e85a7e185abb964491c87e` (PR #587 latest HEAD at study start).
- Research scope: Development / historical closed reconstruction only.
- Frozen and unchanged: Selector, State v2 design/reference, six signal detectors, signal thresholds, Low/High evaluator evidence.
- Not opened or changed: Protected Holdout, Fresh, OOS, Prospective, EXIT, Allocation, Portfolio, production, paper/live trading.
- Provider requests: 0.

The machine-readable pre-result lock is `POLICY_LOCK.json` (SHA-256
`794a1ff0c1dd43a145b6cc0c990572c5f343042db1a86523d7d457c0fcdfa3d3`).
It was written before Entry v1 outcome evaluation.

## Causal state estimate

At checkpoint `t`, the estimator reads only the saved causal signal-census row
whose latest source bar starts strictly before `t`.  It uses the sign of the
already-existing `context.returnPct["5"]` primitive:

| Value | Coarse state |
|---:|---|
| `> 0` | UP |
| `< 0` | DOWN |
| `== 0` | NEUTRAL |
| missing | UNKNOWN |

There is no fitted model, learned cutoff, threshold sweep, Future State input,
or Oracle input.  Frozen State v2 NOW is joined after all decisions and is used
only for diagnostics.

## Fixed Entry policy

| Initial state | Fixed action | Existing source arm | Allowed signal families | Fallback |
|---|---|---:|---|---:|
| UP | BUY NOW | A | none | 0m |
| DOWN | wait for recovery | D | HIGHER_LOW, LOWER_WICK, RECLAIM | 10 active minutes |
| NEUTRAL | wait for upward transition | C | BREAKOUT, COMPRESSION_EXPANSION | 10 active minutes |
| UNKNOWN | wait; never treat as bullish | E | all six frozen signals | 10 active minutes |

Fallback was precommitted.  It was not added or changed after seeing results.
The six existing detectors and their thresholds are reused byte-for-byte.

## Baselines and evaluators

| Label | Meaning |
|---|---|
| A — Immediate | Existing arm A for all 2,155 Opportunities |
| B — Signal-only | Existing all-six arm E for all 2,155 Opportunities |
| C — Entry v1 | A/D/C/E selected only by the causal initial coarse state |

Oracle Low/Later High, selector outcome, and exact 30m/60m labels are parsed
only after all 2,155 state and arm decisions are immutable.  They are evaluator
inputs, never decision inputs.  Signal absence, missing state, NO ENTRY, and
session-boundary/retry outcomes remain in the population.

## Safety

All nine flags are fixed `false`: `executionAllowed`, `brokerWriteAllowed`,
`excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`,
`paperTradingAllowed`, `automaticPromotionAllowed`, `productionUpdateAllowed`,
and `transmitted`.

