# Phase30 Parts1-4: Shadow Forward Operations

## Scope

This phase adds a production-like shadow workflow without any broker-side effects.

- Part1: frozen shadow prediction records
- Part2: automatic future-outcome evaluation
- Part3: cost-aware virtual PnL
- Part4: immutable daily logs and audit checksum

## Safety contract

The workflow is advisory and shadow-only.

- brokerWriteAllowed: false
- liveTradingAllowed: false
- orderCreationAllowed: false
- orderTransmissionAllowed: false
- orderCancellationAllowed: false
- orderModificationAllowed: false
- excelOrderWriteAllowed: false
- orderTriggerWriteAllowed: false

The engine never calls `RssStockOrder`, never writes `ARK_ORDER!B9`, and never creates a live order.

## Inputs

Each shadow candidate may contain:

- symbol
- BUY / SELL / HOLD / NO_TRADE
- entry price
- stop-loss and take-profit reference levels
- confidence
- expected holding days
- market regime
- model and feature snapshot identifiers

## Outputs

The orchestrator returns:

- frozen predictions
- settled evaluations when an outcome exists
- gross and net returns
- virtual gross and net PnL
- commission, slippage, and delay costs
- daily win/loss, pending, and no-trade counts
- immutable-input marker and audit checksum

This phase does not schedule itself yet. Scheduling, regime reports, dashboards, and weekly/monthly summaries belong to Phase30 Parts5-8.
