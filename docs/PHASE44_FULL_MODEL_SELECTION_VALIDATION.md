# Phase44 — Model Selection & Validation

Phase44 adds a review-only model-selection layer above the Phase43 registry.

## Scope

- deterministic candidate records
- walk-forward validation metadata
- overfitting and insufficient-sample gates
- market-regime performance storage
- weighted candidate ranking
- Champion/Candidate comparison
- feature-set and dataset lineage checks
- human-review dashboard payload

## Fail-closed rules

A candidate is blocked when any of the following occurs:

- insufficient walk-forward folds
- unstable walk-forward results
- insufficient sample size
- feature-set mismatch with Champion
- dataset lineage mismatch

Extreme win rate or profit factor is not accepted silently; it is surfaced as a review warning.

## Safety

Phase44 is strictly review-only.

- no broker writes
- no live trading
- no order create/transmit/cancel/modify
- no Excel order writes or trigger changes
- no automatic Candidate promotion
- no Production updates
- no automatic rollback
- human approval required

The output can recommend human review, but it cannot change Production state.
