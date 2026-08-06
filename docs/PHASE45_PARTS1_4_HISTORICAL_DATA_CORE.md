# Phase45 Parts1-4 — Historical Data Core

## Goal

Create the first real-data path for AI training without enabling any broker or order capability.

## Part1 — Versioned initial universe

- 1 to 50 Tokyo Stock Exchange equity symbols
- symbols must use the `7203.T` style
- duplicate symbols are blocked
- benchmark set is fixed to Nikkei 225, TOPIX, NASDAQ, SOX, VIX and USDJPY
- universe output is versioned and immutable

## Part2 — Provider-neutral normalization

`normalizeHistoricalRecord` accepts common JSON/CSV-shaped fields and converts them into the existing Phase41 contracts:

- `OHLCV`
- `INDEX`
- `MACRO`

The normalized record contains symbol, session date, update time, source, currency and the required numeric fields.

## Part3 — Historical ingestion batch contract

`buildHistoricalIngestionBatch` creates a provider-labelled batch. A batch is emitted as `READY_FOR_PHASE41` only when all blocking quality checks pass. Invalid data produces an empty, fail-closed `BLOCKED` batch.

## Part4 — Data-quality gate

Blocking checks include:

- duplicate `kind + symbol + sessionDate`
- invalid dates
- missing or non-finite values
- low above high
- open or close outside the daily range
- negative volume
- non-positive prices

Large calendar gaps are review warnings rather than automatic corrections. The pipeline does not silently repair market data.

## Safety invariants

All outputs keep the following values fixed:

- `executionAllowed: false`
- `brokerWriteAllowed: false`
- `excelOrderWriteAllowed: false`
- `rssOrderFunctionAllowed: false`
- `liveTradingAllowed: false`
- `automaticPromotionAllowed: false`
- `productionUpdateAllowed: false`
- `humanApprovalRequired: true`

No MARKETSPEED II RSS order function is imported or called. Read-only market data may be added in later Parts, but `RssStockOrder`, `RssModifyOrder`, `RssCancelOrder` and other write-capable functions remain prohibited.

## Next Parts

- Part5: direct Phase41 ingestion-plan adapter
- Part6: daily local CLI
- Part7: fixture datasets for equities, indices and FX
- Part8: CI safety regression and deterministic dataset manifest
