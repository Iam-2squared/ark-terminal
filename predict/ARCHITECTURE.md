# Prediction Lab architecture

Prediction Lab is separated into six layers so new data sources do not need to
change the scoring UI directly.

1. `api/`: Vercel server functions that normalize external data.
2. `data.js`: browser-side API client.
3. `analysis/indicators.js`: pure OHLCV-to-indicator calculations.
4. `analysis/scoring.js`: pure indicator/context-to-score calculations.
5. `backtest/`: prediction records, walk-forward evaluation, and metrics.
6. `script.js`, `market.js`, `performance.js`: UI orchestration only.

## Adding a data source

An adapter should return an object with:

```js
{
  available: true,
  score: 0,
  reason: "",
  data: {}
}
```

Unavailable adapters must use `available: false`. They are excluded from the
score denominator and lower data coverage instead of adding invented neutral
points.

## Backtest rule

Walk-forward evaluation passes only candles at or before the simulated
analysis date into `calculateIndicators`. The future candle is used only after
the score has been created.

## Weight optimization

Weights are stored in the browser. A factor needs at least 20 resolved samples
before it can be adjusted. One optimization run changes each weight by at most
5%, then normalizes the complete set back to 100%.

## External services still required

TDnet, Yahoo Finance message boards, X, Reddit, options, institutional flow,
short interest, and margin data need a permitted data source and its own server
adapter. Their extension slots are listed in `extensions/registry.js`.

The broker execution slot remains disabled. Analysis and order execution must
stay separate.
