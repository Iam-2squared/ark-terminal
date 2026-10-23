# Phase57 Entry追加情報 — no-fit descriptive diagnostic

**MSH_ENTRY_LONG_ADDITIONAL_INFORMATION_DIAGNOSTIC_COMPLETE**  
**Primary screen: FAST_FAIL_NO_NEW_FEATURE_NOMINATED**  
2026-09-17 JST / PR #587 / Historical Development only

## 結論

新しく調べた情報から、固定EXIT純利益を直接見分ける主推薦条件を満たすfeatureは出なかった。主判定を変更しない。

ただし事前指定の補助risk診断では、`range6Pct`（直前6本の5分足の値幅）とEntry後30分のD30>=5%に関連が観測された。次の別契約で追加価値を調べる仮説は残るが、今回のEntry改善・利益改善・model PASSではない。補助指標へ主目的を差し替えてPASSにもしない。

## 実施範囲

Source head `7599df41199a8c4d1ea86d5f3cb595edd599dd21`。76 sessions、2024-09-17〜2025-01-09。既存の暗号化Development checkpoint8個だけをrunner内で復号し、76日のraw pages SHA/page response SHA/normalized bars SHAを確認した。API keyの値は取得・出力・配布せず、J-Quants API呼出し0。raw temporary cacheのpurge成功。

Protocol precommit `6512209ffd6bc9c3e44af4e54b84ae50690e772e`。8項目だけのdescriptive screen。モデルfit・model prediction・新Entry判断・threshold sweep・Portfolio replayは0。原本12ファイル、3,800 event IDs、277 v1 anchors、181 strict labelableを照合した。

| Population | Rows | Symbols | Fixed EXIT known | Net positive | Strict30m known |
|---|---:|---:|---:|---:|---:|
| All frozen candidates | 3,800 | 934 | 1,897 | 716 | 1,828 |
| Frozen v1 anchors | 277 | 156 | 192 | 83 | 181 |

192件は個別の固定EXIT参照損益の評価可能数であり、旧173件Portfolioとは異なる。v1のEXITとstrict30m両方があるのは170件。

## Primary: fixed EXIT net > 0

AUCは「featureが高いほどnet positiveか」の単変量記述値。モデルOOF・勝率・利益率ではない。0.5未満は逆方向の関連を表す。複数feature/outcomeの探索で、有意差確認との主張はしない。

| Feature | Available /277 | Joint N | Raw AUC | Symbol/session-balanced AUC |
|---|---:|---:|---:|---:|
| range6Pct | 197 | 154 | 0.4389 | 0.4265 |
| lastCloseLocation | 238 | 182 | 0.4217 | 0.4444 |
| lastUpperWickFraction | 238 | 182 | 0.4346 | 0.4490 |
| turnover6Jpy | 197 | 154 | 0.4608 | 0.4918 |
| relativeVolume5 | 197 | 154 | 0.6111 | 0.5356 |
| directionalVwapDistancePct | 108 | 91 | 0.5204 | 0.6073 |
| priorSelectionCount | 277 | 192 | 0.4898 | 0.4919 |
| ridgeDeltaPreviousSelection | 33 | 25 | 0.6200 | 0.5948 |

主推薦heuristicはraw AUC>=0.60または<=0.40、時系列3/4・固定銘柄群3/5以上で同方向、最大正負寄与銘柄除外後も同方向。研究推薦用の条件で統計的保証ではない。

新情報の推薦0。RelativeVolume5は生の条件を満たすが、既にP0診断済みのため新情報として推薦しない。均衡化すると0.5356、89180/57590除外後0.5569。VWAPも既存情報で、欠損と群差が大きい。Ridge score変化はN25、時系列方向一致2/4で不足。

## Supporting: range6Pct vs D30>=5%

`range6Pct = 100*(max high - min low)/latest close` of six preceding completed scheduled 5m bars。未来barを含まない。昼休みを跨ぐ場合、six trading barsは壁時計30分とは異なる。評価D30はstrict30mのまま。

| Check | Result |
|---|---:|
| v1 feature+risk observed | 144 |
| D30>=5% | 20 |
| Raw AUC | **0.8036** |
| Symbol/session-balanced AUC | **0.7304** |
| 89180/57590除外 | **0.7312**, N114 / adverse13 |
| 直前6barの30個の1分足がすべて観測できる場合のみ | **0.7576**, N75 / adverse14 |

時系列4区間のAUCは0.6250 / 0.7240 / 0.9118 / 0.9306。同方向だが3番目のadverseは1件だけなので高AUCを過大解釈しない。固定5銘柄群ではadverseを含む4群で同方向、残る1群はadverse0のためUNKNOWN。

最大正負寄与は固定EXITのreference return合計で定義した記述的感度分析であり、cash Portfolio contributionとは異なる。銘柄除外を取引ルールにしていない。

range6のMFE>=3 / >=5 AUCは0.4602 / 0.4612。これで『rangeを使ってもwinnerを失わない』とは言えない。Risk分離とwinner保持・利益の両立はまだ未測定。

## Limitations

- すべて既存76日へoutcome-exposed。Selector/v1の学習露出が残る。区間別/銘柄群別集計は追加モデルのOOSではない。
- Frozen candidate membershipがfuture-label availabilityに条件付けられる制約は残る。full live-universe PIT認証ではない。
- six-bar available197/277のうち30個の元minute全観測は96件、partialは101件。80件はsix-bar不足。欠損補完しない。
- close location/wickはzero-range37件、直前bar欠損2件をNULL。zero-rangeを適当な0に変換しない。
- turnoverはraw Va欠損を別監査し、normalizerのmissing→0を新featureへ継承しない。Partial minute sumsを完全な市場turnoverとは呼ばない。
- 正確な当時のtick-size schedule・板・spread・depth・fill probabilityは未評価。株価からspreadを捏造しない。
- 単変量AUCから追加予測力や利益改善を推論しない。弱い単変量結果から非線形/相互作用を含む全改善可能性の不存在も主張しない。

## 次の判断

新しい利益分類featureを採用せず、現状のEntryモデルは維持。補助で残ったrange6Pctの1情報だけについて、次の明示許可・別契約でv1への追加価値を短く測る余地がある。新しいmodel/thresholdを今回作っていない。追加試験でもwinner保持とrisk/利益が両立しなければその案を終了し、同じ案を延命しない。

## Reproducibility / safety

- Exporter commit: `62d62c21b9d9e42fa8a5a9b8ca22160c5a82feb9`
- Export run `35183197002`: SUCCESS、hash確認・offline synthetic test・export・purge・upload成功。
- Derived feature artifact `10481177427` / `phase57-entry-new-information-35183197002`
- Synthetic feature tests14 PASS、statistical unit tests14 PASS。28ユニークテスト。全既存regressionを新規実行したという意味ではない。
- 再現コード: `scripts/analyze_phase57_entry_additional_information.py`
- 再現CI: `.github/workflows/phase57-entry-additional-information-checks.yml`。最終実行結果は当該headのchecksを参照。
- 同じbranchに別のinformation-screen更新が並行していたため、sourceを固定し固有ファイル名で分離。他の結果は本集計へ取り込んでいない。

Model fit/prediction=0、new trading decisions=0、threshold sweep=0、EXIT/Portfolio replay=0、new market data/Fresh/OOS/SHORT=0。Frozen Selector/v1/EXIT/Equal/cash ledgerに変更0。main未merge。

Safety executionAllowed/brokerWriteAllowed/excelOrderWriteAllowed/rssOrderFunctionAllowed/liveTradingAllowed/paperTradingAllowed/automaticPromotionAllowed/productionUpdateAllowed/transmittedは全false。

Protocol SHA `6b5c96d578dde9dee5dfbfa80b8e1ff83c7920b2ae6a890dff0ca5d9d30ce2f7`  
Feature SHA `e68cae479da9fa511d8ccb0b9a80cadac8488f6c3168c77e35fc1bf3de5f41bb`  
Local primary result SHA `199277bce8b414be6e8c7c754fb0edd5515de9afadd50b7a2c114f050246ebe1`  
Local Python3.13.5 / NumPy2.3.5。CI再現では数値を照合し、runtime version差は別記録する。
