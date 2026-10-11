> **2026-10-10最新版への導線**：本書の本文は10月9日時点の監査記録です。現在は既存デスクトップWorkbookからRSS4系統のREAD ONLY読取が実機で成立し、個人保有1件のOwnership Baselineも本人確認後にローカル固定済みです。2026-10-10の `DESKTOP_SINGLE_WORKBOOK_HANDOFF-ja.md` を優先してください。最新のUI2自動更新とCapital v5資金プレビューは、CI検証が済んでも新しいWindows実機E2Eは未実施です。ライブFrozenイベント、真の到着時刻、Broker注文・約定の経路は引き続きBLOCKED。注文許可OFF、実発注0を維持します。

---

# 🔒 No.1.1 → MSII Cash-only : Integration Gate status

As of 2026-10-09 JST. Integration branch only. No main merge; no order submission.
Frozen No.1.1 authoritative research HEAD: 10c94c92c4bd2a59a22744667fd0210252602df4.

## Completed engineering on this branch (offline only)

| Subsystem | What is implemented | Certification level |
|---|---|---|
| Frozen decision intake | Strict new integration-envelope schema, source hash/commit, no symbol/lot/SOR/account defaults | Synthetic contract tests; **not native No.1.1 exporter** |
| Symbol normalization | Explicit dated, verified JPX→MSII mapping proof; unknown/collision blocks | Synthetic tests |
| Account read | Existing proven RSS/Excel READ ONLY snapshot adapted to remove all RegisterXLL calls | Static check and PowerShell AST; Windows re-run pending |
| RSS status evidence | Capacity/Order/Execution/Position status observation and 30s gate | **Not actual broker feed-arrival certificate** |
| Ownership | Explicit owner classification, private frozen baseline hash, broker parity | Synthetic tests; human confirmation pending |
| No.1.1 first-SELL-fill latch | Local durable Safety ledger, duplicate broker execution handling, next-session reset; never triggers on SELL_INTENT | Synthetic tests; real broker intent/order/execution linkage pending |
| Runtime fault halt | Current locked branch includes persisted latched state + manual reset; final design must remove any **additional manual trading permission** while automatically halting on faults and resuming only after verified recovery | Synthetic tests only; live redesign not implemented |
| Order draft | 20 MSII RssStockOrder args, SOR, DAY, cash BUY/SELL, trigger=0 and TEXT ONLY | Synthetic tests; physical order ID never allocated |
| UI2 | Recovered original HTML and overlay as byte-identical Git blobs, loopback read-only server, original read model and CLI | Original Python tests/Node/static tests; six-screen PC E2E pending |
| CI | Branch-scoped Node tests, original Python server tests, byte SHA parity, Windows PowerShell syntax parsing | Automated offline PASS when green |

The formerly tested real account read-only path belongs to PR #584 / #588. It was NOT rerun on this PC by the current GitHub job.

## Hard blockers — not safe to silently invent

1. The 2026-10-08 No.1.1 Freeze is a **research baseline definition**. Its source JSON does not expose a production native live Decision Event stream. The adapter only accepts an explicitly attested upstream event. Native causal inference and model inputs must be recovered and certified separately; no synthetic model decision may be promoted.
2. The original MarketSpeed II account sheet does not certify the exact data-arrival timestamp of every RSS value. Our source health says actualFeedTimestampCertified=false.
3. RssOrderIDList → unique order ID → RssOrderList/RssExecutionList → partial fill → persistent cash/slot reconciliation has no full Windows physical-roundtrip certification. A text-only Draft is NOT a live order pipeline.
4. Personal positions must be classified on the PC, not guessed or copied into a public repository.
5. Full Windows COM fault handling, UI 6 pages, locked account E2E and real-time frozen strategy event E2E require running on the machine; neither GitHub CI nor historical data substitutes for these.
6. The current implementation has no native executable live-order path. Its locked flags must not be mistaken for a completed order adapter. Per user direction on 2026-10-10, live authorization will require **only Excel's manual RSS order-enable switch**; add no independent Ark approval/reset gate. Retain automatic correctness checks (identity, fresh account, cash, positions, lot, no duplicate order, broker fills) as logic rather than separate user-facing locks. See ONE_MANUAL_PERMISSION_POLICY-ja.md.

## Manual action boundary

Read: docs/integration/no1-1-msii/MANUAL_WINDOWS_GATE-ja.md

First human step: MarketSpeed II login → Excel RSS add-in via Excel → confirm dedicated Workbook saved/open → run Get-No11ReadOnlySnapshot.ps1 read only. The scripts never register an XLL or submit orders.

Do not merge, unlock, run RssStockOrder with trigger=1, alter frozen Entry/EXIT/Capital, fill UNKNOWN with zero, or write real account data to GitHub.

All strategy/execution safety flags stay false, including executionAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, transmitted and productionReady.
