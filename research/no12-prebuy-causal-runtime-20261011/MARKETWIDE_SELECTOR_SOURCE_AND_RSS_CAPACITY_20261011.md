# Ark Terminal No.1.2 — 全市場Selectorの本番入力とRSS容量（2026-10-11 JST）

**対象:** Draft PR #592 isolated synthetic source-capacity planning only. Frozen No.1.1, PR #591, main, 現行口座Workbook、個人保有・Safety原本は変更しない。

## 実際に存在している旧技術

既存の`scripts/fetch_p25_marketwide_5m_spark.mjs`は、保管されたJPX銘柄一覧を参照し、TradingView Japan scannerから全市場snapshotを集め、Phase57 P25 Dynamic5m V1/V2へ渡す。旧Lane Y→Lane Mには市場横断sourceの保存・候補の動的観測slot配分（`predict/realtime/phase57-msii-dynamic-watchlist.js`）まで実装されている。

**重要：これは研究用。正式Frozen No.1.1 native Selectorの同一性、ライブpre-BUY適格性、本番使用権の保証ではない。**
TradingViewの公式規約は、自動データ収集およびデータをアルゴリズム売買判断に使う非表示利用を明示的に禁止している。独自有償ライセンス等の別権原が確認できない限り、旧TradingView scannerをArkの実売買Selector入力に転用しない。
- https://www.tradingview.com/policies/
- https://www.tradingview.com/support/solutions/43000674726-why-is-my-account-banned-due-to-suspicious-activity/

JPX J-Quants APIの分足・Tickは個人向けには**日次配信**であり、本番で必要な当日リアルタイムの全市場分足を置き換えない。
- https://www.jpx.co.jp/markets/other-data-services/j-quants-api/index.html

## 楽天MarketSpeed II RSSの公式容量

楽天証券RSS公式オンラインヘルプ：
https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_08.html

- 国内株式等の同時市況表示シンボル上限：**500**（市場・コードを含む）。
- `RssChart`同時関数上限：**50**。既存Workbook/他の機能も予算から差し引く。
- 1Mと5Mを別々の関数で監視すれば、1銘柄につき**2チャート関数**。50候補に両方を割り当てる設計は不可能。
- 1Mから5Mを後処理で合成する方法は候補だが、必要な1Mの完全性と実機5Mとの同値照合が取れるまでは原本と呼ばない。
- 複数のWorkbookやプロセスを作って50/500の上限を回避したと見なさない。

## 新規の安全な容量計画器

`runtime/no12_marketwide_rss_capacity.mjs`は、**市場価格・スコアを含まない日付付きJPX銘柄コード一覧**（最低3000銘柄）のみを入力にするpure function。TradingViewデータや架空のスコアを購入判断へ入れない。

1. 管理中の保有銘柄を各観測waveに常時固定し、EXIT監視用Chartにも必須とする。
2. 既存のRSS市況・Chart関数使用量を引き、500市況枠に入るwaveへ全銘柄を決定論的に分割する。
3. 対象Chartは1M/5Mそれぞれ実関数数で予算計上。50を越えたときはfail closedし、Frozen Selectorの選択銘柄を勝手に間引かない。
4. その後の実機実測レコードから、すべてのwaveが5分以内に取得できたかを別監査する。**計画に成功しただけで全銘柄のライブ観測に成功したとは言わない。**
5. 計測clockはPC観測時刻で、Broker真のdelivery timeではない。Statusは常に研究用、`productionReady=false`, `orderTransmission=false`。

## 本番の成立条件（未達）

利用許諾済みの全市場ライブ入力、正式な原本Selector/First Entry/State9/EXITのpoint-in-time生成、50チャート予算・個人株保護・MAX3・現金の連続検証、RSSの実注文ID/部分約定/取消/故障復旧、独立した前向き性能検証、実機終日E2Eが必要。

No.1.2の合成スコアはFrozen No.1.1 H2/H3/H5 R0と同じではない。Frozen R0にはBUY_FILL後に確定する特徴が含まれており、これをBUY前に予測値で代用して原本スコアと呼ばない。

**火曜日のRSS接続確認だけで実売買解禁はできない。** PCでしか取れない証拠と、GitHubで実装すべき未完成箇所を混同しない。Excelの唯一の将来手動売買許可ON/OFFという方針は維持するが、安全性・正規判断器は自動の技術要件として残す。
