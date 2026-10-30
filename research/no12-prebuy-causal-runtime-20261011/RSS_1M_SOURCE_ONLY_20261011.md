# No.1.2 — MarketSpeed II RSS 1分足の原本契約（READ ONLY）

2026-10-11 / isolated Draft PR #592 / user-provided 楽天証券 `ms2rss_function(1).pdf` p18 and p33.

- 公式の `RssChart(header, symbol, "1M", bars)` は1分足と表示本数1..3000を仕様上受け付ける。
- 本moduleは**入力済みsource observation**を厳格に検証するpure code。Excel COM、RSS呼出、Workbook生成、注文・取消機能は実装していない。
- 1銘柄の2000本取得を将来のWindows READ ONLY試験候補とし、5直近営業日（通常330本/日、計1650本）を固定JPX現物カレンダーに対して検査。
- 休業日、旧日の代用、重複、OHLCV異常、先頭・末尾足欠落、未確定足、future as-of、30秒超の保存時刻、3分超の最新足を拒否／不十分とする。
- 1Mタイムスタンプが足の開始・終了どちらかは未認証。完全な2つの形式を区別して受け付けるが、これをBroker arrival認証とは呼ばない。
- `sourceKnownAt` はこのPCがSnapshotを読み取った時刻。履歴取得時刻と過去のPIT knownAtを混同しない。
- 市場全体・複数銘柄への適用、RssChart容量、MarketSpeed II実機受信、オリジナルState9の1M逐次推論、Selector、First Entry、EXIT、本番運用、PnLは**未認証**。
- Frozen No.1.1、PR #591、mainは変更しない。現物LONG/100株/MAX3/個人保有隔離、productionReady=false、実注文0、Excel発注許可OFF。

次の認証は「原本Excelと競合しない1M read-only取得」、「State9正式kernel inputへの必要なPIT/availabilityを満たすか」の検査。1MのSynthetic PASSだけで正式売買判断を生成しない。
