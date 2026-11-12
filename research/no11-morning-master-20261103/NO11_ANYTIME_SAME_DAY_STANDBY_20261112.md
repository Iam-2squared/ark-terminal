# ARK No.1.1 — Flexible same-day standby (2026-11-12)

## Request and explicit safety boundary

The old OneClick **08:30–08:59 JST standby** is unnecessarily narrow.
The proposed source-level change makes it possible to **request same-day standby
at any clock time from 00:00:00 through 08:59:59 JST**, on an eligible weekday
with an existing verified **same-date** handoff and explicit same-day approval.

**This does not widen LIVE order time, broker authorization, or session dates.**
From 09:00, the existing direct Trade request path and all native gates remain
unchanged; from 15:20, entries close; from 18:00, the nightly data button retains
its own workflow. At 21:00, users may have the UI open for **read-only status**
but must not pre-authorize the *next* session's real orders with yesterday's
consent. Weekend/holiday eligibility still depends on the exact same-day handoff
and original policy; no new holiday fallback is added.

## Exact source delta (candidate-only, not installed)

`no11_anytime_preopen.py` checks known source anchors and generates the
reversible, byte-localized modifications for:

1. `Start-No11PreopenStandby.ps1`: widen **IsArmWindow** lower boundary from
   08:30 to 00:00 and extend the offline boundary selftest. Retain **IsLaunchWindow**
   at `[09:00:00,09:02:00)`, original same-day request timestamp, original
   approval and nonce, and existing one-shot durable claim. Do not replay Trade.
2. `Start-No11OneClick.ps1`: allow the existing preopen button to queue from
   00:00; update the visible waiting copy. Original `$trade.Enabled` expression
   and all callbacks stay byte-identical.
3. `no11_oneclick_display_v2.py`: classify genuine early approved receipts as
   valid and show `RESERVED 09:00` also during `BEFORE_OPEN`. Reject
   previous-day/future-day receipts and expired reservations as before.

The standalone program **only stages these changes within a disposable Git
checkout**. It does not update an installed program or attach approval to a
future date.

## Nonnegotiable release gate

The user's installed white OneClick has original, immutable
`oneclick-display-v2-install.json` and
`oneclick-display-v2-overlay-compat-install.json` receipts and a contract
binding to the displayed code. **Do not directly copy these generated scripts
or rehash the old journals**: doing so can invalidate historical V2 and overlay
verification, and could render the UI unsafe or unavailable.

A subsequent, separate after-hours release must:

- Identify the user's actual installed source and verify both complete V2
  and overlay chains plus sidecar bytes and original broker source pins.
- Apply only the reviewed worker/UI/presentation deltas; rebind the display
  contract in a **new journaled migration**, preserving all original receipts.
- Verify atomic readback, PowerShell 5.1 parse, source hash, no live
  worker/collector, no affected ARK-controlled workbook, and no change to
  broker order, trade authorizations, claims or previous ledger.
- Confirm any historical unclosed Chart50 attempt stays **unverified**;
  successful standby is not permission to reset/replay that old session.
- Fail closed on a new deployment mismatch, partial migration or changed
  permitted source. Do not start Trade or Excel as part of installation.

Dedicated Windows/Linux CI validates the original 08:30 package, the exact
proposed transforms, a synthetic 00:00 / 08:29 / 08:59 / 09:00 display
case, and real Windows PowerShell 5.1 offline selftests. CI is not a real
broker order test.

## Operator meaning

**Standby at 06:00**: with tomorrow/current-day handoff properly prepared,
the operator can explicitly approve **today's** 09:00 request. The worker
waits for 09:00 with the PC awake and will request the native launcher once
if all original source, broker, cash, date and no-retry checks pass.

**Standby at previous evening**: read-only UI monitoring may continue,
but **no next-day unattended LIVE order** is requested using previous-day
approval. The operator must approve on the actual session date.

**After 09:00**: use the existing normal Trade entry path only when its original
approval and order requirements are satisfied; no backdated 09:00 trigger.
