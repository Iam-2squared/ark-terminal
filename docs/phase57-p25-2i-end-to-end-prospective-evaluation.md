# Phase57 P25.2I — End-to-End Prospective Evaluation

## Purpose

P25.2I composes the precommitted Day expansion into one reproducible research path:

1. frozen pre-open P25.2C universe;
2. P25.2F post-session point-in-time prefix replay;
3. P25.2E immutable Frozen Entry ledger;
4. P25.2G Fixed Horizon outcome materialization at the frozen 0.05% round-trip cost;
5. P25.2H five-variant multi-session evidence accumulation.

The five variants remain `FIXED_5`, `OLD_FIXED_30`, `DYNAMIC_30`, `DYNAMIC_40`, and `DYNAMIC_50`. Current outer OOS is never used to choose Dynamic N.

## Daily MarketSpeed policy

Routine daily P25.2 evaluation is provider-agnostic and **does not require MARKETSPEED II, Excel, board, quote, or tick capture**. Session OHLCV may be collected after the close by a separate data adapter, then replayed cutoff-by-cutoff. Every scorer call receives only the completed 5-minute prefix available at that cutoff.

MARKETSPEED II RSS remains available for later, separate verification at important milestones and for eventual explicitly approved execution integration. A later RSS verification may not rewrite the frozen universe, Entry, threshold, direction, or P25.2 OOS record.

Microstructure is not part of the current Day completion gate. Existing `RssMarket` / `RssTickList` work is retained but frozen for possible future overlay research.

## Operational evidence

Expected trading sessions are declared before evaluation. A day with no ready packet remains a zero-Entry operational day in the `Days to 400` pace calculation. Blocked sessions, incomplete replay decisions, and unresolved Fixed Horizon outcomes remain visible.

Routine outputs retain:

- valid Frozen Entries / trading session;
- observed and pace-estimated Days to 400;
- directional Hit Rate;
- after-cost Trade Win Rate;
- after-cost Net;
- PF;
- MaxDD;
- coverage and its denominator;
- symbol/sector concentration;
- same-time correlation diagnostics;
- session-equal-weight portfolio diagnostics;
- time-bucket and regime stability.

CI green validates implementation/tests only. It is not a performance improvement claim.

## CLI

```bash
node scripts/run_p25_prospective_evaluation.mjs \
  --history-pack <historical-session-json> \
  --session-bundle <prospective-session-bundle-json> \
  --output data/p25-prospective-evaluation.json
```

The CLI records SHA-256 fingerprints for both input files and writes one reproducible result artifact.

## Safety

All execution and promotion surfaces remain disabled:

- `executionAllowed=false`
- `brokerWriteAllowed=false`
- `excelOrderWriteAllowed=false`
- `rssOrderFunctionAllowed=false`
- `liveTradingAllowed=false`
- `paperTradingAllowed=false`
- `automaticPromotionAllowed=false`
- `productionUpdateAllowed=false`
- `transmitted=false`
- `freshHoldoutConsumed=false`
