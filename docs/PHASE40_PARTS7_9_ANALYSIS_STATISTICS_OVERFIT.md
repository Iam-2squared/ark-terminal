# Phase40 Parts7-9 — Backtest Analysis, Statistics, and Overfit Review

## Scope

This phase consumes historical backtest results only. It does not connect to brokers, Excel order cells, live orders, cancellations, modifications, Candidate promotion, or Production updates.

## Part7 — Backtest Dashboard

The dashboard summarizes:

- overall sample count, win rate, average/median/total net return
- profit factor, maximum drawdown, approximate Sharpe
- symbol, sector, market regime, horizon, and partition breakdowns

## Part8 — Champion / Candidate Review

The comparison reports:

- Champion metrics
- Candidate metrics
- deltas for win rate, return, profit factor, and drawdown
- blockers when either side has no results

The output never permits automatic promotion.

## Part9 — Statistical and Overfit Review

The statistical layer includes:

- deterministic bootstrap with fixed seed
- 95% interval for Candidate minus Champion average return
- probability that Candidate is better in the resamples
- training / validation / test decay checks
- validation-to-test sign-flip warning
- test drawdown expansion warning
- sample-size warning

## Safety Contract

All analysis outputs keep the following values fixed:

- `brokerWriteAllowed: false`
- `liveTradingAllowed: false`
- `orderCreationAllowed: false`
- `orderTransmissionAllowed: false`
- `orderCancellationAllowed: false`
- `orderModificationAllowed: false`
- `excelOrderWriteAllowed: false`
- `orderTriggerWriteAllowed: false`
- `automaticPromotionAllowed: false`
- `productionUpdateAllowed: false`
- `humanReviewRequired: true`

The highest state is `READY_FOR_HUMAN_REVIEW`.
