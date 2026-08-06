# Phase41 Parts4-6: Local ingestion

## Scope

Phase41 Parts4-6 add the local persistence and daily-ingestion layer above the immutable Data Lake contract.

### Part4: local persistence

- writes the latest immutable shard to `data/data-lake/shards/latest.json`
- writes `manifest.json`, `checkpoint.json`, and `rejected.json`
- uses temporary files plus rename for atomic JSON replacement

### Part5: provider adapters

Supported input contracts:

- generic JSON arrays
- JSON objects containing `rows` or `records`
- CSV files with `Date,Open,High,Low,Close,Adj Close,Volume`
- MARKETSPEED RSS-derived rows already exported to JSON/CSV

All inputs are converted to the Phase41 `OHLCV`, `INDEX`, or `MACRO` contract before persistence.

### Part6: daily runner

PowerShell example:

```powershell
node tools/run_phase41_daily_ingestion.mjs `
  --input data/historical/prices/7203.T.csv `
  --symbol 7203.T `
  --kind OHLCV `
  --output-dir data/data-lake
```

Repeated execution merges by `kind + symbol + sessionDate`. Older revisions are ignored. Manifest integrity must be valid before files are replaced.

## Safety

This layer is data-only.

- broker writes: disabled
- live trading: disabled
- order creation/transmission/cancellation/modification: disabled
- Excel order writes: disabled
- `ARK_ORDER!B9` changes: disabled
- automatic model promotion: disabled
- Production update: disabled
