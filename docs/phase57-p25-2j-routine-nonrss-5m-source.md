# Phase57 P25.2J — Routine non-RSS 5m source

## Decision

Routine P25.2 Day evidence must not require the user to keep MARKETSPEED II or Excel open every trading day.

P25.2J therefore adds a separate research-only Yahoo Finance chart 5m source for post-close routine collection. This matches the provider family already used by the frozen Phase57 P24 historical 5m measurement, while remaining explicitly **non-broker ground truth**.

MARKETSPEED II RSS remains available only for separate milestone/final verification and for a much later explicitly approved execution integration. Board/Tick/Microstructure are not part of the current Day completion gate.

## Flow

After the JPX session:

1. load the frozen pre-open P25.2C universe record;
2. build the union of Fixed5 / OldFixed30 / Dynamic30 / Dynamic40 / Dynamic50;
3. fetch 5m OHLCV for every symbol in that frozen union;
4. fail the whole session if even one target symbol cannot provide the minimum valid bar set;
5. save the immutable session bundle on `automation/p25-day-data`;
6. later pass the full completed session to P25.2I/P25.2F, where each scoring call receives only the prefix available at that cutoff.

The source does not use quote, board, tick, order-list, position, buying-power, or any order function.

## Schedule

`.github/workflows/phase57-p25-routine-5m.yml` runs at 16:45 JST on weekdays and can also be run manually with an explicit session date.

The session artifact is immutable by date. A rerun may reuse an identical SHA, but a different payload is rejected rather than silently replacing prior prospective evidence. If collection is incomplete, the blocked artifact is still preserved and the workflow fails closed. Missing/blocked days therefore cannot make Days-to-400 look artificially faster.

## Timestamp convention

Yahoo chart 5m timestamps identify the start of the five-minute interval, matching the historical P24 source convention. P25.2 replay is performed only after the completed session is available, and future bars are not passed to the scorer. P25.2 Fixed Horizon outcomes continue to use the same bar-index semantics as the frozen P24 continuity baseline.

## Limits

This provider is a practical routine research source, not broker ground truth. Provider availability, corrections, missing bars, or timestamp differences are possible. Final milestone checks should compare a sample against MARKETSPEED II RSS before any claim of production equivalence.

CI green validates the implementation only; it does not establish improved trading performance.

## Safety

All execution and promotion surfaces remain false, including `executionAllowed`, `brokerWriteAllowed`, `excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`, `paperTradingAllowed`, `automaticPromotionAllowed`, `productionUpdateAllowed`, `transmitted`, and `freshHoldoutConsumed`.
