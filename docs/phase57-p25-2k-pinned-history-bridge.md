# Phase57 P25.2K — Pinned P24 history bridge

## Why this exists

Routine P25.2 scoring must not depend on the user opening MARKETSPEED II / Excel every day, but the prospective Phase57 scorer still needs a frozen historical training base.

P25.2K bridges the already-pinned P24.10 Yahoo 5m canonical capture into the `historicalSessions` shape used by the prospective P21 scorer. It does not fetch new historical data and does not consume the Fresh P23.51 holdout.

## Frozen source

- canonical source run: `31785422471`
- artifact: `phase57-p24-9-oos-canonical-candidate`
- required snapshot SHA-256: `10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a`
- frozen data end: `2026-08-12T06:30:00.000Z`
- frozen window: 56 days
- symbols: `7203.T`, `6758.T`, `9984.T`, `8306.T`, `8035.T`

The bridge refuses any different SHA, data end, window, universe, or pre-performance-freeze attestation.

## Extraction semantics

The byte snapshot contains duplicate query1/query2 provider responses. They are de-duplicated by symbol+timestamp and must agree exactly. Any conflicting duplicate fails closed.

Session filtering follows the P24 historical baseline convention: Yahoo 5m timestamps, JST regular-session range, and at least 30 valid 5m bars per symbol-session. The output is a deterministic array of `{symbol, sessionDate, bars5m}` records for the prospective scorer.

This historical base is frozen. New prospective session outcomes are never folded back into it during the current P25.2 comparison, preventing the training base from drifting as outer OOS results arrive.

## CLI

```bash
node scripts/build_p25_pinned_history_pack.mjs \
  --snapshot artifacts/oos/phase57-p24-9-oos-byte-snapshot.json \
  --output data/p25-pinned-history-pack.json
```

The CLI verifies the exact canonical snapshot SHA before writing the pack.

## Daily operating policy

Routine daily path:

`frozen JPX universe -> non-RSS 5m session capture -> pinned P24 historical base -> prefix-only Phase57 replay -> Frozen Entry -> Fixed Horizon outcome -> five-variant evidence`

No daily MARKETSPEED II or Excel session is required. MARKETSPEED II RSS remains a separate milestone/final verification source and cannot rewrite already-frozen P25.2 evidence.

CI green validates code/reproducibility only, not trading performance.

## Safety

All execution/promotion flags remain false, including `executionAllowed`, `brokerWriteAllowed`, `excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`, `paperTradingAllowed`, `automaticPromotionAllowed`, `productionUpdateAllowed`, `transmitted`, and `freshHoldoutConsumed`.
