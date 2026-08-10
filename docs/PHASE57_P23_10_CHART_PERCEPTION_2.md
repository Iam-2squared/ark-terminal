# Phase57 P23.10 — Chart Perception 2.0 Architecture Reset

## Why this exists

P23.9A–E showed that adding more numeric predictors and gates did not improve the frozen development sample reliably. The project therefore stops treating the problem primarily as `features -> forecast` and introduces an explicit perception/understanding layer before prediction.

New order:

`completed OHLCV -> chart perception -> market structure -> setup/scenario understanding -> historical evidence -> later prediction/decision research`

This phase does **not** claim an edge and does **not** enable any trading path.

## Core principles

1. **Describe before predicting.** The engine must first say what the chart is doing now.
2. **Structure before indicators.** Swing structure, impulse/pullback, breakout/retest, volatility and volume context are primary. RSI/MACD-style indicators remain optional supporting evidence elsewhere.
3. **Multi-timeframe context.** 5m, 15m and 60m views are represented explicitly rather than collapsing everything into one feature vector.
4. **Scenario + invalidation.** A chart state is represented as a scenario with an explicit structural invalidation reference, not only a future-return label.
5. **Point-in-time only.** No future bar, realized MFE/MAE, realized return or exit outcome may enter perception.
6. **Provider-independent reasoning packet.** `buildChartReasoningPacket()` creates a stable structured packet that can later be reviewed by a visual/reasoning model without coupling Ark to a specific external API in this phase.

## P23.10 first-pass outputs

Per timeframe:

- swing market structure: higher-high / higher-low / lower-high / lower-low
- regime: uptrend / downtrend / range-or-transition
- impulse vs pullback phase
- 20-bar location and recent swing distances
- breakout / retest / failed-breakout state
- candle body and wick structure
- robust relative-volume context
- volatility compression / expansion
- trend efficiency / persistence quality
- primary structural scenario
- structural invalidation reference
- compact human-readable narrative

Multi-timeframe output:

- independent 5m / 15m / 60m perceptions
- directional alignment score
- explicit conflict flag
- one causal cutoff

## OpenAI / visual reasoning direction

P23.10 deliberately creates an intermediate `ARK_CHART_REASONING_PACKET_V1` instead of directly asking a model “will price rise?”. The intended later role of a reasoning/vision model is:

- inspect the chart state and rendered chart image together
- explain the dominant structure
- identify competing scenarios
- identify invalidation evidence
- classify setup quality
- remain grounded in the causal cutoff

The visual reasoner is a **research perception/understanding component**, not an order generator. External API integration is deferred until its exact current interface, privacy/cost constraints and deterministic fallback are verified.

## What is intentionally not done yet

- no optimized entry threshold
- no new exit threshold
- no outer-outcome selection
- no P23.8 frozen-window tuning
- no live or paper execution
- no automatic promotion
- no production update

## Next research steps

P23.10A: correct session-aware multi-timeframe aggregation and chart-image rendering packet.

P23.10B: build a labeled chart-state corpus from historical completed bars without reusing frozen outcome labels for architecture selection.

P23.10C: compare human-style setup classes (trend pullback, breakout/retest, failed breakout, compression expansion, range rejection) against future distributions on a fresh development window.

P23.10D: add scenario evidence scoring and only then test selective entry/exit behavior.

A final edge claim remains forbidden until a fresh untouched OOS period is evaluated after the architecture is frozen.

## Safety

All of the following remain false:

- executionAllowed
- brokerWriteAllowed
- excelOrderWriteAllowed
- rssOrderFunctionAllowed
- liveTradingAllowed
- paperTradingAllowed
- automaticPromotionAllowed
- productionUpdateAllowed
- overnightHoldingAllowed

Human approval remains required for any future progression beyond research.
