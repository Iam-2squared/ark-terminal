# Phase41 Part1-3: Data Lake Foundation

## Scope

Phase41 adds a deterministic, immutable data-lake contract above the Phase40 historical-data audit and batch backtest layers.

### Part1: Unified record contract

Supported record kinds:

- `OHLCV`
- `INDEX`
- `MACRO`

Every record receives a stable key:

```text
kind:symbol:sessionDate
```

### Part2: Immutable shards and manifests

Each shard contains:

- schema version
- deterministic checksum
- immutable records
- duplicate-key audit
- record count

The manifest contains shard checksums and counts. Missing, modified, or mutable shards are blocked before backtesting.

### Part3: Incremental daily merge

Daily updates:

- deduplicate by `kind + symbol + sessionDate`
- keep the newest `updatedAt`
- ignore stale revisions
- preserve existing records
- emit inserted, updated, and ignored-stale key lists

## Safety

This module is data-only.

```text
brokerWriteAllowed: false
liveTradingAllowed: false
orderCreationAllowed: false
orderTransmissionAllowed: false
orderCancellationAllowed: false
orderModificationAllowed: false
excelOrderWriteAllowed: false
orderTriggerWriteAllowed: false
automaticPromotionAllowed: false
productionUpdateAllowed: false
```

It never reads broker credentials, writes to Excel, changes `ARK_ORDER!B9`, or calls any order API.

## Next

Phase41 Part4-6 should add local filesystem persistence, source adapters, and scheduled incremental collection. External data providers must remain swappable and must feed this common contract rather than bypassing it.
