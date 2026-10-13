# 2026-10-13 保存済みExcelからの1M・5M RSS確認（注文なし）

## 現時点で実機確認済み

ユーザーのWindows PCにて、MarketSpeed II RSSの現在値と秒単位更新時刻を保存済み `Ark_No11_MARKET_RSS.xlsx` から取得。PowerShell 5秒×6回で全件FRESH、No.1.1市場入力As-of検査は `PASS_MARKET_ONLY`。PC観測時刻と市場更新時刻の差は約0.88〜2.96秒（**Brokerの配信遅延ではない**）。

## 今回の次工程

保存済みNo.1.1口座Workbookと市場Workbookを持つ**既存のRSS有効Excelインスタンス**に、ウィンドウからCOMでアタッチ。Excelの新規COMインスタンスではRSSアドインがロードされない実機事象を回避する。

`windows/Probe-No11SavedExcelChartInputsReadOnly.ps1` は、1つの**保存しない一時Workbook**だけに `RssChart(...,"1M",300)` と `RssChart(...,"5M",100)` を順次入力し、数値の終値行数を確認する。既存の2つのWorkbookは開いたままで、セル・数式・保存内容を変更しない。Excel UI2口座監視ポート8767が有効ならBLOCK。RSS発注許可はOFFのまま。

実機での取得は未確認。まずPowerShellの完全オフライン自己診断：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011\windows\Probe-No11SavedExcelChartInputsReadOnly.ps1 -OfflineSelfTest
```

次にUI2監視を通常手順で停止済みであること、RSS発注不可であることを確認して実機：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011\windows\Probe-No11SavedExcelChartInputsReadOnly.ps1 -OneMinuteBars 300 -FiveMinuteBars 100 -WaitSeconds 15
```

結果の `NO11_CHART_1M_NUMERIC_CLOSE_ROWS` と `NO11_CHART_5M_NUMERIC_CLOSE_ROWS` は**数値が返った行数の診断**であり、足の完結性・タイムスタンプの正確性・欠損なし・原本State9と同一性を証明しない。次にバーの日時・OHLCV・足種・確定足を照合し、原本Selector・State9の入力契約と突き合わせる必要がある。

**この段階で元のFrozen Selector・First Entry・State9・H2/H3/H5・Capital・EXITは実行しない。実資金注文は0件、productionReady=false。**
