# Phase57 P25.3A — Prospective Session Integrity Ledger

## Problem

Routine P25.2 evidence now runs without daily MARKETSPEED II / Excel. That creates one important ambiguity: if the non-RSS provider returns no usable bars, the system must not silently decide that the exchange was closed. A total provider outage and a genuine non-trading day can look similar.

Misclassifying an outage as a holiday would make `Days to 400` look artificially faster.

## Classification

P25.3A classifies each immutable P25.2J daily capture artifact before it enters the operational pace denominator.

- `READY_CONFIRMED_TRADING_SESSION`: the whole frozen target union was captured successfully.
- `BLOCKED_CONFIRMED_TRADING_SESSION`: capture was incomplete, but at least one target symbol produced a valid 5m session. The market therefore traded; this day remains a zero-Entry operational day.
- `UNRESOLVED_MARKET_CLOSED_OR_PROVIDER_FAILURE`: zero target symbols produced a valid session. The system does not guess whether this was a holiday or a provider failure.
- `VERIFIED_NON_TRADING_SESSION`: zero valid bars and an independent, auditable calendar `evidenceId` explicitly verifies a non-trading date.

## Conservative Days-to-400 rule

Until an unresolved date receives independent non-trading evidence, it remains in `recommendedExpectedSessionDatesForP252H`. This deliberately biases the operational pace slower rather than faster.

P25.3A also reports a confirmed-only date set and the unresolved set separately so the uncertainty is visible.

Outer-OOS performance can never change the session classification.

## CLI

```bash
node scripts/build_p25_session_integrity_ledger.mjs \
  --capture-dir <immutable-daily-capture-directory> \
  --output data/p25-session-integrity-ledger.json
```

An optional `--verified-nontrading <json>` file may contain independently verified non-trading records shaped as:

```json
[{"sessionDate":"YYYY-MM-DD","evidenceId":"PINNED_CALENDAR_RECORD_ID","source":"PINNED_JPX_CALENDAR"}]
```

A verified non-trading classification conflicts and fails closed if any valid 5m bars were captured for that date.

## Daily operating policy

No MARKETSPEED II, Excel, board, Tick, or Microstructure input is required. MARKETSPEED remains a separate milestone/final verification path only.

CI green validates implementation integrity only, not performance.

## Safety

All execution, broker-write, Excel-order-write, RSS-order, live/paper trading, promotion, production, transmission, and fresh-holdout flags remain false.
