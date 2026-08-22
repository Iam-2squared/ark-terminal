# Phase57 P25.3O — Sharded immutable evaluation recovery

Status: PRECOMMITTED IMPLEMENTATION DESIGN

## Goal

Recover the frozen 2026-08-19 P25 prospective evaluation after the monolithic evaluator exceeded both the 45-minute and 120-minute GitHub Actions job limits.

The evaluation semantics must not change. This part is compute sharding only.

## Frozen inputs

- immutable 2026-08-19 P25 evidence and lineage
- exact pinned P24 canonical snapshot
- the same P25 pinned history pack
- the same frozen pre-open universe record
- the same fixed-horizon formal baseline
- the same Entry thresholds and Phase57 Frozen policy

No current outer-OOS result may select a symbol, horizon, threshold, model, or Dynamic-N.

## Five independent shards

Run one shard for each precommitted variant:

1. `FIXED_5`
2. `OLD_FIXED_30`
3. `DYNAMIC_30`
4. `DYNAMIC_40`
5. `DYNAMIC_50`

Each shard scores only symbols belonging to its selected variant, but **the fair cutoff grid must still be computed from the full all-five target union**. This is required so sharding cannot create extra decision times for a smaller universe and cannot change any selected-variant decision relative to the monolithic evaluator.

The frozen universe record itself remains unchanged and still contains all five variants. Dynamic30/40/50 remain nested as frozen before the session.

## Equivalence invariant

For a selected variant V:

- full-union bar validation is unchanged;
- common fair cutoffs are computed from the full all-five target union;
- only scorer calls for symbols in V are executed in the shard;
- the Phase57 scorer receives the exact same historical sessions, prefix bars, frozen policy, symbol, session date, and feature cutoff it would receive in the monolithic evaluator;
- only V's metrics from that shard are admissible for the final comparison;
- metrics for non-selected variants from a shard are ignored because their symbol sets were intentionally not fully scored.

A later combiner may assemble the five selected-variant metric blocks into one scorecard, but it must not rank, filter, tune, or select Dynamic-N from the current outer OOS.

## Required output

Persist one immutable artifact per variant with:

- selected variant
- evidence lineage head SHA-256
- P24 canonical identity
- expected session denominator
- ready/blocked session counts
- valid frozen entries / trading session
- days to 400 valid entries
- Hit/Win
- after-cost Net
- PF
- MaxDD
- Coverage
- symbol concentration
- sector concentration
- same-time correlation
- session/regime stability

Then combine only the five precommitted variant rows for presentation.

## Safety

The following remain false:

- `executionAllowed`
- `brokerWriteAllowed`
- `excelOrderWriteAllowed`
- `rssOrderFunctionAllowed`
- `liveTradingAllowed`
- `paperTradingAllowed`
- `automaticPromotionAllowed`
- `productionUpdateAllowed`
- `freshHoldoutConsumed`

No MARKETSPEED II, board, Tick, Excel order surface, broker write, paper/live trading, or fresh untouched holdout is used in this recovery.
