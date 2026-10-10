# No.1.1 Position RSS default-header remediation — 2026-10-09 JST

Status: **PENDING WINDOWS REAL-MACHINE VERIFICATION / LOCKED**

Real Windows evidence:
- Original `=RssPositionList(AL2:AU2)`: broker symbol missing, holding metadata available.
- Unsaved `=RssPositionList()`: valid 4–5 character symbol, same name/account/quantity.
- Unsaved independent `=RssPositionList(A2:J2)`: invalid symbol but same name/account/quantity.
- Default first four headers match provider names.
- Custom header root cause is not proven; the same failure reproduces in two workbooks.

The versioned `C:\Ark\Ark_No11_RSS_DefaultHeaders_v2.xlsx` is a distinct new read-only workbook, never an overwrite of the former `C:\Ark\Ark_No11_RSS_ReadOnly.xlsx` or legacy workbook. Three other RSS functions remain unchanged.

Position uses `=RssPositionList()` with the 18-field default order defined by MarketSpeed II RSS official 2026-03-30 spec:
1. AL2: 銘柄コード
2. AM2: 銘柄名称
3. AN2: 口座区分
4. AO2: 保有数量
5. AP2: 発注数量
6. AQ2: 平均取得価額
7. AR2: 時価
8. AS2: 前日比
9. AT2: 前日比率
10. AU2: 時価評価額
11. AV2: 評価損益額
12. AW2: 評価損益率
13. AX2: 銘柄情報等
14. AY2: JAX時価
15. AZ2: JNX時価
16. BA2: PER
17. BB2: PBR
18. BC2: 配当利回り

CRITICAL: position marketValue is AU(column 47), unrealizedPnl is AV(column 48), unrealizedPnlPercent is AW(column 49). AS/AT are day-change fields. Builder and snapshot both validate all 18 headings; missing symbols and unmatched headings block.

Offline tests are **not** Windows RSS proof. The first run must verify real source status, headings, symbol, quantity and PnL labels without logging private broker values. Previously confirmed EXTERNAL owner must still be explicitly reconciled on a newly fresh snapshot before a private baseline freeze.

The following remain **BLOCKED**: actualFeedTimestampCertified, native No.1.1 live strategy events, ownership baseline, full broker order/fill/cash roundtrip, runtime safety PC certification, UI2 PC E2E and any physical order.

No RegisterXLL, no order formula, no order write, no strategy change, no main merge, no transmission. All Safety flags false.

## Correction: shared diagnostic receipt invalidates cross-workbook attribution

On 2026-10-10 JST, user observed `TARGET_EXISTS=False`, while the shared `workbook-diagnostic.json` reported `workbook=Ark_No11_RSS_ReadOnly.xlsx` (legacy No.1.1, not v2). Consequently the previously reported v2 `AL1=RSS_STATUS_UNRECOGNIZED` is **not admissible as v2 evidence**. We do **not** know whether another process rewrote the shared report or the previous launch failed to persist v2. Do not assert a root cause beyond the observed record identity mismatch.

Remediation:
- Each launch uses an independent GUID-named receipt under local application data; old fixed-name diagnostic is not read by the launcher.
- Check expected v2 file existence immediately after the builder returns.
- Before writing the receipt, builder proves returned Workbook.FullName equals the requested v2 path and the file is persisted.
- Before consuming the receipt, launcher proves diagnostic.workbook equals requested v2 path and observedAt belongs to this attempt.
- A BLOCKED status remains BLOCKED; no order/ownership promotions.

Live Windows proof remains pending. Runbook must never treat previous account values or an old workbook diagnostic as fresh proof.

## 2026-10-10 — Physical SaveAs target diagnostic

Additional Windows proof: after V2 Create, `NO11_DIAGNOSTIC_WORKBOOK_IDENTITY_MISMATCH`, but subsequent independent read-only probe shows `V2_FILE_EXISTS=False`, `OLD_FILE_EXISTS=True`, Excel has only the OLD Workbook open, and there are zero per-run receipts. No V2 RSS status or broker symbol values can be certified from this.

The builder now checks the newly created COM Workbook's FullName and actual on-disk V2 file immediately after SaveAs. If either fails, throws a distinct fail-closed error. The function returns `[pscustomobject]@{Workbook=$book;SavedWorkbookPath=$FullPath}` instead of passing the COM object directly through the Windows PowerShell function pipeline (which can enumerate COM objects). The caller extracts only `$created.Workbook`. This is a targeted engineering correction; it does not prove SaveAs succeeded until another Windows run.

Do not re-use the shared historical report or overwrite the old Workbook. No RSS order formula, order call or account data is added.


## 2026-10-10 — Root-cause code-path and design correction

**Physical proof:** Immediately following $Excel.Workbooks.Add(-4167),
the identity check observed either the existing
Ark_No11_RSS_ReadOnly.xlsx or protected Ark_MSII_LiveSource.xlsx,
and raised NO11_NEW_WORKBOOK_IDENTITY_UNSAFE. The exact Excel/COM-level
mechanism remains unknown; Workbooks.Add returning a protected existing
workbook violates the intended new-book contract. Previous iterations had
no guard at this point, so the existing workbook could have been edited
in-memory. Do NOT save the user-owned legacy workbook after those runs
until its contents are reviewed.

The Create path no longer invokes Workbooks.Add. It builds a minimal OOXML
single-sheet staging .xlsx from pure .NET (no formulas or broker data),
opens that **exact** staging file and validates Workbook.FullName and
ReadOnly=false **BEFORE any Excel cell write**. Only then are the four
read-only RSS functions and expected headings inserted. The stage is saved,
closed, and File.Move places it atomically at the versioned target without
overwriting. The final target is reopened READ ONLY with exact path
verification. COM Application and Workbook function returns use scalar
PSCustomObject wrappers. A mismatched unexpected COM reference is NEVER
closed, saved, or edited. A staging artifact is deleted only if this run
created it. Existing legacy workbooks are never targets.

The XML/ZIP structure is tested in Windows PowerShell 5.1 CI; actual Excel
acceptance still needs a single physical run. No user/manual trading
authorization is added; RssStockOrder remains absent.

## 2026-10-10 — Retire invalid staging file generator

Real Windows evidence: **NO11_STAGE_OPEN_FAILED** immediately after `Excel.Workbooks.Open(stage,0,false)`; no RSS formula write occurred on that run. Whether Excel rejected the minimal package or Excel COM returned null cannot be established from this log. Therefore the minimal OOXML generator and all Excel Workbook creation and formula writes are removed from the Create path.

A verified fixed finished template `Ark_No11_RSS_DefaultHeaders_v2_READY.xlsx` is generated offline with one `ARK_ACCOUNT_READONLY` worksheet, 18 position headers, exactly four READ-ONLY RSS functions, and no macro/order function/account values. SHA-256 `3db01750b742f85cc19c2f6c7a7547f075c3b2ed1b6f1a36d917d4e21f981c17`; size 4305 bytes. It must be placed by the user at `C:\Ark\Ark_No11_RSS_DefaultHeaders_v2_READY.xlsx`. Create mode only checks that SHA, copies file without overwrite to `C:\Ark\Ark_No11_RSS_DefaultHeaders_v2.xlsx` and opens the copy READ ONLY. No Workbooks.Add, Save, SaveAs or Excel Range.Formula/Value2 setter remains.

Excel opening a correctly formed completed file still requires Windows confirmation; if COM returns a foreign Workbook or no target, the run stops, retains the verified file, and asks the user to open it in Excel manually. Do not save or repair the older workbook. Cached `#NAME?` for offline unsupported RSS functions is not broker evidence; live Excel/RSS must recalculate and produce valid RSS statuses before Snapshot and Ownership.
