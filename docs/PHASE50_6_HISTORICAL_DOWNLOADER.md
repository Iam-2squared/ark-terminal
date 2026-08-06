# Phase50.6 Historical Downloader

## Purpose

Download historical market data with a read-only HTTP request, normalize it to the Phase45 contract, run fail-closed quality checks, and persist only valid records into the existing Phase41/45 Data Lake.

## Safety

- broker writes: disabled
- Excel order writes: disabled
- MARKETSPEED II RSS order calls: disabled
- live orders: disabled
- automatic promotion: disabled
- Production updates: disabled
- human approval: required

The downloader never imports or calls order functions.

## Local command

```powershell
node .\tools\run_phase50_historical_downloader.mjs --symbols 7203.T --start 2020-01-01 --end 2026-08-08
```

Multiple symbols:

```powershell
node .\tools\run_phase50_historical_downloader.mjs --symbols 7203.T,6758.T,9984.T --start 2020-01-01 --end 2026-08-08
```

Include configured benchmarks:

```powershell
node .\tools\run_phase50_historical_downloader.mjs --symbols 7203.T,6758.T --start 2020-01-01 --end 2026-08-08 --include-benchmarks true
```

## Outputs

- `data/historical/downloaded.phase45.json`
- `data/data-lake/shards/latest.json`
- `data/data-lake/manifest.json`
- `data/data-lake/checkpoint.json`
- `data/data-lake/rejected.json`

## Fail-closed behavior

Any provider failure, empty result, invalid OHLC, duplicate record, or normalization blocker aborts the universe run. The existing Data Lake is not replaced with partial output.

The external chart provider mapping is configurable in `predict/data/phase50-historical-downloader.js`. Provider availability is not guaranteed; failed or changed symbols must be reviewed before use.
