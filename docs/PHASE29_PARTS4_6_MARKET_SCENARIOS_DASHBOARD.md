# Phase29 Parts4-6: Market Overlay, Scenarios, Dashboard

## Part4: Market Regime Overlay

Combines the read-only live portfolio with market regime, volatility, breadth and index trend context.

Supported regimes:

- BULL
- BEAR
- RANGE
- HIGH_VOLATILITY
- LOW_VOLATILITY

Missing or unknown market context is treated as review-required. It never enables execution.

## Part5: Portfolio Scenarios

Builds three human-review-only scenarios:

- BASE
- DEFENSIVE
- RISK_ON_REVIEW

Scenarios are comparative estimates, not orders. Every scenario has:

- `executable: false`
- `orderCandidateCreated: false`
- `humanReviewRequired: true`

## Part6: Read-only Dashboard Aggregate

`buildLivePortfolioDashboard()` combines Phase29 Parts1-6:

1. broker snapshot normalization
2. concentration and loss-risk analysis
3. position advice
4. market overlay
5. scenario comparison
6. dashboard summary

## Safety Contract

The complete suite preserves:

- `brokerWriteAllowed: false`
- `liveTradingAllowed: false`
- `orderCreationAllowed: false`
- `orderCancellationAllowed: false`
- `orderModificationAllowed: false`
- `automaticExecutionAllowed: false`
- `humanApprovalRequired: true`

It does not write to Excel, change `ARK_ORDER!B9`, call `RssStockOrder`, or create a live order candidate.
