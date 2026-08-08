# Phase53.0 Adaptive Horizon Integration

Phase53.0 introduces a read-only adaptive horizon review gate for Ark Terminal.

## Purpose

Use resolved OOS prediction evidence across the supported 1 / 3 / 5 / 10 / 20 business-day horizons to identify a review candidate without enabling trading or automatic promotion.

## Fail-closed rules

- Minimum OOS samples per horizon default to 10.
- A candidate is not selected when OOS evidence is insufficient.
- When the best and second-best eligible horizons are too close, the result remains `OBSERVE`.
- The output is advisory/review-only and must not directly alter broker, Excel, RSS, live-trading, or production state.

## Safety contract

- `executionAllowed=false`
- `brokerWriteAllowed=false`
- `excelOrderWriteAllowed=false`
- `rssOrderFunctionAllowed=false`
- `liveTradingAllowed=false`
- `automaticPromotionAllowed=false`
- `productionUpdateAllowed=false`
- `humanApprovalRequired=true`

A future phase may consume this review result for further validation, but Phase53.0 itself cannot transmit or execute orders.
