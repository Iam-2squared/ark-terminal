# Ark Terminal — State Predictiveness V2 最終報告

作成JST：2026-10-02T10:50:43.317551+09:00  
文書ID：WORK_STATE_PREDICTIVENESS_V2_NEXTSTATE_MAX_THROUGHPUT_20261002_V1

## 🏁 結論

**STATE_NEXTSTATE_PREDICTIVENESS_MEASURED_NO_PROMOTABLE_STATE**（B：測定完了・昇格可能Stateなし）。独立照合PASS、核心不一致0。次の異なるStateのB3正解率は60.44%、RISE予測のPrecisionは60.00%。ただしB2/B3の確率log lossはB1より悪く、固定された昇格条件を満たすStateはない。弱い結果をintegrity BLOCKへ読み替えていない。Entry、EXIT、利益、Holdoutには進まない。

新規取得は72候補中35銘柄sessionまで完了し、U_UNAVAILABLEでexportが中断した。13日・2評価foldで測定可能だが、予定第3foldと残り取得は未完了。この限界は消さず、再選定・fold組み替え・Actions上限増加は0。全Developmentを取得できたとは主張しない。

## 🔒 Frozen identity・事前固定

V1 final HEAD `7e3ce89cb2928d46f66d4606e1010ba3a3a1896f` は開始時実GET一致。V1正式BLOCK、bootstrap超過、旧RC1 16FAIL・88workflow incident・既存Exposure/予算を保持した。

| 対象 | SHA256／結果 |
| --- | --- |
| path_contract | fc3808cb7d3d161e85527d7ebf97f902df7f0c3463457beddf1a25d053cee268 / MATCH |
| RC2 | 45859122a62ccdc946b31bb5709f3fc080ea4a4f935958afd8f1ca895f75b6ff / MATCH |
| profile | 77ee61ba1808a2c17614439fe7d14212a53cbfa7358c032ce16989eeb5248922 / MATCH |
| source_snapshot | 08e1a20a4d022a1429b74387169dd8729a2eaeb4dc0008f3af2b52ec0e661c23 / MATCH |
| M0 | 08cad3ca8316ccab644872e3d843e2d491ac6a953a03193d5c391be3bcf73bb3 / MATCH |
| V1 Contract | 393de497cd2218f546ec01d2b0cf24f1d2791332c3f5400069d102ccb5e9fe41 |
| V2 Contract | 833ca78a5f2a0e23b4d746989b725e68f5431d40c919c8624bddd1b7c4bf6c77 |
| V2 Data scope | 2c1d3901a44812fd40c7bad9185775595568dfe76869767ca0743dcbc9ba6e4e |
| State9 / Path / profile / M0変更 | 各0 |

事前固定はC2/C3でV2 labels・fitより前にGitHub保存。事後の意味・target・split・class/family・閾値・モデル変更は0。補助的なPath比較・図・集計は固定Contractの決定論的適用で、再fit・再drawはない。

## 🧪 V1局所forensic

V1 registered STOPは正しく発火した記録として維持し、actual leakage provenへは置き換えない。1,170 available SHIFT60 targetのsource/target時刻・連続区間・segment/fold・matched keysを直接監査して違反0。完全な60+h区間が必要なため疎なrawが多く落ち、OOF matchedはH5=81、H15=51、H30=20件、いずれも2日／1foldへ集中した。current/shift Primary一致率やPearsonは記述的で、regime依存の因果証明ではない。

V1 bootstrapはhorizon loop内で1000ずつ生成し計3000、cap1000から2000超過。V1 nonconformanceを永久保持。V2はglobal1000 vectorsを一度だけ生成し、全model/target/class/familyで再利用、独立checker新draw0。

V1 Fold2の2025-04-30／2025-06-02は5銘柄session・各horizon分母1635 endpoint。raw session自体が不在ではなく、開始点欠損・厳密horizon欠損・中間gap等で全targetが落ちた。security×date×horizonのexact countsはV1_FOLD0TARGET_REASON_COUNTS.csvを保存。

| V1 horizon | reason | N |
| --- | --- | --- |
| 5 | AUCTION_OR_OPENING_BOUNDARY | 1 |
| 5 | EXACT_HORIZON_OUTSIDE_SESSION | 10 |
| 5 | EXACT_HORIZON_UNAVAILABLE | 166 |
| 5 | INTERVENING_UNKNOWN_OR_REJECTED | 56 |
| 5 | START_AUCTION | 6 |
| 5 | START_UNAVAILABLE | 1396 |
| 15 | AUCTION_OR_OPENING_BOUNDARY | 4 |
| 15 | EXACT_HORIZON_OUTSIDE_SESSION | 20 |
| 15 | EXACT_HORIZON_UNAVAILABLE | 167 |
| 15 | INTERVENING_UNKNOWN_OR_REJECTED | 42 |
| 15 | START_AUCTION | 6 |
| 15 | START_UNAVAILABLE | 1396 |
| 30 | AUCTION_OR_OPENING_BOUNDARY | 1 |
| 30 | EXACT_HORIZON_OUTSIDE_SESSION | 30 |
| 30 | EXACT_HORIZON_UNAVAILABLE | 161 |
| 30 | INTERVENING_UNKNOWN_OR_REJECTED | 41 |
| 30 | START_AUCTION | 6 |
| 30 | START_UNAVAILABLE | 1396 |

## 🗃️ Development入力と実行範囲


| 項目 | N／状態 |
| --- | --- |
| 承認済みmetadata inventory | 145日 / 142 currentリンク |
| 新規固定対象 | 24日 / 72 metadata候補 / 日最大3銘柄 |
| 新規完了 | 13日 / 35 security-session |
| 入力不適格skip | 3 |
| U算定不可で中断 | 1 |
| 以後未取得 | 33 |
| 旧特徴量再利用 | 10日 / 25 security-session / 8050 endpoint |
| 総入力 | 23日 / 60 security-session / 19495 endpoint |
| 新規observed/null | 2118 / 9327 |
| 全observed/null | 4256 / 15239 |
| Primary OOF | 1360件 / 13日 / 26 security-session / 2fold |
| 予定fold | 3（第3fold=0件を保持） |
| core日数区分 | GOOD（13日）。全9State support充足の意味ではない |

全145日をmetadataで固定したうえで有限計算予算により、V1最後の再利用日より後の未使用Development24日を日付順、dated masterのhash順位で各最大3銘柄と事前固定した。価格・targetによる補充0。旧データはtrain/diagnostic、新規日をprimary OOFに使用。V2_NEW_DEV_EVALは「V1未使用」という研究内区分であり、既存strategy exposureがないFresh/OOSとは認証しない。

正規J-Quants binding・既存Development許可の継承だけを使用。追加provider request251（初回173＋修復78）、secret値の取得／表示／保存0。dated masterと当日・前日factor=1、既知State露出除外を適用。provider条件の新認証はしていない。元JSON数値lexeme→plain strへの型修復のみ行い、数値lexeme・Frozen M0は変更0。失敗run2件と消費量を保持。

一時rawは削除済みで、original response SHA・row pointer・取得時刻・exact派生Close/U・traceを保存。historical actual known_atはUNKNOWN、研究用assumed available_at=bar_endとの分離を維持。受信時刻の実証や完全provider rawの第三者再検証は本成果からはできない。

## 🎯 Targetと評価母数

NEXT_DISTINCT_PRIMARYは30 scheduled tradable slots以内に実際に生じた最初のgenuine transitionの行だけで9class評価する**条件付き**問題。先にgap/null/resetが来ればunavailable。イベント後のgapはこの条件付きdestination labelを無効にしない。NO_TRANSITIONは第10Stateにしない。

NEXT_OBSERVED_PRIMARYは隣接するcausally connected observed endpointで、同State継続を含む。これはpersistence込みで別評価。TRANSITION_WITHIN30はイベント後を含め全30slots観測可能な窓だけでbinary評価。

## 📈 Overall・9class指標（REAL OOF）

B0=prior、B1=current Primary Markov、B2=State9 tuple、B3=State9+Path。モデル選択を結果から追加していない。

| target | model | N | accuracy | balanced | macro P | macro R | macro F1 | Brier | log loss | date-equal log loss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NEXT_DISTINCT_PRIMARY | B0 | 1360 | 24.49% | 11.11% | 2.72% | 11.11% | 4.37% | 0.835473 | 1.9814 | 2.009 |
| NEXT_DISTINCT_PRIMARY | B1 | 1360 | 45.59% | 20.76% | 23.27% | 20.76% | 16.03% | 0.6892 | 1.34068 | 1.35484 |
| NEXT_DISTINCT_PRIMARY | B2 | 1360 | 63.31% | 36.11% | 32.75% | 36.11% | 33.29% | 0.582849 | 1.89034 | 1.75484 |
| NEXT_DISTINCT_PRIMARY | B3 | 1360 | 60.44% | 33.30% | 28.49% | 33.30% | 30.29% | 0.597738 | 1.67326 | 1.49685 |
| NEXT_OBSERVED_PRIMARY | B0 | 1751 | 28.04% | 11.11% | 3.12% | 11.11% | 4.87% | 0.829379 | 1.87153 | 1.76797 |
| NEXT_OBSERVED_PRIMARY | B1 | 1751 | 67.85% | 52.88% | 69.94% | 52.88% | 56.68% | 0.499026 | 1.03812 | 1.03299 |
| NEXT_OBSERVED_PRIMARY | B2 | 1751 | 63.05% | 45.01% | 65.69% | 45.01% | 48.68% | 0.518876 | 1.22319 | 1.08864 |
| NEXT_OBSERVED_PRIMARY | B3 | 1751 | 63.62% | 45.57% | 65.40% | 45.57% | 49.04% | 0.511819 | 1.1876 | 1.0631 |

## 🎯 予測State別Precision・Recall・F1

全9Stateを除外せず掲載する。NAはpredicted N=0等の分母0で定義できない率。実数の支持数0を記録し、偽の0%へ置き換えない。F1のNA規約とmacroのみのzero division規約は事前固定済み。

### NEXT_DISTINCT_PRIMARY — B3


| predicted State | predicted N | correct N | precision | actual N | recalled N | recall | F1 | Precision 95% CI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISE_STOP | 0 | 0 | NA | 67 | 0 | 0.00% | NA | NA – NA |
| RISE | 545 | 327 | 60.00% | 354 | 327 | 92.37% | 72.75% | 37.18% – 74.36% |
| SHARP_RISE | 4 | 0 | 0.00% | 60 | 0 | 0.00% | 0.00% | 0.00% – 0.00% |
| PULLBACK | 165 | 123 | 74.55% | 193 | 123 | 63.73% | 68.72% | 42.86% – 88.30% |
| RANGE | 6 | 0 | 0.00% | 76 | 0 | 0.00% | 0.00% | 0.00% – 0.00% |
| REBOUND | 185 | 125 | 67.57% | 180 | 125 | 69.44% | 68.49% | 62.69% – 75.33% |
| SHARP_DROP | 0 | 0 | NA | 54 | 0 | 0.00% | NA | NA – NA |
| DROP | 455 | 247 | 54.29% | 333 | 247 | 74.17% | 62.69% | 40.28% – 61.62% |
| DROP_STOP | 0 | 0 | NA | 43 | 0 | 0.00% | NA | NA – NA |

### NEXT_OBSERVED_PRIMARY — B3


| predicted State | predicted N | correct N | precision | actual N | recalled N | recall | F1 | Precision 95% CI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISE_STOP | 3 | 1 | 33.33% | 35 | 1 | 2.86% | 5.26% | 33.33% – 33.33% |
| RISE | 497 | 300 | 60.36% | 518 | 300 | 57.92% | 59.11% | 53.22% – 67.62% |
| SHARP_RISE | 16 | 10 | 62.50% | 33 | 10 | 30.30% | 40.82% | 42.86% – 77.78% |
| PULLBACK | 145 | 96 | 66.21% | 195 | 96 | 49.23% | 56.47% | 57.12% – 71.44% |
| RANGE | 247 | 214 | 86.64% | 255 | 214 | 83.92% | 85.26% | 78.77% – 92.23% |
| REBOUND | 155 | 103 | 66.45% | 173 | 103 | 59.54% | 62.80% | 61.00% – 76.92% |
| SHARP_DROP | 23 | 13 | 56.52% | 34 | 13 | 38.24% | 45.61% | 0.00% – 61.90% |
| DROP | 663 | 375 | 56.56% | 491 | 375 | 76.37% | 64.99% | 46.84% – 65.47% |
| DROP_STOP | 2 | 2 | 100.00% | 17 | 2 | 11.76% | 21.05% | 100.00% – 100.00% |

### 全modelのState別Precision（NEXT_DISTINCT_PRIMARY）


| State | B0 | B1 | B2 | B3 |
| --- | --- | --- | --- | --- |
| RISE_STOP | NA | NA | NA | NA |
| RISE | NA | 47.19% | 63.23% | 60.00% |
| SHARP_RISE | NA | NA | 33.33% | 0.00% |
| PULLBACK | NA | 87.10% | 71.50% | 74.55% |
| RANGE | NA | NA | NA | 0.00% |
| REBOUND | NA | 33.33% | 66.83% | 67.57% |
| SHARP_DROP | NA | NA | 0.00% | NA |
| DROP | 24.49% | 41.78% | 59.82% | 54.29% |
| DROP_STOP | NA | NA | 0.00% | NA |

### 全modelの9State support／Recall／F1

両target×B0/B1/B2/B3の全数値、FP実destination内訳・FN predicted-as内訳はPER_STATE_PRECISION_RECALL_F1.csv。支持数専用2CSVも同梱。SHARP_RISE次distinctはB3 0/4、DROP_STOP次observedは2/2であり、後者100%を十分なEvidenceとは呼ばない。

### NEXT_DISTINCT_PRIMARY 9×9（B3、行=actual／列=predicted）


| actual \ predicted | RISE_STOP | RISE | SHARP_RISE | PULLBACK | RANGE | REBOUND | SHARP_DROP | DROP | DROP_STOP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISE_STOP | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 66 | 0 |
| RISE | 0 | 327 | 0 | 5 | 0 | 0 | 0 | 22 | 0 |
| SHARP_RISE | 0 | 0 | 0 | 25 | 0 | 1 | 0 | 34 | 0 |
| PULLBACK | 0 | 2 | 3 | 123 | 6 | 0 | 0 | 59 | 0 |
| RANGE | 0 | 34 | 0 | 10 | 0 | 10 | 0 | 22 | 0 |
| REBOUND | 0 | 51 | 0 | 0 | 0 | 125 | 0 | 4 | 0 |
| SHARP_DROP | 0 | 29 | 0 | 0 | 0 | 24 | 0 | 1 | 0 |
| DROP | 0 | 67 | 1 | 1 | 0 | 17 | 0 | 247 | 0 |
| DROP_STOP | 0 | 35 | 0 | 0 | 0 | 8 | 0 | 0 | 0 |

### NEXT_OBSERVED_PRIMARY 9×9（B3、行=actual／列=predicted）


| actual \ predicted | RISE_STOP | RISE | SHARP_RISE | PULLBACK | RANGE | REBOUND | SHARP_DROP | DROP | DROP_STOP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISE_STOP | 1 | 25 | 0 | 0 | 6 | 0 | 0 | 3 | 0 |
| RISE | 1 | 300 | 2 | 39 | 12 | 7 | 0 | 157 | 0 |
| SHARP_RISE | 0 | 20 | 10 | 0 | 0 | 3 | 0 | 0 | 0 |
| PULLBACK | 0 | 76 | 4 | 96 | 0 | 0 | 0 | 19 | 0 |
| RANGE | 1 | 13 | 0 | 8 | 214 | 5 | 0 | 14 | 0 |
| REBOUND | 0 | 0 | 0 | 0 | 0 | 103 | 8 | 62 | 0 |
| SHARP_DROP | 0 | 0 | 0 | 0 | 2 | 0 | 13 | 19 | 0 |
| DROP | 0 | 63 | 0 | 1 | 13 | 37 | 2 | 375 | 0 |
| DROP_STOP | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 14 | 2 |

全model/両target/両controlsの完全matrixはCONFUSION_MATRIX_9STATE.csvと03_confusion_all_models.png/SVGに保存。

## ↗️ Motion / Trend-context family

「上昇」は価格利益ではなく、固定State groupに合ったという意味。UP_MOVEとUP_CONTEXTを混同しない。

| target | family（B3） | predicted N | correct N | Precision | actual N | Recall |
| --- | --- | --- | --- | --- | --- | --- |
| NEXT_DISTINCT_PRIMARY | DOWN_MOVE | 620 | 431 | 69.52% | 580 | 74.31% |
| NEXT_DISTINCT_PRIMARY | NON_DIRECTIONAL_OR_STOP | 6 | 0 | 0.00% | 186 | 0.00% |
| NEXT_DISTINCT_PRIMARY | UP_MOVE | 734 | 504 | 68.66% | 594 | 84.85% |
| NEXT_OBSERVED_PRIMARY | DOWN_MOVE | 831 | 525 | 63.18% | 720 | 72.92% |
| NEXT_OBSERVED_PRIMARY | NON_DIRECTIONAL_OR_STOP | 252 | 224 | 88.89% | 307 | 72.96% |
| NEXT_OBSERVED_PRIMARY | UP_MOVE | 668 | 445 | 66.62% | 724 | 61.46% |
| NEXT_DISTINCT_PRIMARY | DOWN_CONTEXT | 640 | 426 | 66.56% | 610 | 69.84% |
| NEXT_DISTINCT_PRIMARY | RANGE_CONTEXT | 6 | 0 | 0.00% | 76 | 0.00% |
| NEXT_DISTINCT_PRIMARY | UP_CONTEXT | 714 | 486 | 68.07% | 674 | 72.11% |
| NEXT_OBSERVED_PRIMARY | DOWN_CONTEXT | 843 | 635 | 75.33% | 715 | 88.81% |
| NEXT_OBSERVED_PRIMARY | RANGE_CONTEXT | 247 | 214 | 86.64% | 255 | 83.92% |
| NEXT_OBSERVED_PRIMARY | UP_CONTEXT | 661 | 574 | 86.84% | 781 | 73.50% |

NEXT_DISTINCTのUP_MOVEは504/734＝68.66%、UP_CONTEXTは486/714＝68.07%。全model・family混同行列は専用CSV。family予測は9class argmaxの固定mappingで、family確率の再argmaxではない。

## 🧭 B1→B2→B3、fold再現性、集中


| target | 比較 | accuracy差(pp) | macro F1差(pp) | date-equal LL改善 | date-equal Brier改善 |
| --- | --- | --- | --- | --- | --- |
| NEXT_DISTINCT_PRIMARY | B0→B1 | +21.10 | +11.66 | 0.654164 | 0.141665 |
| NEXT_DISTINCT_PRIMARY | B1→B2 | +17.72 | +17.25 | -0.400001 | 0.0888386 |
| NEXT_DISTINCT_PRIMARY | B2→B3 | -2.87 | -2.99 | 0.257993 | -0.0272985 |
| NEXT_DISTINCT_PRIMARY | B1→B3 | +14.85 | +14.26 | -0.142008 | 0.0615401 |
| NEXT_OBSERVED_PRIMARY | B0→B1 | +39.81 | +51.81 | 0.734975 | 0.295592 |
| NEXT_OBSERVED_PRIMARY | B1→B2 | -4.80 | -8.00 | -0.0556511 | -0.0243056 |
| NEXT_OBSERVED_PRIMARY | B2→B3 | +0.57 | +0.36 | 0.0255488 | 0.00517202 |
| NEXT_OBSERVED_PRIMARY | B1→B3 | -4.23 | -7.64 | -0.0301023 | -0.0191335 |

NEXT_DISTINCTはB2/B3のaccuracy・macro F1がB1を上回るが、確率log lossはB1より悪い。B3はB2よりaccuracy −2.87pp、macro F1 −2.99pp、log loss改善、Brier悪化という混在で、Pathの安定したincremental valueは認証できない。NEXT_OBSERVEDはB1の67.85%がB3の63.62%より高く、persistence baselineを超えていない。

| Primary fold | model | N | date N | accuracy | macro F1 | date-equal LL |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | B0 | 767 | 8 | 28.55% | 4.94% | 1.92734 |
| 2 | B0 | 593 | 5 | 19.22% | 3.58% | 2.13966 |
| 3 | B0 | 0 | 0 | NA | 0.00% | NA |
| 1 | B1 | 767 | 8 | 44.20% | 16.31% | 1.32215 |
| 2 | B1 | 593 | 5 | 47.39% | 15.96% | 1.40714 |
| 3 | B1 | 0 | 0 | NA | 0.00% | NA |
| 1 | B2 | 767 | 8 | 57.37% | 31.26% | 1.79658 |
| 2 | B2 | 593 | 5 | 70.99% | 34.24% | 1.68805 |
| 3 | B2 | 0 | 0 | NA | 0.00% | NA |
| 1 | B3 | 767 | 8 | 51.76% | 25.29% | 1.41362 |
| 2 | B3 | 593 | 5 | 71.67% | 34.85% | 1.63001 |
| 3 | B3 | 0 | 0 | NA | 0.00% | NA |

B2/B3 accuracy改善は2foldで同方向でも、それだけでは昇格できない。State別・確率品質・集中制約は維持。B3 RISEのPrecision差CIは正でも、gross positive correctness gainは1日／1銘柄へ100%集中。PULLBACKの新規correctness gainは71.43%集中。REBOUNDはPrecisionのB1比較が改善したfoldは1つ。B3 DROPの調整CIは0を含む。B2もglobal calibration gateを通らない。PATH_INCREMENTAL_ASSESSMENT_V2.csvはB3対B2の同じ固定gateを適用し、合格0。18候補の多重比較CI tail1/720を結果後に緩めていない。

## 🧪 Controls・binary imbalance


| task | control | model | matched N | date N | fold N | REAL log loss | control log loss | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NEXT_DISTINCT_PRIMARY | TRUE_NULL | B1 | 1360 | 13 | 2 | 1.34068 | 1.99143 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_DISTINCT_PRIMARY | TRUE_NULL | B2 | 1360 | 13 | 2 | 1.89034 | 2.2988 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_DISTINCT_PRIMARY | TRUE_NULL | B3 | 1360 | 13 | 2 | 1.67326 | 2.28247 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_DISTINCT_PRIMARY | SHIFT60 | B1 | 125 | 2 | 1 | 1.20761 | 1.90759 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_DISTINCT_PRIMARY | SHIFT60 | B2 | 125 | 2 | 1 | 1.4957 | 7.95446 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_DISTINCT_PRIMARY | SHIFT60 | B3 | 125 | 2 | 1 | 1.41714 | 7.92224 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_OBSERVED_PRIMARY | TRUE_NULL | B1 | 1751 | 13 | 2 | 1.03812 | 1.90655 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_OBSERVED_PRIMARY | TRUE_NULL | B2 | 1751 | 13 | 2 | 1.22319 | 2.48936 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_OBSERVED_PRIMARY | TRUE_NULL | B3 | 1751 | 13 | 2 | 1.1876 | 3.13052 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_OBSERVED_PRIMARY | SHIFT60 | B1 | 153 | 2 | 1 | 1.29729 | 2.1914 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_OBSERVED_PRIMARY | SHIFT60 | B2 | 153 | 2 | 1 | 1.9093 | 7.26129 | NO_COMPARABLE_CONTROL_WARNING |
| NEXT_OBSERVED_PRIMARY | SHIFT60 | B3 | 153 | 2 | 1 | 1.87869 | 7.21728 | NO_COMPARABLE_CONTROL_WARNING |
| TRANSITION_WITHIN30 | TRUE_NULL | B1 | 347 | 4 | 2 | 0.0312692 | 0.0439503 | NO_COMPARABLE_CONTROL_WARNING |
| TRANSITION_WITHIN30 | TRUE_NULL | B2 | 347 | 4 | 2 | 0.0323142 | 0.0425709 | NO_COMPARABLE_CONTROL_WARNING |
| TRANSITION_WITHIN30 | TRUE_NULL | B3 | 347 | 4 | 2 | 0.0516305 | 0.109602 | NO_COMPARABLE_CONTROL_WARNING |
| TRANSITION_WITHIN30 | SHIFT60 | B1 | 68 | 1 | 1 | 0.00639864 | 1.00009e-12 | REGIME_PERSISTENCE_OR_SHIFT_CONTROL_WARNING |
| TRANSITION_WITHIN30 | SHIFT60 | B2 | 68 | 1 | 1 | 0.00264525 | 1.00009e-12 | REGIME_PERSISTENCE_OR_SHIFT_CONTROL_WARNING |
| TRANSITION_WITHIN30 | SHIFT60 | B3 | 68 | 1 | 1 | 0.00652187 | 1.00006e-12 | REGIME_PERSISTENCE_OR_SHIFT_CONTROL_WARNING |

TRUE_NULL warning0。within-date/securityのmarginal class priorを残すため理想的global iid nullではない。B0 equalityは予期されたものとして除外し、B1/B2/B3は固定control判定に従った。V1 STOP ruleの撤回はしていない。V2 SHIFT60 warning3セルはbinaryの68件・1日／1foldで、全control labelsがTRANSITIONという偏り。REGIME_PERSISTENCE_OR_SHIFT_CONTROL_WARNINGとして保存し、actual leakageとはしない。直接時刻／partition audit違反0。

Binary REAL OOFは347件・4日、TRANSITION345／NO_TRANSITION2。B0/B1/B2は全TRANSITION予測で99.42% accuracyでもbalanced accuracy50%にすぎない。B3は98.27%、balanced49.42%。NO_TRANSITIONの支持数不足を保持し、発生予測が完成したとは主張しない。

## 💹 V1価格negativeの継承・V2 secondary

価格targetはV1どおり（future raw Close−current raw Close）/U、単位JPY/Uであり%、return、利益、Entry/EXITではない。異なる銘柄価格scaleの影響が大きい。この定義を有利な尺度へ修正していない。V1とV2は別母集団で、absolute MSEを市場性能の改善と直結しない。

| version | horizon | model | N | date N | MSE | date-equal MSE |
| --- | --- | --- | --- | --- | --- | --- |
| V2 | 5 | B0 | 1443 | 10 | 1.29533e+09 | 6.26177e+08 |
| V2 | 5 | B1 | 1443 | 10 | 1.29486e+09 | 6.26058e+08 |
| V2 | 5 | B2 | 1443 | 10 | 1.29287e+09 | 6.26321e+08 |
| V2 | 5 | B3 | 1443 | 10 | 1.29279e+09 | 6.26527e+08 |
| V2 | 15 | B0 | 672 | 9 | 6.21764e+09 | 2.68376e+09 |
| V2 | 15 | B1 | 672 | 9 | 6.23046e+09 | 2.69623e+09 |
| V2 | 15 | B2 | 672 | 9 | 6.25988e+09 | 2.69614e+09 |
| V2 | 15 | B3 | 672 | 9 | 6.26713e+09 | 2.69946e+09 |
| V2 | 30 | B0 | 360 | 4 | 1.78482e+10 | 1.53448e+10 |
| V2 | 30 | B1 | 360 | 4 | 1.78835e+10 | 1.54416e+10 |
| V2 | 30 | B2 | 360 | 4 | 1.79062e+10 | 1.54539e+10 |
| V2 | 30 | B3 | 360 | 4 | 1.78433e+10 | 1.54295e+10 |
| V1_RETAINED | 5 | B0 | 1544 | 5 | 3.25756e+07 | 2.86614e+07 |
| V1_RETAINED | 5 | B1 | 1544 | 5 | 3.529e+07 | 3.12862e+07 |
| V1_RETAINED | 5 | B2 | 1544 | 5 | 3.5544e+07 | 3.24588e+07 |
| V1_RETAINED | 5 | B3 | 1544 | 5 | 3.74689e+07 | 3.40905e+07 |
| V1_RETAINED | 15 | B0 | 1096 | 5 | 9.23054e+07 | 7.28019e+07 |
| V1_RETAINED | 15 | B1 | 1096 | 5 | 1.01731e+08 | 8.072e+07 |
| V1_RETAINED | 15 | B2 | 1096 | 5 | 1.18826e+08 | 9.4098e+07 |
| V1_RETAINED | 15 | B3 | 1096 | 5 | 2.1554e+08 | 1.63274e+08 |
| V1_RETAINED | 30 | B0 | 775 | 5 | 2.68356e+08 | 1.70465e+08 |
| V1_RETAINED | 30 | B1 | 775 | 5 | 2.76498e+08 | 1.75439e+08 |
| V1_RETAINED | 30 | B2 | 775 | 5 | 4.144e+08 | 2.65765e+08 |
| V1_RETAINED | 30 | B3 | 775 | 5 | 5.70069e+08 | 3.55965e+08 |

V1はB2/B3全horizonでB0よりMSE悪化を保持。V2ではrow-weighted MSEのB3 H5/H30に微小改善があるが、H15は悪化、date-equal MSEはB2/B3とも5/15/30でB0より悪い。価格secondaryでnext-State gateを救済しない。

## 🔍 独立監査・予算・境界


| 項目 | 実数／結果 |
| --- | --- |
| 独立main checks | 1747929 |
| 独立supplement checks | 1062 |
| 独立不一致 | 0 / PASS |
| Synthetic target probes | 10 paths / 20 assertions / 0 mismatch |
| V2 fit operations | 210 / cap648 |
| global bootstrap draws | 1000 / cap1000 |
| independent新draw／refit／kernel | 各0 |
| State9旧8050 endpoint | reuse、再kernel0 |
| 新規Frozen generation | 11445 steps / cap36864 |
| provider requests | 251 / cap900 |
| isolated Actions | 2 / cap2、fanout1 |
| V1予算 | 超過3000保持、V2は0超過 |
| State9 / Path / profile / M0変更 | 各0 |
| Common Holdout / Protected | 各0 |
| Fresh / OOS / Prospective | 各0 |
| Entry / EXIT / profit | 各0 |
| Capital / Portfolio / orders / external AI | 各0 |
| future classifier input | 0（Development future labelsのみ許可） |
| raw / secret export | 各0 |
| main merge / force push | 各0 |
| graphs | 11種類×PNG/SVG、CSV根拠あり |

独立監査はV2 candidate helperをimportせず、保存traceから63featuresのprimitive再構成、endpoint tupleからtransition/null/censoring、exact Close/U price、fold/donor purge、混同行列、family、matched control、保存1000indicesのCI、ridge最終normal equation／OOF predictionを直接再計算。State9/Path kernel全再audit0、モデル再fit0。inner-grid losses自体は別fitせず、保存lossからの選択を照合したという限界を明示する。

## 📋 必須27問への回答

1. NEXT_DISTINCT overall：B0 24.49%、B1 45.59%、B2 63.31%、B3 60.44%。
2. NEXT_OBSERVED overall：B0 28.04%、B1 67.85%、B2 63.05%、B3 63.62%。
3–7. 全9State Precision／Recall／F1／predicted・actual support／9×9：上表・全model CSV・heatmap。
8. RISE次distinct：B3 327/545＝60.00%、B2 63.23%。
9. SHARP_RISE次distinct：B3 0/4＝0.00%、support不足。
10. REBOUND次distinct：B3 125/185＝67.57%。
11. UP_MOVE次distinct：B3 504/734＝68.66%。
12. UP_CONTEXT次distinct：B3 486/714＝68.07%。
13. B1→B2：Primary accuracy＋17.72pp、macro F1＋17.25pp、date-equal LL悪化。
14. B2→B3：Primary accuracy−2.87pp、macro F1−2.99pp。確率品質はLL改善／Brier悪化の混在。
15. Path incremental value：固定昇格gateで認証できない（合格0）。
16. fold再現：2評価fold、Primary accuracy改善はB1比較で両foldだがState・calibration gate全通過なし。第3fold0は保持。
17. 集中：上記gross positive shareはStateにより1日／1銘柄依存あり。多銘柄支持数だけでは否定しない。
18. TRUE_NULL：matched log loss比較でwarning0。これ単独でpredictive promotionにはならない。
19. SHIFT60：regime stress warning、actual leakageは直接監査で未証明。V1正式STOP維持。
20. Bootstrap：V2は1000一度生成、checker0新drawで解消。V1超過は取り消さない。
21. V1 Fold2=0：開始点欠損、exact horizon欠損、中間unknown/rejected等のexact counts表。
22. V2 Primary OOF：13日／2評価fold／1360行。secondaryは13日／2fold／1751行、binary4日／2fold／347行。
23. Price：V1negative保持。V2 date-equal MSEもB2/B3全horizonでB0より悪い。
24. Entryへ渡せるもの：研究用Frozen特徴schema・失敗/支持数Evidenceのみ。昇格State／採用Path featureは0、Entry設計自動開始なし。
25. Holdout準備：未達。開封0。新しいDevelopment/calibration計画を別Contract化して判断。
26. State9／Path意味変更：各0、profile／M0変更も0。
27. Holdout／Protected／Entry／EXIT／profit exposure：今回delta各0。過去unknown/nonzero exposureは継承し0へリセットしない。

## 📦 保存と次工程

REPORT、CSV、11種graphs、OOF・fits・labels、new/old特徴trace、原本V1 ZIP、hash manifestを単一ZIPへ保存。Public GitHubはContract・source・aggregate/receiptsのみ。row-level private evidenceや原価格・秘密値をGitHubに追加していない。

最終status B。次工程は自動Entryではない。取得未完了33候補とU_UNAVAILABLEを明示した新規Development計画／V3の可否を判断する。V2結果を見て同じV2で日・銘柄を追加／補充／calibration改良することはしない。

### 非blockingなfit記録finding

実行append ledgerは206行までで、receiptの210と4行差がある。84 final fitted artifacts＋保存された42×3 inner-grid評価から必要fit210を別に再集計し、実行counter／OOF固定receiptの210と一致した。予算は210を計上、648以内。欠けた行を捏造して追記せず、元ledgerを保持。欠落原因はUNKNOWN、数値／予測の独立再現不一致は0。このprovenance限界をFIT_LEDGER_COMPLETENESS_FINDING.jsonに明示した。

### 空foldの表示修復

初回fold図がmacroの空集合規約0を測定値として描いたため、第3foldはN=0のNO EVALUATION表示へ修復した。CSV・metric規約・予測・Contractは変更0。初回図はSUPERSEDEDとして保持し、focused redraw1件を予算へ計上。
