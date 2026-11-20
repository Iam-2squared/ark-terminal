# No.1.1 — 2026 RSS対Frozen Selector接続の境界（2026-10-14 / 実測）

## 受領証跡と物理監査

- 提出された `no11-2026-selector-source-gap-731a5095e605ad17.json` のSHA256：`731a5095e605ad17bf9b6e5f128ac912d6cd7dfe3cec5a3e38cdb4068ee75df8`。
- 4,327対象 / RSS 1M観測4,071銘柄 / 3,705,797本 / 完全5×1Mを含む暫定5Mが337,023本。
- 不完全5Mグループ914,088は、1M欠損の補完禁止により除外したグループ数。914,088本の欠損OHLCVが確定したという意味ではない。
- 8営業日のFrozen意思決定10時刻で、暫定価格参照の件数は全銘柄合計59,712、旧watch先頭950銘柄で8,335。**これは順位・適格・買い候補の件数ではない。**
- 旧watch950のうち8営業日すべてにRSS 1Mがあったのは856。しかし5M完全連続性、発注前情報、現在上場区分は認証されていない。

## 元Frozenコードの入力実態（既存コード変更なし）

- `predict/long-only/phase57-long-only-integrated-dataset.js` のL0は、各営業日のmaster（市場部、普通株区分）、日足調整済み終値、前営業日の調整済み終値、コーポレートアクション・調整連続性を要求する。RSS 1MのOHLCVから再構成不可。
- 同コードの元 `normalizeAndAggregateMinuteRows` は部分観測5Mを `observedMinutes` を保持して構成する。今回の「完全5本だけ」の新規proxyは**より狭い別の研究用規則**であり、元5M変換のParity PASSを意味しない。
- `phase57-long-only-l1-labels-features.js` は従来の `Va`（分足売買代金）から厳密なVWAP/売買代金を求める。取得済み `RssChart` 1Mの列は日付/時刻/OHLC/出来高までで、`Va` が無い。OHLC×出来高の代用品を元Frozenの値だと称さない。
- 元15項目中、`segmentStandard`, `segmentGrowth`, `liquidityLow`, `liquidityHigh`, `sectorBreadthPositivePct` はRSS 1Mアーカイブ単体では未完成。残り10項目も**値を計算済みという意味ではない**。例：VWAPには原本 `Va` が必要。
- MarketSpeed II公式RSS関数資料（利用者提供2026-03-30版）では `RssChart` はOHLCVの10項目、`RssMarket` は現在の市場部・前日終値・売買代金・VWAPなどを返す。**その場のRssMarket取得が過去8日の分足Va/実受信時刻を復元するわけではない。** `RssChartPast` は日足・週足・月足のみ。

## セパレート評価と統合ゲート

追加した `tools/no11_2026_rss_price_only_observability.py` は、確定済み暫定5M価格参照と「**その後観測されたHigh/Low**」を別々のprivate出力に保存する。未知の未来区間で不達だった銘柄は `UNKNOWN` とし、負例へ変換しない。H2/H3/H5既存Teacherを偽造せず、学習・本番推論・売買注文は一切行わない。

- **Selector正式出力:** L0とL1の本物の入力・パリティ・時刻既知証跡が揃うまで BLOCK。
- **First Entry / State9 / H2/H3/H5:** ネイティブ候補証跡がない限り BLOCK。
- **将来のShadow:** ベンダーライブRSS時点の初回観測ログを新たに収集し、価格・市場部・VWAP・前日終値の可用性と購買前契約を別途検証。大規模銘柄を同時監視できるとの保証はしない。
- Frozen No.1.1と元24モデル不変、main未マージ、注文許可OFF。
