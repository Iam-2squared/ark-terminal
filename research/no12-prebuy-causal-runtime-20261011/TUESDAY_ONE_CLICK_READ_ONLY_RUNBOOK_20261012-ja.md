# 2026年10月13日（火）No.1.1 RSS実機検証 — 3つの診断を1回で実行

## 目的

Frozen No.1.1の売買ルールを変えずに、**5M → 1M → RssMarket秒単位 → No.1.1のAs-of市場入力**を1回のREAD ONLYスクリプトで順番に確認する。**実際の注文は一切送らない。**

## 前提

- ユーザー自身がMarketSpeed IIにログイン。Excel RSS注文許可はOFFのまま。
- 既存のNo.1.1 UI2口座監視を通常手順で停止し、元の口座Workbookを安全に閉じる。個人保有・Safety・口座台帳は変更しない。
- No.1.2隔離worktreeを検証済みPR #592のHEADへfast-forward更新。ブランチは `research/no12-prebuy-causal-runtime-20261011`。mainには直接作業しない。
- 実機実行時は、別のExcel Workbookを開いていないことを確認。診断スクリプト側も、既存Workbookが見つかれば停止する。
- 必須: Windows PowerShell 5.1、Node.js、git、Excel/MarketSpeed II RSS。外部サーバーへ情報を送らない。

## まず完全オフライン自己診断

隔離worktreeルートで以下を実行。Excelと証券会社には接続しない。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File research/no12-prebuy-causal-runtime-20261011/windows/Run-No12TuesdayReadOnly.ps1 -OfflineSelfTest
```

`NO12_TUESDAY_OFFLINE_SELFTEST_PASS=True`、`ORDER_TRANSMISSION=False`を確認する。

## 火曜日の市場時間中にREAD ONLY実行

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File research/no12-prebuy-causal-runtime-20261011/windows/Run-No12TuesdayReadOnly.ps1 -PhysicalReadOnly
```

処理は以下の順番で、前の診断がPASSした場合のみ次へ進む。

1. 7203.T 5分足RssChart（500本）を一時Workbookで読み取り、private receiptを保存。
2. 同銘柄の1分足RssChart（2,000本）を別の一時Workbookで読み取り、5営業日履歴の完全性を検査。
3. 同銘柄のRssMarket現在値・更新秒時刻・最良気配を一時Workbookで5回取得。ローカルreceiptを作成。
4. No.1.1 As-of Shadowへ**市場データ部分のみ**を変換。価格のソース時刻・PC読取時刻・現在判断時刻を比較し、未来・古い値・receipt改ざんをBLOCK。

3つのプローブは**同時実行しない**。実行時は独占ローカルロックを使用。既存Workbookは開かず、診断用Workbookは保存せず閉じる。失敗した場合はその時点で停止する。

## 出力の意味

- `NO12_TUESDAY_MARKET_OBSERVATIONS_COMPLETE_READ_ONLY=True`：3つのRSS診断と市場価格As-of変換を**このPCでREAD ONLY完了**。正式No.1.1の自動売買が完成したという意味ではない。
- `NO11_RSS_SECONDS_ASOF_STATUS=LOCAL_RSS_SECONDS_ASOF_MARKET_SOURCE_ONLY`：市場価格のPC受信時刻と判断時刻の整合が取れた。**Brokerの真の配信時刻を証明したわけではない。**
- `NO12_TUESDAY_RUNNER_BLOCKED=True`：いずれかの前提・取得・時刻検証が不合格。自動でRSS注文許可をONにしない。
- 個人口座・株価の実数値は画面に出さず、証拠は`%LOCALAPPDATA%\ArkTerminal\No12`内のprivateファイルに保持する。

## 終了後

診断用Workbookが閉じたことを確認し、元のNo.1.1口座監視を通常手順で復旧。個人保有とSafetyが変更されていないことを確認。

**まだ本番認証ではない:** 正式な数千銘柄Selectorのライブ供給、Frozenモデルの未来日付運用選択、正規First Entry/State9/EXITのライブ推論、Capital資金・実約定照合、独立OOS検証。これらが揃うまでは実資金発注はOFF。
