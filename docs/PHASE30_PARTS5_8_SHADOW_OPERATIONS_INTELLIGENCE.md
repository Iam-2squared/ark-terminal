# Phase30 Parts5-8: Shadow Operations Intelligence

## Scope

This phase completes Shadow Trading operations without enabling any broker or Excel order path.

### Part5: Market-regime performance

Groups evaluated shadow predictions by `marketRegime` and calculates:

- sample count
- wins and losses
- win rate
- total net PnL
- average net return
- profit factor

### Part6: Operations dashboard aggregate

Combines daily logs and evaluations into a read-only dashboard payload containing:

- total predictions
- evaluated and pending counts
- NO_TRADE count
- cumulative net PnL
- regime performance
- latest 30 daily logs

### Part7: Weekly and monthly reports

Creates weekly and monthly summaries with:

- prediction and evaluation counts
- pending count
- win rate
- total and average daily net PnL
- number of operating days

### Part8: Fail-closed operational safety

Shadow operations are halted when any blocker is detected:

- Kill Switch active
- data quality failure
- Python Bridge disconnected
- MARKETSPEED II RSS disconnected
- excessive pending outcomes
- daily loss limit breach
- stale data
- audit checksum mismatch

Low sample size is a warning, not a live-trading permission.

## Safety contract

All outputs remain `SHADOW_ONLY`.

- `brokerWriteAllowed: false`
- `liveTradingAllowed: false`
- `orderCreationAllowed: false`
- `orderTransmissionAllowed: false`
- `orderCancellationAllowed: false`
- `orderModificationAllowed: false`
- `excelOrderWriteAllowed: false`
- `orderTriggerWriteAllowed: false`
- `executionAllowed: false`

The module never calls `RssStockOrder`, never writes `ARK_ORDER!B9`, and never creates a live order candidate.
