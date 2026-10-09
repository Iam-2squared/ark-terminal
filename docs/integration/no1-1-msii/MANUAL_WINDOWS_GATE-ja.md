# 🖥️ No.1.1 専用 MarketSpeed II RSS — Windows READ ONLY 実機ゲート

**旧Ark_MSII_LiveSource.xlsxのセル操作を繰り返さない。**
専用Workbook `C:\Ark\Ark_No11_RSS_ReadOnly.xlsx` を**新規作成**し、
そのままRSS4系統の診断とFresh Account Snapshotを一括取得する。

## 事前条件

- MarketSpeed IIを本人が起動してログインする。
- Excel 64bitとRSSアドインはExcel側で正規に有効化する。
- **RegisterXLL自動呼出は禁止**。この作成スクリプトには含まれない。
- 既存 `C:\Ark\Ark_MSII_LiveSource.xlsx` は**上書き・保存・修復しない**。
- 発注用RSS関数、注文トリガー、発注セル、実注文送信は一切作らない。

## 実行（ローカル worktree の更新＋ワンコマンド診断）

以下はPowerShellを `C:\Users\Owner\Desktop\Yosuke\ark-terminal-git` で開いて実行する例。

~~~powershell
$wt = "..\ark-terminal-no11"
$dirty = @(git -C $wt status --porcelain)
if ($dirty.Count -gt 0) {
    Write-Host "STOP: No.1.1作業フォルダにローカル変更があります。上書きしません。"
} else {
    git -C $wt fetch origin integration/no1-1-msii-cash-locked-v1
    if ($LASTEXITCODE -ne 0) { throw "NO11_FETCH_FAILED" }
    git -C $wt switch --detach origin/integration/no1-1-msii-cash-locked-v1
    if ($LASTEXITCODE -ne 0) { throw "NO11_SWITCH_FAILED" }
    powershell -NoProfile -ExecutionPolicy Bypass -File (
        Join-Path $wt "integration\no1-1-msii\windows\Start-No11ReadOnlySetup.ps1"
    )
}
~~~

- 新Workbookがない場合は `Create`。ある場合は `Diagnose`。既存Workbookを自動上書きしない。
- 新Workbookには `ARK_ACCOUNT_READONLY` 1シートだけ、RSS読取関数4種類だけ。
- Excelの表示設定（数式表示）と、式が文字列でなく本物の数式かを自動チェックする。
- 出力は `%LOCALAPPDATA%\ArkTerminal\No11\workbook-diagnostic.json`。
- RSSが準備できていれば同じ操作内でSnapshotを読取取得。準備できていなければ `BLOCKED` で停止。

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

次にUI2 6画面のRead-only実機確認へ進む。注文送信、取消、Kill Switch解除、
Strategy Edit、実売買開始はすべて別Gate。

## 報告してよいもの

チャットには次の状態名のみ報告する。

- `NO11_WORKBOOK_MODE`
- `NO11_RSS_WORKBOOK_STATUS`
- `L1 / N1 / AA1 / AL1` の状態
- `NO11_SETUP_READ_ONLY_COMPLETE` の有無
- エラーコード（発生した場合）

残高・保有銘柄・数量・個人口座Snapshot・Ownership原本は送らない。
