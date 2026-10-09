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
