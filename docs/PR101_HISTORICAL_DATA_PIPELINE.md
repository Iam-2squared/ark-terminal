# PR101 — Historical Data Pipeline

## Goal

Build the first real-data training foundation for Ark Terminal without enabling any broker or order write path.

The implementation extends the existing Phase41 Data Lake and daily-ingestion contracts instead of creating a separate storage system.

## Initial universe

- approximately 50 liquid Japanese equities
- Nikkei 225
- TOPIX
- NASDAQ Composite
- Philadelphia Semiconductor Index (SOX)
- VIX
- USD/JPY

The universe must be configurable and versioned. Expansion order is 50 → 300 → 1000 → all TSE listings after data-quality and runtime evidence is acceptable.

## Required pipeline

1. Fetch historical OHLCV and index/macro series from an explicitly configured provider.
2. Normalize provider rows into the existing Phase41 `OHLCV`, `INDEX`, or `MACRO` contracts.
3. Apply split/adjusted-price, missing-value, duplicate, date-order, non-finite-value, and OHLC consistency checks.
4. Fail closed when required data quality is not satisfied.
5. Persist only validated records through the existing immutable Data Lake manifest/checkpoint flow.
6. Produce a machine-readable daily-run report and non-zero exit status when blockers exist.
7. Support deterministic CLI execution and scheduled daily updates.

## Data-quality gates

A run is blocked when any of the following is true:

- symbol or session date is missing
- duplicate keys remain after deterministic merge
- dates are not monotonic within a series
- OHLC values are non-finite or non-positive
- `high < max(open, close, low)`
- `low > min(open, close, high)`
- volume is negative
- adjusted-price treatment is ambiguous
- required benchmark coverage is missing
- manifest checksum validation fails

Warnings, rather than silent repair, are required for suspicious gaps, zero volume, stale rows, and extreme daily returns.

## Safety invariants

This PR is data-only and READ ONLY with respect to the live account.

- broker writes: disabled
- live orders: disabled
- order create/transmit/cancel/modify: disabled
- Excel order writes: disabled
- `ARK_ORDER!B9` changes: disabled
- MARKETSPEED II RSS order functions: disabled
- automatic Candidate promotion: disabled
- automatic Production update: disabled
- automatic rollback: disabled
- human approval: required

No implementation in PR101 may import or invoke the RSS order bridge.

## Delivery parts

### Part1 — Repository and execution-path audit

- confirm Phase41 Data Lake contracts
- confirm Phase28 RSS bridge remains isolated and fail-closed
- identify the provider boundary, CLI conventions, and tests

### Part2 — Universe and provider contracts

- versioned 50-equity universe plus benchmark series
- provider interface and normalized response contract
- provider timeout/retry/rate-limit behavior

### Part3 — Historical fetch and normalization

- bounded date-range fetch
- OHLCV/index/macro normalization
- deterministic run metadata and source lineage

### Part4 — Quality inspection and persistence

- quality gate report
- fail-closed persistence into Phase41
- rejected-row and blocker artifacts

### Part5 — Daily CLI and CI coverage

- idempotent daily update command
- fixture-based tests with no network dependency
- safety regression tests proving zero broker/Excel/order writes

## Evidence before any execution expansion

PR101 does not authorize semi-automatic or automatic trading. The next stages are training-dataset construction, real model training, walk-forward evaluation, paper trading, and shadow operation. Stable profitability cannot be guaranteed by a calendar target; activation decisions must be based on out-of-sample evidence, costs, drawdown, sample size, regime stability, and explicit human approval.
