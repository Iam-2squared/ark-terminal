# Phase40 Parts1-3: Historical Data Foundation

## Scope

This phase prepares historical OHLCV data for large-scale walk-forward backtests.

### Part1: Historical OHLCV normalization

Accepted source fields are normalized into a common contract:

- symbol
- time/date/timestamp
- open
- high
- low
- close
- adjustedClose/adjClose/adjusted_close
- volume

Rows are sorted by trading time and marked immutable before validation.

### Part2: Adjusted-price validation

The validator checks:

- positive OHLC values
- high/low consistency
- adjusted-close coverage
- adjustment-factor consistency
- large factor transitions that may indicate a split, consolidation, or other corporate action

Corporate-action candidates are warnings until verified. Invalid OHLC is blocking.

### Part3: Data-quality audit

The audit blocks backtests when it finds:

- insufficient history
- excessive missing/invalid rows
- duplicate trading dates
- non-increasing dates
- invalid OHLC relationships

The audit also records whether survivorship bias and corporate actions were explicitly controlled.

## Output contract

Only audited datasets produce backtest-ready candles. Adjusted OHLC values use the same factor as adjusted close. The existing walk-forward engine can consume the generated candle contract.

## Safety

This phase is historical-data-only.

- no broker writes
- no live trading
- no order creation, transmission, cancellation, or modification
- no Excel order writes
- no ARK_ORDER B9 changes
- no model promotion or Production update
