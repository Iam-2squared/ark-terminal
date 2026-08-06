# Phase40.5 — Local Backtest CLI

## Purpose

Run Phase40 historical backtests from a local terminal against CSV or JSON files.

## Safety

The CLI is locked to `HISTORICAL_BACKTEST_ONLY`.

- broker writes: forbidden
- live trading: forbidden
- order create/transmit/cancel/modify: forbidden
- Excel order writes: forbidden
- `ARK_ORDER!B9` writes: forbidden
- automatic Candidate promotion: forbidden
- Production updates: forbidden

The CLI prints and persists `brokerWrites: 0` and `liveOrders: 0`.

## Supported input

One file per symbol in `data/historical/prices`.

Supported formats:

- CSV
- JSON array
- JSON object with `rows` or `candles`

Filename example:

```text
7203.T.csv
6758.T.json
```

Expected columns:

```text
Date,Open,High,Low,Close,Adj Close,Volume
```

Aliases such as lowercase names, `adjustedClose`, and `AdjustedClose` are accepted.

## Windows PowerShell example

```powershell
node tools/run_phase40_backtest.mjs `
  --data-dir data/historical/prices `
  --symbols 7203.T,6758.T,9984.T `
  --periods 1,3,5,10,20 `
  --concurrency 2 `
  --maximum-samples 300 `
  --output-dir data/backtest-runs/first-run
```

## Resume

Run the same command again with the same `--output-dir`.

The CLI automatically reads:

```text
checkpoint.json
```

Completed tasks are skipped. Failed tasks are skipped unless:

```powershell
--retry-failed true
```

is specified.

## Output

```text
data/backtest-runs/first-run/
  config.json
  dataset-audits.json
  checkpoint.json
  completed.json
  failed.json
  summary.json
  analysis.json
```

Start with a small run before increasing the universe:

- 3 to 10 symbols
- 5 years of daily data
- horizons 1,3,5,10,20
- concurrency 2

Then expand to 50 symbols after the first run passes data-quality checks.
