# 🖥️ No.1.1 → MarketSpeed II：Windows実機 READ ONLY ゲート

Status: MANUAL_WINDOWS_GATE / NO LIVE ORDERS
Frozen: 10c94c92c4bd2a59a22744667fd0210252602df4
Branch: integration/no1-1-msii-cash-locked-v1

このRunbookは実口座READ ONLYとUI 2.0の確認だけ。発注・取消・Excel注文書込・RSS注文関数・本番解除は含まない。

## 0. 開始条件

- Windows PC / MarketSpeed II / Excel 64bit / Node.js / Pythonが利用可能。
- MarketSpeed IIへ本人がログインする。
- Excel側でRSS XLLを正規に手動有効化する。ArkからRegisterXLLを呼ばない。
- C:\Ark\Ark_MSII_LiveSource.xlsxを**本人がExcelで開く**。ARK_ACCOUNT_READONLY Sheetがファイルとして保存済み。
- このintegration branchをローカルへfetchする前にgit statusを確認し、未コミット変更を上書きしない。
- 口座・保有・残高・OwnershipファイルはGitHubにアップロードしない。

## 1. 既存Workbookの4系統

| 関数 | セル | 以前の実機PASS |
|---|---|---|
| RssCapacityList | L1 | 完了 |
| RssOrderList | N1 | 配信中 |
| RssExecutionList | AA1 | 配信中 |
| RssPositionList | AL1 | 配信中 |

#NAME?、Sheet不在、RSS異常時は中止。自動登録・注文有効化は禁止。

## 2. Fresh Snapshot をREAD ONLY取得（人間のPC）

PowerShellで、リポジトリのルートに移動して実行する。

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\integration\no1-1-msii\windows\Get-No11ReadOnlySnapshot.ps1 -WorkbookPath "C:\Ark\Ark_MSII_LiveSource.xlsx" -DoNotAutoOpenWorkbook
~~~

本人のAppDataに private SnapshotとRSS status observationが作られる。Excelへの注文書き込みはない。

~~~powershell
$dir = Join-Path $env:LOCALAPPDATA "ArkTerminal\No11"
node .\integration\no1-1-msii\tools\no11_shadow_preflight.mjs probe --snapshot (Join-Path $dir "snapshot.json") --health (Join-Path $dir "source-health.json")
~~~

期待値：RSS_STATUS_OBSERVED_READ_ONLY / TRANSMITTED=FALSE。実際の証券会社配信時刻の認証や売買許可ではない。

## 3. Ownership分類（本人だけが確定）

~~~powershell
node .\integration\no1-1-msii\tools\no11_ownership_cli.mjs draft --snapshot (Join-Path $dir "snapshot.json") --health (Join-Path $dir "source-health.json") --output (Join-Path $dir "ownership-draft.json")
~~~

Draftの各ownerは必ずUNCLASSIFIED。現在の保有それぞれを、本人がEXTERNAL（個人）かARK_MANAGED（Ark保有）へ変更する。昔の408A 180株は過去の記録であり、現状の保有ではない。

**分類後にStep 2のSnapshotを取り直す**（30秒Freshnessが必要）。数量が変わっていれば一致しないのでSTOP。

~~~powershell
node .\integration\no1-1-msii\tools\no11_ownership_cli.mjs freeze --snapshot (Join-Path $dir "snapshot.json") --health (Join-Path $dir "source-health.json") --classification (Join-Path $dir "ownership-draft.json") --confirm I_CONFIRM_EACH_POSITION_OWNER --output (Join-Path $dir "ownership-baseline.json")
~~~

Outputが既存なら上書き禁止。BaselineはPC内privateで保管し、GitHubへ送らない。

## 4. オリジナルArk Terminal UI 2.0をREAD ONLY表示

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\integration\no1-1-msii\windows\Start-No11UiReadOnly.ps1 -WorkbookPath "C:\Ark\Ark_MSII_LiveSource.xlsx" -OwnershipBaselinePath (Join-Path $dir "ownership-baseline.json") -Port 8767
~~~

URL: http://127.0.0.1:8767/

HOME / SELECTOR / POSITIONS / ORDERS / PERFORMANCE / SYSTEM の6画面を確認。未接続値はUNAVAILABLE、--、BLOCKEDのままが正しい。Read-only段階では注文/取消/戦略編集/Kill Switch変更は使えない。

初期Kill SwitchはラッチまたはUNKNOWN、TradeReadiness=BLOCKEDが正常。UIでFRESHでも実売買の許可ではない。

## 5. Fail Closed / 報告項目

#NAME?、Excel COM 0x80010001/0x800706BE、30秒超Snapshot、Ownership不一致、COM retry exhaustion、注文・約定不明、部分約定、実行後再起動の状態不明はBLOCKする。永続Kill Switchファイルを消して解除しない。

チャットへ返すのは、エラーコード・4つのRSS状態・6画面表示可否・SourceState/Ownership/RuntimeSafety/TradeReadinessという**状態名**だけ。口座額、銘柄、数量、Snapshot原本は貼らない。

## 6. この手動ゲートをPASSしても残る独立した製品Gate

1. No.1.1 Frozen実装から実時間のDecision Eventを出す機構（Freeze JSONだけでは市場シグナルは生成されない）。
2. 現実の市場データ、H2/H3/H5、State9/Path、Slot Reserveを凍結済みcausal Contractどおりに駆動し、受信時刻・欠測を認証する。
3. RssOrderIDListと実注文ID/注文番号/約定IDの永続照合、合法SELL約定後のBUY停止、未約定/部分約定の検証。
4. G8の実PC障害注入、Shadow/LOCKED実機E2E、最終独立安全監査とユーザーの別途明示承認。

いまのResearch Freeze・offline CI・旧実機READ ONLY PASSは、物理注文を有効化する証明にはならない。ここでは送信できず、必ずBLOCKを維持する。
