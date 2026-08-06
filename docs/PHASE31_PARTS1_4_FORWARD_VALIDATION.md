# Phase31 Parts1-4 — Forward Validation Foundation

## Goal

Create a strict long-running Champion/Candidate forward-validation contract on unseen Paper-only data.

## Parts

1. Build immutable paired comparison runs.
2. Enforce same symbol, session, horizon, actual return, cost contract, and holding-period contract.
3. Block non-Out-of-sample, non-Paper-only, future-leak, and data-contract mismatches.
4. Produce basic paired performance comparison for later statistical review.

## Metrics

- paired sample count
- directional sample count
- accuracy
- average and total net return
- profit factor
- maximum drawdown
- Candidate minus Champion deltas

## Result states

- `READY_FOR_STATISTICAL_REVIEW`
- `CONTINUE_FORWARD_TEST`
- `BLOCKED`

No state promotes a Candidate automatically.

## Safety invariants

- `automaticPromotionAllowed: false`
- `productionUpdateAllowed: false`
- `brokerWriteAllowed: false`
- `liveTradingAllowed: false`
- no order creation, transmission, cancellation, or modification
- human approval remains mandatory
