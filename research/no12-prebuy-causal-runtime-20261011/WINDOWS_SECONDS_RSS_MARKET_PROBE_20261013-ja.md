# 2026-10-13 RssMarket 秒単位 READ ONLY 物理検査

楽天証券のユーザー提供公式PDF ms2rss_function(1).pdf（2026/3/30）のRssMarket関数仕様より、現在日付・現在値・現在値詳細時刻（HH:MM:SS）・最良売気配値・最良買気配値を1銘柄で取得する。

**目的:** 秒単位の取引所更新時刻がRSSで取得できるか、PCで何秒後に観測したかを測定する。**実際のBroker配信時刻や全銘柄の秒単位保証を証明するものではない。**

- Public固定サンプル7203.Tのみ。既存No.1.1 UI2を停止し、口座Workbookを閉じ、Excelに他のWorkbookが無いことを確認する。Excel RSS発注許可はOFF。
- 一時Workbookを作成し、RssMarket READ ONLYの5セルのみ設定。標準では5サンプル×2秒間隔。Workbookは保存せず終了。
- PC sampledAt とRssMarket現在値詳細時刻を比較する。市場で約定がなければ現在値時刻が進まない可能性があるため、「時間が進まない」だけで接続失敗と決めつけない。
- 私有フォルダ LOCALAPPDATA/ArkTerminal/No12 に市場サンプルとSHA receiptを保存。口座データ・保有株・個人注文データは扱わず、画面には株価や口座情報を表示しない。
- 価格・気配は複数セルの非原子的読取。買気配と売気配の時間差、更新間隔、通信遅延、源泉の真正性は追加検証が必要。
- RSSの現在値更新時刻（HH:MM:SS）はソースの市場時刻であり、PCの受信時刻ではない。PC sampledAt は初観測の上界にすぎない。
- Frozen Selector/Entry/State9/Capital/EXITや本番注文経路は未接続。productionReady=false、orderTransmission=false。

## 実行（隔離No.1.2 worktreeルート）

まずBrokerを使わない自己診断：

    powershell -NoProfile -ExecutionPolicy Bypass -File research/no12-prebuy-causal-runtime-20261011/windows/Probe-No12RssMarketSecondsReadOnly.ps1 -OfflineSelfTest

次に火曜の実機市場中に、既存Workbookを閉じた状態でREAD ONLY：

    powershell -NoProfile -ExecutionPolicy Bypass -File research/no12-prebuy-causal-runtime-20261011/windows/Probe-No12RssMarketSecondsReadOnly.ps1 -Samples 5 -IntervalSeconds 2 -WarmupSeconds 5

5M、1M、秒単位RssMarketの3診断は**同時実行しない**。どれかがBLOCKEDなら自動で発注許可をONにしたりSafety解除したりしない。すべて終わって一時Workbookが閉じたことを確認したら、既存No.1.1 UI2監視を復旧する。
