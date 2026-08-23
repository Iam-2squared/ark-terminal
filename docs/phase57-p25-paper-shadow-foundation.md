# Phase57 P25.3U — Paper / Shadow Foundation Contract

Status: PREPARATION ONLY. This document does not enable paper trading, shadow promotion, broker writes, Excel order writes, RSS order functions, live trading, automatic promotion, or production updates.

## Purpose

Prepare the existing Ark Terminal paper/shadow components while P25 multi-session prospective validation continues. P25's current prospective test remains frozen and isolated: no model, Entry, universe, threshold, Dynamic-N, fair-cutoff, or fresh-holdout decision may be changed from P25 results during this preparation.

## Existing foundation to reuse

Ark already contains a paper engine/account/order/position/ledger/risk stack and shadow proposal/fill-feasibility/audit/diff/safety components. P25.3U should adapt and test those components rather than create a second trading stack.

## Hard safety boundary

The following capabilities remain disabled throughout P25.3U and later preparation work until a separate explicit promotion decision:

- executionAllowed = false
- brokerWriteAllowed = false
- excelOrderWriteAllowed = false
- rssOrderFunctionAllowed = false
- liveTradingAllowed = false
- paperTradingAllowed = false
- automaticPromotionAllowed = false
- productionUpdateAllowed = false
- freshHoldoutConsumed = false

No MARKETSPEED II order function, Excel order cell write, broker mutation, or live/paper order submission may be introduced by this foundation work.

## Separation from the active P25 prospective test

P25.3U may read schemas and frozen prospective artifacts for compatibility tests, but it must not feed Paper/Shadow results back into the active P25 model or use current outer-OOS/prospective performance to select Dynamic30/40/50, symbols, horizons, models, thresholds, or Entry rules.

The active P25 multi-session evidence/evaluation pipeline remains the source of prospective evidence until its predeclared evaluation checkpoint is reached.

## Foundation layers

1. Signal-to-intent adapter
   - Convert a frozen Ark Entry decision into a deterministic research-only trade intent.
   - Preserve source timestamp, symbol, direction, model/version, universe variant, confidence/score fields, and immutable evidence lineage.
   - No broker-specific order payloads.

2. Paper portfolio simulator
   - Reuse predict/paper account, order, position, ledger, execution, and risk modules.
   - Model cash, positions, realized/unrealized PnL, commissions, and deterministic fills.
   - Add slippage assumptions only as explicit versioned research parameters; never tune them to improve results.

3. Shadow execution observation
   - Reuse predict/shadow order proposal, fill feasibility, audit log, paper-shadow diff, and safety gate modules.
   - Compare intended paper fills with observable market feasibility without sending an order.

4. Risk and kill-switch layer
   - Keep long-only/lot-size/cash/exposure checks explicit and versioned.
   - Any invalid/missing market input must fail closed.
   - Safety flags above must be asserted false in tests.

5. Immutable research ledger
   - Record intent -> simulated acceptance/rejection -> simulated fill -> mark -> close -> performance outcome.
   - Preserve provenance so Paper/Shadow results can be compared with the corresponding prospective evidence without rewriting old sessions.

6. Promotion gate
   - Preparation may compute readiness metrics but must never promote automatically.
   - Paper activation, Shadow activation, semi-auto, and any real execution each require a separate explicit decision after sufficient prospective evidence.

## Metrics required before any later promotion discussion

- resolved trade count and session count
- after-cost Net
- Profit Factor
- Max Drawdown
- win/hit rate
- mean/median trade return
- slippage sensitivity
- fill feasibility / rejected-intent rate
- portfolio exposure and concentration
- same-time overlap / effective independent entries
- symbol, sector, time-of-day, session, and regime stability
- Paper vs Shadow divergence
- data-integrity/future-leak blockers = 0
- kill-switch/safety tests = pass

## P25.3U implementation order

A. Inventory and contract tests for existing paper/shadow modules.
B. Add a research-only P25 signal-to-intent adapter with provenance.
C. Add deterministic paper replay tests using synthetic/frozen fixtures only.
D. Add Paper-vs-Shadow comparison report schema.
E. Add fail-closed safety tests asserting all execution/write/promotion flags remain false.
F. Do not schedule or activate Paper/Shadow trading yet.

## Exit condition for this foundation part

The foundation is ready when CI proves that a frozen research signal can traverse signal -> intent -> simulated risk -> simulated fill/ledger -> shadow comparison entirely offline, deterministically, with provenance retained and every execution/write/promotion capability still disabled.
