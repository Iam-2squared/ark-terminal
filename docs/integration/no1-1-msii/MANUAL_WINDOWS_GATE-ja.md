# 🖥️ No.1.1 専用 MarketSpeed II RSS — Windows READ ONLY 実機ゲート

**旧Ark_MSII_LiveSource.xlsxのセル操作を繰り返さない。**
専用Workbook `C:\Ark\Ark_No11_RSS_DefaultHeaders_v2.xlsx` を**新規作成**し、
そのままRSS4系統の診断とFresh Account Snapshotを一括取得する。

## 事前条件

- MarketSpeed IIを本人が起動してログインする。
- Excel 64bitとRSSアドインはExcel側で正規に有効化する。
- **RegisterXLL自動呼出は禁止**。この作成スクリプトには含まれない。
- 既存 `C:\Ark\Ark_MSII_LiveSource.xlsx` と `C:\Ark\Ark_No11_RSS_ReadOnly.xlsx` は**上書き・保存・修復しない**。
- 発注用RSS関数、注文トリガー、発注セル、実注文送信は一切作らない。

## 実行 — 既存worktreeとWorkbookを保持する

PowerShellを `C:\Users\Owner\Desktop\Yosuke\ark-terminal-git` で開いたまま実行。
今まで手動診断した `ark-terminal-no11` は変更せず、**新しい分離worktree**へ更新済み接続コードを配置します。

~~~powershell
$repo = "C:\Users\Owner\Desktop\Yosuke\ark-terminal-git"
$newWt = "C:\Users\Owner\Desktop\Yosuke\ark-terminal-no11-default-v2"
git -C $repo fetch origin integration/no1-1-msii-cash-locked-v1
if ($LASTEXITCODE -ne 0) { throw "NO11_FETCH_FAILED" }
if (Test-Path -LiteralPath $newWt) { throw "NO11_V2_WORKTREE_ALREADY_EXISTS_DO_NOT_OVERWRITE" }
git -C $repo worktree add --detach $newWt origin/integration/no1-1-msii-cash-locked-v1
if ($LASTEXITCODE -ne 0) { throw "NO11_V2_WORKTREE_CREATION_FAILED" }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $newWt "integration\no1-1-msii\windows\Start-No11ReadOnlySetup.ps1")
~~~

- MarketSpeed IIには本人がログイン済み、ExcelでRSSアドインを正規有効化済み。
- 元のExcelファイルは閉じてもよいが、**手動修正・保存・削除はしない**。
- 新 `Ark_No11_RSS_DefaultHeaders_v2.xlsx` がなければ一度だけ新規生成。存在する場合は診断のみ。自動上書きなし。
- `RssPositionList()` の公式18項目すべてのヘッダーと取得コードを検査する。
- 同じWorkbookにCapacity/Orders/Executions/PositionsのREAD ONLY RSS関数4系統だけを置く。
- 診断出力は毎回異なる `%LOCALAPPDATA%\ArkTerminal\No11\workbook-diagnostic-<runId>.json` と `snapshot.json`。旧固定名のレポートは流用しない。正常値を捏造しない。
- 以前のSnapshotは所有区分Baselineを固定する権威には使わない。
- この確認はRSS状態と一時刻の保有識別であり、真のbroker delivery timestamp認証ではない。

## 正常なステータス

| RSS関数 | セル | 期待 |
|---|---|---|
| RssCapacityList | L1 | 完了 |
| RssOrderList | N1 | 配信中 |
| RssExecutionList | AA1 | 配信中 |
| RssPositionList | AL1 | 配信中 |

成功時に `NO11_SETUP_READ_ONLY_COMPLETE` が出る。
未接続やExcelアドイン不在なら `BLOCKED`。市場時間外の状態変化は単独で故障と断定しない。

**この診断はRSSの状態セルの観測であり、実際の市場データ到着時刻や注文許可を認証しない。**

## この後の手動作業

RSSが正常になったら、現在の保有のOwnershipを本人が分類する。
昔の408A 180株は過去Evidenceであり、現在の個人保有をArk管理と推測しない。

次にUI2 6画面のRead-only実機確認へ進む。これは実機の機能検証であり、
ユーザーに何重もの許可操作を要求するゲートではない。

**将来の実売買の手動許可はExcel側のRSS注文機能ONだけ**とする。
Ark独自の手動承認・追加ロック解除は設けない。
現行コードはまだREAD ONLYで、Excelの許可だけでは発注できない。
金額・保有・重複注文・鮮度・Frozen戦略制約の自動チェックは維持する。
詳細はONE_MANUAL_PERMISSION_POLICY-ja.md参照。

## 報告してよいもの

チャットには次の状態名のみ報告する。

- `NO11_WORKBOOK_MODE`
- `NO11_RSS_WORKBOOK_STATUS`
- `L1 / N1 / AA1 / AL1` の状態
- `NO11_SETUP_READ_ONLY_COMPLETE` の有無
- エラーコード（発生した場合）

残高・保有銘柄・数量・個人口座Snapshot・Ownership原本は送らない。
