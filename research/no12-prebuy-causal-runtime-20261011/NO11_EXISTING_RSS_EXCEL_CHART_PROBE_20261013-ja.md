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

## 追加監査：実取得バーの構造と時刻ラベル

実機で `1M=295/300`、`5M=99/100` の数値終値行を確認済み。ただし、数値行数だけでは日時・OHLCVの整合性が分からないため、同じ一時ブックの読取を拡張した。

- Excel日付/時刻のOADateまたは表示文字列をJSTに正規化し、当日PC観測より未来の行を拒否。
- 始値/高値/安値/終値は正の有限数、出来高は0以上の安全な整数、高値・安値と始終値の大小関係を確認。
- 同じ足種内で日付＋時刻の重複を拒否。5分足ラベルは5分境界か確認。
- `NO11_CHART_1M_VALID_OHLCV_ROWS`、`NO11_CHART_5M_VALID_OHLCV_ROWS`、INVALID/DUPLICATE、EARLIEST/LATESTを出力。
- `NO11_CHART_PROBE=PASS` は**バー形式の検査**だけを意味する。欠測なし、タイムラベルが足の開始/終了か、未確定足の排除、原本State9の再現は**未証明**。結果のFALSE表示を維持する。
- 既存Excel二冊の保存・変更、口座データ出力、学習、発注は行わない。

実機の検査結果が返るまでは `NO11_CHART_OHLCV_AUDIT` は未検証。CIの自己診断と実機のMarketSpeed II出力を混同しない。
