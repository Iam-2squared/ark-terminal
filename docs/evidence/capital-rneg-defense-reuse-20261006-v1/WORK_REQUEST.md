# 🛡️ Ark Terminal — RNEG Defense / 過去資産再利用・有限実験Work

文書ID: `ARK_CAPITAL_RNEG_DEFENSE_REUSE_V1_20261006`
作成実時計JST: `2026-10-06T08:51:38+09:00`
状態: `DESIGN_READY_NOT_EXECUTED`
Repo: `Iam-2squared/ark-terminal`
研究branch: `capital-main-reallocation-20261005`
設計時actual-GET HEAD: `0565369b3354afc2a454f261bccb3e44464e82da`
同tree: `696abacb7cf40dc668802369f568dabc838b101f`

## 0. 🎯 目的と今回の権限

**全Frozen Entryを対象に、現在の固定EXIT/EODで費用後RがマイナスになるEntryを、購入判断時点の情報で識別し、Capitalで買わずに済むかを検証する。**

U5/U10の内側だけを調べない。上昇余地の予測、新Winner順位、数量集中、EXIT改善は今回の主題にしない。損失ゼロは目標であって保証ではない。全件見送りで損失ゼロ、微損だけを減らして大きな利益を失う変更は成功にしない。

このWorkの出口は、既存資産の照合→接続→有限RNEG予測→過去だけで見送り条件を決定→必要条件が揃えば最大1つのDefenseをCapitalで検証→損失と最終資産の比較、まで。工程境界だけで確認待ちにしない。本書は別cycleとして下記の有限学習・1政策検証を許可する。旧Workの学習0／Replay0は当時の実績として保持する。

今回のDefenseの行動は **`PASS_TO_V5` / `VETO_THIS_ENTRY`** の2つだけ。PASSは安全宣言でも買い命令でもない。VETOは当該新規Entryを購入しない意味で、後から買うためのWAITではない。

## 1. 📌 設計前に確認できたこと

| 保存Evidence | 確認事項 | 今回の意味 |
|---|---|---|
| Full R Spectrum | 1,039 Entry、R known 1,016、不明23。負554・正462 | 既存R原値を再利用。全域分類を作り直さない |
| 旧V5購入台帳 | 150購入中、負82・正68 | fundedだけを学習すると選択偏りがある。全適格候補で学習し、購入集合でも別評価 |
| CORE_RUNTIME_CAUSAL | **1,600行**、27 numeric＋7 categorical | 1,039行はOOF側candidate stream。両者を混同しない |
| CORE feature manifest / projection | State9 current、主・局所方向、stop、dwell、15/30/60分の遷移・観測履歴、last3 connected stateが既存 | **State9を初めて導入する研究ではない** |
| Capital Quality v3 | **HL0は既に費用後return<=0を予測するL2 Logisticで、8fold学習済み** | 同一入力・同一モデル・同一目的の再fitを禁止 |
| HL0保存診断 | N=1,016、AUROC=0.5026450685、Brier=0.2630797970 | 旧損失予測は弱い。既に解けているとも、全手法で不可能とも解釈しない |
| FIRST ENTRY P1_Q70 Freeze | P0 price/volume/path/Selector context＋RC2 State9現在・過去履歴。P0 numeric110、P1 numeric148／categorical15 | 現行COREで省略された、購入前の価格・出来高contextの再利用候補がある |

これらは保存原本の事実。以下の新learner、見送り条件、実験予算は**今回の設計選択**であり、既存の認証値や最適値ではない。

## 2. 🔒 変更しない境界

Selector、Frozen FIRST ENTRY v2 P1_Q70、Frozen Structural EXIT v3、既存EOD／約定／費用契約、U/R原定義、MAX3、100株lot、LONG現物cash-onlyを保持する。V5はControlのまま。V5.1不採用、旧Quality v3・Reserve・Rank cutoff・MRET等の負結果を保存し、救済上書きをしない。

State9の9ID、RC2 profile、Pathの意味・窓・gap処理を変えない。State予測V6の不採用・未校正状態も保持する。現在のStateをRの将来方向と同一視しない。`DROPだから拒否`、`REBOUNDだから安全`等を名前だけで決めない。

禁止: Entry時刻・価格変更、EXIT変更、損切り追加、部分売却、買い増し、過去Entry復活、re-entry、同じ結果を見た後の候補追加・閾値救済。既存Rank／Reserve／配分式を緩める変更は含まない。

## 3. 📚 最短の原本回収と再利用

開始時に最新branchをreadし、basis以降の差分だけを確認する。次の系列を順に辿る。全repoや全ZIPを何度も探索しない。

1. `docs/evidence/capital-full-r-spectrum-20261006-v1/` のCURRENT_STATE、R contract、source binding、原R行、監査receipt。
2. `docs/evidence/capital-v51-reset20-r5r10-20261006-v1/` のR_LABEL_CONTRACT、RESET20、coverage、会計監査とprivate参照。
3. `research/capital-max3-top3-quality-v3-20261004-v1/` のtrain_heads.py、core_features.py、preprocessing.py、quality.py、および同名EvidenceのHEAD_QUALITY_DIAGNOSTICS／MODEL_HASHES／学習・OOF保存物。
4. `research/capital-max3-upward-staircase-v4-20261004-v1/` のcore_features.py／prepare.pyと、同名EvidenceのCORE_FEATURE_MANIFEST／SESSION_SPLIT。
5. Frozen Entry commit `4a2d6f35946b16820a13449a9288a6685a5c283c` の `research/persistent-watchlist-uptrend-first-entry-20261003-v2/CORRECTED_LINEAGE_FAST_FREEZE_20261003/`。FIRST_ENTRY_V2_FREEZE_HANDOFF、P1_Q70_ENTRY_CONTRACT、private原matrix／metadata参照を読む。
6. 既存State/Path・旧loss研究のregistryは、上記manifestから必要な依存だけ辿る。古い566特徴は別lineageなので、列数だけを理由に混ぜない。

重要な入力照合値:

| 入力 | SHA256 |
|---|---|
| CORE_RUNTIME_CAUSAL.jsonl.gz | `827abcf716c9203a70bc766783948a6be3cee3428abf6a772d1c3495096fd197` |
| UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz | `c446633dec923e3a80a534b19325ccff49f769a2ff1d29c7af1202202de614d4` |
| SESSION_SPLIT.json | `e83291b8706c48a4e496739219f1a645246b73be28f2195bebfaeb6614a12274` |
| CORE_FEATURE_MANIFEST.json | `3aa3abd322e239d27776dfde896d93e38c4e84602ddbf0f9d6a6451865ba55f2` |
| RC2 contract / profile | `45859122a62ccdc946b31bb5709f3fc080ea4a4f935958afd8f1ca895f75b6ff` / `77ee61ba1808a2c17614439fe7d14212a53cbfa7358c032ce16989eeb5248922` |
| State Path contract | `fc3808cb7d3d161e85527d7ebf97f902df7f0c3463457beddf1a25d053cee268` |

HL0の保存OOF・係数・preprocessor・train IDを回収し、同じ推論であることを確認してreuseする。旧HF1／MRET／MOVE系は目的が異なるため、RNEGモデルとして改名しない。

`REUSE_MATRIX.json`へ、資産、元target、as-of、現在Entryとの対応、過去成績、reuse／exclude／missing理由を1回保存する。既存HL0・新しいRNEGの違いが明記できなければ同じfitを始めない。

## 4. 🏷️ target、母集団、費用

原Rは `r = sell_credit / buy_debit - 1`。BUY1.0005、SELL0.9995、commission0の既存実効価格を用い、費用を二重控除しない。固定Structural EXITだけの別returnで置き換えず、現行Capitalの固定EXIT＋EOD経路に一致させる。

`y_neg = 1[r < 0]`、既知のr>=0は0。不明はnull。厳密0は別集計する。旧HL0は<=0なので、特にwarmupを含め0の有無・ラベル差を監査し、違いがあれば旧HL0を別targetのreferenceとして保持する。教師を上書きしない。

学習母集団は各foldより前の、固定Entry・費用契約でRが判明した実行適格候補。**U5条件、Rank通過、V5購入、将来source完備を入力条件として学習母集団を絞らない。** 実行適格性は既存の購入前契約で決め、教師が不明な行は学習／採点からのみ分離し、runtimeから消さない。

warmup20のRは既存TEACHERS_EVALUATION等から同契約の原値をreuseする。OOF側でcanonical Rとの一致、原debit／creditと費用を照合する。warmup原値が存在しない、または契約差が解けない場合、別EXITで補完・新市場Replayはしない。そのfoldはTRAINING_UNAVAILABLE、DefenseはOFFとして残す。後続foldは過去の確定原Rが足りれば実行してよい。

集計はALL_ENTRY、EXECUTION_ELIGIBLE、RANK_PASS、旧V5_FUNDED、各RESET20口座を分離する。1039、1016、492、150を同じ分母として扱わない。

## 5. ⏱️ 購入前情報の契約

predictionの時点は**現行Capitalが当該Entryの数量を確定する直前**。元Entryの発火を遅らせず、約定後情報をその判断へ戻さない。

joinは正確なEntry ID＋session＋symbol＋intent/fill時刻で行う。別watch・同銘柄別日・最も近い未来snapshotへの近似joinは禁止。各行へfeature_as_of、max_source_available_at、snapshot hash、model train cutoff、label maturityを保存する。

CORE projectionは既存コード上 `bar_end_minute <= fill_minute` のprefixを使う。この等号だけで実時間可用性を証明したことにはしない。固定イベント順で本当に数量決定前に読めるか確認する。fill価格／fill待ち時間／first_intent内の値も自動的にpre-buy扱いしない。取得時点が遅い列は、**原COREを変えずDefense入力projectionから除外**する。必須State prefix自体が遅いなら、その行はABSTAIN。

現在のhistorical actual arrivalはUNKNOWN。既存のassumed availabilityを継承した場合は、`HISTORICAL_ASSUMED_AVAILABILITY`と表示し、実受信PITやlive認証へ昇格しない。

現在Stateの正式9IDを使う。UP/DOWNは既存context/local direction、架空のRECOVERY IDを追加しない。UNKNOWN／CARRIED／INITIALIZINGを観測Stateへ変換しない。Pathのgap、昼休み、segment切替、pivot確認時刻は保存定義を継承する。

学習済みp1等のscoreをfeatureへ入れる場合、そのscoreを生成したmodelにも外側testの教師が入っていないことを辿る。OOFというファイル名だけでは合格にしない。依存関係を証明できない学習済みscoreは今回のXから外す。pP/U2/U3/MRETを結果に合わせてblend・反転することは禁止。

## 6. 🧠 新しい問いを2つの固定recipeだけで検証

今回の仮説は「State9を追加すれば勝てる」ではなく、以下の2つ。

- **D1 CORE_INTERACTION:** 既存State／Path／contextに、旧線形HL0が表現しにくい条件の組合せによるRNEG情報があるか。
- **D2 CORE_CONTEXT_INTERACTION:** COREに含まれていない、旧Frozen Entryで使用した購入前の価格・出来高contextを足すと、D1を上回るか。

| 役割 | 入力／処理 | 新fit |
|---|---|---:|
| B0 | 各foldの過去RNEG率を返す定数baseline | 0 |
| B1 HL0 | 既存保存モデルとOOFをそのまま使用 | 0 |
| D1 | 既存CORE 27 numeric＋7 categoricalのうちas-of確認済み列 | 最大8 |
| D2 | D1＋Frozen P0のnumeric110から同時点で直接reuseできる非重複列 | 最大8 |

D2用featureはFrozen P0列リストからmetadataだけで固定し、Rとの相関で選ばない。符号・期間・窓を新設しない。同時点の保存値または同じ凍結extractorと既存sourceからの機械的再構成に限定する。利用権・時間・単位が一致する列だけを入れる。元110全列が揃うと決め打ちしない。

D2が成立する条件は、追加列が1列以上あり、全8blockで実行適格行の90%以上について共通のas-of接続契約が証明できること。これは今回の運用上のcoverage下限で、性能の認証値ではない。未達なら**結果を見る前にD2をdisabled**と記録してD1を進める。大規模な旧データ復旧の待ち時間にしない。

D1/D2とも同じ固定小型learnerを使用:

```text
HistGradientBoostingClassifier
loss=log_loss, learning_rate=0.05, max_iter=100
max_leaf_nodes=7, max_depth=3, min_samples_leaf=20
l2_regularization=1.0, max_bins=255
categorical_features=None, early_stopping=False
warm_start=False, class_weight=None, random_state=57
```

numericは既存COREと同じ欠測値＋indicator、train-only変換。categoricalはtrain-only one-hot＋UNKNOWN。D2の追加列も同じ方法。native preprocessingを利用し、全期間でのscaler／category vocab／feature selectionはしない。行／銘柄ID、date ID、fold番号はXに入れない。

結果を見て深さ・葉数・正則化・class weight・seedを変更しない。自動ランダムvalidationを使わずearly stoppingを無効化する。環境の既存対応versionを固定し、version・全パラメータ・code hashを記録する。別learnerへこっそりfallbackしない。

D1/D2のfit前に、最低100既知training行・10既知session・両class各20行を要する。不足foldは定数予測＋Defense OFF。単変量のState表が良くなかったことだけで、事前固定したinteraction検証を中止しない。

## 7. 🧪 時間順OOFと学習量

元SESSION_SPLITの58 session／warmup20／OOF38／8blockを変えない。各blockのtrainはそのblock開始前だけ、testは元の5 session（最終3）。同じsession・Entryをtrain/testへ分割しない。学習にはそのcutoff以前に固定EXIT/EOD結果が成熟した行だけを使う。

「現在は過去の結果を知っている」と「当時の学習に渡してよい」は別。fit処理へtest教師payloadを渡さない。前処理、欠測処理、推定、モデル選択、見送り閾値の全段階でこの境界を守る。

各model/blockのpredictionは**初回の未来向き推論**を保存し、後から新modelで過去を採点し直してOOFにしない。先行blockで作ったOOFを、後続blockの見送り条件選定に再利用するため、新inner fitは不要。warmupのin-sample予測はその選定に使わない。

D1/D2それぞれ最大8 fits、合計最大16。HL0 refit0、旧Entry/State/EXIT model fit0、full-data最終fit0。これは新しいRNEGモデルの有限予算であって、全工程のfit0とは報告しない。

同じ市場期間は反復利用済みDevelopment。precommitや時間順OOFを行ってもFresh/OOSに戻らない。State定義・旧Entry選択がこの期間に影響を受けたexposureも残す。

## 8. 🚫 「負けそうだから全部拒否」を防ぐ見送り条件

modelの出力はRNEG risk scoreとして扱い、0.8なら損失確率80%と無条件に宣言しない。単純な0.5 cutoffで全体の過半を拒否する設計にはしない。

各block開始時に、**それ以前のblockで初回OOF予測が保存され、Rが成熟したrank-pass／実行適格行だけ**を`CAL_PAST`とする。モデルごとに作る。現在blockの予測分布・R・未来到来数をCAL_PASTへ入れない。

本書で新たに定める見送りの研究用誤拒否予算:

| 条件 | 固定値／式 |
|---|---|
| CAL_PAST support | 100行以上、10 sessions以上、負／非負が各20行以上 |
| 見送り群support | 20行以上、5 sessions以上 |
| 正の取引の誤拒否率 | 正Rを見送る件数／CAL_PASTの正R件数 <=10% |
| 正利益の巻込み | 見送り群のsum(max(r,0))／CAL_PASTのsum(max(r,0)) <=10% |
| 見送りprecision | 見送り群のRNEG率 > 同じCAL_PAST全体のRNEG率 |
| 見送り群の純価値 | `sum(-r for rejected rows) > 0` |
| 単一session依存の点検 | 見送り群から任意1sessionを除いても上の純価値が0以上 |

10%は将来保証でもユーザーが指定した値でもない。今回は利益を全消去しないために事前固定する研究用上限。全期間の結果で緩めない。RN tailやR5に別の都合のよい閾値を追加しない。

**閾値学習を以下の1手続きに限定する。** 各modelのCAL_PASTに存在するdistinct risk scoreを候補tauとして、`score >= tau`の群を同順位まとめて評価する。上記全条件を満たす組の中で、負Rの回避recall最大→precision最大→tau最大→固定model順D1/D2、の辞書順で1組を選ぶ。現在block中はmodelとtauを固定する。

これは過去学習領域だけでの有限閾値・model選択を明示的に許可する設計であり、「閾値選定をしていない」とは報告しない。学習するのは2つの固定recipeとこの1つの選択手続きだけ。各tauで新fitやCapital Replayを回さず、全期間OOFを見て最良tauを1個選ぶことも禁止。

条件を満たす組がなければ、そのblockは`DEFENSE_OFF`。第1blockは過去OOFがないため必ずOFF。OFF期間を成績から除かない。HL0は比較用で、結果を見て3番目の配備候補へ追加しない。

ここでの純価値は同額notional当たりの保存単体returnの比較にすぎず、資金回転を含む新Portfolio利益ではない。正利益を10%以内に抑えたとしても、実数量では損害が大きくなる可能性を残して検証する。

## 9. 📊 予測とDefenseの評価

全OOF結果を固定後、ALL eligible、rank-pass、旧V5 fundedで以下を別表にする。source不足・prediction不足は分母から黙って落とさない。

- RNEG AUROC、average precision、Brier、log loss。B0とHL0を同じmaskで比較。baselineの率も過去だけで算出する。
- RNEGをどれだけ拒否したか、拒否precision、残した群のRNEG率、正R誤拒否率、実際のnon-veto coverage。
- RN1/RN3/RN5/RN10の回避、正側の0〜1／1〜3／3〜5／5〜10／10%以上の巻込み。
- 旧V5と各reset口座の保存数量で、静的に見送る損失額、同時に捨てる正PnL、両者の差を分離する。

`static_removed_loss`を「実際に回避できた損失」と呼ばない。見送り後はcash、数量、後続購入が変わる。単純な旧損失額の足し引きでnew final equityを作らない。

「買う件数を減らせば損失件数は減る」だけで終わらせない。同じblock×native rankで同数を無情報に見送った場合の期待負件数と期待損失・利益除去を計算し、Defenseとの差を示す。これは保存台帳のanalytic referenceで、新しい無作為Portfolio Replayはしない。

8block別、session別、全symbolの対称leave-one-outによる保存寄与の依存度を示す。無数のState×閾値を探索して良いsubsetだけを報告しない。旧全R 56bucket・元AUC一式を再生成せず参照する。

## 10. 🔧 条件付きCapital検証：変更は購入拒否だけ

以下が揃えば確認待ちを挟まず、研究候補`V5_RNEG_DEFENSE_V1`を1つだけ実装・検証する。

- source/as-of/label/OOF境界・見送り条件の監査がPASS。
- 少なくとも1blockで過去だけからDefenseがactiveになり、旧V5の保存購入へ実際のVETOがある。
- 第8節の手続き、全blockのpolicy snapshot、code hashを結果調整なしで保存済み。

aggregate AUROCが低いから別headを追加する、全OOFのPnLを見てmodelを選び直すことはしない。activeなしなら`NO_ACTION`で終了し、同一V5の無意味なReplayはしない。

処理順:

```text
同時刻に可用となった既存SELL／cash release
→ 現在のFrozen Entry batch／元の安定順序
→ 元のcutoff・admission・入力・same-symbol検査
→ Defense: VETOなら当該Entryを除外、PASSなら継続
→ 元のV5 occupancy/Reserve gate
→ 元のV5 allocationで整数数量を再計算
→ BUYを会計へ記録
→ 固定EXIT/EODを追跡
```

VETOしたEntryはpickedにも仮のslot数にも入れない。残った候補に対するV5 cap、target、配分式、Reserve表を変更しない。同batchで空いた資金を恣意的に強制再配分しない。VETO後にV5自身の式が返す数量差は許容し、必ず記録する。

旧V5の150購入IDをruntime whitelistにしない。新口座状態で後続の合法なEntryが買える場合は、同じDefense＋V5を適用する。過去の見送りEntryは復活させない。将来EXIT source不足を知って現在の候補を除外しない。

予測不能・正当な欠測・未知categoryでリスクを確定できない場合は`ABSTAIN/PASS_TO_V5`。これは安全認定ではない。schema/hash破損等の整合性異常は測定をBLOCKEDとし、通常のPASSで隠さない。

## 11. 💴 RESET20：損失減少と最終資産を同時に測る

既存RESET20 wrapper、calendar、窓ID、会計をreuse。各窓は100万円・保有0から始め、20営業日内を閉ループで追跡する。口座状態だけをresetし、歴史時点の学習model・OOF履歴・policy snapshotはresetしない。

元の予定21窓、完了可能9窓、coverage不明12窓を全て表に残す。同じ条件のV5保存結果はreuseし、新Controlの全Replayは0。新Defenseだけ最大1正式batch、現状9窓なら180日評価。新しく未決済になった窓は測定不能として残し、片側完了を都合よくpaired比較へ入れない。

7/11・7/14を0-returnで埋めない。このWorkはcoverage再調査を主題にせず、既存未解決を保持する。12窓を外した9窓だけの結果で全期間・普遍的な月次性能を認定しない。

| 必須比較 | V5 | Defense | 差 |
|---|---:|---:|---:|
| 負取引数／全購入数、負率 | 保存 | 新測定 | 差 |
| 負PnL絶対総額／RN tail損失 | 保存 | 新測定 | 差 |
| 正PnL総額／誤拒否した正取引 | 保存 | 新測定 | 差 |
| 最終資産 Min／Mean／Median／Max | 保存 | 新測定 | 差 |
| 最終資産200万円到達数 | 保存 | 新測定 | 差 |
| MaxDD／購入N／cash／slot利用 | 保存 | 新測定 | 差 |
| 予定／完了／片側未完了／coverage不明 | 全件 | 全件 | 差 |

V5-only、共通購入、Defense-onlyのEntryを分け、共通購入は数量差も分ける。損失率が下がっても、残った大Loserへの増額や新たなLoser購入で損失額が増えていないか確認する。

各窓の会計式 `ending_cash = initial_cash + sum(actual_trade_pnl)` を、全決済と原BUY/SELLから独立再構成する。tradeのRは費用後であること、cashはSELL前に解放しないこと、same-time順序、MAX3／lot／cash制約を新経路で検算する。

## 12. ✅ 結果判定：識別・防御・資産を分ける

| status | 意味 |
|---|---|
| `BLOCKED_SOURCE_OR_ASOF` | 原本・時点・targetの必要条件が不足。可能な独立部分は完了 |
| `RNEG_NO_INCREMENTAL_SIGNAL` | 今回の有限recipeでは有用な追加情報を確認できない。全手法で不可能とは言わない |
| `RNEG_SIGNAL_ONLY` | 識別の改善はあるが、見送りsupportや経済条件が不足 |
| `DEFENSE_NO_ACTION` | 過去だけで決めた条件は全blockでOFF、または購入への差分0 |
| `DEFENSE_LOSS_REDUCED_WEALTH_NOT_IMPROVED` | 負取引／損失は減ったが最終資産が改善しない。配備はしない |
| `DEFENSE_DEVELOPMENT_PROGRESS_PARTIAL` | 同じ完了窓で損失額と負率が下がり、中央値が上がり、平均も下がらない。部分Development結果として保持 |
| `DEFENSE_REJECTED` | 損失または資産が悪化、あるいは検証不成立 |

中央値差とpaired差の中央値は別に報告する。最高額だけの上昇は個別改善として残してよいが、全体改善へ昇格しない。0件購入やわずかな取引での「負け0」は根拠十分なDefense成功にしない。取引数・期間・巻込みを必ず併記する。

今回良くてもproductionReady=false、V5自動置換なし。採用判断に必要な未解決coverage／独立確認を明示する。Defense研究を優先するが、最上位目的の100万円→約200万円／20sessionsは変更しない。

## 13. 🔍 必須の最小監査

原監査を巨大な件数で繰り返さず、新しい接続と意思決定経路に絞る。

1. label r=0／正負境界、旧HL0<=0との差、unknown非混入、実効費用1回。
2. Entry identity 1対1、schema、source hash、COREと追加contextの時刻整合。
3. 未来suffix／現在blockのR／将来arrival／将来EOD可用性を変更しても、既に作った現在predictionとVETOが不変。
4. train-only preprocessing。各fitのtrain IDs、ラベル成熟、学習済み入力の依存graph。in-sampleをCAL_PASTへ混入しない。
5. CAL_PASTから現在／未来blockを確実に除外。同scoreのtie、ゼロ分母、support不足、all-PASSを検算。
6. D2欠測で有利な行だけが採点されないこと。missingとunknown labelを別maskにする。
7. Defense OFFのsyntheticでnative V5と一致。市場互換性は必要なら既存最初の1日だけ、全Controlを再走行しない。
8. VETOで仮slotを消す、後続Entryへ同じDefense適用、購入済みpositionのEXITを変えない。
9. 独立会計、共通／追加／消失取引と数量差の照合、全予定窓と失敗履歴の保存。

## 14. ⚡ 予算と停止しない進め方

| 処理 | 上限 |
|---|---:|
| HL0／旧head refit、State/Entry/EXIT fit | 0 |
| D1新fit／D2新fit | 各8、最大16 |
| hyperparameter／feature／seed探索 | 0 |
| 新calibration model fit | 0 |
| 過去OOF閾値・model選択 | 第8節の1手続き、各外側blockにつき1回 |
| 凍結featureの機械的補足生成 | 1 batch、元State定義の再研究0 |
| Rの市場／EXIT再materialization | 0 |
| 新Capital候補／正式Replay | 1／1 batch |
| V5全Control Replay | 0、保存結果reuse |
| 追加技術fit再試行 | 最大2。入力・target・recipe不変の技術障害だけ |
| 正式Replay技術再起動 | 最大1。成績を見た救済不可 |
| provider市場価格取得／protected開封／注文／main merge／force push | 全て0 |
| Claude | 原則0。争点が残れば必要性だけ報告し、自動送信しない |

D2入力の回収中はD1のas-of監査と合成テストを進める。fit待ち中は会計テスト、report枠、保存処理を進める。互いのoutcome境界を壊して並行化しない。依存のない部分を先に完了し、1件の不足で全工程を停止しない。

新しいlearner追加、第三recipe、別target、別gate、v5.3、EXIT改変へは進まない。十分な根拠が出ない場合は、原因と次の必要情報を具体的に残して有限終了する。

## 15. 📦 成果物・GitHub・報告

新cycle例: `capital-rneg-defense-reuse-20261006-v1`。既存同名cycleがあれば内容を照合し、無断上書きしない。

成果物はWORK_REQUEST、REUSE_MATRIX、SOURCE_BINDING、FEATURE_ASOF_CONTRACT、FEATURE_JOIN_COVERAGE、RNEG_TARGET_BINDING、MODEL_AND_POLICY_PRECOMMIT、FIT_LEDGER、初回OOF predictions、PAST_QUALIFICATION、各block policy snapshots、LOSS_DEFENSE_DIAGNOSTIC、必要ならRESET20結果と独立会計、CURRENT_STATE、MANIFEST、REPORT-ja.md。private Entry/symbol別台帳・model原入力は既存private保存先へ分離する。

開始、入力・設計固定、OOF完了、policy固定、Replay／最終の重要checkpointに、実時計JST、basis HEAD/tree、完了、未実行、blocker、counts、次の方針を保存する。commit後にactual GETで本文・blob/tree・branch HEADを確認。receiptを再帰的に増やさない。

REPORT冒頭は次だけで読めるようにする。

**旧HL0から何を変えたか → 購入前に何件のRNEGを識別できたか → 誤って何件・何円の利益を捨てたか → 実口座経路で損失額と最終資産はどう変わったか。**

数値は表、必要な図はRNEG回避と正利益巻込み、block別incremental skill、開始日別資産比較。未実行の図や仮成績は作らない。全R再集計を新成果として水増ししない。

## 16. 📎 設計根拠と参考の区別

[S1] basis HEADの `docs/evidence/capital-full-r-spectrum-20261006-v1/REPORT-ja.md` と `reviews/RECEIVED_REVIEW_20261006_080843-ja.md`：R分布、資金損失、score両側tail。

[S2] 同HEADの `research/capital-max3-top3-quality-v3-20261004-v1/train_heads.py`、同名Evidenceの `HEAD_QUALITY_DIAGNOSTICS.json`：HL0のtarget／学習済み8fold／AUC。HL0が新規という過去会話の含意は本書で訂正する。

[S3] 同HEADの `research/capital-max3-upward-staircase-v4-20261004-v1/core_features.py`、CORE_FEATURE_MANIFEST／SESSION_SPLIT、および受領Quality private dependency：既存State/Path入力、1,600行とOOF1,039行の区別。

[S4] Frozen Entry commit `4a2d6f35946b16820a13449a9288a6685a5c283c` のFIRST_ENTRY_V2_FREEZE_HANDOFF：State9は既に使用済み。P0/P1入力数は接続候補の所在であり、今回全列を利用可能と認証した値ではない。

[S5] `Ark_Terminal_NEW_CHAT_HANDOFF_After_V6_20261002(1).zip` の01_CURRENT_STATE_HANDOFF：State R2 signal未再現のclosureと、causal representationを別目的で検証する許容。旧反転予測の成功を前提にしない。

[S6] scikit-learn公式のHistGradientBoostingClassifier、Common pitfalls、decision-threshold tuning文書を実装参考として確認。train/test分離、train-only前処理、閾値を評価データで選ばない原則を利用。今回のモデル数値、10%誤拒否予算、support条件、配備手続きは本書独自の研究設計であり、公式文書やArk過去実績の推奨最適値ではない。

## ▶ Workへの実行文

本指示書を実行してください。全Entryの費用後R<0回避に集中し、既存State9/Pathと学習済みHL0を先にreuseしてください。同じHL0を再fitせず、固定2recipeまでのRNEG検証を時間順に実施し、購入見送り条件は過去の初回OOFだけから決めてください。条件が成立すれば確認待ちを挟まず最大1つのDefenseをV5へ接続し、RESET20の損失額・正利益巻込み・最終資産まで測ってください。Selector／Entry／EXITは完全凍結。新価格取得・保護データ開封・発注は0。途中の失敗と未実行を保持し、現在地・方針・実時計をGitHubへ保存、読み戻しまで完了してください。

END_OF_WORK_REQUEST
