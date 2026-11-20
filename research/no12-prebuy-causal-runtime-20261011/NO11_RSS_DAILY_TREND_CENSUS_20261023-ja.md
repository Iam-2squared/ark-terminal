# 既存統合版 — RSS日足の上昇構造census

対象はPR #592のみ。先行HEAD `ff1bb856fe826713b74f1a808e3291c69c262bbe`のG1を、RSS日足の観測集計へ接続する。別Selector・新学習モデル・寄り前Top15・元10時刻Top5の変更はない。

## 実装

`windows/Run-No11RssDailyTrendCensusReadOnly.ps1`が既存の可視Ark Excelに接続し、独立した一時Workbookで`RssChart(...,"D",100)`だけを作成する。元2冊は変更・保存しない。口座値の読取・出力、発注、RegisterXLL、Excel終了・強制終了は行わない。既存チャート系関数を保守的に数え、追加分と合わせて50以下で逐次取得する。標準は20銘柄ずつ。

対象リストは以前の`rss_symbols_to_acquire.txt`のSHA256を固定する。旧リストで取得済みのため除外していた7203.Tを重複なく追加。したがって旧4,327件なら今回4,328件。これは過去の取得対象集合であって、2026年の当日銘柄マスタ・全上場銘柄の保証ではない。

PCの日本時刻から直近の完了営業日を決める。18:00以降に当日を使うのは保守的な収集方針であり、RSS側の確定・訂正なしを認証する意味ではない。休日は既存のJPX現物calendarを利用し、未登録年は拒否。2026-10-23基準なら2026-07-02〜2026-10-23の76営業日がG1の必要窓。

各銘柄のデータ・計算対象日・取得前後の実PC観測時刻・式を、SHA256を名前に含むprivate JSONとして保存する。同じ対象日・同じコードidentityの再実行では保存バイトを照合して未取得分だけ続行。途中の`.pending`は完了扱いしない。全件空の取得群は接続障害と区別できないため保存完了にせず停止。76日分が揃う銘柄が取得群に一つもなければ部分reportを出して停止する。

Nodeの`tools/no11_rss_daily_trend_census.mjs`がplan・再開・集計を担当。PowerShell 5.1対応のASCIIソースで日本語headerをUnicodeコードから組み立てる。`-OfflineSelfTest`はExcelなしで動く。NodeテストからWindows上の構文解析と自己診断も実行する。

## 出力の意味

`observedStructureCounts`は、RSSが返した観測終値を使ったPASS/WAIT/REJECT/UNKNOWN件数。以前の厳密G1と同じ整数・10進数比較関数を使うが、計算の共通化によってRSSの価格basisを認証済みに変更しない。

- `priceBasis=RSS_CHART_UNVERIFIED` / `corporateActionsCleared=false`。
- `decimalProvenance=EXCEL_VALUE2_ROUNDTRIP`。Excel数値を文字列にしたものであり、元providerの10進文字列を保存したという意味ではない。
- 当日途中の足は窓に入れない。欠けた日を前値で補完しない。上場後76日未満、無約定、重複、OHLCV不正はUNKNOWN。
- `admittedLiveSymbols=null`。暫定通過を売買可能銘柄として出力しない。
- 500件超でも切り捨てない。PASSとUNKNOWNを別表示し、全部UNKNOWNだったことを容量解決としない。

共有用`no11-daily-trend-summary-*.json`は集計とhashのみ。個別銘柄・株価・ローカルパスは含めない。private-detailsとsource filesはPC内に残す。再送が必要なのは集計JSONだけ。

## まだ解決していないこと

500以下という件数だけではライブ接続完了にならない。RssChartは50関数、歩み値も50関数で、市況の500銘柄とは別枠。元Selectorの市場・業種breadthや流動性三分位は元の横断集合に依存するため、絞った集合だけで再計算すると元の特徴量が変わる。このcensusでは参照集合の縮小や不足値の補作をしない。

日足の価格調整・企業行動・当日銘柄マスタ、正確な分Va、横断集合の供給、2026モデル割当、全体Shadow・発注管理は未完。元モデルを増やす作業ではなく、既存入力契約の接続残件である。新fit0、selector実行0、注文0、productionReady=falseを保持する。

## 公式仕様（2026-10-23確認）

- チャート/D日足・100本指定: https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_04.html
- 市況500銘柄・チャート50関数（RssChartPastは関数数上限なし）: https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_08.html
- JPX現物休業日: https://www.jpx.co.jp/corporate/about-jpx/calendar/index.html

この版では既存取得成功経路と同じRssChartをDへ変更して使い、RssChartPastの開始日方向を実測なしで仮定しない。
