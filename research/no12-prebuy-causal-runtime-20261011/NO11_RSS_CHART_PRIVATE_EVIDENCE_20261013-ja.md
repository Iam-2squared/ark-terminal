# MarketSpeed II RSS 1M/5M OHLCVのローカル証跡保存（2026-10-13）

## 既に実機確認済み

- RSSが接続中のとき、トヨタ7203.Tの1M数値295本・5M数値99本を取得。
- 2026-10-13 14時台を含む実測で、日付・時刻・OHLCV整合性295/295、99/99、重複0、不正0。
- 前の0本はユーザー報告のRSS切断中。再接続で回復。

## 今回追加した機能

既存 `Probe-No11SavedExcelChartInputsReadOnly.ps1` に任意の `-SaveEvidence` を追加。

- 既存の口座用 `Ark_No11_MSII_RSS.xlsx` と市場用 `Ark_No11_MARKET_RSS.xlsx` は一切編集・保存・終了しない。
- 一時ブックに1M・5MのRssChartを設定し、数値終値だけでなく全OHLCV・日付・時刻を検査。片方でも不正なら証跡保存を拒否。
- 両方PASSした場合だけ、`%LOCALAPPDATA%\ArkTerminal\No12\chart-evidence-<GUID>.json` に**上書き禁止の新規ファイル**として、7203.Tの市場OHLCVのみ保存。口座番号・残高・保有銘柄は保存しない。
- 出力の `NO11_CHART_EVIDENCE_FILE` と `NO11_CHART_EVIDENCE_SHA256` を控える。ファイル自体はGitHubへアップロードしない。
- Node検証器 `tools/no11_saved_chart_evidence_check.mjs` は保存済みファイルを再検査し、1M/5Mの各本数・安全側に確定済みとみなせる本数・除外本数を表示。
- 足ラベルが開始/終了のどちらを表すかは**未認証**。各足のラベルに1分または5分を加算してPC観測時刻より後なら、確定足と見なさない。保守的な暫定処理であり原本State9の再現ではない。
- 市場データの欠測なし、全市場Selector、Frozen State9/Entry/モデル、Capital/EXIT、注文は**未認証**。

## 実機コマンド（RSS接続中・発注不可・No.1.1監視停止）

```powershell
$script="C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011\windows\Probe-No11SavedExcelChartInputsReadOnly.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File $script -OfflineSelfTest
powershell -NoProfile -ExecutionPolicy Bypass -File $script -OneMinuteBars 300 -FiveMinuteBars 100 -WaitSeconds 15 -SaveEvidence
```

実行結果の `NO11_CHART_EVIDENCE_FILE` を用いて：

```powershell
node "C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011\tools\no11_saved_chart_evidence_check.mjs" --evidence "実行時に表示されたJSON絶対パス"
```

**本工程は読み取り・ローカル証跡保存だけ。Frozen原本やmainは変更しない。実注文0。**
