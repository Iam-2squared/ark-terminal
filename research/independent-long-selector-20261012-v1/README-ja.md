# Ark Terminal — Independent LONG Selector v1 / 研究プロトコル

作成: 2026-10-12 JST / 状態: **DESIGN_AND_IMPLEMENTATION_ONLY; NO_MARKET_RESULT; NO_FIT**  
基底: Ark Integrated No.1.1 Frozen `10c94c92c4bd2a59a22744667fd0210252602df4`。独立研究ブランチにのみ追記し、Frozen本体・main・実運用PR #591は変更しない。

## 目的と前提

日本株の**現物買いのみ**で、将来の値幅が大きく、かつ急落や大きな逆行が少ない候補を因果的に選ぶ。旧Selector/Entry/EXIT/Capitalの重み・特徴選択・閾値・学習済み係数は一切流用しない。既存State9・Path・Dictionaryは、as-of/knownAt、実データ整合性、学習lineageが確認できる場合に限る**観測入力**として再利用可。既存モデルを新モデルと見なさない。

目標は損失側を限りなく減らすこと。ただしリスクゼロを保証しない。極端な安全寄りの「候補ゼロ」で成績を偽装しないため、Top5固定の一次比較とrisk-abstain時のcoverageを必ず別々に示す。将来Highは**利益確定や実際の約定利益ではない**。

研究専用、取引機能ゼロ。SHORT/信用/margin/leverage/先物/空売り/overnight carryは禁止。100株ロット・MAX3・現金制約は後工程Capitalで適用し、Selectorで無理に約定可能と見なさない。可能性のある100株最低購入原価は参考欄にできるが、候補母集団を事後的に変更しない。

## 基本比較契約（事前固定）

- JPX国内現物のPIT eligible universe（Prime/Standard/Growth）。上場廃止・当時非上場を今日の銘柄リストで入れ直さない。企業行動の価格basisが不明なら当該行はUNKNOWN。
- 旧Phase57 LONG Frozen Selector v1 の比較用時刻: **09:30/10:00/10:30/11:00/11:30/13:00/13:30/14:00/14:30/15:00 JST**。両方式とも同じ `(session,decisionTime)` で eligible を確定し、**各回Top5**。同一銘柄の別時刻選出は別イベント。
- 価格: `decisionTime` までに確定・利用可能だった最後の継続市場価格（有効なterminal auctionを別扱い）。価格年齢0〜5分、正値必須。欠測/休止を0・前値補完・未来参照・別providerの無言代替で埋めない。
- 一次ラベル: 選出**後**から当日終了までの実観測・継続5分足の最大High。`100 * (maxFutureHigh / decisionPrice - 1)` を**符号つき**で集計。負の値を0でclipしない。5分足の開始時刻 `>=decisionTime` かつ利用可能時刻 `>decisionTime`。future path無しはUNKNOWN。
- 排他的bin: `0〜<1`, `1〜<2`, `2〜<3`, `3〜<4`, `4〜<5`, `>=5`。負側は `-1〜<0`, `-2〜<-1`, `-3〜<-2`…1%刻みで、観測された最小値まで出す。正負の境界は左閉右開。UNKNOWNは独立。
- 累積 `>=1/2/3/4/5%`、選出数、評価可能N、不明N、bin件数・割合、1decision当たりWinner数、session別、時刻別、セグメント別を出す。差分のCIは**同じsessionを単位にpaired cluster**して評価。
- 追加の**安定上昇リスク**: 選出後の将来LowからのMAE（負）、`MAE<=-1/-2/-3/-5%`、先に下落してから上昇した件数、将来の5分足Closeでの+1/2/3/4/5到達。OHLC内High/Low前後関係は推定しない。MFE clipped値を負側bucket計算に流用しない。
- 評価母集団: baselineとcandidateは全く同一 `(session,decisionTime,eligibleUniverseHash,labelVersion,priceBasis)`。同一ではない集計を性能差として比較しない。残る相違はselected symbolのみ。旧aggregateから新bucket件数を推測しない。
- Baseline A: `predict/research/phase57-long-only-frozen-selector-v1.json`、Freeze payload SHA `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59`。旧76-session 3,800件の+1/2/3/5累積値は参考表示のみ。Baseline B: Ark No.1.1 `10c94c92...` はEntry/Exit/Capitalの異なる統合系であり、Top5同一母集団ではない。無理に同一列に混ぜない。将来は20-session cash portfolioで別途比較。

## 使用したい因果特徴 family（固定機能群・現時点は性能未確認）

1. **日足**: 5日SMAを必須候補、10/20/25/50/60/75/100/120/200日線、各乖離/傾き/クロス、EMA、5/10/20/60日リターン、連騰連落、ギャップ、前日高安、ATR、RSI、MACD、Bollinger、Donchian、ADX、volatility、出来高/売買代金、終値位置・ヒゲ・ローソク形態、52週高安。
2. **分足**: 1/5/15/30/60分 momentum/SMA/VWAP、VWAP乖離/傾き、opening range、当日高安更新、pullback/reclaim/breakout/failure、トレンド効率、出来高加速度、出来高/売買代金の時間帯相対値、range/volume compression→expansion。
3. **市場横断**: 業種・市場セグメント・breadth、指数変化、セクター相対モメンタム、同時刻relative volume/turnover、market regime、流動性/気配スプレッド/約定難度（ソースに因果時刻証跡がある場合のみ）。
4. **銘柄性格/State**: PIT Dictionaryのvolatility/gap/continuation/giveback/drift/confidence、State9・State Path・transition。時点別の出力がある場合のみ。
5. **付加データ**: 決算/業績/配当/企業行動/材料/ニュース/板/歩み値/需給は、当時の公開・受信時刻・権利・coverageが証明できる場合のみ候補に入れる。ないものを合成しない。

「使える要素は全て」は未来情報・質の悪いデータ・存在しないサンプルを混入させる意味ではない。特徴量ごとに `source,availableAt,lookback,missingReason,quality` を持ち、欠損率・冗長性・ablationを記録して、全候補投入が本当に有利か検証する。実装初期に算出できるfeatureと後工程featureを明確に区別する。

## 学習（未実行）

- 独立学習する頭: +1/+2/+3/+4/+5将来High到達確率、MAE<=-1/-2/-3/-5確率、持続的上昇のproxy。**未来ラベルは学習時の教師と評価器だけ**。
- モデル案: 非線形ツリー系と正則化線形の事前固定少数候補。時間順FIT→SELECT→QUALIFYのPurged session split、train側のみ前処理/欠損統計/閾値決定/確率較正。label成熟・forward gapを守り、同日イベントをcross splitしない。symbol暗記に依存しない。
- 候補スコアはupsideだけでなくdownside riskを明示的に罰する。scoreの係数とrisk gateは開封前のDevelopment内でのみ確定。Top5のhit分布とMAE分布を同時に判定し、`>=3/5` Winner喪失・候補不足・高損失tailを監視する。未調整な固定重みを「確定最適」と呼ばない。
- negativeほぼ0という目標は、**各segment・各session・時間帯でのリスク帯の件数と信頼区間**を伴わなければPASS扱いにしない。

## データ・取得・露出Gate

現時点のGitHub原本 `docs/phase57-long-only-data-budget-and-dataset-split.md` に、J-Quants Light/Minuteの2026-10-06利用予定終了日とraw/derived purge条件の記録あり。**2026-10-12現在の契約継続状態は未確認**。手元にデータがあることと、再利用権・公開許可があることを混同しない。ユーザー添付2025年5〜8月のminuteファイルも、partitions/権利/PITが確認されるまで開封しない。

既存Developmentの再使用はE2 outcome-exposedと明記し、Fresh/OOSと称しない。既存REPORT/Validation/OOS/Common Holdout/Reserve/Prospectiveを勝手に開封しない。新規provider要求0。ライセンス・partition確認後の許可済みDevelopmentデータだけで初回実験する。成果はaggregate-onlyで、J-Quants原本・モデルへ復元可能なデータ・private行はpublic GitHubへpushしない。

## 終了点 / 進捗

- 独立research branch作成: DONE
- 契約と比較定義: DRAFT PRECOMMIT
- extractor / ranking / evaluator / synthetic tests: IN PROGRESS
- real market inputs/PIT/entitlement verification: BLOCKED
- 新model fit / 本番データ評価 / paired old vs new bucket表: NOT RUN
- Validation/OOS / 統合Entry・EXIT・Capital / live: NOT STARTED

研究branch作業は常時 `executionAllowed=false`, `brokerWriteAllowed=false`, `excelOrderWriteAllowed=false`, `rssOrderFunctionAllowed=false`, `liveTradingAllowed=false`, `paperTradingAllowed=false`, `automaticPromotionAllowed=false`, `productionUpdateAllowed=false`, `transmitted=false`。注文と本番接続0、main merge0、force push0。
