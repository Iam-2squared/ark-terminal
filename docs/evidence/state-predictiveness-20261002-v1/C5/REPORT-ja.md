# 📋 Ark Terminal — State Predictiveness V1 最終報告

作成JST：2026-10-02T09:30:31.441291+09:00  
Work：`WORK_STATE_PREDICTIVENESS_MAX_THROUGHPUT_20261002_V1`  
stage：`STATE_PREDICTIVENESS_20261002_V1`  
親cycle：`STATE9_RC2_MARKET_SEMANTIC_AUDIT_20261001_V1`

## 🛑 結論

**`BLOCKED_LEAKAGE_OR_SEMANTIC_INTEGRITY`**

主目的のpredictive improvementは示されませんでした。full State9（B2）とState9+Path（B3）は、5/15/30分のすべてでB0よりdate-equal MSEが悪化しました。OOFは5日・2評価foldで、事前条件の6日・3foldも満たしません。

さらに、事前固定したSHIFT60 negative-control停止条件が3cellで発火し、保存前検査ではbootstrap総上限1,000本に対し実消費3,000本の不適合を検出しました。定義・上限の読み替えや都合の良い再選定はしていません。**停止条件発火は実際の未来リークの証明ではありません**が、V1をvalidation-readyやfully-budget-compliantとして昇格しません。実施済みの結果・失敗・疑義を保存して終了します。

別実装による直接照合は **905,746項目一致、mismatch0**。これは数値再現性のPASSであり、negative-controlや予算不適合を解除するPASSではありません。

## 🔒 Frozen identity・事前固定

| 対象 | SHA256 / 結果 |
| --- | --- |
| path_contract | fc3808cb7d3d161e85527d7ebf97f902df7f0c3463457beddf1a25d053cee268 / MATCH |
| RC2 | 45859122a62ccdc946b31bb5709f3fc080ea4a4f935958afd8f1ca895f75b6ff / MATCH |
| profile | 77ee61ba1808a2c17614439fe7d14212a53cbfa7358c032ce16989eeb5248922 / MATCH |
| source_snapshot | 08e1a20a4d022a1429b74387169dd8729a2eaeb4dc0008f3af2b52ec0e661c23 / MATCH |
| M0 | 08cad3ca8316ccab644872e3d843e2d491ac6a953a03193d5c391be3bcf73bb3 / MATCH |
| STATE_PATH_ADJUDICATION_RECEIPT_20261002.json | c174a6423460582441ea5a00bd1f657629bcec41585f33683ac62cad7196e0c3 / MATCH |
| STATE_PATH_ADJUDICATION_REPORT_20261002.md | 2fe8d806fe01a0433ce46adce08e3fdbcd089c8122e65e96d5a15bc9fec9b6d7 / MATCH |
| REVIEW_FINAL(1).json | 7e667ccbabe17c74aa4038eb2f67fcd73ea62ee0297ca651685b8a35d74f0fc6 / MATCH |
| STATE_PATH_ChatGPT_Blind_Review.zip | 23cd04914179c04214bf76f3c856e2b3beb3dba95cab66ff8175c680e5008df5 / MATCH |

Blind first-answer canonical：`b37443eff20c44138049453832563765cd3cb387cd997092d9ab279212b1b88a`を原本ZIP内のcanonicalとbyte-exact照合済み。新しいadjudicationやreviewer回答は作成していません。State9とPathは正式な入力基盤として継承した**SEMANTIC_FREEZE_CANDIDATE**であり、production認証ではありません。

継承一致：State9 classification29/29・observed/null29/29・observed Primary18/18・Primary9/9coverage。Path endpoint302/302、event609/609、run91/91。context resetの裁定を維持。RC1の16FAIL、88-workflow incident、旧予算/Exposureを保持。

Predictiveness Contract：`393de497cd2218f546ec01d2b0cf24f1d2791332c3f5400069d102ccb5e9fe41`  
Precommit：`21ce257a88f334b2f00b7798465c7cb50741b2d47bd2c8da14fb7c8d1f3f5fca`  
事前固定JST：`2026-10-02T08:48:15.222939+09:00`、固定前future label0。repo C1のContractも同じSHAを実読確認しました。

原本のmetadata/M0確認は最初の完全Contract再読と一部interleaveしました。厳密な指定読順を満たしたとの虚偽証明はしていません（FROZEN_IDENTITY_RECEIPTに記録）。定義・数値/API・profile/M0/Path・seed/grid/horizon/gateの結果後変更0。

## 🧮 数値/API契約と単位

指示式を文字どおり固定：`y_h=(raw unadjusted CloseJPY[t+h]-CloseJPY[t])/frozen U`。M0のUはdimensionless log-return scaleなので、**yの単位はJPY/U、percent returnではありません**。canonical log displacement `delta_x`は別のdescriptive secondaryで、primaryの代わりに救済使用していません。

exact Close/U token、80桁Decimal値と有理数、exact signを保存。float64はモデル入力/集計だけ。exact horizonを飛ばさず、欠損やreset越えは明示的unavailable。価格補完なし。現行Stateはtまで、run閉鎖/future dwellはfeatureへ未入力。学習時の補完・scale・語彙・ridge選択は過去trainingだけです。

featureは63（State numeric33/categorical11、Path numeric11/categorical8）。source featureは現在source種別の定数/欠損で、security/date/raw source pointerはjoin-only。S/A/B/C・Membership・velocityはすべてDEFINITION_INCOMPLETE、除外。

## 🗃️ 母集団・欠損・独立標本

| 項目 | N |
| --- | --- |
| 元pre-price proposals | 36 |
| 元current dates | 12 |
| input-eligible pairs / securities | 25 / 25 |
| eligible current dates | 10 |
| 入力品質除外 | 11（前日adjacent不足9、minuteなし2） |
| scheduled endpoints | 8050 |
| raw present / absent | 3772 / 4278 |
| observed semantics / formal null | 2138 / 5912 |
| duplicate canonical keys | 0 |
| feature unique runs | 649 |
| 新semantic sample draw / 新provider request | 0 / 0 |

29 semantic caseを母集団にはしていません。元の価格を見る前に固定した36proposal全体と除外分母を引き継ぎ、eligible25session全scheduled endpointを使用。全承認Development145日などへ結果後拡張していません。2025-05-28と2025-07-18は元入力品質でeligible sessionなし、置換0。

| horizon | 全available price labels | OOF unique rows | OOF date / pair / run | Fold1 / 2 / 3 rows |
| --- | --- | --- | --- | --- |
| 5分 | 1895 | 1544 | 5/9/338 | 896/0/648 |
| 15分 | 1278 | 1096 | 5/8/237 | 736/0/360 |
| 30分 | 846 | 775 | 5/7/168 | 583/0/192 |

price OOFのunique row×horizonは3,415、4model複製を独立標本とは数えません。REAL/control/modelの保存prediction27,928行、secondary9,216行。HOLD・同一run・overlapping forward windowsで依存があります。

| horizon | OOF strict overlapping row pairs | 共有endpointでtouchするpair | 最大rows/run |
| --- | --- | --- | --- |
| 5分 | 5531 | 1260 | 50 |
| 15分 | 12906 | 775 | 40 |
| 30分 | 18234 | 506 | 27 |

不確実性単位はsession date。IID-row bootstrapではありません。5日しかないことでintervalは不安定。target不足を精密なnull効果の証明に読み替えません。

## 📉 B0/B1/B2/B3とhorizon

B0＝date/security-session重み付きunconditional mean/prior。B1＝Primary lookup + pseudo-count10。B2/B3＝ridge、強度[0.01,0.1,1.0]を最後の過去training日で選択、intercept無penalty。nonlinear追加なし。directionは同じ強度のone-hot least-squares scoreをclip/normalize。確率保証ではなくcalibration表を保存しています。

下表MSEは**百万(JPY/U)^2**、小さい方がよい値です。

| horizon | OOF rows | coverage | B0 | B1 | B2 | B3 |
| --- | --- | --- | --- | --- | --- | --- |
| 5分 | 1544 | 5日 / 2fold | 28.66 | 31.29 | 32.46 | 34.09 |
| 15分 | 1096 | 5日 / 2fold | 72.80 | 80.72 | 94.10 | 163.27 |
| 30分 | 775 | 5日 / 2fold | 170.46 | 175.44 | 265.76 | 355.97 |

改善率はcomparatorのdate-equal MSEに対する減少率です。**負＝悪化**であり、forward returnの%表示ではありません。

| horizon | B1−B0 | B2−B1 | B3−B2 | B2−B0 | B3−B0 |
| --- | --- | --- | --- | --- | --- |
| 5分 | -9.16% | -3.75% | -5.03% | -13.25% | -18.94% |
| 15分 | -10.88% | -16.57% | -73.52% | -29.25% | -124.27% |
| 30分 | -2.92% | -51.49% | -33.94% | -55.91% | -108.82% |

B2/B3対B0の改善foldは全horizonで0。Fold2は0targetで未評価、PASS扱いなし。PRIMARY candidate0。REGISTERED intervalは99.1667% date-cluster percentile（tail1/240）。各horizonの保存1000drawのintervalを独立再計算しましたが、**総本数3000は固定総上限1000に不適合**です。後からper-horizon予算と定義し直しません。

方向accuracy/balanced accuracy/Brier/log-loss/Spearman/MAE・pooled/date-equal R2はMETRICS_AGGREGATE/BY_FOLD、bucket mean/medianはPREDICTION_BUCKETS、calibrationはDIRECTION_CALIBRATIONに全cell保存。

## 🧭 集中度・secondary

正の局所改善だけを集めたgross contributionは、net改善が負でも計算しています。その最大寄与とleave-oneを事前条件どおり残します。

| horizon | model | 最大1日寄与 | 最大1銘柄寄与 | leave-one |
| --- | --- | --- | --- | --- |
| 5分 | B2 | 76.7% | 73.7% | FAIL（leave-one改善は負） |
| 5分 | B3 | 61.3% | 57.5% | FAIL（leave-one改善は負） |
| 15分 | B2 | 61.0% | 60.2% | FAIL（leave-one改善は負） |
| 15分 | B3 | 35.3% | 34.4% | FAIL（leave-one改善は負） |
| 30分 | B2 | 62.2% | 61.9% | FAIL（leave-one改善は負） |
| 30分 | B3 | 44.0% | 43.5% | FAIL（leave-one改善は負） |

secondary next-Primary：B0/B1/B2/B3 accuracy31.74/69.22/68.58/71.19%。B3のnext-state accuracy上昇はありますが、B1よりBrier/loglossは悪化し、primary gateを救済しません。TRANSITION_WITHIN30 accuracyは全model96.46%、balanced accuracy50%で強いclass imbalance。これをfuture price signalとは呼びません。time-to-next-transition・direction relationは条件付き/censoredの保存labelに限定。

## 🧪 Negative controls・独立検査

日内permutationはtuple/sign/provenance一体、seed2026100202、+60 tradable-slot shiftはwrap/session/gap越えなし。実結果とcontrolは**同じrow key集合**で比較。

| horizon | model | matched rows | control clusters | real改善率 | SHIFT60改善率 |
| --- | --- | --- | --- | --- | --- |
| 5分 | B2 | 81 | 2日 / 1fold | +0.332% | +24.178% |
| 5分 | B3 | 81 | 2日 / 1fold | +3.653% | +23.086% |
| 15分 | B1 | 51 | 2日 / 1fold | +1.426% | +33.377% |

SHIFT60の改善が正のreal matched改善の90%以上になる事前条件で3STOP。少数2日/1fold、regime persistenceやsample variationもあり得るので「実リーク確認」と断定していません。それでも条件を弱めずBLOCK。permutationがactual全体よりよく見えるcellも隠さず18control cell全体を保存。

| 独立検査 | assertion | mismatch | 範囲 |
| --- | --- | --- | --- |
| 第一別script | 829954 | 0 | causal fields/segment/clock/exact target/fold/prediction/baseline/metric/CI/control |
| 追加別script | 75792 | 0 | train-only encoder/target hashes/seed mapping/secondary/bucket/calibration/concentration |
| 合計 | 905746 | 0 | candidate helper import0、kernel再実行0、fit再実行0、新bootstrap0 |

共有はNumPy/Decimal等の標準依存のみ。raw provider pagesはrunner一時なので原ページ再取得の独立確認ではなく、原hash bindingに結び付いたexact Close/U derived tableの直接検査。inner-grid選択は保存lossから検査し、別fitはしていません。独立human reviewerの新回答は代筆0。

## ⚠️ 予算・修復・継承

| 消費 | 今回実績 | 固定/継承 |
| --- | --- | --- |
| Actions | 2runs / 2jobs、各fanout1 | 初回失敗を保持、次は孤立routine repair |
| State9 feature generation | 4837 | cap18432、unique4830+未保存memory反復7 |
| trace reuse | 元3220 + 初回完了302 | 成功export reuse3522 |
| モデルfit | 170（baseline40/ridge130） | 有限最大294、成果80fit artifacts |
| bootstrap saved draw vectors | 3000 | 固定総cap1000、不適合+2000 |
| 独立checker新fit/kernel/bootstrap | 0 / 0 / 0 | 保存結果直接照合 |
| 新provider / 新sample draw | 0 / 0 | 旧provider168・draw1を保持 |
| 修復incident | 11 | 履歴31にappend、既知累積42。停止上限にはしない |
| 旧RC1 FAIL / 旧workflow incident | 16 / 88 | UNKNOWN_NONZERO履歴を消さない |

初回ratio decoder失敗は未来label/モデルを見る前、309kernel steps消費。302完了traceを次のrunへ引継ぎ、未保存D002 memory7stepsの反復だけを別計上。raw平文は両runでpurge確認、元encryptedartifactとderivative evidenceは保持。secret値取得/表示/保存0。

bootstrap不適合は単なるcount naming修復ではありません。COMPUTE_BUDGET_FINDINGの総capと実消費を保持し、追加bootstrap/fitや結果削除なし。全予算PASSは宣言しません。

## 📊 図表・GitHub保存

必須7chartをPNG/SVG（14file）で完成。model×horizon、incremental、fold、全model bucket、63feature coverage、sample/cluster、control comparison。全PNGを目視確認し、small-layout limitationsをQAに残しました。未評価foldを0やPASSへ変えていません。

専用branch：`state-predictiveness-20261002-v1`、repo：`Iam-2squared/ark-terminal`。C0〜C4実commit確認、C5最終保存。C5自身のSHAを自己fileへ循環埋込せず、**最終HEAD/JST/実GitHub要求数はCHECKPOINTS/C5_POST_COMMIT_RECEIPTとGITHUB_REQUEST_USAGE_AT_DELIVERYへ保存**します。main merge/force push/他branchEvidence上書き/既存workflow改変停止0。C3 Evidence commitのActions0を実GET確認。raw/row-level feature/label/OOFはpublic repoへ未公開。

この報告作成時点のconnector実消費read33/write22。最終C5の実要求は別append-only receiptで合算し、未実施要求を消費済みと書いていません。runner内部existing artifact GET2は別計上。connector内部physical HTTP総数はUNKNOWN。

## 🧾 12の問いへの回答

| 番号 | 問い | 回答 |
| --- | --- | --- |
| 1 | State9はcausalにforward targetを予測できたか | 今回のliteral primary targetでは証拠なし。B2/B3は全horizonでB0よりMSE悪化。対象範囲と5日/2foldの有限結果であり、市場一般で情報が存在しない証明ではない。 |
| 2 | full State tupleのPrimary超過価値 | なし。B2−B1 MSE改善は5/15/30分で−3.75/−16.57/−51.49%。 |
| 3 | Path/TransitionのState9超過価値 | なし。B3−B2は−5.03/−73.52/−33.94%。secondary next-Primary accuracyの増加だけでcoreを救済しない。 |
| 4 | 最も安定したhorizon | 安定した正のhorizonなし。5分の悪化幅が相対的に小さいだけでcandidateではない。 |
| 5 | fold再現 | B2/B3対B0改善は0/2評価fold。Fold2はtarget0で未評価。3fold条件と6日条件を満たさない。 |
| 6 | 1銘柄/1session依存 | 集中度条件を満たさず、leave-one改善も負。特にB2のgross positive改善寄与は1日61.0〜76.7%、1銘柄60.2〜73.7%。正のnet改善はそもそもない。 |
| 7 | negative controlに勝ったか | いいえ。SHIFT60のB2/B3×5分、B1×15分で事前固定STOP。2日/1foldだけのcontrolで、実リーク断定とは別。 |
| 8 | leakage/gap/reset/duplicate | 直接causal timestamp/eligibility/segment/fold/dedup検査は一致、違反検出0。gap/resetを跨ぐlabelはunavailable。独立数値一致はnegative-control疑義を消さない。 |
| 9 | Entryへ渡すfeature群 | 予測signalとして昇格する群は0。凍結意味・causal schemaと失敗Evidenceのみ技術引継ぎ。個別群ablation/因果的重要度は未事前固定・未実施。 |
| 10 | Holdout準備 | 未完了。candidate0、integrity/budget未解決。Common HoldoutもProtected/Fresh/OOS/Prospectiveも開封0。 |
| 11 | State9/Path意味変更 | 0。profile/M0/RC2/Path Contract、固定feature/target/grid/gateの結果後変更も0。旧16FAIL・88incident維持。 |
| 12 | Future/Entry/EXIT/Profit/Protected exposure | 許可された研究price label：REAL4019、SHIFT601170、計5189tuple。structural next-Primary1948/window791。未来classifier/model-feature input0。Entry/EXIT/Profit/Protectedは各0。研究future labelを0と虚偽表示しない。 |


## 🚫 Exposure・次の行動

研究forward labelは許可範囲のDevelopmentのみ：REAL4019 + SHIFT601170 =5189available price tuples。next-Primary1948、transition window791。未来State9/Path/model-feature input0、Entry/EXIT/profit/Capital/Portfolio/CommonHoldout/Protected/Fresh/OOS/Prospective/外部AI/発注/mainmerge各0。旧strategy-outcome Exposureは別としてそのまま引継ぎ、今回0でresetしません。

次は**固定Evidenceの別レビュー**です。解決前のvalidation、Holdout開封、Entry/EXITや予算/target読み替えへの自動進行はありません。V2が必要なら別Contractと新承認に分離し、V1の失敗と予算を残します。

## 🛠️ 使用スキル

SpreadsheetsスキルをCSV欠損・数値/単位契約・直接照合の運用に使用。answers-chartsスキルを比較指標の読みやすい表示に使用。workbookや架空のreviewer回答は作っていません。
