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
