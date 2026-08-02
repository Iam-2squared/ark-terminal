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
8. `market-intelligence/`: normalized cross-market data, providers, and cache.
9. `backtest/`: chronological evaluation, records, costs, and metrics.
10. `script.js`, `market.js`, `performance.js`: UI orchestration only.

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

## Market Intelligence data core

`market-intelligence/market-data-model.js` is the canonical registry for the
15 Phase 7 market series. Providers return raw source data, the normalizer
converts it to the shared `symbol`, `price`, `change`, `changePercent`,
`timestamp`, `source`, `status`, and `confidence` contract, and the service
isolates source failures while deduplicating concurrent requests. TOPIX,
JPX400, and Growth250 use explicitly labelled ETF proxies with reduced
confidence until stable direct-index adapters are configured.

## Market Intelligence snapshot

`market-intelligence/market-snapshot-engine.js` composes the Bundle 1 data
contract into the required `indexes`, `macro`, `regime`, `score`, and
`timestamp` snapshot. `global-index-engine.js` scores the four Japanese and
four US indexes, while `macro-engine.js` scores VIX, rates, currencies,
commodities, and crypto inputs. Daily changes are normalized with
symbol-specific scales and source confidence is included in the effective
weight.

Missing or failed series are excluded instead of being assigned a neutral
score. The remaining weights are renormalized, and reduced data availability
is reported separately through coverage and confidence. The composite score
uses 70% global indexes and 30% macro inputs. Regime classification reuses the
existing analysis regime engine and recommendation mapping, with the absolute
VIX level retained as a high-volatility risk override.

## Market Intelligence breadth and sectors

`market-intelligence/market-observation-normalizer.js` defines the immutable
constituent-level input used by Bundle 3. It keeps missing values as `null` and
normalizes daily change, volume and turnover ratios, moving-average
participation, new highs/lows, sector, timestamp, source, and confidence.
Duplicate symbols are resolved before aggregation.

`market-breadth.js` combines advance/decline balance, participation above the
20- and 50-session moving averages, and new-high/new-low balance.
`liquidity-engine.js` separates volume activity from directional up/down
volume and optional turnover activity. `sector-strength-engine.js` reuses both
engines for sector momentum, participation, and liquidity; small sector
samples receive lower confidence. `sector-rotation-engine.js` compares only a
current sector report with an explicitly older report, and rejects a previous
timestamp that is in the future.

`composite-market-score.js` combines breadth (35%), liquidity (25%), sector
strength (25%), and sector rotation (15%). Every level excludes unavailable
components, renormalizes effective weights, and propagates data coverage and
source confidence instead of creating neutral placeholder scores.

## Market Intelligence news

`market-intelligence/news-data-model.js` and `news-data-normalizer.js` define
the provider-neutral Bundle 4 contract for news, company IR, TDnet disclosures,
and earnings results. Provider aliases, timestamps, numeric actual/consensus
metrics, source confidence, and importance are normalized without mutating the
upstream payload. Missing text remains unavailable and duplicate URLs or stable
identities are resolved before analysis.

`news-sentiment-engine.js` reuses the existing bilingual context sentiment
lexicon. `news-event-classifier.js`, `news-surprise-engine.js`, and
`news-risk-engine.js` separately classify corporate events, compare actuals
with consensus using explicit metric polarity, and surface material risk
signals. A missing consensus never becomes an in-line result, and an unreadable
article never becomes a zero-risk result.

`news-summary-service.js` accepts an injected AI summarizer but has no hard
dependency on a model provider. It labels source, extractive, title-only, and
AI summaries separately and safely falls back when a summarizer fails.
`news-score.js` combines sentiment, surprise, and inverted risk with confidence,
importance, and time decay. `news-intelligence-engine.js` composes the complete
pipeline while leaving data acquisition adapters independent.

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
- Bundle 3 requires a point-in-time constituent universe from a future breadth
  provider. Current constituents must not be substituted into historical
  walk-forward samples because that would introduce survivorship bias.
- Bundle 4 classifies and scores supplied source records but does not scrape or
  license news, IR, or TDnet content. Each production adapter must enforce the
  source terms, retention policy, and point-in-time timestamps independently.
- Rule-based sentiment, event, surprise, and risk scores are features rather
  than verified facts or calibrated return probabilities. AI summaries must
  retain links to their source record for review.
- Backtests and confidence scores do not guarantee future performance.
