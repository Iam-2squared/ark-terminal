# MA4寄り前Selector — RSS入力契約（2026-10-14）

実市場学習・較正・7日の監視リスト・OHLC測定は完了。LIVE_READINESS=NOT_CERTIFIED。Windows/RSS/Workbook/証券口座への接続・操作実績はない。

日足独立SMA/EMA5/15/25/75、前日分足MA5/15/30/60分、週/月独立MAなし。数百の指標は取得した元系列からArk側で計算し、個別RSS関数で直取りしない。登録554/FIT観測464/fit使用463。90全欠測＋1定数はFITのみで除外。板、本文ニュース、真のaggressor等の未観測値を0にしていない。

| 必須family | 過去研究 | 将来の毎朝の供給・停止条件 |
| --- | --- | --- |
| 日足MA4/出来高/売買代金/下落 | RAW OHLC/Vo/Va・比較可能suffix | MA75 slopeは通常76 closes、EMA/Wilder固定seed、週/月統計別依存。最新D-1更新未確認・basis不一致・不正OHLCで停止、履歴不足Noneと理由保持 |
| calendar/dated ordinary master/100株lot | 過去時点の証券種別と市場を照合 | 毎朝のcalendar/master/種別/lot根拠が必要。今日の一覧や末尾のみで代用しない |
| 財務/valuation/決算予定 | PIT出版＋保守的schedule仮定、単位分離 | 訂正/version、knownAtの継続供給が必要。Git保存時刻を過去公開時刻へ置換しない。実受信は未確認 |
| 前日分足/全Tick | 各3原本、各197,509 raw security-days、日足OHLC/Vo/Va不一致0 | 実D-1全sessionが必要。RSS300本窓との意味差、欠落/遅延/再接続、timestamp/列schemaを検査 |
| 市場/業種/部門別フロー | TOPIX、dated sector、過去breadth、公表section結合 | 寄り前全市場cacheの毎日更新が必要。15監視銘柄だけで全JPX realtime breadthは作らない |
| State/Dictionary | Frozen RC2因果的D-1 State、formal観測69,250/197,509 raw security-days | 旧rules/profile・上流fit0。初回D-1未マウント・formal非観測を理由付きNone。Dictionary歴史fit lineage未確認は未接続 |

全市場の寄り前cacheと候補15の寄り後監視は別母集団。保存済み2024原本は将来D-1を供給しない。継続更新元、取得完了時刻、実受信、欠損時停止/代替条件は未認証。縮小live profileは別の事前契約が必要。

楽天公式を2026-10-14確認：市況関連合計500銘柄、chart50関数、歩み値50関数。15候補に各1chart/1tickなら各15だが、他Workbook/sheet/指数の使用分を含める。RssTickList表示1〜300本。完全Tick、全板履歴、全ニュースを保証する仕様ではない。

添付RSS関数PDF SHA256 `298145f74a3cf147859a1d6c0bdb954ba1398d0fb052f7390b09e6e92c022d1a` のRssMarket/RssChart/RssTickList引数と1〜300本を照合。実機動作証明ではない。始値・出来高・売買代金、歩み値時刻/出来高/約定値のsymbol/session・単位・受信timestampを別保存。遅い寄りを09:00に置換しない。

predict_preopen_watchlist.pyはtrusted private model/hash、固定schema、labelなしfeature store、calendar、target/D-1、利用根拠と明示profileを検査。非営業日、D-1不一致、stale cache、cutoff超過、必須source欠落、未確認liveRefresh、schema/hash破損を拒否。今回の歴史watchlistはhistoricalResearchOnly、将来朝の実行PASSではない。

session/cutoff、canonical/RSS code、市場/sector/rank、score/10head、model/config/schema/input hash、quality/missing理由をprivate保存。scoreは費用後EVではない。entryAllowedを含む全11 flags=false。空母集団はno-candidate receipt、寄り後差し替え禁止。

後半補助診断09:30/11:00/13:00/14:00は参照以後のHighのみ、known32/27/27/25、UNKNOWN73/78/78/80。多くが固定5分以内の参照価格なし。bar終了時刻を過去市場テープ可用時刻とする再構成仮定を明記、providerのEOD16:30保存可用性を場中実受信へ戻していない。主Open→High不変更、Entry/EXIT/資金回転・約定性能ではない。

最終構想は現物LONG、同時1銘柄現金集中、全SELL約定確認後の順次回転、第2回以降慎重。差金決済、残注文、余力、容量、実約定、Entry/EXIT/Capitalは後工程。MAX3へ戻さず、注文/paper/Excel/RSS注文関数/自動promotionは0。

公式資料：

- https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_08.html
- https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_03.html
- https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_07.html
- https://jpx-jquants.com/ja/spec/eq-bars-daily
- https://docs.github.com/en/actions/concepts/security/github_token
