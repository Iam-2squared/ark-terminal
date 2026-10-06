# 🛡️ Ark Terminal — Capital 第1審査：Entry→EXIT 符号専用フィルター

文書ID: `ARK_CAPITAL_SIGN_ONLY_FILTER_STAGE1_V1_20261006`  
設計記録JST: `2026-10-06T10:25:50+09:00`  
状態: `DESIGN_READY_NOT_EXECUTED / FILTER_ONLY`  
Repository: `Iam-2squared/ark-terminal`  
研究branch: `capital-main-reallocation-20261005`  
設計時actual GET HEAD: `6f3a09e4800a1cccbf359364c9acc9ba1f05e8dc`  
同tree: `ba69773ee6331acfd426e90d0a8ab17db3785bdc`

## 0. 🎯 今回の目的・権限・終了点

**固定Entryから固定EXIT/EODまで通した費用後結果が、プラスかマイナスか。この正負を、購入前情報から識別するCapital側の第1審査だけを研究する。**

Selector／Entry／EXITの良し悪しを再評価するWorkではない。すべて完全Freeze。全市場銘柄ではなく、Frozen Entryが実際に発した候補を受け取り、その候補をCapitalが二次審査する。

今回、教師・学習損失・特徴群の比較・閾値選定・合否はすべて正負の二値だけを使う。利益額、利益率の大きさ、R1〜R10、RN tail、U5/U10、MFE/MAE、投下額、数量、最終資産を判定へ混ぜない。正負件数、正負の正解率・誤分類率・保存率は使用する。

| 今回行う | 今回行わない |
|---|---|
| 正負だけの教師view、入力再利用、固定された特徴群比較 | 大・中Winnerの強度分類、正利益の金額保護 |
| 時間順の学習・初回OOF予測、符号だけの閾値決定 | 損失額・平均R・期待収益でのモデル／閾値選択 |
| フィルター単体の混同行列と通過／見送り件数 | V5への接続、Replacement研究、数量配分変更 |
| 検算、結果・現在地・次方針の保存 | Capital／RESET20 Replay、発注、本番昇格 |

**良い結果でも、このWork内では第2審査とCapital接続へ進まない。** 終了点は第1審査の性能表・限界・再現可能なモデル／予測／閾値成果物。工程区切りでは確認待ちにせず、この範囲を一括完了する。

本書は新しい限定研究cycleの設計である。旧RNEG Defenseの「条件成立なら自動Capital Replay」「正利益10%金額保護」「見送り群の純価値>0」は今回に持ち込まない。旧実験の不採用結果は変更しない。

## 1. 📚 開始時の照合と重複防止

最新branchをactual GETし、上記HEAD以降に進行中の同等Workがないか差分確認する。元の失敗実験、source binding、モデル、教師、as-of監査を最初に再利用する。

優先原本は以下。存在しない下位ファイル名を推測せず、各MANIFEST／設定／コードから実パスを解決する。

1. `docs/evidence/capital-rneg-defense-reuse-20261006-v1/` のREPORT-ja.md、CURRENT_STATE.json、MANIFEST、入力設定、学習台帳、初回OOF保存先。
2. `research/capital-rneg-defense-reuse-20261006-v1/` のprepare_rneg.py、fit_rneg.py、rneg_io.py、audit_oof.py。旧rneg_policy.pyの金額条件は使用しない。
3. `docs/evidence/capital-full-r-spectrum-20261006-v1/` と `docs/evidence/capital-v51-reset20-r5r10-20261006-v1/` の固定R／EXIT＋EOD契約、Entry identity、費用・unknownの原本。
4. 既存HL0系列、CORE_FEATURE_MANIFEST、SESSION_SPLIT、および上記から参照されるFrozen P0／P1の特徴量・OOF score原本。

今回の設計前にGitHubで確認した既存結果:

| 項目 | 保存結果 |
|---|---:|
| CORE全期間 | 1,600行／58 sessions |
| warmup既知教師 | 544行 |
| OOF全Entry | 1,039行 |
| OOF正負が既知／不明 | 1,016／23 |
| OOFマイナス／プラス／厳密0 | 554／462／0 |
| 実行適格候補 | 1,028行、既知1,016 |
| Rank通過 | 494行、既知492 |
| 旧V5購入 | 150行、負82／正68 |
| 旧HL0／D1／D2の全既知RNEG AUROC | 0.502645／0.529334／0.521678 |

これらは原本照合用で、新しい学習結果ではない。不一致なら理由を保存し、件数を合わせるための削除・補完をしない。

**旧HL0／D1／D2は既に正負を学習していた。** 「今回初めてプラマイ教師を作る」「正負だけにすれば予測力が出る」と説明しない。今回の新しい検証は、情報群を分離して比較すること、符号だけの読出し条件に統一すること、Capitalの口座変化から切り離すこと。

同一target、同一Entry ID・training mask、同一入力値・列順、同一前処理、同一learner設定・versionに一致する学習済みモデル／初回OOFがあれば、そのままreuseする。名前だけ変えた再fitは禁止。異なる特徴群の比較は「情報群の除去・追加を検証する別構成」と明記する。

## 2. 🏷️ 正解ラベルは符号だけ

固定原本の `sell_credit` と `buy_debit` をFraction／Decimalで比較する。既存の実効価格・費用を継承し、費用は1回だけ。Structural EXIT単体の別returnへ置き換えず、現行の固定EXIT＋EOD経路を教師の権威とする。

| 原本の比較 | 教師status | y_neg |
|---|---|---:|
| sell_credit > buy_debit | POSITIVE | 0 |
| sell_credit < buy_debit | NEGATIVE | 1 |
| sell_credit = buy_debit | EXACT_ZERO | null |
| 固定決済結果を確定できない | UNKNOWN | null |

厳密0はプラスにもマイナスにも入れず、独立件数として保存する。unknownと0は別物。微小な正負を丸めて0にしない。費用分だけの小さなマイナスもマイナスの1件として保持する。

**小さなプラスも大きなプラスも同じ1件。小さなマイナスも大きなマイナスも同じ1件。** sample_weightは全行1、class_weightなし。R絶対値、損益円、株数、過去購入額、Winner強度に応じた重み付けは0。

教師builderだけが原debit／creditを読み、学習・閾値・評価へ渡すviewは次に限定する:

```text
entry_id / session / sign_status / y_neg / label_maturity / source_hash
```

連続R、損益額、U/R階層、実EXIT理由、将来保有時間、将来High/Lowをこのviewへ渡さない。学習・選定・判定器は符号view以外のoutcomeファイルを読まない。

購入前の価格・出来高などの入力数値は利用してよい。「結果の大きさを使わない」という指定であり、入力まで符号1bitにする指定ではない。

## 3. 🧭 母集団と判断時点

主対象は `FROZEN_ENTRY_EXECUTION_ELIGIBLE`。元の購入前条件で実行適格なEntry出力を、Rank／Reserve／保有枠／資金配分による選別より前の第1審査へ渡す。全市場、全Selector watch、Entry未発火の行へ母集団を広げない。

全過去の実行適格・確定教師を学習へ利用し、旧V5購入150件だけに限定しない。これは購入済みのものだけへ過適合しないためであって、全候補を買う設計ではない。実際の説明も「Entry候補を二次審査する」と表現する。

| 評価集合 | 扱い |
|---|---|
| 実行適格なFrozen Entry | 学習・閾値履歴・第1審査評価の主母集団 |
| ALL_ENTRY | 不適格・UNKNOWNも含めたcoverage管理 |
| Rank通過、旧V5購入 | 同じ予測・同じ閾値の補助slice。別チューニングしない |
| RESET20の重複購入行 | 学習／符号評価へ入れない |

予測時点は旧RNEGと同じ、元fill時刻の購入直前・数量確定前。閉じたState prefixとFrozen first-intent snapshotのみを継承し、Entryを遅らせない。fill raw open quoteは旧V5の可用性仮定を明記する。fill足H/L/C/volume、未来のEXIT可用性は入力不可。

`feature_as_of <= t_decision` と、sourceがその順序で利用可能であることを別々に確認する。actual arrivalが不明な限り `HISTORICAL_ASSUMED_AVAILABILITY` を維持し、実受信PIT認証へ昇格しない。

## 4. 🧩 4つの入力構成を事前固定する

同じlearnerで次の4構成だけを比較する。全体結果を見て「効いた特徴」を選んでから統合することは禁止。統合構成も最初から固定する。

| ID | 入力 | 役割 |
|---|---|---|
| SF_A_PRICE | Frozen P0の価格・出来高・VWAP・ボラティリティ・価格経路・時刻等、非State・非学習scoreの既存列 | 価格／出来高情報単独の比較 |
| SF_B_STATE | COREのState9、Path、遷移・方向・dwell・stop・gap／観測情報の既存列 | State／Path情報単独の比較 |
| SF_C_SCORE | 購入前の既存学習score・Selector score/contextの監査済み列 | 既存予測情報単独の比較 |
| SF_D_UNION | 利用可能と事前認証したA＋B＋Cの和集合、重複列は1回 | **唯一のPrimary構成** |

AにはState以外の価格経路の形状を含めてよい。Bの状態IDに「安全」「負け確定」といった意味を付けない。COREの名前だけで全列をBへ入れない。学習済みscoreと機械的な観測特徴は分ける。

Cの追加回収候補は既存CORE内のP1 scoreと、保存済みpP／MOVE_U2／MOVE_U3／MRETに限定する。HL0／旧D1／旧D2は比較対象であり、今回のCへ積み重ねない。未来Uラベルを入れることと、購入前に生成済みのpPを入力することは区別する。

使用する列・所属群・時間・producer・元定義・重複除去を `FEATURE_FAMILY_MAP.json` へ固定する。群分けは元metadata／生成コードの意味で決め、正負との相関やOOF成績で決めない。所属不明列はUNRESOLVEDとして除外し、都合よく再割当しない。

旧P0の108追加列の接続receiptを再利用する。古い566列を一括混入しない。新しい指標・期間・Path pattern・銘柄embeddingは作らない。利用可能な旧特徴値を読む／joinすることだけを許可し、新しい市場feature生成batchは0。

### 学習済みscoreの二段利用

Cのscoreは行ごとのproducer cutoff／train IDが辿れ、外側testの教師がproducerに入っておらず、その行の時点で生成可能なものだけ使用する。単にOOFというファイル名で通さない。

warmup時点にscoreが存在しなければ欠測のまま。未来で学習したproducerでwarmupを再採点したり、in-sample scoreをOOFへ代用したりしない。既存producerの新fitも0。

正当な欠測はindicator付きで保持し、行を落とさない。時点を証明できない列は、outcome比較前に列ごと除外する。Cが全部不成立ならCをdisabled、D=A+Bとして固定する。AまたはB自体が成立しなければPrimaryはBLOCKED、成立部分の診断だけ完成させる。

A/B/C/Dの配列・列順・入力maskを確定してからmodel実験を開始する。C回収は既存manifest参照→指定保存先1回→不足receiptまで。見つかるまで全repoを繰り返し探さない。

## 5. 🧠 learnerと再利用予算

モデルfamily自体の探索を避け、旧D1/D2と同じ小型HistGradientBoostingClassifierを使う。変更するのは事前固定した入力群と符号専用の閾値読出しだけ。

```text
loss=log_loss
learning_rate=0.05
max_iter=100
max_leaf_nodes=7
max_depth=3
min_samples_leaf=20
l2_regularization=1.0
max_bins=255
categorical_features=None
early_stopping=False
warm_start=False
class_weight=None
random_state=57
sample_weight=None
```

旧fit_rneg.pyのtrain-only前処理を継承する。numericは欠測0＋欠測indicator、標準化はtrainのみ。categoricalはtrain vocabulary＋UNKNOWNのone-hot。numericのみ／categoricalのみの群に対応するshape処理だけをadapterで補い、意味を変えない。

全候補で同じtarget、split、training eligibility、前処理規則、learnerを使う。新しい学習量の最大は4構成×8fold=32。入力署名が旧D1/D2等と完全一致する構成・foldは保存OOFをreuseし、新fitを減らす。機械的な符号ラベルview変更だけでは再fit理由にしない。

特にSF_Dが旧D2と一致したら、その8fitは必ずreuseする。C追加がない場合に同じD2を新しい統合モデルと称して再学習しない。単にy_negをy_posへ反転する再fitも禁止。

比較用にB0過去負率、旧HL0、旧D1、旧D2を保持する。旧OOFが回収できないものは未取得とし、穴埋めの再fitをしない。

## 6. ⏱️ 時間順学習と初回OOF

元SESSION_SPLITの58 sessions／warmup20／OOF38／8blockを維持する。各blockの学習はその開始前に結果が成熟した過去の正負だけ。ランダム行分割、同sessionのtrain/test混在、未来score依存を禁止する。

最低training supportは既知100行、10 sessions、正負各20行。足りないfoldは過去率baseline＋MODEL_UNAVAILABLEとし、比較表から消さない。strict0とUNKNOWNを追加標本にしない。

各foldで、前処理fit→モデルfit→当該blockの全Entry予測→予測hash保存→判定出力保存、の後に評価用の当該block教師を結合する。未来教師をfit関数へ渡さない。既存OOFをreuseするときも元の初回推論lineageを継承する。

今回も反復利用済みDevelopmentである。新しいprecommit・別ラベル名・時間順OOFによってFresh/OOSへ戻ったとは言わない。既知の旧成績から本設計を作ったexposureを保存する。

## 7. ⚖️ 二値予測とフィルターを区別する

モデル出力は `score_neg`。大きいほどマイナス側という向きを固定し、AUCが悪かった構成だけ後から符号反転しない。未校正なので「0.8なら必ず80%で損失」と解釈しない。

### 7.1 純粋なプラマイ予測

```text
score_neg >= 0.5 → PREDICT_NEGATIVE
score_neg <  0.5 → PREDICT_POSITIVE
```

この固定0.5判定について、正負の混同行列・accuracy・balanced accuracy・各class precision/recallを必須表示する。後述の見送り閾値で結果が変わっても、この表を隠さない。

### 7.2 見送り強度の3つの固定表示

| 表示 | 過去OOF内の正例誤拒否予算alpha | 位置づけ |
|---|---:|---|
| 保守 | 5% | 比較用 |
| 標準 | **10%** | **Primary** |
| 強 | 20% | 比較用 |

これは正例の**件数**の予算であり、利益金額ではない。将来でも同じ率を保証するものではない。過去の発言にあった仮例「負率30%」等を、達成済みの値や自動選定条件にしない。

3点とも同じ保存scoreから計算し、追加fitはしない。結果を見て主判定を5%や20%へ変更しない。

## 8. 🚫 閾値は過去の正負だけから1手続きで決める

構成ごと・blockごとに、以前のblockの初回OOF予測があり、符号が成熟した実行適格行を `CAL_PAST` とする。Rank通過やV5購入だけへ限定しない。現在／未来block、warmup in-sample予測は入れない。

最低supportは100行、10 sessions、正負各20行。足りなければそのblockのフィルターはOFF／ALL_PASS。モデルの二値予測は別に採点する。

各alphaで次を実行する。

1. CAL_PASTにあるdistinctなscore_negを小さい順に並べ、末尾にALL_PASS sentinelを加える。
2. 各tauに対して `score_neg >= tau` をREJECT、それ未満をPASSとする。同scoreは全部同じ側に置き、銘柄IDや未来順位で分割しない。
3. `REJECTされた実POSITIVE数 <= floor(alpha × CAL_PASTの実POSITIVE数)` を満たす**最小のtau**を採用する。該当する有限tauがなければALL_PASS。
4. tauを現在blockの予測分布・教師を見る前に保存し、block中は変更しない。

これにより閾値は過去正例の誤拒否件数だけで定まる。負例の大きさ、期待損益、正利益巻込み額、全期間の最良recallで選ばない。有限閾値選定をしている事実と試したdistinct数は保存する。

モデルごとにtauを求めるが、PrimaryはSF_D＋alpha10%で固定。過去成績を使ったモデル切替も、今回は追加しない。各群の違いを混ぜず観測するためである。

標準の結果が悪いときに、旧D1やSF_Aへその場で採用先を変更しない。別構成の良い結果は次設計の材料として保存し、このcycleのPrimary成功へ付け替えない。

## 9. 📊 合否に使う量はすべて符号件数

実際の正負を行、フィルターの出力を列にする。

| 実際のEntry→EXIT結果 | PASS側 | REJECT側 |
|---|---:|---:|
| POSITIVE | P_keep | P_reject |
| NEGATIVE | N_keep | N_reject |

```text
プラス保存率       = P_keep / (P_keep + P_reject)
プラス誤拒否率     = P_reject / (P_keep + P_reject)
マイナス除去率     = N_reject / (N_keep + N_reject)
通過後マイナス率   = N_keep / (P_keep + N_keep)
見送りprecision    = N_reject / (P_reject + N_reject)
通過率             = (P_keep + N_keep) / 全正負既知N
J_sign             = マイナス除去率 - プラス誤拒否率
filter balanced accuracy = (マイナス除去率 + プラス保存率) / 2
```

分母0はnull。全見送りなら通過後負率0%とは表示しない。OFF／判定不能はPASS_UNASSESSEDとして運用coverageへ残し、既知符号は主表のPASS側に含める。別欄でその件数を示し、予測POSITIVEと呼ばない。

Primaryは全38 OOF sessionsの同じ実行適格集合。初期OFF期間も含む。ACTIVEだけの補助表は作ってよいが、良く見える方へPrimaryを切り替えない。予測欠落、教師unknown、不適格はそれぞれ別件数にする。

AUROC、正負それぞれのAP、Brier、log loss、balanced accuracyも同じ符号だけで算定する。金額加重、tail優先採点は0。B0のscoreがfoldで変わるためpool AUROCが0.5と一致するとは限らない。all-positive／all-negativeの無情報判定も参考表示する。

各8blockの同じ表を保存する。符号の識別差が特定blockだけへ依存していないかを調べる。任意の不調session・銘柄を除いた成績を主成績にしない。

## 10. ✅ 事前の終了判定

今回の閾値・support・到達目安は新しい設計選択であり、統計的保証や過去の最適値ではない。

| 状態 | 判定 |
|---|---|
| SIGN_FILTER_BLOCKED | 必須source／教師／as-of／lineageの不足。可能な独立部分だけ完成 |
| SIGN_FILTER_NO_SEPARATION | 正負単体の明確な改善を確認できない。全手法で不可能とは言わない |
| SIGN_FILTER_TRADEOFF_ONLY | 負例は減るが正例保存との両立不足、主目安未達、またはblock不安定 |
| SIGN_FILTER_STAGE1_REVIEW_CANDIDATE | 下記の符号だけの到達目安をすべて満たす。次の検討へ渡す候補で、本番完成ではない |

SF_D＋標準alpha10%について、以下を同時に満たした場合だけREVIEW_CANDIDATEとする。

- source／符号／as-of／時間順監査PASS。
- Primary母集団で、モデル自身による有効予測coverageが95%以上。baseline fallbackで満たしたことにしない。
- 全OOFのプラス保存率90%以上、マイナス除去率30%以上、通過後マイナス率が同じ集合の無フィルター値より低い。
- 事前のCAL supportが足りたblockのうち、評価側に正負各10行以上あるblockを対象に、少なくとも4blockが評価可能。その75%以上でJ_sign>0。

この目安は「マイナスを大幅に消せた最終完成」ではない。達成しても残存負率を必ず数値で示す。目安未達を埋めるために結果後のalpha変更・features追加・新seed・学習やり直しをしない。

CIは任意の説明補助。算出するなら固定済み予測へのsession-cluster bootstrap 2,000回・seed57・2.5/97.5 percentileに限定し、再fit／再閾値選択は0。これは固定予測のDevelopment感度で、系列依存・設計選択・未知期間の一般化を認証しない。CIを後付けの救済Gateにしない。

**今回の合否を、利益額・R階層・最終資産で覆さない。** 将来のCapital統合で別の経済検証が必要なことと、今の符号単体評価は分離する。

## 11. 🔍 新しい箇所だけの必須監査

1. 原credit／debit比較と符号が一致し、厳密0・unknown・微小正負を取り違えない。
2. 入力、学習、閾値、判定に未許可の連続R・円PnL・U/R階層が渡らない。
3. **符号不変テスト:** 原結果の絶対値を同じ符号内で任意に変えても、X・符号・成熟時刻が同じなら、学習要求payload、重み、閾値、予測の評価、終了判定が不変。元source hashの変化は監査用に別記する。再fitせずpayload hashと独立評価で検算する。
4. 未来suffix／当該test教師を変えても、保存済み当該prediction・閾値が不変。評価結果だけが変わる。
5. 同じ学習済みscoreのproducer lineageと外側splitを確認する。未来modelで過去scoreを埋めない。
6. A/B/Cの列重複・所属・並び、Dの和集合、全群の共通row identity、UNKNOWN処理を確認する。
7. 旧D1/D2と同一学習署名の構成に再fitがない。同一OOFを新モデルの性能改善と数えない。
8. tauのtie、正例誤拒否予算のfloor、ALL_PASS、ゼロ分母、初期OFF、欠測予測の件数を独立算定する。
9. 合成テストで「全マイナス予測」「全プラス予測」「全部拒否」「判断不能だらけ」が成功判定にならない。
10. Selector／Entry／EXIT／State定義・元Capitalコードのhash不変と、Replay／発注0を確認する。

巨大な既存State監査やR全域監査を再実行して検査件数を増やさない。

## 12. ⚡ 実施量上限と作業順

| 処理 | 上限 |
|---|---:|
| 情報構成 | A／B／C／Dの4つ |
| 新規model fit | 最大32、完全一致する旧モデルはreuseで減算 |
| 旧HL0／旧D1／旧D2の同一構成refit | 0 |
| hyperparameter／seed探索、追加構成 | 0 |
| 追加calibration／stacking／inner fit | 0 |
| 閾値表示 | 5%／10%／20%の3点、各構成×blockで過去符号だけから計算 |
| 新しい価格／State feature生成、市場／EXIT再materialization | 0 |
| Capital／RESET20／Replacement Replay | **0** |
| 第2審査、Winner強度fit、数量配分変更 | **0** |
| provider価格取得、保護データ開封、注文、main merge、force push | **0** |
| Claude | **0**。必要な争点だけ報告し、自動で外部送信しない |

新fit最大32に技術再試行は含めないが、技術再試行の上限は全体2回。OOM／保存障害などで同一入力・同一設定のまま再起動する場合だけ。完走fitを性能都合で再試行しない。全attemptを保存する。

作業順は、最新原本確認→再利用表→符号view／入力群固定→合成テスト→初回OOFまたは保存OOF再利用→符号のみ閾値→全表／曲線→独立検算→終了保存。

入力回収待ちは独立した符号・閾値テストやreport枠を進める。fit待ちは依存しない保存・検算を進める。過去と未来の境界を壊す並行実行はしない。ファイル不在を理由に同じ探索を繰り返さず、回収先・不足名を1つのreceiptへまとめる。

## 13. 📦 成果物と報告の形

新規保存先: `docs/evidence/capital-sign-only-filter-stage1-20261006-v1/`。既存RNEG Defense directoryはread-onlyとして不採用結果を保持する。

必須成果物:

```text
WORK_REQUEST.md
CURRENT_STATE.json / WORK_STATUS_LOG.jsonl
SOURCE_BINDING.json / REUSE_MATRIX.json
SIGN_TARGET_CONTRACT.json / SIGN_LABEL_COUNTS.json
FEATURE_FAMILY_MAP.json / ASOF_AND_SCORE_LINEAGE.json
MODEL_PRECOMMIT.json / FIT_LEDGER.json
INITIAL_OOF_PREDICTIONS（private）
SIGN_ONLY_THRESHOLD_SNAPSHOTS（block別）
BINARY_CONFUSION.csv / FILTER_COUNTS.csv
SIGN_METRICS.json / BLOCK_METRICS.csv
INDEPENDENT_SIGN_AUDIT.json
REPORT-ja.md / MANIFEST.json
```

REPORTの冒頭は次の2表から始める。マイナス／プラスを数字上でも取り違えない。

| 固定0.5の二値予測 | 実マイナスを正しく予測 | 実プラスを正しく予測 | balanced accuracy | 有効予測coverage |
|---|---:|---:|---:|---:|
| B0／HL0／旧D1／旧D2／SF_A／SF_B／SF_C／SF_D | 実測 | 実測 | 実測 | 実測 |

| 構成・強度 | PASSの実プラス | PASSの実マイナス | REJECTの実プラス | REJECTの実マイナス | プラス保存率 | マイナス除去率 | 通過後マイナス率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 無フィルター／保守／標準／強 | 実測 | 実測 | 実測 | 実測 | 実測 | 実測 | 実測 |

図は、プラス保存率×マイナス除去率の3点曲線、構成別の通過群正負構成、block別J_signのみを必須とする。全期間から事後算出したROC／PR曲線は識別診断として追加してよいが、その曲線から新しいruntime閾値を選ばない。

損益円、平均R、R5/R10、RN tail、U5/U10、資産曲線は今回のreportの成績欄に載せない。未計算を未計算と書く。以前の資産結果の不採用statusは履歴にだけ残す。

最後は「どの情報群が正負識別に寄与したか／寄与は未確認か」「標準でプラス何件を残し、マイナス何件を除いたか」「Primaryの終了判定」「不足Evidence」を答える。符号性能が上がっただけで資産も増えるとは言わない。

## 14. 💾 GitHub運用と引き渡し

開始、入力・仕様固定、OOF完了、評価・最終の重要checkpointに、実時計JST、basis HEAD/tree、現在地、完了、未実行、blocker、実施量、次方針を保存する。保存後はactual GETで本文・blob・HEADを読み戻す。元closureを上書きしない。

私有のEntry／symbol別台帳・特徴行・model入力はprivate成果物へ分離し、GitHubには契約・集約・hash・状態を保存する。未来のcommit SHAを保存前に捏造しない。

stage1が良好でも `productionReady=false / executionAllowed=false / automaticPromotionAllowed=false`。将来第2審査へ渡す場合は、**実際のプラスだけをoracle抽出した集合ではなく、当時のOOFフィルターがPASSした候補**を渡す。PASS内に実マイナスが残ることを隠さない。第2審査の実装は別Work。

## 15. 📎 根拠と設計選択の区別

[S1] 上記basis HEADの `docs/evidence/capital-rneg-defense-reuse-20261006-v1/REPORT-ja.md`／CURRENT_STATE.json: 旧HL0/D1/D2、教師数、108列接続、時間順・availability、不採用実績。

[S2] 同HEADの `research/capital-rneg-defense-reuse-20261006-v1/fit_rneg.py`: 旧learner・train-only前処理・初回OOF・旧政策に連続Rを渡していた処理。今回その政策部分を使用しない。

[S3] 本会話の最新指示: 第1審査はEntry→EXIT結果の正負だけ。第2審査は後工程。Selector／Entry／EXIT Freeze。

[S4] scikit-learn公式「Tuning the decision threshold for class prediction」「HistGradientBoostingClassifier」「Common pitfalls」: 実装上の参考。学習と閾値選定の分離、train-only前処理を確認。今回の特徴群、alpha、support、到達目安は本書の設計選択であり、公式推奨の最適値やArkの達成実績ではない。

## ▶ Workへ送る実行文

この指示書に従って、Capital第1審査の符号専用フィルターを研究してください。正解はFrozen Entry→Frozen EXIT/EODの費用後結果がプラスかマイナスかだけです。学習・閾値・合否に利益額、Rの大きさ、U5/U10、RN tail、最終資産を使用しないでください。旧HL0/D1/D2・入力・初回OOFを再利用し、重複fitを避け、事前固定した4情報構成までを時間順に比較してください。PrimaryはSF_D＋標準alpha10%で固定し、全体結果後の選び直しはしないでください。フィルター単体の正負混同行列、プラス保存率、マイナス除去率、通過後マイナス率までまとめて完成させてください。Capital接続・Replay・第2審査は0。Selector／Entry／EXITを変更せず、現在地・方針・実時計をGitHubへ保存し、読み戻しまで完了してください。

END_OF_WORK_REQUEST
