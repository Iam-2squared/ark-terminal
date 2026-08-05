# Phase19 Part4 — Broker Write Lock

## Goal

Keep the connected real brokerage account strictly read-only while Ark Terminal improves AI accuracy and validates Paper Trading profitability.

No live order submission or cancellation is permitted in this part.

## Implemented Safety Boundary

All broker write requests now pass through a fail-closed lock at the Execution Bridge boundary.

Permitted write modes:

- `paper`
- `dry-run`

Blocked modes and states:

- `live`
- unknown or missing broker mode
- any adapter reporting `liveTradingEnabled=true`
- live order cancellation
- live order submission even when `allowLiveTrading=true`
- live order submission even when a human approval provider returns approval

## Release State

```text
status=LOCKED
liveTradingEnabled=false
allowLiveOrderSubmission=false
allowLiveOrderCancellation=false
releaseStage=NOT_APPROVED
releaseRequiresCodeChange=true
```

The lock cannot be disabled through a runtime flag, environment variable, UI action, approval token, or connected broker setting.

## Requirements Before Any Future Release

The repository records the following prerequisites, but satisfying them does not automatically unlock trading:

1. Stable Paper Trading results over a meaningful forward-test period
2. Validated accuracy, drawdown, transaction-cost, and risk metrics
3. Semi-automatic mode with explicit human approval
4. Explicit owner approval
5. A separate reviewed code change and regression test update

## Regression Coverage

Tests verify that:

- a live submit request never reaches the adapter
- a live cancellation request never reaches the adapter
- unknown broker modes fail closed
- an adapter that claims Paper mode but reports live execution enabled is blocked
- existing Dry Run execution remains available

## Scope Boundary

This part does not enable semi-automatic or automatic real trading. The connected real account remains read-only for account, balance, position, order-history, execution-history, and reconciliation reads only.
