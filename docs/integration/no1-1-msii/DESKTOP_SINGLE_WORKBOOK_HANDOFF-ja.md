# Ark No.1.1 — single desktop workbook / read-only integration handoff

Updated 2026-10-10 JST. Status: **READ-ONLY functional handoff; not a live-order release**.

## Confirmed on the user's Windows PC (reported terminal evidence)

- Research Freeze `10c94c92c4bd2a59a22744667fd0210252602df4` restored under `C:\ArkTerminal\repo`.
- Exactly one Excel workbook `%USERPROFILE%\Desktop\Ark_No11_MSII_RSS.xlsx`, worksheet `ARK_ACCOUNT_READONLY`.
- MarketSpeed II RSS 4/4 status functions: capacity `完了`, orders/executions/positions `配信中`.
- Real RSS position symbol and quantity validated; 1 position, 0 order rows, 0 execution rows at the time of capture. Not all historical order records.
- User explicitly classified that 1 existing position `EXTERNAL` and created private `%LOCALAPPDATA%\ArkTerminal\No11\ownership-baseline.json`.
- `Ark-No11-CaptureReadOnly-v2.ps1` succeeded on the PC; its SHA256 must be `0EAB3CA3081B2E0CB323D8438719F2B820B69FC02F373AD843B5907315838E2C`.
- PR #591 read-only RSS gate `RSS_STATUS_OBSERVED_READ_ONLY` and `BLOCKERS=` empty confirmed by the user.
- `actualFeedTimestampCertified=false` and `productionReady=false` throughout.

These observations do **not** prove market-source delivery freshness, a frozen live decision exporter, or any order-fill roundtrip.

## Policy / accounting boundary

- Cash limit: 100% of **RSS 現物買付可能額**. Never subtract personal holdings' market value from this cash again.
- Capital inputs (preview): `cash=buyingPower`, `exposure=Ark-managed stock market value`, `equity=cash+exposure`. Personal stock value is excluded. Missing or mismatched valuation blocks.
- Keep audited Frozen Capital v5 S/A/B, slot reserve, 100-share lots, MAX3, fees, cash budget and no forced backfill unchanged.
- ARK EXIT/SELL cannot apply to personal holdings. An identical personal symbol also blocks an ARK BUY. Classification overlaps or changed broker quantities block.
- The first **legally verified** SELL fill (not intent) prohibits new BUY for that session. The source-time certification for this still requires live implementation.

## New reusable desktop read-only check (integration worktree)

`integration/no1-1-msii/windows/Start-No11DesktopReadOnly.ps1` verifies immutable Freeze HEAD and clean tracked files, pins the PC-proven snapshot reader by SHA256, takes a real read-only RSS snapshot, validates the private ownership baseline, then writes a **private** Capital funding preview to:

`%LOCALAPPDATA%\ArkTerminal\No11\desktop-capital-readonly.json`

Expected result with healthy source: `NO11_DESKTOP_READ_ONLY_POLL_PASS=True`, `NO11_DESKTOP_CAPITAL=READ_ONLY_CAPITAL_PREVIEW`, `PRODUCTION_READY=FALSE`.

For continued read-only monitoring, pass `-Watch -RefreshSeconds 30`. Ctrl+C stops. A failure stops the watcher; it must not default to stale last-good account data. No Excel writes, Excel saves, new workbooks, RSS order calls, Git commits, or account data uploads.

**Do not run this script from the frozen research checkout**: it exists on the **Draft integration** branch. Keep the frozen source checkout unchanged. Do not copy the private ownership file into GitHub or chat.

## Remaining blockers before the final Excel RSS order-enable step

1. Frozen No.1.1 **native live decision and State9 event exporter** is absent. No replay score or synthetic batch can authorize a trade.
2. Market data **actual source receive time** is unproven. An observation timestamp in the snapshot is not a broker feed-arrival certificate.
3. Physical MarketSpeed II **RssOrderIDList / unique ID / order-list / execution-list / partial-fill / cash reservation** roundtrip is unverified.
4. A persistent Ark-owned fill ledger and strict SELL ownership match must be certified end-to-end on Windows.
5. Real Windows continuous session E2E, failure/recovery, UI2 pages, account/order reconciliation and original Frozen decision lineage require physical verification.

Do not turn on the Excel RSS order permission yet. There is **only one eventual manual trade permission**, the Excel RSS order-enable switch, with no Ark-side extra approval/unlock. All accuracy and safety checks are automatic technical prerequisites, not additional user-facing permissions. A hypothetical completed Excel permission alone must never override these blocked states.

Status: **NOT READY FOR MANUAL ORDER ENABLE / NO LIVE ORDER PATH**. Draft PR only. Main and research Freeze are unchanged.

## UI2 read-only desktop path (same workbook, no new Excel)

`integration/no1-1-msii/windows/Start-No11DesktopUi.ps1` takes one private
RSS/Capital snapshot, serves the existing byte-verified UI2 pages **only on
`127.0.0.1:8767`**, and automatically refreshes using the same SHA256-pinned
desktop capture. `Write-No11DesktopReadOnlyPreview.ps1` is the sole approved
desktop preview helper. The UI has no order/cancel API (HTTP mutations return
405), no Excel writes, and no manual Ark approval switch.

The UI presents READ ONLY information; its update time is an **observation
timestamp**, not proof of when the broker's market feed delivered a value.
Missing or stale data BLOCKS the UI instead of silently recycling a previous
snapshot. Keep the private baseline and workbook in their existing locations.

The original legacy UI helper remains available only for prior research;
do not point the desktop launcher at `C:\Ark\Ark_No11_RSS_DefaultHeaders_v2.xlsx`.

## 2026-10-10 desktop fail-closed hardening (offline code / CI only)

- Desktop UI read-model age is **30 seconds** (not 90).
- Failed automatic refresh immediately changes a previously FRESH model to `REFRESH_FAILED` / `BLOCKED`; only a successful new RSS capture restores FRESH. No stale last-good model is promoted.
- RSS subprocess stdout/stderr (which may contain private account values) is not copied into UI refresh errors.
- Concurrent desktop RSS capture attempts are rejected by a Windows named mutex. A failed capture/Capital-Ownership inspection while holding the mutex is latched in the **private** Safety Ledger, never silently treated as success. No reset or live permission is granted.
- This is only offline code. Windows physical checks, broker arrival-time proof, native Frozen No.1.1 event generator and real order/fill reconciliation remain unverified. Excel order enable stays **OFF**.
