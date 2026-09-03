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

## R1 implementation boundary
The R1 core is implemented in `predict/realtime/phase57-msii-shadow-execution.js`. It is a downstream adapter and does not modify the Yahoo lane or any Frozen selector, Entry, EXIT, threshold, weight, or allocation rule.

The module provides:
- normalization of the existing `58.p9.sync-capture` row into an immutable, hashed MarketSpeed event;
- immutable `ShadowOrderIntent` creation for only the 28 identities exported by `phase57-stateful-contract.js`;
- a read-only adapter from already-committed Phase57 allocation decisions into 28 Lane M intents;
- causal marketable-quote and passive-reference fill evaluation;
- immutable execution-aware closed trades;
- a same-timestamp-idempotent, conflict-rejecting, globally time-ordered hash-chain ledger;
- ledger-read-only per-strategy and aggregate execution metrics;
- exact strategy/symbol/decision-timestamp pairing with Lane Y.

Every source observation must be committed to the Lane M ledger before an intent or fill that depends on it can be committed. A fill cannot cite an uncommitted observation. Same timestamp plus same symbol plus identical content is idempotent; conflicting content fails closed. Different symbols may share the same timestamp, while a later append may not move the market-wide clock backward.

## Frozen lineage and quantity rules
`strategyId` is validated against the four frozen cells crossed with the seven frozen allocation profiles. The adapter consumes quantities that the existing Phase57 capital allocator already accepted; it does not calculate a replacement quantity. Selector, Entry, EXIT v3/v4, and allocation version identifiers are mandatory metadata and are never inferred from observed results.

The existing Lane C lot size remains authoritative. R1 does not relax or retune that lot constraint.

## Fill evidence rules
Marketable-quote research uses the first source-ready quote observed at or after the predeclared decision-latency boundary and strictly after `decisionAt`. Fill price is the observed best ask for BUY or best bid for SELL. Quantity is capped by the visible size at that observed top-of-book level and rounded down to the existing frozen lot size. R1 does not invent deeper liquidity.

Passive-reference research uses only post-decision ticks observed at or through the immutable reference price. Quantity and volume-weighted fill price are derived only from those observed ticks. Identical tick tuples repeated in rolling `RssTickList` snapshots are conservatively counted once because the source currently provides no durable exchange trade identifier in this capture contract.

Events later than the requested evaluation cutoff, after TTL, from another symbol/session, or at/before the decision timestamp are excluded. Missing or unverifiable evidence returns `SOURCE_NOT_READY`; an observed non-cross before TTL is `NO_FILL`; the same condition at/after TTL is `EXPIRED`. Partial visible evidence remains `PARTIAL` and is never silently promoted to a full fill.

## Explicit MarketSpeed size-unit gate
The current checked-in Phase58 synchronized row contains best-level sizes and tick volumes but does not encode their unit. R1 therefore requires the ingestion caller to explicitly attest both `marketSizeUnit` and `tickSizeUnit` as `SHARES`. Until that source contract is configured and verified, quantity-based quote/tick evidence fails closed as `SOURCE_NOT_READY`. R1 never guesses a unit and never fabricates a partial fill from an unknown unit.

## Current limitations and next integration step
- No live MarketSpeed session has been measured by this R1 code yet; no execution performance is claimed.
- Top-of-book marketable fills are deliberately conservative and do not infer depth beyond the observed level.
- Passive fills do not claim exchange queue priority or a broker acknowledgement.
- The R1 module produces dashboard-ready and post-close metrics, but wiring it into the long-running Phase58 session runner and a rendered Lane M dashboard remains a subsequent runtime integration step.
- One-month prospective comparison and Champion Candidate freeze remain separate validation work. They cannot enable automatic promotion or production update.

The executable contract is covered by `predict/tests/phase57-msii-shadow-execution.test.mjs`, including future-row exclusion, partial/no-fill/expiry/source-not-ready states, 28-way identity preservation, source anchoring, hash integrity, duplicate conflict rejection, global timestamp causality, Lane Y isolation, ledger-read-only scoring, and all eight safety flags.
