# Ark Terminal No.1.1 — As-of input policy, user-selected (2026-10-12)

## Fixed design

The user-selected implementation candidate is to use the newest information **actually received by the PC before the BUY decision**. Preserve original Frozen No.1.1 Selector, First Entry, State9, 24 saved H2/H3/H5 model weights, PAVA/ML, S/A/B, Capital V5 and EXIT. Never promote No.1.2's First Entry score/threshold surrogate rank to the Frozen production strategy.

This is a **fixed implementation direction**, not a certification that original strategy profits or model input semantics remain unchanged. The price/state reference time changes; scores, rankings, portfolio and outcomes may change.

## Private original-data measurements

Original V5: 24 saved models and 1,039 feature rows exactly reproduced. The previous as-of experiment anchored at archived research BUY fill (NOT actual BUY_INTENT) had 10/905 ML admission flips under optimistic zero-lag bar-end assumption. An additional private test anchored at **First Entry BUY_INTENT** instead found **55/1039 ML admission flips and 84/1039 band flips** (optimistic zero-lag); with 1-minute buffer for price and State9, **85/833 admission flips and 169/833 band flips**. All are retrospective Development comparisons using original fill-based labels; true source arrival times and actual broker fills are UNKNOWN. No fresh OOS or integrated No.1.1 PnL is certified. The ¥1,476,245 figure from the earlier 38-day sensitivity test is NOT a live No.1.1 equity projection.

## Major unresolved issue: model blocks

The saved 24 models are 3 heads across 8 chronological OOF blocks. Their held-out dates span **2025-06-27 through 2025-08-25**; the latest H2_BLOCK_08 was trained through 2025-08-20. The original OOF contract does NOT specify which model to use for a new 2026-10-13 live session. Automatically choosing the latest block or averaging all 8 would itself create a new deployment policy. Do not silently select one.

## New read-only Shadow gate

- runtime/frozen_no11_asof_shadow_gate.mjs validates sourceAsOf <= receivedAt <= knownAt <= decisionAt for Selector event, First Entry intent, closed State9, and RSS market price.
- Rejects future and unclosed bars, stale prices/states, invalid First Entry threshold, PULLBACK/SHARP_DROP at entry, and all archived fill/teacher fields in pre-buy inputs.
- Persistent Selector watches may be older than five minutes: the Selector price-eligibility age at original selection and watch lifetime are different concepts.
- Provisional Shadow engineering limits (90s First Entry intent, 90s State9, 30s RSS price) are NOT Frozen thresholds; they require real-PC latency measurement before final policy.
- An accepted input only establishes internally consistent **declared PC receipt times**, not independently authenticated broker delivery, licensed market-wide Selector source, native model inference, live order readiness or profitability. productionReady=false and orderTransmission=false always.

## Tuesday 2026-10-13

READ ONLY physical 1M/5M and seconds quote timestamp + PC first-seen latency; confirm legal full-market Selector data and native producer parity; run no-order Shadow original-model comparison; reconcile real order IDs/partial fills/cash/EXIT and independent OOS before live authorization. Existing MarketSpeed II/Excel RSS connection success is preserved. Excel RSS order permission remains OFF. No Frozen/main/PR591/private account edits, no force-push or unauthorized merge.
