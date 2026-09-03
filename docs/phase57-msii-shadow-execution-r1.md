# Phase57 MarketSpeed II Shadow Execution R1

## Goal
Run a second prospective lane in parallel with the existing Yahoo-delayed realtime research engine, but use MarketSpeed II RSS read-only data so the measurement is closer to actual market-time conditions.

This lane is research/shadow-only. It may create synthetic order intents and synthetic fills for measurement, but it must never transmit an order or write an order trigger.

## Safety contract
The following must remain false at all times:
- executionAllowed
- brokerWriteAllowed
- excelOrderWriteAllowed
- rssOrderFunctionAllowed
- liveTradingAllowed
- paperTradingAllowed
- automaticPromotionAllowed
- productionUpdateAllowed

MarketSpeed II usage is read-only. Allowed inputs include RssMarket, RssChart, RssChartPast, RssTickList and other read-only account/market functions. Order functions such as RssStockOrder, RssMarginOpenOrder, RssMarginCloseOrder, RssModifyOrder and RssCancelOrder are forbidden. Excel order sheets/triggers are never written.

## Parallel architecture
Lane Y (existing): TradingView point-in-time selection -> Yahoo finalized 5m bars -> Phase57 realtime stateful engine -> 28-strategy research ledger.

Lane M (new): MarketSpeed II read-only market/tick/chart capture -> causal feature snapshot -> frozen Phase57 Selection/Entry/EXIT/Allocation logic -> shadow order-intent simulator -> read-only fill estimator -> append-only MarketSpeed shadow ledger -> live dashboard/post-close scoring.

## What "closest to real execution" means here
The simulator records the exact decision timestamp and then estimates whether a hypothetical order could have filled using only subsequent read-only MarketSpeed observations. It must model:
- observed bid/ask or best available market quote at decision time when available;
- tick sequence after decision time;
- spread and adverse movement;
- configurable local processing/decision latency;
- partial/no-fill states when evidence is insufficient;
- transaction-cost and slippage fields separately from strategy alpha;
- no look-ahead: no tick or bar after the synthetic fill decision may be used to improve the decision itself.

No synthetic fill may be created from a price that was not observed. Missing market data fails closed.

## R1 deliverables
1. MarketSpeed read-only event contract normalized from existing Phase58 synchronized capture.
2. ShadowOrderIntent schema with strategyId, symbol, side, decisionAt, reference quote/tick, requested notional/quantity, TTL, and frozen strategy lineage.
3. ShadowFill schema with FILLED/PARTIAL/NO_FILL/EXPIRED/SOURCE_NOT_READY and causal evidence timestamps.
4. Append-only hash-chained shadow execution ledger.
5. Paired comparison against the existing Yahoo lane for the same strategy identity where timestamps overlap.
6. Dashboard metrics: decisions, intents, fills, fill rate, decision-to-fill latency, spread cost, slippage, gross/net return, PF, WinRate, MaxDD, and sample count.

## Non-goals for R1
- No broker transmission.
- No RSS order functions.
- No Excel order writes.
- No real or broker paper orders.
- No automatic promotion to any execution surface.
- No retuning of Frozen selector, Frozen Entry, EXIT v3/v4, Capital Allocation, thresholds or weights.

## Measurement status labels
- FULL_FRESH_MSII: complete prospective MarketSpeed session from the predeclared start boundary.
- PARTIAL_INCOMPLETE_MSII: started late or has gaps; never upgraded by backfill.
- SOURCE_NOT_READY: required read-only source evidence is missing; do not fabricate a fill.

## First implementation path
Reuse the existing Phase58 MarketSpeed II read-only capture chain (`phase58_excel_5m_chart_export.py`, `phase58_excel_synchronized_capture.py`, and `phase58_prospective_session_runner.py`) as the local data substrate. Build the new shadow-execution engine downstream of those captures, keeping the current Phase57 realtime engine untouched so Yahoo and MarketSpeed measurements can run in parallel.
