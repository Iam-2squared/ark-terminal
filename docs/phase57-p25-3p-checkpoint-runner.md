# Phase57 P25.3P — checkpointed sharded runner

Status: PRECOMMITTED EXECUTION PLAN

## Goal
Execute the frozen 2026-08-19 P25 prospective evaluation without changing research semantics after the monolithic evaluator exceeded 45m, 120m, and 300m job limits.

## Frozen inputs
- immutable 2026-08-19 evidence and lineage
- exact pinned P24 canonical snapshot
- same 190-session pinned history pack
- same frozen pre-open universe record
- same Phase57 Frozen policy and Entry thresholds
- same fixed-horizon formal baseline

No current outer-OOS result may select symbol, horizon, threshold, model, universe size, shard membership, or Dynamic-N.

## Compute topology
1. Build the full all-five target union and common fair cutoff grid exactly once from the frozen session bars.
2. Partition only expensive Phase57 scorer calls into deterministic disjoint symbol batches.
3. Each batch writes an immutable checkpoint containing the frozen session identity, lineage head SHA-256, full target union identity, fair-cutoff identity, scored symbols, decision attempts, blocked decisions, and safety attestations.
4. Restarted jobs may reuse only checkpoints whose identities exactly match the frozen inputs and cutoff grid.
5. Recombine all disjoint checkpoints with `recombineP253PrefixShards` only after complete target-union coverage is proven.
6. Only the recombined full-union ledger may be used for fixed-horizon outcome materialization and the five precommitted variant metrics.
7. Persist the final all-five scorecard without ranking, filtering, winner selection, or post-hoc tuning.

## Equivalence gates
Before the 2026-08-19 run is considered admissible:
- fixture tests must show monolithic replay and sharded+recombined replay produce an identical ledger surface;
- common fair cutoff arrays must be identical across all checkpoints;
- no duplicate or missing target symbols are allowed;
- no partial checkpoint may create comparison-eligible trades;
- outcome materialization happens only after deterministic full-union recombination;
- all five variants remain in the final scorecard.

## Checkpoint policy
Checkpoint boundaries are compute-only and outcome-independent. Batch size may be chosen from runtime/operational constraints before reading current outer-OOS performance. Changing batch size must not change scorer inputs or admissible metrics.

## Safety
`executionAllowed`, `brokerWriteAllowed`, `excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`, `paperTradingAllowed`, `automaticPromotionAllowed`, `productionUpdateAllowed`, and `freshHoldoutConsumed` remain false. No MARKETSPEED II, board, Tick, Excel order write, broker write, paper/live trading, or fresh untouched holdout is used.
