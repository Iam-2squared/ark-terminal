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

## Market Intelligence prediction features

`market-intelligence/prediction-feature-model.js` defines the immutable Bundle 5
feature contract: MarketScore, Breadth, Liquidity, Volatility, Macro, NewsScore,
SectorStrength, Momentum, FearGreed, and CompositeAI. Every value uses a 0–100
scale, but Volatility is explicitly marked as risk polarity and is inverted only
when a supportive directional score is required. Missing values remain `null`.

`prediction-feature-composer.js` reuses the Bundle 2 snapshot, Bundle 3 breadth,
liquidity and sector reports, Bundle 4 News Intelligence, the shared weighted
score helper, the Market Regime VIX scale, and directional-change scoring.
`fear-greed-engine.js` is a derived feature, not a separately fetched index. The
composer rejects a source timestamp later than the feature snapshot so future
information cannot enter a historical sample.

`multi-horizon-prediction-engine.js` emits separate 1, 3, 5, 10, and 20 trading-
day forecasts. Horizon weights increase the relative role of macro and sector
strength over longer periods and the role of news, liquidity, and momentum over
shorter periods. Expected movement reuses the existing ATR-by-square-root-of-
time contract. Confidence describes source quality and coverage, never a
calibrated probability.

`prediction-feedback-adapter.js` creates records compatible with the existing
prediction history, outcome resolver, Accuracy Dashboard, Learning Dataset,
Trade Memory context, and generic Weight Optimizer. It never persists records
or enables execution on its own. `market-prediction-engine.js` is the stateless
orchestrator; record creation remains an explicit caller action.

## Market Intelligence runtime integration

`market-intelligence-orchestrator.js` is the Bundle 1–5 composition boundary.
It accepts either supplied reports or raw market data, constituent observations,
and news records; reuses the existing snapshot, breadth, liquidity, sector,
news, and prediction engines; and returns one point-in-time prediction result.
Raw records dated after the requested analysis timestamp are rejected before
scoring.

`market-intelligence-runtime-adapter.js` selects the supported horizon nearest
to the Prediction Lab period and converts only a `ready` forecast into one
weighted Runtime v3 consensus engine. Unavailable, low-confidence, or failed
Market Intelligence remains visible for diagnosis but cannot affect consensus.
If no Market Intelligence input is supplied, the previous Runtime v3 engine
list and decision path are unchanged.

The browser analysis input builder forwards existing market-context coverage,
news/disclosure records, quote momentum, ATR, and any richer precomputed Bundle
reports without inventing missing values. Runtime output is propagated through
the AI result composer and rendered as separate 1, 3, 5, 10, and 20 trading-day
cards. These cards label confidence as data quality rather than probability.
The runtime integration does not persist forecasts by default and never grants
order-execution permission.

## Historical Market Intelligence snapshots

`historical-market-snapshot-normalizer.js` converts Runtime or orchestrator
output into one point-in-time Bundle 2–5 record. It independently rejects any
report, feature, prediction, or news publication timestamp later than the
analysis timestamp. Large raw news bodies and provider payloads are excluded;
the archive retains derived results and source references under an explicit
retention-policy version.

`historical-market-snapshot-model.js` creates a deeply immutable snapshot with
a deterministic symbol/timestamp identity and content fingerprint. Capture
time is not part of the fingerprint, so retrying the same logical snapshot is
idempotent. A different payload for an existing identity is rejected instead
of rewriting historical evidence.

`historical-market-snapshot-repository.js` provides bounded browser persistence
through the shared storage-key registry and a replaceable repository boundary.
It isolates corrupt records, returns newest-first queries, and exposes an
at-or-before lookup that can never select a future snapshot. The in-memory path
uses the same contract in Node tests and can later be replaced by IndexedDB or
a server-side time-series store without changing the model or service.

`historical-market-snapshot-service.js` owns capture and retrieval. Runtime v3
captures only when `captureMarketIntelligenceSnapshot` is explicitly enabled;
the browser AI input builder enables it when Market Intelligence input exists.
Persistence failures are returned as diagnostics and never affect consensus.
Prediction Feedback stores only the verified snapshot reference, avoiding a
second copy of the reports. Snapshot and feedback execution permission remains
disabled.

## Historical accuracy feedback

`historical-market-outcome-normalizer.js` creates a synthetic evaluation anchor
from the price captured at prediction time and accepts only market candles after
the snapshot and at or before the declared evaluation time. It never infers an
entry price from history downloaded later, because a daily candle could contain
information that was not complete when the prediction was made.

`historical-market-accuracy-engine.js` converts an immutable snapshot back into
the existing Prediction Feedback record schema and delegates outcome labels,
cost treatment, and forecast error calculation to the existing backtest
resolver. Insufficient future sessions remain pending rather than being scored.

`historical-market-accuracy-composer.js` deduplicates those records and supplies
the same resolved evidence to Accuracy Dashboard, Walk Forward summaries,
Weight Optimizer metrics, and the chronological Learning Dataset. Snapshot
identity and fingerprint follow each learning row for auditability.

`historical-market-accuracy-service.js` evaluates batches with one shared cutoff
time, isolates corrupt snapshots, and rejects conflicting identities or attempts
to rewrite a resolved outcome. All outputs are evaluation-only and keep order
execution disabled.

## AI Accuracy Monitor

`ai-accuracy-monitor-engine.js` is the single metric boundary for the main-screen
accuracy display. It reuses `summarizePerformance`, excludes Walk Forward
training and validation partitions, and gives resolved real prediction records
priority over the frozen final-test partition. A final-test result is labelled as
a validation value and is never presented as live accuracy.

The primary number is the directional hit rate among actionable predictions in
the latest 30 resolved-record window. The monitor displays its Wilson 95%
confidence interval, evaluation coverage, pending count, all-time result,
forecast MAE, confidence-calibration gap, and independent 1, 3, 5, 10, and 20
trading-day results. No resolved actionable sample is rendered as unavailable,
not as zero percent.

`ai-accuracy-monitor-view-model.js`, `ai-accuracy-monitor-ui.js`, and
`ai-accuracy-monitor-controller.js` keep formatting, non-destructive DOM
mounting, storage access, and refresh events separate. Prediction confidence is
still labelled as data quality rather than hit probability. The monitor is
evaluation-only and never grants order-execution permission.

## Automatic outcome refresh and durable accuracy history

`prediction-outcome-service.js` groups every pending prediction by symbol,
fetches each history once with bounded concurrency, reuses the existing outcome
resolver, and isolates provider failures by symbol. The browser controller runs
the refresh on startup, reconnect, focus, and a six-hour interval while
coalescing concurrent requests and throttling repeated wake events.

Resolved records are written through the existing Prediction Storage boundary,
which keeps the active window in local storage and the full archive in
IndexedDB. The AI Accuracy Monitor first renders synchronously, then hydrates
from that durable archive so its all-time metrics are not limited to the active
window. Refresh reports and records remain evaluation-only and explicitly keep
execution disabled.

## Daily Market Intelligence capture

`daily-market-snapshot-controller.js` reuses the browser analysis state, the
existing AI input builder, Runtime v3, and the historical snapshot service. A
normal Prediction Lab analysis therefore captures at most one immutable Market
Intelligence snapshot per symbol and Tokyo market date. Reanalysis, reconnect,
and six-hour wake checks are idempotent for the same date, while the next market
date creates a new point-in-time record. The bounded browser retention window is
365 snapshots and every capture remains evaluation-only.

## Resolved feedback learning loop

`resolved-feedback-service.js` converts the durable resolved prediction archive
through the existing chronological Learning Dataset, technical-factor weight
derivation, and Market Intelligence weight metrics. Its controller refreshes on
outcome events and stores a bounded audit summary through
`LearningFeedbackRepository`. Candidate weights are generated only after the
existing evidence thresholds are met; this stage never calls `saveWeights`,
never mutates the active model, and marks every candidate as requiring human
approval.

## Interface encoding integrity

`index.html` is stored and served as UTF-8, matching its explicit charset
declaration. The encoding regression test uses a fatal UTF-8 decoder, rejects
known multi-conversion mojibake markers, confirms critical Japanese interface
labels, verifies balanced structural tags, and preserves every required module
entry point exactly once. This prevents an encoding rewrite from silently
shipping corrupted labels or malformed closing tags again.

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
- Bundle 5 horizon weights and decision thresholds are versioned heuristics
  until point-in-time walk-forward results provide enough samples for promotion.
  A `ready` feature report is not permission to place an order, and every
  generated feedback record has execution disabled.
- Historical Bundle 5 validation must use the market, breadth, sector, news,
  and volatility snapshots that were available at each prediction timestamp.
  Reusing the latest snapshot in old samples would leak future information.
- Backtests and confidence scores do not guarantee future performance.
