# Phase57 P25.3O — Sharded immutable evaluation recovery

Status: PRECOMMITTED IMPLEMENTATION DESIGN

## Goal
Recover the frozen 2026-08-19 P25 prospective evaluation after the monolithic evaluator exceeded both the 45-minute and 120-minute GitHub Actions job limits. Evaluation semantics must not change; this part is compute sharding only.

## Frozen inputs
- immutable 2026-08-19 P25 evidence and lineage
- exact pinned P24 canonical snapshot
- same P25 pinned history pack
- same frozen pre-open universe record
- same fixed-horizon formal baseline
- same Entry thresholds and Phase57 Frozen policy

Current outer-OOS results may not select symbol, horizon, threshold, model, or Dynamic-N.

## Five independent shards
Run one shard for each precommitted variant: `FIXED_5`, `OLD_FIXED_30`, `DYNAMIC_30`, `DYNAMIC_40`, `DYNAMIC_50`.

Each shard scores only symbols belonging to its selected variant, but the fair cutoff grid MUST still be computed from the full all-five target union. This prevents smaller shards from gaining extra decision times and preserves equivalence with the monolithic evaluator.

The frozen universe record remains unchanged and still contains all five variants. Dynamic30/40/50 remain nested exactly as frozen before the session.

## Equivalence invariant
For selected variant V:
- full-union bar validation is unchanged;
- common fair cutoffs are computed from the full all-five target union;
- only scorer calls for symbols in V are executed;
- the scorer receives the same history, prefix bars, frozen policy, symbol, session date, and feature cutoff as the monolithic evaluator;
- only V metrics from that shard are admissible;
- non-selected variant metrics from a shard are ignored because those symbol sets were not fully scored.

A combiner may assemble the five precommitted variant rows into one presentation scorecard, but may not rank, filter, tune, or choose Dynamic-N from current outer OOS.

## Required output
Persist one immutable artifact per variant with selected variant, lineage SHA-256, P24 canonical identity, expected session denominator, ready/blocked sessions, valid frozen entries/trading session, days to 400 valid entries, Hit/Win, after-cost Net, PF, MaxDD, Coverage, symbol concentration, sector concentration, same-time correlation, and session/regime stability.

## Safety
`executionAllowed`, `brokerWriteAllowed`, `excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`, `paperTradingAllowed`, `automaticPromotionAllowed`, `productionUpdateAllowed`, and `freshHoldoutConsumed` remain false. No MARKETSPEED II, board, Tick, Excel order surface, broker write, paper/live trading, or fresh untouched holdout is used.
