# Phase29 Parts1-3: Live Portfolio Intelligence

## Goal

Combine the fail-closed MARKETSPEED II RSS account snapshot with portfolio risk and AI context without creating or transmitting an order.

## Part1: Live portfolio normalization

- accepts only `readOnly: true`
- requires `connection.connected: true`
- requires `synchronized: true`
- normalizes positions, account metrics, sectors and AI context
- rejects disconnected or writable snapshots

## Part2: Portfolio risk analysis

- single-position concentration
- sector concentration
- loss-threshold warnings
- invalid position data
- returns `HEALTHY` or `WARNING`

## Part3: Human-review advice

Possible advisory states:

- `HOLD_REVIEW`
- `REDUCE_REVIEW`
- `HOLD_OR_ADD_REVIEW`
- `REBALANCE_REVIEW`

Every item is non-executable. No order candidate is created.

## Safety invariants

- `brokerWriteAllowed: false`
- `liveTradingAllowed: false`
- `orderCreationAllowed: false`
- `orderCancellationAllowed: false`
- `orderModificationAllowed: false`
- `automaticExecutionAllowed: false`
- `humanApprovalRequired: true`

This phase does not modify `ARK_ORDER`, does not change B9, and does not call `RssStockOrder`.
