# 🛡️ Ark Terminal — Independent Entry→EXIT Sign Classifier V1
## 独立した第1審査：プラス／マイナスだけを学習・評価する

文書ID: `ARK_INDEPENDENT_ENTRY_EXIT_SIGN_V1_20261006`
状態: `DESIGN_READY_NOT_EXECUTED`
Repo: `Iam-2squared/ark-terminal`
研究branch: `capital-main-reallocation-20261005`
設計時確認HEAD: `b34c305367633b696dfb134f051d15abe7dbc981`
同tree: `965b21f2a7b56860ce06ee1864e3b12e3c188162`
作成実時計JST: `2026-10-06T11:38:45+09:00`

## 0. 🎯 最優先の目的・権限

**Frozen Entryが発した候補について、現行のFrozen EXIT/EODまで通した費用後結果がプラスかマイナスかを、購入前情報から予測する独立モジュールを作る。**

これはCapital側の第1審査であり、Selector／Entry／EXITを再設計する研究ではない。全市場の銘柄選別でも、全Entryを購入する研究でもない。既存CapitalのRank、Reserve、数量、購入実績に学習目的を従属させない。

将来の構成は `Frozen Entry → Sign判定 → 予測PLUS側へ既存Winner Rank → 配分 → Frozen EXIT`。ただし今回はSign判定器と単体評価まで。**第2層のRankを作り直さず保存し、Capital接続・Replay・第2層学習は0。** 通過候補は実際のPLUS確定集合ではなく、MINUSも残る予測集合である。

本書をWorkへ実行指示として渡した場合、原本回収、独立データview、有限のモデル比較、事前固定した後半確認、診断、保存までを同一Workで進めてよい。工程の区切りだけで承認待ちにしない。一方、本書の作成・保存だけでは実験が実行されたことにならない。

「独立」はコード・入力契約・教師・評価器・モデル選択をCapitalから分離する意味。既存市場期間が未使用データへ戻る意味でも、成功や最短時間の保証でもない。

## 1. 🔄 旧Workからの切替と競合防止

旧 `ARK_CAPITAL_SIGN_ONLY_FILTER_STAGE1_V1_20261006` は本書へ切替える。旧RNEG Defenseの不採用、V5保持、過去の失敗は変更しない。

設計開始時のGitHubでは、旧Sign-only Workは11:24:24 JSTに入力回収中・保存new_fits=0だった。その後、執筆中の再確認HEAD `8039a7b14fa42b17483398ed1b9a66227f8c0ad6` では、11:37:57 JSTに旧Workの32fitsと初回OOFが完了していた。Capital Replay／第2層は0。今回は完了メタデータだけを確認し、その新しい分類成績を使って本設計を調整していない。旧Workを未実行や停止済みとは扱わない。[S1][S5]

開始時にlatest HEADと該当Workの実行状態を確認する。旧Workの追加学習batchは開始せず、進行中のfitがあれば実行担当が安全なcheckpointで停止・保存する。完了済みOOFの監査・集計・閉鎖は新fitなしで完了してよい。既にできた原本回収、列対応、テスト、等価なfitは再利用する。他作業者の成果を上書きせず、無関係なjobを停止しない。旧予算と新予算を並行消費しない。

`SUPERSESSION_RECEIPT.json` に、旧status、切替時の実行済み数、引継ぎ資産、新しい実行ownerを残す。GitHubへの切替文書保存は、別環境のprocess停止確認とは区別する。

## 2. 🔒 Freezeと今回扱わないもの

Selector、FIRST ENTRY v2 P1_Q70、Structural EXIT v3、既存EOD／約定／費用、State9 RC2／Pathの意味・窓・gap・pivot契約を保持する。旧Rank、pP/U2/U3等のproducerを改変・再学習しない。

今回の学習・選択・合否に入れないもの:

- 将来のreturnの大きさ、円PnL、R1〜R10、RN tail、U5/U10、将来High/Low、MFE/MAE。
- 購入数量、投入額、資金利用、空きslot、Reserve判断、Capitalの最終資産。
- 実際のEXIT時刻／理由、保有時間、将来sourceの完備性等の購入後情報。

入力には購入前の価格変化率やVWAP等を使ってよい。「結果の大きさを使わない」と「過去の価格特徴を使わない」は別。

NO BUY、WAIT、Entry時刻変更、EXIT上書き、損切り追加、再Entryを実取引経路へ実装しない。今回は研究出力の `PASS_CANDIDATE` / `REJECT_CANDIDATE` まで。

## 3. 📚 確認済み資産と回収順

まず既存RNEGの `REPORT-ja.md`、`CURRENT_STATE.json`、`PREPARED_INPUT_CONFIG.json`、source/as-of監査、private manifestを読む。次に旧Sign-only Workで回収済みの列対応を読む。全repo探索・全ZIP展開を何度も行わない。

| 資産 | 保存事実 | 今回の扱い |
|---|---|---|
| CORE runtime | 1,600行／58 sessions | 原本を保持し独立viewを作る |
| OOF Entry | 1,039行、正負既知1,016、不明23 | Entry IDを維持する |
| 正負既知 | PLUS462／MINUS554 | 開始照合値。新結果で黙って変更しない |
| warmup教師 | 既知544、OOFと合わせ既知1,560 | 成熟時刻を守り学習に再利用 |
| State／Path | COREに既存、意味変更なし | 新たなState研究をしない |
| P0 context | 既に108非重複列を接続済み | 価格・出来高等の数値を再利用 |
| HL0／D1／D2 | 過去の正負予測器 | baseline。名前だけ変えた再fitは禁止 |

これらは旧RNEG保存結果に基づく。[S2][S3] 旧モデルのAUROCはHL0約0.503、D1約0.529、D2約0.522であり、今回の性能ではない。独立モジュール化だけで予測情報が増えたとは主張しない。

原本候補:
`docs/evidence/capital-rneg-defense-reuse-20261006-v1/`
`research/capital-rneg-defense-reuse-20261006-v1/`
`docs/evidence/capital-sign-only-filter-stage1-20261006-v1/`
`docs/evidence/capital-v51-reset20-r5r10-20261006-v1/`

private ZIP: `Ark_Capital_RNEG_Defense_20261006_PRIVATE.zip`
SHA256: `a70abbbb2e4d9933d7a6479dff4e1081b07627ccaad5c3eeb2c3132e5312f47d`

既存入力照合:
- `RUNTIME_FEATURES.jsonl.gz`: `2ac6acd608385eedf61e5ad912b6ec5a4be5750622167c1f619b30dda323628d`
- `RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz`: `fe8053da6798adcf01b5f4c09236304f607113c541acfee35a8f4ea74c9b9293`
- `SESSION_SPLIT.json`: `e83291b8706c48a4e496739219f1a645246b73be28f2195bebfaeb6614a12274`

hash差は理由を記録して解消し、過去原本を上書きしない。古いMSH／IMMEDIATE／R50等の別Entry・別EXIT系列の教師を、行数を増やすために混ぜない。

## 4. 🏷️ 教師を符号だけへ物理的に分離する

既存費用後BUY debitとSELL creditをexactに比較する。費用は原契約で1回のみ。新しいEXIT Replayや結果価格の作り直しは0。

| exact比較 | sign_status | y_plus |
|---|---|---:|
| sell_credit > buy_debit | PLUS | 1 |
| sell_credit < buy_debit | MINUS | 0 |
| sell_credit = buy_debit | EXACT_ZERO | null |
| 結果不明 | UNKNOWN | null |

旧y_negとは符号の向きが逆。`p_plus = 1 - p_neg` は旧モデルの出力向きを揃える変換であって、新モデル学習や改善ではない。

独立教師viewが外部へ渡せる列は `entry_id, session, sign_status, y_plus, label_maturity, source_hash` のみ。金額・return原値は監査adapter以外から読めない構成にする。母集団・fold・銘柄識別は別metadataに置く。

+0.01%も+30%もPLUSの1件、-0.01%も-17%もMINUSの1件。全行等重み、sample_weight=None、class_weight=None。重複口座や同Entryの複数snapshotで教師数を増やさない。厳密0をプラス／マイナスへ便宜的に寄せず、epsilon帯を新設しない。

主対象はFrozen Entryの購入前契約上実行適格な候補。U条件、Rank通過、旧V5購入で学習母集団を絞らない。これは将来審査を受けるEntryの教師を使うためで、全件購入の意味ではない。Rank通過／旧V5購入は結果固定後の補助集計だけ。

unknown教師は学習・正負採点から分離するが、runtime行自体は削除しない。予測不能と教師不明も別statusにする。

## 5. ⏱️ 判断時点と情報契約

判断時点は既存契約でCapitalが数量を決める購入前event。元Entryのintent/fillを動かさない。first-intent snapshotと、そのevent以前に利用可能な閉じたState/price prefixだけを読む。

各入力へ `source_available_at, feature_as_of, valid_from, transform_version, source_hash` を記録する。時刻が同じだけでは合法としない。元のevent順で数量確定より前に利用できることを確認する。fill barのH/L/C/volumeや約定後の遅延確定情報は禁止。

近傍の未来snapshot、別日の同銘柄、別watchへの近似joinは禁止。Entry ID＋first-intent row identity＋sessionを正確に対応させる。UNKNOWN／CARRIED／INITIALIZING、segment break、昼休み、pivot確認時刻は元定義を継承する。

historical quote/arrivalの仮定は `HISTORICAL_ASSUMED_AVAILABILITY` のまま。actual arrivalの原証拠がないものをPIT VERIFIEDへ昇格させない。

## 6. 🧩 独立入力：2種類の表現を固定する

既存の列名・定義・時間的依存をmetadataで割り当て、符号との相関を見る前に `FEATURE_REGISTRY.json` を固定する。

| group | 内容 |
|---|---|
| G_PRICE | 既存P0の価格経路、出来高／売買代金、VWAP、変動性、pullback等 |
| G_STATE | 既存State9、方向、stop、Path遷移・dwell・観測状態 |
| G_CONTEXT | 購入前に確定した時刻、Selector到来からの経過、既存Entry context |
| G_SCORE | 時間順依存を証明できる保存済み学習scoreのみ |

**X_RAW = G_PRICE＋G_STATE＋G_CONTEXT。学習済みscoreを含めず、第2層のRankがなくても動く基準表現。**
**X_AUG = X_RAW＋G_SCORE。既存scoreに追加情報があるかを比較する補助表現。**

G_SCOREの回収対象は、既存Entry p1_score/p1_threshold、pP/MOVE_P5、MOVE_U2、MOVE_U3に限定する。存在・単位・producer名はmanifestで解決する。旧HL0/D1/D2は比較用であり入力へ積み重ねない。Rankによる事前除外・sample重み付けはしない。既存Winner scoreのtargetを正負へ改名しない。

score producerも、その行の判断時点より前の成熟教師だけで生成されたことを確認する。特に外側testだけでなく、**今回のCALの教師がFIT行のscore producerへ入っていないこと**を依存graphで検算する。OOFというファイル名だけでは認証しない。warmupのin-sample scoreで穴埋めしない。

X_AUGは、適法な追加列が1列以上あり、予定する各FIT/CAL/TEST区分で必要なscore接続が95%以上成立する場合だけ、ラベル比較前に有効化する。未達ならX_AUGを無効にしてX_RAWを進める。この95%は今回の設計上のcoverage条件であり性能保証ではない。残る未接続行はABSTAINとして保持し、有利な行だけで主結果を作らない。

既存P0108列の接続を再構築する必要はない。将来値を使わない機械的view作成・重複除去は1batchまで許可する。新しい市場特徴定義、窓の探索、全組合せ、Dictionary再構築、巨大な旧566列の無差別追加は今回は行わない。Daily等は今回の固定原入力に実在する列だけ。存在しないデータを推定しない。

## 7. 🧠 モデルfamily比較：最大6候補

同じ入力、同じ時間分割、同じ符号教師・等重みで以下3familyを比較する。モデルを巨大化させるためではなく、線形／boosting／ランダム分岐ensembleの違いを検証する。[M1–M3]

| family | 事前固定する主要設定 |
|---|---|
| L：L2 Logistic | C=0.1、solver=lbfgs、max_iter=2000、tol=1e-4、fit_intercept=True、random_state=57 |
| H：HistGradientBoosting | loss=log_loss、learning_rate=0.05、max_iter=100、max_leaf_nodes=7、max_depth=3、min_samples_leaf=20、l2_regularization=1、max_bins=255、early_stopping=False、random_state=57 |
| E：ExtraTrees | n_estimators=300、criterion=gini、max_depth=6、min_samples_leaf=10、min_samples_split=2、max_features=0.5、bootstrap=False、random_state=57、n_jobs=2 |

全てclass_weight=None、sample_weight=None、warm_startなし。Hはcategorical_features=Noneとして共通one-hotを使う。その他既定値は使用環境のget_paramsで開始時に固定し、結果後に変更しない。

候補IDは `RAW_L, RAW_H, RAW_E, AUG_L, AUG_H, AUG_E` の最大6つ。追加family、seed探索、hyperparameter探索、学習後のscore反転・blend・ensemble選択は0。これは今回選んだ有限の研究設定であり、最適値との主張はしない。

前処理はFITだけで確定。numeric欠測は0＋各列のmissing indicator、平均／標準偏差はFITだけ、scale=0は1。categoricalはFIT vocabulary＋UNKNOWN、unseenはUNKNOWNへ。actual XにID／symbol one-hot／日付ID／fold番号を入れない。前処理済み値や既定値のversionを保存する。

FITは既知100行・10sessions以上・各class20行以上を要する。不足時は該当fitを実行せずUNAVAILABLEとする。意味を変えるfallbackは禁止。等価signature（行ID、教師、前処理、入力列、設定、cutoff）が一致する保存fitは再利用する。単に学習回数を満たすためのrefitをしない。

## 8. 🧪 FIT・CAL・TESTを同じモデルで分離する

元の58sessions、warmup20、OOF38／8blocksの時系列境界を基準とし、日付は元SESSION_SPLITから解決する。市場日を足したり並べ替えたりしない。

各外側block bについて:

1. `PAST_b` = 元splitの当該blockより前のsessions。
2. `CAL_b` = PAST_bの最後の5sessions。
3. `FIT_b` = PAST_bからCAL_bを除いた、それ以前のsessions。
4. FITの教師はCAL開始より前に成熟したものだけ。CAL教師はTEST開始より前に成熟したものだけ。
5. 前処理＋モデルをFITで1回fit。そのモデルでCALを推論し、符号だけで閾値を決める。
6. **CALで閾値を決めた後にモデルを再fitしない。** 同じモデル・同じ前処理・固定閾値で次のTEST blockを予測する。
7. 予測・閾値・hashの保存後にのみTEST符号を採点する。

これにより、旧foldの異なるモデルが出したscoreを寄せ集めて閾値を合わせるのではなく、実際にTESTで使うモデルを、直前の未学習CALで点検する。代償としてモデル学習に使う直近5sessionsは減る。その条件も比較表に明示する。[M4][M5]

random split、日内EntryシャッフルCV、既定のstratified threshold CVは使わない。label maturityで境界跨ぎ行をpurgeする。future suffix・現在block教師を変更しても、学習・現在予測が変わらないことを検査する。

CAL不足ならraw二値予測は出せるがfilterはOFF（全件PASS_CANDIDATE）とし、OFFも集計へ残す。TEST内での学習／閾値更新は0。

## 9. 🔍 探索と最終確認を分離する

### A. DISCOVERY：元OOF block1〜5

最大6候補を同じ5blocksで測る。後述の主filter条件でblock平均balanced accuracyを比較し、**1候補だけ**を選ぶ。これはモデル選択に使う探索成績であり、採用後の未知性能とは呼ばない。

候補の選定順は、(1) filterのblock平均BA最大、(2) 最悪block BA最大、(3) pooled filter MCC最大、(4) pooled Brier最小、(5) X_RAW優先、(6) L→H→E。結果を見て選択基準を変更しない。

モデル予測coverageが全体95%未満、あるいは主filterが有効なblockが3未満の候補は、実用filter選択資格なしとして別表に残す。全候補が資格を満たさなければNO_QUALIFIED_FILTERで有限終了する。閾値やsupportを緩めない。

### B. LATE_DEV_LOCKED_CHECK：元OOF block6〜8

DISCOVERY後、1候補のfamily／表現／設定／閾値手続き／合否基準をGitHubへ固定・読み戻し。その1候補だけをblock6〜8で第8節の通り順次評価する。後半13sessionsで6候補全部を再比較しない。

後半でもblockごとの再学習は固定手順の一部として行う。先行blockの成熟符号が後続blockのFIT/CALへ入ることは許可するが、手動でモデルを選び直さない。後半の成績・図表は3blocks分の予測固定後にまとめて開く。機械的な過去教師利用と、人間の結果後調整を分離する。

**この後半も既に過去研究で閲覧したDevelopmentである。今回再び区切っただけでFresh/Holdout/OOSには戻らない。** `LATE_DEV_LOCKED_CHECK / HISTORICALLY_EXPOSED` と表示する。新しい未使用確認データの独立性が証明できないなら、独立検証済みとは書かない。[S4]

このWorkは保護データ開封0。真の独立確認が必要なら、候補固定後の別Workに必要な原本・期間・権限だけを記録する。データがないことを理由に今回のDevelopment研究まで未実行にしない。

## 10. 🚦 二値予測とフィルターを分ける

### 10.1 生の符号予測

`p_plus >= 0.5 → PRED_PLUS`、それ以外はPRED_MINUS。等号はPLUS側。予測不能はABSTAINであり正解扱いしない。元ラベルの厳密0／UNKNOWNは採点外に分離する。

これは「全候補のプラマイをどれだけ当てたか」を測る表。下のフィルター通過とは別列にする。p_plusは未校正のscoreで、0.8が実際の勝率80%と確認されたわけではない。

### 10.2 主filter：CALでPLUSを80%以上残す条件

この80%は今回の研究用設計値で、未来保証ではない。旧Workの90%や円利益条件には拘束されない。90%／70%を固定補助比較として併記するが、結果後に主80%と交換しない。

`PASS_CANDIDATE ⇔ p_plus >= tau`。tau候補はCAL内のdistinct score＋ALL_PASS（tau=0）＋ALL_REJECT sentinel。tieをEntry ID等で分割しない。

CALは既知50行以上・3sessions以上・各class10行以上を要する。各tauでPLUS保存率>=qを満たすもののうち、**balanced accuracy最大 → MINUS除去率最大 → tau最小**で1つ選ぶ。BA<=0.5しか得られないときはALL_PASSとする。ALL_REJECTはq>0なら成立しない。

qは主0.80、補助0.90／0.70。各qごとの選定は同じCALに対する機械的な3手続きだけ。新fitなし。support不足はFILTER_OFF、TEST符号を見て別tauへ救済しない。

PLUS保存率とMINUS除去率は同じ固定CAL上の件数から算出する。金額、正利益合計、Rの深さ、平均return、Rank別利益、最終資産は使用しない。CAL条件を満たしてもTESTで80%保存できる保証はないため、実測値をそのまま出す。

## 11. 📊 主評価表・式・合否

PLUSを正classとする。各表には全Entry数、実行適格数、符号既知数、exact0、不明、予測可能数、ABSTAINを明記する。

| 実際の符号 | 予測PLUS／通過 | 予測MINUS／見送り |
|---|---:|---:|
| PLUS | TP | FN |
| MINUS | FP | TN |

二値予測とfilterでそれぞれ別の混同行列を出す。

- PLUS保存率 = TP/(TP+FN)。MINUS除去率 = TN/(TN+FP)。
- 通過PLUS率 = TP/(TP+FP)。通過MINUS率 = FP/(TP+FP)。
- balanced accuracy = (PLUS保存率＋MINUS除去率)/2。
- 正解率、MCC、両classのprecision/recall、AUROC、PLUS AP、MINUS AP、Brier、log loss。

filterのABSTAINは運用上の自動拒否にはせずPASS_CANDIDATEへ含める。そのため主filterの残存MINUSに算入するが、生二値予測の正解率ではABSTAINを除いた値とcoverageを必ず併記する。

同じFITだけの過去PLUS率B0、ALL_PLUS、ALL_MINUS、多数派予測をbaselineにする。B0にも同じCAL手続きを適用する。旧HL0/D1/D2は保存予測を符号の向きだけ揃えて参照するが、旧学習はCALを含む場合があるため、新候補との同一訓練条件比較とは呼ばない。

集計はDISCOVERY、LATE_DEV_LOCKED_CHECK、block別、session別を分離。主母集団は全適格Frozen Entry。Rank通過・旧V5購入を補助表示しても、その結果でモデルを選び直さない。少数の購入集合の高precisionだけで全体成功にしない。

### 事前固定する研究上の判定

| status | 条件・意味 |
|---|---|
| BLOCKED_INPUT_OR_LINEAGE | 必須原本・ラベル・購入前時刻を確定できない |
| NO_QUALIFIED_FILTER | DISCOVERYで第9節の資格を満たす候補なし |
| SIGN_NOT_SEPARATED_IN_THIS_RUN | 後半主filter BA<=0.5またはMCC<=0 |
| SIGN_SIGNAL_LIMITED | 上記より良いが下の到達条件／supportを満たさない |
| SIGN_LOCKED_DEV_PROMISING_UNCONFIRMED | 後半主filterでPLUS保存>=80%、MINUS除去>=40%、BA>=0.60、MCC>0、coverage>=95%、3blocks中2以上でBA>0.5を満たす |

PROMISINGには後半既知100行以上・各class30行以上・10sessions以上を要する。さらに後述のsession bootstrapのBA下限が0.5を超えることを要する。満たさなければ数値と不足を明記してLIMITEDにする。この数値セットは研究上の到達基準で、ユーザー指定値でも統計上の普遍的最適値でもない。結果後に下げない。

Brier/log lossは確率品質の別診断であり、符号を当てたことと確率が校正されたことを混同しない。PROMISINGでも `productionReady=false`、第2層へ自動進行しない。原本十分だが失敗した場合も「全モデル・全情報で予測不可能」とは言わず、今回の表現・family・期間に限定する。

## 12. 🧬 情報群の寄与を一度だけ調べる

1候補の選定後、同じfamily・設定を固定し、DISCOVERYの5blocksだけで以下を行う。

1. G_PRICEを除く。
2. G_STATEを除く。
3. G_SCOREを除く（X_RAWが選ばれた場合は元候補と同じなので再fit0）。

G_CONTEXTは共通で残す。各比較は最大5fit、合計最大15fit。新しい特徴候補を探すのではなく、既に固定した情報群の差だけを調べる。ablation結果を見て主モデル・後半候補・閾値を差し替えない。

既存入力に同じgroupがない場合はNOT_APPLICABLE。注目した銘柄・日だけ除く、教師を見てStateの意味を変える、エラーを見て追加featureを発明することは禁止。

## 13. 📏 不確実性・学習状況・停止理由

保存予測だけを使い、sessionをまとまりとして同じ日に属する全Entryをまとめて再標本化する。各区間で2,000回、seed=20261006、2.5/97.5 percentile。モデル再fit・tau再選択は0。主filterのBA、PLUS保存、MINUS除去、通過MINUS率のCIを出す。片classしかない反復はNAと数え、有効反復95%未満ならCI_INSUFFICIENTとする。

このCIは反復閲覧、モデル選択、期間依存の全てを補正するものではなく、未知期間の保証には使わない。既存市場期間の重複露出をEXPOSUREとして保持する。

追加fitなしでFIT／CAL／TESTのsign metrics、学習行数、欠測率を示す。FITだけ良いなら過適合の兆候、FITも低ければ表現・設定の限界の候補とするが、どちらも断定しない。負結果を理由にEntry/EXITへ変更要求を戻さず、Signモデルに必要な次の情報・検証だけを限定して書く。

## 14. 🧱 独立モジュールの成果物契約

新しい研究用ディレクトリは `research/independent-entry-exit-sign-20261006-v1/`、Evidenceは `docs/evidence/independent-entry-exit-sign-20261006-v1/` を基本とする。既存同名があれば開始時に照合する。

モデル本体はCapital engineをimportせず、`predict_sign(snapshot, model_artifact, threshold_artifact)` で動く設計にする。出力は少なくとも:

`entry_id, decision_ts, p_plus, predicted_sign, filter_action, availability_status, model_hash, threshold_hash, feature_schema_hash, max_source_available_at, fit_cutoff, cal_cutoff, exposure_status`。

学習ラベル、true R、future EXIT、口座資金、数量は推論interfaceに存在させない。後の第2層はこの出力と同じEntry IDの既存Rankをjoinできるようにするが、本Workではadapter仕様だけを残す。既存Rankの元targetをR強度予測と勝手に言い換えない。通過集合でRankが有効かは後工程で別確認する。

## 15. 🔍 最小の独立監査

以下に絞り、過去Stateの人工監査や全R分類を水増し再実行しない。

- 原debit/creditとsign view、PLUS/MINUSの向き、exact0／UNKNOWN、費用二重控除なし。
- **X固定・符号固定のまま結果の大小だけを変えても、教師view・重み・選択・閾値・合否が変わらない。**
- Entry ID一意、同Entry多重投入なし、as-of、same-time順序、学習済みscoreのCAL/TESTへの依存なし。
- FIT/CAL/TESTの日付・成熟境界、前処理FIT-only、CAL後refitなし、TEST内更新0。
- 全predict／policy保存後の採点、後半candidate交換0、旧OOFの初回性／等価fit再利用receipt。
- tauのtie、ALL_PASS、ALL_REJECT、ゼロ分母、support不足、ABSTAIN、学習class順序。
- 主処理をimportせず保存符号＋予測から混同行列と率を再構成し一致を検算。
- 後半1候補、ablation探索専用、全予定Entryのknown/unknown/coverage、合否の再現。

実装不具合を修復して再実行するときは原因・既に見た結果・影響範囲を保存する。データ／target／family／閾値の意味を変える修復は本予算で救済せず、意味不変の技術修復だけを許可する。

## 16. ⚡ 実施量上限と進め方

| 工程 | 最大fit数 |
|---|---:|
| DISCOVERY：2表現×3family×5blocks | 30 |
| 後半：選んだ1候補×3blocks | 3 |
| ablation：最大3群×5blocks | 15 |
| **新規予定fit合計** | **48** |
| 技術的不具合による同一条件retry | 別枠最大2 |

48は上限でありノルマではない。X_AUG無効、等価fit再利用、対象groupなしの場合は減る。前処理fitは別counterとし教師model数と混同しない。bootstrapの再集計は新fitでない。

新特徴定義0、原R再materialization0、State/Entry/EXIT refit0、full-data最終fit0、calibration model fit0、Capital Replay0、第2層fit0、新provider価格取得0、保護データ開封0、注文0、main merge0、force push0。Claudeは原則0。外部AIへprivateデータを自動送信しない。

1つのviewをhash固定して共有し、独立familyのfit中に合成テスト・report枠・監査を進める。CPU/RAMに応じたbounded並列で、同じモデルの競合書込みとnested過剰並列を避ける。CI待ちだけで停止せず、教師境界を壊さない独立作業を先に完了する。

原本不足は具体的なfile／列／cutoffを1回でまとめる。過去coverage欠落日を延々再探索しない。未知営業日を0%で足さない。限定された現在の分類研究と、全月次評価の未完了を区別する。

## 17. 📦 必須成果物と終了報告

`WORK_REQUEST.md, DESIGN_CONFIG.json, SUPERSESSION_RECEIPT.json, SOURCE_BINDING.json, SIGN_TARGET_CONTRACT.json, SIGN_DATASET_MANIFEST.json, FEATURE_REGISTRY.json, SCORE_LINEAGE_AUDIT.json, SPLIT_FIT_CAL_TEST.json, TRIAL_LEDGER.jsonl, FIT_LEDGER.json, DISCOVERY_RESULTS.json, MODEL_SELECTION_LOCK.json, FIRST_PREDICTIONS.jsonl.gz, THRESHOLD_SNAPSHOTS.json, LATE_DEV_RESULTS.json, ABLATION_RESULTS.json, INDEPENDENT_AUDIT.json, INFERENCE_CONTRACT.json, CURRENT_STATE.json, MANIFEST.json, REPORT-ja.md`。

未実施・該当なしの成果物はそのstatusだけを保存し、仮の性能や空グラフを作らない。private行別入力・モデル・予測は既存private保存先へ分離。publicには集計、hash、定義、監査のみ。

REPORTは冒頭に「PLUS/MINUS×予測」と「PLUS/MINUS×通過」の2表、旧比較、後半statusを置く。図は実測の混同行列、正保存vs負除去、block別BAの3種類を基本にする。最終資産・R帯・大Winnerの図は今回不要。

終了時に答えることは、**何件のPLUSを残し、何件のMINUSを除き、通過側のMINUS率がどこまで下がったか。どのモデル／情報で差が出たか。その差が後半でも残ったか。** 現在のEntry/EXITに責任を移さず、今回の分類器でできたこと・できなかったことを報告する。

## 18. 💾 GitHubと再開可能性

開始、入力・split固定、DISCOVERY終了／候補固定、後半完了、finalのcheckpointで、実時計JST、basis HEAD/tree、進捗、未実行、blocker、実fit数、次方針を保存する。コミット後はactual GETで本文・blob・HEADを読み戻す。

保存前のlatestを確認し、同branchの他writerにlease競合があれば内容を読み直す。旧CURRENT_STATEを古い内容で上書きせず、切替receiptと新cycle stateをappend-onlyで保存する。停止確認と停止指示、実行予定と実行済みを別statusにする。

## 19. 📎 根拠と設計選択の区別

[S1] GitHub commit `b34c305367633b696dfb134f051d15abe7dbc981`：旧Sign-only Workの入力回収開始、保存new_fits=0。最新状態はWork開始時に再確認する。
[S2] 同HEADの `docs/evidence/capital-rneg-defense-reuse-20261006-v1/REPORT-ja.md`：既存母集団、旧16fit、as-of、旧性能・closure。
[S3] 同HEADの同directory `PREPARED_INPUT_CONFIG.json`：既存CORE／P0列と入力hash。
[S4] 過去からのExposure原則：既に見たDevelopmentは再分割や新precommitでもFreshに戻らない。今回の後半は再利用Developmentのロック確認である。
[S5] commit `8039a7b14fa42b17483398ed1b9a66227f8c0ad6` の旧Sign-only `OOF_COMPLETE.json`：旧32fits完了。この設計turnの実行数とは分離する。
[M1] https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
[M2] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html
[M3] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesClassifier.html
[M4] https://scikit-learn.org/stable/modules/classification_threshold.html
[M5] https://scikit-learn.org/stable/modules/cross_validation.html
[M6] https://scikit-learn.org/1.8/auto_examples/model_selection/plot_nested_cross_validation_iris.html

公式資料はモデルinterfaceと学習／閾値／評価の分離原則の参考。3family、2表現、CAL5sessions、探索5blocks／後半3blocks、80%条件、到達基準、48fit上限は**本書で新たに選んだ研究設計**であり、資料が有効性や最適性を保証した値ではない。既存環境を固定し、新しいlibraryへ性能目的で変更しない。

## ▶ Workへ渡す実行文

本書に従いIndependent Entry→EXIT Sign Classifier V1を実行してください。旧Sign-only Workの新規実験は本書へ切替え、回収済み入力・過去の等価fitを再利用してください。教師・学習・閾値・合否は固定Entry→固定EXIT/EODの費用後プラマイだけ。独立dataset／推論interfaceを作り、最大6候補を時間順FIT/CAL/TESTで比較し、1候補を固定して後半確認、情報群の寄与と独立検算までまとめて完了してください。既存Rankは第2層用に保持し、Capital接続・Replay・第2層学習は行わないでください。Selector／Entry／EXITは完全凍結。現在地・方針・実時計・実行量をGitHubに保存し、読み戻しまで確認してください。

END_OF_WORK_REQUEST
