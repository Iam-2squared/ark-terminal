# Frozen No.1.1 — 実RSS秒単位価格のAs-of Shadow入力ブリッジ（2026-10-12）

## 目的と変更範囲

MarketSpeed IIの公開サンプル銘柄7203.Tについて、READ ONLY `RssMarket`から取得した秒単位の時刻・価格の**PCローカル証拠**を、No.1.1 As-of Shadow入力の`market`部分へ実際に変換する。これで「Excelが読めた」だけではなく、「実際に観測した時刻と、BUY判断時点の前後関係を検査する」まで進める。

- 元のFrozen No.1.1 Selector/First Entry/State9/H2/H3/H5/Capital/EXITは**不変更**。
- No.1.2の代替ランキング、未来のfill、再学習、実注文、RSS注文関数は**一切使わない**。
- `runtime/no11_rss_seconds_asof_adapter.mjs`がprivate receipt SHA、3〜30個の市場サンプルの単調時刻・価格・気配・日付・鮮度を検査し、No.1.1のShadow Gateが受け取れる`market`入力だけを返す。
- **重要:** sourceAsOfはRSSが示す取引所更新時刻、receivedAtはExcelからのPC読取時刻、knownAtは**このブリッジがSHA検証を終えた時刻**。保存開始時刻を過去の既知時刻として偽装しない。
- 判断時刻より後に検査したreceiptを過去の判断に使用しない。直近市場時刻が30秒より古ければBLOCK（暫定Shadow工学基準、Frozen閾値ではない）。
- source clockが更新されないのは無約定でも起こるため、取得自体と売買に使える鮮度を分ける。
- 認証できるのは**ローカル保存済み証拠の内部整合**。Broker真の到着時刻、RSS更新SLA、全市場Selector、State9、元24モデルの2026年選択、売買利益は未認証。

## 火曜実機検査

既存の秒単位PowerShell READ ONLY診断がprivate receipt保存後に`tools/no11_rss_seconds_asof_readonly.mjs`を呼ぶ。結果は価格や個人口座情報を表示せず、`NO11_RSS_SECONDS_ASOF_STATUS=LOCAL_RSS_SECONDS_ASOF_MARKET_SOURCE_ONLY`と`NO11_RSS_SECONDS_ASOF_SOURCE_AGE_MS`だけ表示する。

- 市場時刻が古い、receipt不一致、未来データ、PC読取時刻が判断時刻を越える場合は`NO11_RSS_SECONDS_ASOF_STATUS=BLOCKED`。
- 3診断（5M、1M、秒単位）は**順番に**、既存の口座Workbookを安全に閉じ、Excel RSS注文許可OFFのまま実行する。
- `productionReady=false`、`orderTransmission=false`。No.1.1の正式モデル判断器・注文経路はまだ未接続であり、Market単体のPASSを自動売買可能と扱わない。

## 実装テスト

Nodeのfixtureで、private RssMarket publisher→SHA receipt→本ブリッジ→No.1.1 As-of Shadow Gateの**市場側入力のみ**をE2E検査。receipt改ざん、未来日付、古いtick、事後読取、危険フラグを拒否。Windows CIではPowerShell `-OfflineSelfTest`を実行し、Excel/MarketSpeed IIには接続しない。
