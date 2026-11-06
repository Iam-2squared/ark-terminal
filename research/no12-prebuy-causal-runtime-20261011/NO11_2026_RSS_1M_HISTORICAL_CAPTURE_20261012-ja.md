# 2026年の再学習に向けたRSS 1分足の取得（READ ONLY）

## 公式PDFで確認した仕様

ユーザー提供の `ms2rss_function(1).pdf`（2026/3/30）の関数引数一覧 p.18・戻り値一覧 p.33によると：

- `RssChart(ヘッダー,銘柄,足種,表示本数)` は国内株式の `1M` をサポートし、表示本数は**1〜3,000**。
- `RssChartPast(ヘッダー,銘柄,足種,開始日,表示本数)` は過去日付を指定できるが、足種は**D/W/Mのみ**。1分足の任意の過去日付を遡る関数ではない。
- よってRSSだけで2026年7〜10月の市場全銘柄1分足を一括で取り直せると宣言しない。1M 3,000本は、全バーがある場合でも約9営業日分の規模。

## 今日10/12（スポーツの日・現物市場休場）でも試せる歴史データ取得

元のNo.1.1の口座監視を通常手順で停止し、口座Workbookを安全に閉じ、Excelに他のWorkbookが開いていないことを確認。MarketSpeed IIへ本人がログイン。RSS発注許可はOFF。隔離No.1.2 worktreeの最新の検証済みPR #592を使用。

まずExcel・Brokerへ接続しない自己診断：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File research/no12-prebuy-causal-runtime-20261011/windows/Probe-No12MarketRss1mReadOnly.ps1 -OfflineSelfTest -ArchiveHistoricalOnly -HistoryBars 3000
```

次にExcelの**一時Workbookのみ**で公開サンプル7203.Tの最新1分足を最大3,000本取得。既存口座Workbookは開かず、保存しない：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File research/no12-prebuy-causal-runtime-20261011/windows/Probe-No12MarketRss1mReadOnly.ps1 -ArchiveHistoricalOnly -WaitSeconds 25 -HistoryBars 3000
```

- 出力が `NO11_1M_ARCHIVE_STATUS=LOCAL_HISTORICAL_1M_OBSERVED_NOT_TRAINING_CERTIFIED` なら、Excelから取得できた過去足を検査し、ローカルに保存した意味。
- `NO11_1M_ARCHIVE_ROWS` / `NO11_1M_ARCHIVE_SESSIONS` で実際の本数・日数を確認。3,000本指定でも3,000本届くとは限らない。
- 休日・引け後は当日の足がなくても履歴取得を試せる。ただしMSIIの接続状態によってはRSSがデータを返さずBLOCKされ得る。
- 出力は `%LOCALAPPDATA%\ArkTerminal\No12\rss-1m-7203T-*.json` と `*.receipt.json`。SHA256付き、追記式・既存ファイル上書き禁止。個人口座情報を保存せず、価格の実数値を画面に出さない。
- 1Mの時間ラベルが開始時刻か終了時刻かは未認証。市場時刻・PC受信時刻の過去再現は不可。欠測を捏造しない。
- `RssChartPast` の日足を代替の1分足と偽装しない。

## なぜこれだけでは2026年H2/H3/H5を再学習できないか

No.1.1の研究と同条件の再学習には、連続58営業日以上の**市場横断**1分足、元のSelector候補群、First EntryのBUY_INTENT、State9/Path、教師ラベル、判断時点のデータ利用可能性が必要。今回の1銘柄×約9営業日だけでは不足する。必要な権限と取得容量が確認できるまで全市場収集を自動化しない。

**本スクリプトは観測データを集める第一歩。学習済みモデル・Frozen No.1.1・Capital/EXIT・main・PR #591・口座・Safety・RSS注文許可は変更しない。注文0、productionReady=false。**
