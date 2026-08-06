# Phase28 Parts1-3 — MARKETSPEED II RSS order dry-run bridge

## Scope

Phase28 does **not** connect to a Rakuten Securities REST API. The intended execution path is local Windows only:

Ark Terminal → Phase27 approval/risk/kill-switch gates → Python bridge → Excel preview → MARKETSPEED II RSS

This pull request stops before any Excel write or order transmission.

## Parts

### Part1 — Existing bridge audit

- Reuses `tools/rss_bridge.py` and its Windows COM / FastAPI architecture.
- Preserves the current read-only broker snapshot endpoints.
- Keeps credentials, workbook contents and account data off Vercel.

### Part2 — Order workbook contract

The dry-run preview targets an `ARK_ORDER` worksheet with the following contract:

| Cell | Value |
| --- | --- |
| B2 | domestic equity code |
| B3 | BUY / SELL |
| B4 | quantity |
| B5 | LIMIT / MARKET |
| B6 | limit price or blank |
| B7 | execution condition |
| B8 | account type |
| B9 | order trigger, always `FALSE` in this phase |

The intended RSS function is recorded as `RssStockOrder`, but no formula or value is written by this implementation.

### Part3 — Python dry run

`tools/rss_order_dryrun.py`:

- validates the candidate order;
- requires Phase27 two-step approval, risk governor and kill switch states;
- generates the exact Excel cell preview;
- locks the trigger preview to `FALSE`;
- records an audit hash;
- guarantees zero Excel writes, broker writes and live orders.

## Safety invariants

- `excelWriteAllowed = false`
- `triggerLockedFalse = true`
- `brokerWriteAllowed = false`
- `liveTradingAllowed = false`
- human final action remains mandatory
- no order, modification or cancellation route is exposed

Parts4-6 will only be considered after this dry-run contract is reviewed and merged.
