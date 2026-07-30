# Prediction Lab architecture

Prediction Lab is split by responsibility so data acquisition, validation,
calculation, scoring, testing, and rendering can evolve independently.

1. `api/`: Vercel functions that normalize external data.
2. `data.js`: browser API client and non-blocking data-source orchestration.
3. `analysis/data-quality.js`: blocking quality gate and calculation audit.
4. `analysis/indicators.js`: pure adjusted-OHLCV indicator calculations.
5. `analysis/scoring.js`: category-capped factor scoring.
6. `analysis/prediction-output.js`: direction, range, downside, confidence.
7. `market-context/`: benchmark registry and market-regime adapters.
8. `backtest/`: chronological evaluation, records, costs, and metrics.
9. `script.js`, `market.js`, `performance.js`: UI orchestration only.

## Price adjustment and units

`api/history.js` requests Yahoo Finance adjusted close and split events.
Historical OHLC is scaled with the adjusted-close ratio. Historical volume is
scaled only with later split ratios, because dividends change adjusted price
but do not change historical share count. Both raw and adjusted fields are kept
for auditing.

The quality gate checks:

- adjusted-close coverage and positive adjustment factors;
- declared price currency and `shares` as the volume unit;
- invalid OHLC relationships, non-positive prices, missing rows, duplicates;
- negative or missing volume, extreme adjusted returns, and long gaps;
- sufficient history.

Blocking issues stop scoring. Duplicate rows and small recoverable gaps are
reported as warnings. MA5/25/75/200, 52-week high/low, and the 20-session daily
VWAP approximation are independently recomputed and compared before display.

## Category-capped scoring

Factors are classified into trend, overheat, risk, volume, relative position,
and external information. Factors are first averaged within their category.
The category score is then given a fixed cap. This avoids counting MA, MACD,
ADX, and similar trend information as independent full-size signals.

Unavailable external adapters are excluded; no neutral placeholder score is
invented.

## Chronological backtest

The backtest creates samples in time order and keeps at least
`max(prediction horizon, 5)` sessions between analysis dates. Each sample sends
only candles at or before that analysis date into the indicator calculator.
Outcome candles are read only after the score has been created.

Samples are split chronologically:

- first 60%: training;
- next 20%: validation;
- last 20%: final test.

Weights may be derived from the training partition only. A candidate set must
also pass the validation objective, then the selected weights are frozen for
the final test. Metrics shown at the top of the performance page use only the
final-test partition when available.

The default cost model includes 5 bps commission and 10 bps slippage per side.
Results store raw market return, direction-adjusted gross return, round-trip
cost, and net strategy return separately.

## Metrics and confidence

Performance includes win rate with a Wilson 95% confidence interval, mean and
median net return, maximum drawdown, Profit Factor, average profit/loss,
estimated trading costs, streaks, and an annualized Sharpe approximation.
Results can be grouped by direction, partition, symbol, industry, score,
horizon, month, and market regime.

Prediction confidence is not a probability. It is a data-quality score built
from history count, missing-rate quality, indicator agreement, symbol-specific
test history, and market-regime test history. Missing components are omitted
and the remaining component weights are renormalized.

## Market-context adapters

`market-context/registry.js` has enabled adapters for Nikkei 225, NASDAQ, SOX,
and USD/JPY. TOPIX, Growth Market 250, and industry indexes are registered as
adapter-ready because a stable provider symbol/data contract still needs to be
selected. Current market context is never reused as historical context in a
backtest.

## Remaining limits

- Yahoo Finance is an unofficial upstream dependency and may delay, omit, or
  revise data.
- Daily OHLCV cannot produce true intraday VWAP; the displayed value is a
  20-session typical-price/volume approximation.
- The cost model is not broker-specific and excludes taxes, borrow fees,
  partial fills, and liquidity impact.
- Corporate actions other than available split events and adjusted-close
  history may need a dedicated reference-data provider.
- Historical market-regime scoring requires point-in-time aligned benchmark
  histories; until then regime confidence remains unavailable rather than
  using today's regime.
- Backtests and confidence scores do not guarantee future performance.
