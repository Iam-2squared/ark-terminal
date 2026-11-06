# Ark Terminal — State Predictiveness V4 最終報告

作成JST：2026-10-02T15:13:20.736798+09:00

**BLOCKED_V4_INTEGRITY**。Integrity：FAIL_CONTROL。独立再計算：PASS、不一致0。Entryへ渡すモデル：なし。

R2の危険UP→DOWN誤予測はR1より点推定で低下し、V3と同方向だった。 R1 18.53% → R2 15.38%、改善 +3.15 pp。Core 882 anchor／27 OOF日／2 fold、DOWN 167／UP 569。

事前固定したV4 §12のTRUE_NULL integrity判定に抵触したモデル：R3。これはcontrolがREALと同等以上という判定であり、未来feature leakageが直接立証されたという意味ではない。

## 主要結果

| model | UP予測→DOWN実現 | DOWN P | DOWN R | DOWN F1 | UP P | UP R | UP F1 | macro F1 | 日均等LL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | 167/882 = 18.93% | NA | 0.00% | NA | 64.51% | 100.00% | 78.43% | 19.61% | 0.976927 |
| R1 | 159/858 = 18.53% | 33.33% | 4.79% | 8.38% | 65.73% | 99.12% | 79.05% | 21.86% | 0.968635 |
| R2 | 120/780 = 15.38% | 46.24% | 25.75% | 33.08% | 68.08% | 93.32% | 78.72% | 28.60% | 1.13406 |
| R3 | 113/767 = 14.73% | 45.76% | 16.17% | 23.89% | 68.97% | 92.97% | 79.19% | 29.77% | 1.49397 |
| R4 | 105/734 = 14.31% | 38.10% | 19.16% | 25.50% | 70.84% | 91.39% | 79.82% | 31.86% | 0.9863 |

DOWNは価格損失ではなく、V3と同じ30 scheduled tradable slot内の最初の確認済みState/context反転。UP継続は真のRISE/SHARP_RISE遷移とcontext/local=+1でありHOLDではない。REBOUNDもcontext DOWNなら下降反転先に含む。minute anchorと窓が重複するため独立売買試行とは扱わない。

## V3改善の再検証

| model | V3危険率 | V4危険率 | V4−V3 | V4 95%日cluster区間 |
| --- | --- | --- | --- | --- |
| R0 | 16.42% | 18.93% | +2.52 pp | 9.91%–31.01% |
| R1 | 17.70% | 18.53% | +0.84 pp | 9.35%–30.69% |
| R2 | 12.78% | 15.38% | +2.61 pp | 6.56%–27.36% |
| R3 | 14.26% | 14.73% | +0.47 pp | 5.66%–26.80% |
| R4 | 13.86% | 14.31% | +0.44 pp | 6.43%–24.83% |

![V3 vs V4危険誤予測](CHARTS/01_v3_vs_v4_dangerous_rate.png)

| 比較 | 危険率改善 | 95%改善CI | DOWN F1差 | UP F1差 | macro F1差 | 日均等LL改善 | 日均等Brier改善 | ECE改善 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1→R2 | +3.15 pp | +1.19 pp–+6.32 pp | +24.70 pp | -0.32 pp | +6.75 pp | -0.165424 | 0.0987145 | -0.0653309 |
| R2→R3 | +0.65 pp | -0.38 pp–+1.60 pp | -9.18 pp | +0.47 pp | +1.17 pp | -0.359908 | 0.00470496 | -0.00931412 |
| R2→R4 | +1.08 pp | -0.63 pp–+3.23 pp | -7.58 pp | +1.09 pp | +3.25 pp | 0.147759 | 0.00384748 | 0.0493316 |

差の向きは「改善が正」。V3とV4は別の日・銘柄のcohortで、V3の12.78%を同じ分母で再試験したものではない。V4内のR1/R2/R3/R4は同じtest keysで比較する。PathがR2を超えない場合は、記述/anatomyでの有用性とpredictorへのincremental promotionを分離する。

![モデル・確率品質](CHARTS/02_r1_r4_reversal_metrics.png)

![反転・継続P/R/F1](CHARTS/03_down_up_precision_recall_f1.png)

## Development拡張とsplit

| 項目 | 結果 |
| --- | --- |
| 事前承認145日／142リンク | その範囲内だけで取得 |
| 未exposed固定リンク | 106、元の時系列順 |
| 新しい銘柄候補 | 318 |
| 新規取得status | {"ACQUIRED": 216, "PROVIDER_FAILURE": 27, "RAW_UNAVAILABLE": 21, "U_UNAVAILABLE": 54} |
| 新しい取得日 | 94 |
| 保存済み再利用 | 90 pairs／29,305 endpoints |
| 全入力 | 306 pairs／128 dates／98,862 endpoints |
| observed／null | 16,594／82,268 |
| OOF Core | 882／27日／2fold |
| Core support | {"DOWN_REVERSAL": 167, "NO_DECISION_WITHIN30": 2, "RANGE_OR_STOP": 144, "UP_CONTINUE": 569} |
| 選択済み未取得・旧新合計 | 109 |
| metadata段階の未選択capacity | 0 |
| 結果によるdate/security補充 | 0 |

36のV1/V2/V3 exposure日は学習専用。新しい最初の5日はwarmup、残り101日は34/34/33の3固定fold。raw/U/label availabilityを見て日付を移動しない。meta/factorだけでfirst3を選び、分足が空でも別銘柄に交換しない。元の7件は取得不能Evidenceを再利用して保持した。UNAVAILABLE_INPUTSにはmetadata不成立と選択済みraw/U不成立を区別して保存し、実在しないsecurityを作らない。new分足取得はcurrent/previousの承認済み依存日のみ。

| fold | 固定test日 | 入力があるtest日 | train日 | Core anchors | Core有効日 |
| --- | --- | --- | --- | --- | --- |
| 1 | 34 | 29 | 0 | 0 | 0 |
| 2 | 34 | 34 | 31 | 603 | 17 |
| 3 | 33 | 31 | 70 | 279 | 10 |

## Calibrationと安定性

| model | 未較正日均等LL | 較正後日均等LL | 較正後日均等Brier | 較正後ECE |
| --- | --- | --- | --- | --- |
| R0 | 0.910654 | 0.976927 | 0.60067 | 8.00% |
| R1 | 0.888616 | 0.968635 | 0.577809 | 9.06% |
| R2 | 0.908501 | 1.13406 | 0.479095 | 15.60% |
| R3 | 1.08049 | 1.49397 | 0.47439 | 16.53% |
| R4 | 0.835118 | 0.9863 | 0.475247 | 10.66% |

較正でouter日均等LLが改善したモデル：なし。同一のtrain-only温度gridを継承し、alphaとtemperatureには同じ最後のtrain日を使用する限界も保持した。outer testでmethod/temperatureを探索していない。uncal/cal両方のLL/Brier/ECEを保存し、結果を見て較正方法を追加しない。

| model | V3較正後日均等LL | V4較正後日均等LL | V3較正後Brier | V4較正後Brier | V3 ECE | V4 ECE |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | 0.939986 | 0.968635 | 0.476468 | 0.577809 | 21.13% | 9.06% |
| R2 | 4.74978 | 1.13406 | 0.380238 | 0.479095 | 21.40% | 15.60% |
| R3 | 2.9031 | 1.49397 | 0.437373 | 0.47439 | 17.60% | 16.53% |
| R4 | 2.26379 | 0.9863 | 0.399695 | 0.475247 | 13.81% | 10.66% |

V3→V4の数値比較は異なるDevelopment cohortであり、calibration法の改善効果を分離した比較ではない。R2のV3較正後日均等LL 4.74978 → V4 1.13406 という変化と、V4内で未較正 0.908501 → 較正後 1.13406 という変化を混同しない。

![calibration](CHARTS/04_calibration_curve.png)

![DOWN bucket](CHARTS/05_down_probability_vs_actual.png)

![fold安定性](CHARTS/06_fold_stability.png)

![日・銘柄](CHARTS/07_date_security_concentration.png)

| model | 比較先 | 危険誤予測減少の最大日share | 最大銘柄share | 正解増加の最大日share | 最大銘柄share | 集中gate |
| --- | --- | --- | --- | --- | --- | --- |
| R2 | R1 | 23.08% | 23.08% | 21.05% | 21.05% | True |
| R3 | R1 | 21.74% | 21.74% | 33.33% | 33.33% | True |
| R3 | R2 | 33.33% | 33.33% | 38.71% | 38.71% | True |
| R4 | R1 | 22.22% | 22.22% | 18.75% | 18.75% | True |
| R4 | R2 | 58.82% | 58.82% | 29.63% | 29.63% | False |

## Path Anatomy

| 長さ | anchor N | sequence N | 完全history N | 支持基準合格 |
| --- | --- | --- | --- | --- |
| 1 | 882 | 4 | 882 | 2 |
| 2 | 882 | 18 | 782 | 3 |
| 3 | 882 | 51 | 689 | 2 |
| 4 | 882 | 93 | 615 | 0 |

記述的支持基準N>=100・日>=8・銘柄>=3を満たすsequenceは合計7。長さ1=current、長さ2=current＋直前1 completed run、長さ3/4はその延長。R4 predictorの前run1–4はV3と同じ。RISE開始、SHARP_RISE開始、PULLBACK含有、RISE_STOP含有は各長さの別CSVを保存。V3と共通するsequenceについて、cohort全体に対するUP/DOWN rate差の同方向再現をPATH_TENDENCY_V3_V4.csvに保存した。小Nの100%はpromotion根拠にしない。

| sequence | V3 N | V4 N | V3 DOWN | V4 DOWN | V3 UP | V4 UP | UP傾向同方向 | DOWN傾向同方向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISE | 355 | 516 | 21.41% | 18.02% | 69.86% | 63.95% | True | False |
| PULLBACK | 216 | 281 | 6.48% | 17.44% | 91.67% | 70.82% | True | True |
| RISE&gt;PULLBACK | 211 | 228 | 6.64% | 21.49% | 91.47% | 72.37% | True | False |
| PULLBACK&gt;RISE | 193 | 140 | 12.95% | 7.14% | 84.97% | 83.57% | True | True |
| DROP&gt;RISE | 75 | 133 | 32.00% | 28.57% | 48.00% | 48.87% | True | True |
| RISE&gt;PULLBACK&gt;RISE | 193 | 131 | 12.95% | 6.11% | 84.97% | 83.97% | True | True |
| PULLBACK&gt;RISE&gt;PULLBACK | 153 | 120 | 7.19% | 25.83% | 90.20% | 65.00% | True | False |
| &lt;MISSING&gt;&gt;RISE | 30 | 99 | 76.67% | 29.29% | 23.33% | 56.57% | True | True |
| &lt;MISSING&gt;&gt;&lt;MISSING&gt;&gt;RISE | 30 | 99 | 76.67% | 29.29% | 23.33% | 56.57% | True | True |
| &lt;MISSING&gt;&gt;&lt;MISSING&gt;&gt;&lt;MISSING&gt;&gt;RISE | 30 | 99 | 76.67% | 29.29% | 23.33% | 56.57% | True | True |
| RISE&gt;PULLBACK&gt;RISE&gt;PULLBACK | 153 | 79 | 7.19% | 13.92% | 90.20% | 72.15% | True | True |
| PULLBACK&gt;RISE&gt;PULLBACK&gt;RISE | 132 | 76 | 18.94% | 7.89% | 79.55% | 78.95% | True | False |

![Path長さ](CHARTS/08_path_length_reversal_support.png)

![反転Paths](CHARTS/09_top_down_reversal_paths.png)

![継続Paths](CHARTS/10_top_up_continue_paths.png)

## Negative controlsとintegrity

| control | model | matched N | 日 | REAL日均等LL | control日均等LL | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| TRUE_NULL | R2 | 882 | 27 | 1.13406 | 1.51057 | False |
| TRUE_NULL | R3 | 882 | 27 | 1.49397 | 1.3135 | True |
| TRUE_NULL | R4 | 882 | 27 | 0.9863 | 1.25099 | False |
| SHIFT60 | R2 | 53 | 5 | 0.78421 | 2.45733 | False |
| SHIFT60 | R3 | 53 | 5 | 0.786024 | 1.45257 | True |
| SHIFT60 | R4 | 53 | 5 | 0.797477 | 1.52193 | True |

事前固定したV4 §12のTRUE_NULL integrity判定に抵触したモデル：R3。これはcontrolがREALと同等以上という判定であり、未来feature leakageが直接立証されたという意味ではない。 V3ではwarning／promotion vetoだったが、ユーザーV4 §12の明示条件に従い、primary calibrated TRUE_NULLの日均等LLがREAL以下、またはR1へのpositive gainがREALの90%以上という判定を新label前に固定した。低accuracyや悪calibrationだけでBLOCKにはしない。SHIFT60は同じ連続bridgeでのregime/dependence stressで、単独ではfuture leakageの証明にしない。timestamp、target順序、fold、train/end purge、whole-label donor移動は独立logicで直接監査した。

## 9State secondary

| task | R1 accuracy | R2 accuracy | R3 accuracy | R4 accuracy | V4 support | 有効日 |
| --- | --- | --- | --- | --- | --- | --- |
| NEXT_DISTINCT_PRIMARY | 42.23% | 50.76% | 55.19% | 52.79% | 3834 | 48 |
| NEXT_OBSERVED_PRIMARY | 77.61% | 77.24% | 77.57% | 71.51% | 4851 | 53 |

![V2/V3/V4 precision](CHARTS/11_nine_state_precision_v2_v3_v4.png)

![9x9混同行列](CHARTS/12_nine_by_nine_confusion.png)

全9classは支持0でも残す。分母0はNAであり0%への置換ではない。9State精度とrare Stateの母数はsecondaryで、reversal gateの代わりにしない。V2/V3との比較は別cohortでありcontrolled incremental gainではない。略号RS/R/SR/PB/RG/RB/SD/D/DSはRISE_STOP/RISE/SHARP_RISE/PULLBACK/RANGE/REBOUND/SHARP_DROP/DROP/DROP_STOP。

## 独立監査・予算・禁止境界

| 項目 | 結果 |
| --- | --- |
| 独立監査 | PASS／5,704,657 assertions／mismatch 0 |
| provider HTTP | 1367/2200 |
| Frozen step | 69557/110000 |
| fits | 384/1200（final 120＋inner 264） |
| bootstrap | 1000 vectors exactly once；全metric共用；独立new draw0 |
| Actions | 1run／fanout1 |
| 12図 | PASS |
| State9/Path/profile/M0/target/family変更 | 各0 |
| Holdout/Protected/Fresh/OOS/Prospective | 各0 |
| Entry/EXIT/profit/Capital/Portfolio/orders | 各0 |
| main merge/force push/external AI | 各0 |

監査は同じassistantによる別コードで、外部人間の独立査読ではない。保存features/labels/split/OOF/fit係数、inner選択、target、risk、metric、calibration、Path、9State、controls、bootstrapを再計算した。normal equationは検算するがrefitしない。State9/Path kernel全semantic suiteは再実行していない。purge済みfull API responseの再取得監査でもない。historical known_at UNKNOWNとbar_end availability仮定を区別する。V1 3000/cap1000超過、V2の4fit ledger gap、旧16FAIL／88workflow incident、過去outside exposure unknown/nonzeroを保存しリセットしない。

独立checker初回はgrouped containerへのappendが一時listへ書かれる実装不具合でPath検算時に例外停止した。格納行を修正し、全OOF recordのgroup収容assertionを追加してread-only監査を再実行した。未完了の初回をPASSとは扱わない。AUDIT_IMPLEMENTATION_REPAIR_RECEIPT_V4.jsonに失敗source hash・原因・修正境界を保存し、candidate OOF・ラベル・features・model・calibration・gateには変更0、追加fit/draw0。figure03のlegend位置と空foldの表示も提示上だけ修正した。

## Promotion・次段階

| model | baseline | support | danger改善 | 主要反転metric | calibration | DOWN recall | 集中 | TRUE NULL不合格 | 総合 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R2 | R1 | True | True | True | False | True | True | False | False |
| R3 | R1 | True | True | True | False | True | True | True | False |
| R3 | R2 | True | False | False | False | False | True | True | False |
| R4 | R1 | True | True | True | True | True | True | False | True |
| R4 | R2 | True | False | False | True | False | False | False | False |

Entryへ渡す候補：なし。V4を結果に合わせてtarget/model/calibrationで修復してpromotionしない。必要な次研究は新しいContractで、V4をexposedとして固定する。 将来EXIT研究へ再利用できるのは、観測済みのPath/context/stop/gap証拠とrisk指標・prefix/provenanceであり、EXIT/HOLD ruleやprofit Evidenceではない。

日／銘柄などのsubsetが1日clusterしか持たない場合、保存global bootstrapによるCIは点推定へ退化し、有効な不確実性認証ではない。risk CSVのcluster_CI_informativeを確認する。新しいwithin-date drawで救済しない。主要metricのadjusted-tail CIは固定gateであり、全追加macro比較を含む厳密なfamily-wise error保証は主張しない。provider cap guardの事前I/O counterと実HTTPはRUNNER_ACCOUNTING_V4で区別し、原本receiptを保持する。

## V2/V3/V4 secondaryの母数比較

| task | State | V2 support | V3 support | V4 support | V4−V3 |
| --- | --- | --- | --- | --- | --- |
| NEXT_DISTINCT_PRIMARY | RISE_STOP | 67 | 107 | 258 | 151 |
| NEXT_DISTINCT_PRIMARY | RISE | 354 | 445 | 887 | 442 |
| NEXT_DISTINCT_PRIMARY | SHARP_RISE | 60 | 2 | 68 | 66 |
| NEXT_DISTINCT_PRIMARY | PULLBACK | 193 | 274 | 331 | 57 |
| NEXT_DISTINCT_PRIMARY | RANGE | 76 | 67 | 271 | 204 |
| NEXT_DISTINCT_PRIMARY | REBOUND | 180 | 178 | 562 | 384 |
| NEXT_DISTINCT_PRIMARY | SHARP_DROP | 54 | 42 | 126 | 84 |
| NEXT_DISTINCT_PRIMARY | DROP | 333 | 309 | 1070 | 761 |
| NEXT_DISTINCT_PRIMARY | DROP_STOP | 43 | 66 | 261 | 195 |
| NEXT_OBSERVED_PRIMARY | RISE_STOP | 35 | 45 | 107 | 62 |
| NEXT_OBSERVED_PRIMARY | RISE | 518 | 567 | 1243 | 676 |
| NEXT_OBSERVED_PRIMARY | SHARP_RISE | 33 | 5 | 31 | 26 |
| NEXT_OBSERVED_PRIMARY | PULLBACK | 195 | 230 | 342 | 112 |
| NEXT_OBSERVED_PRIMARY | RANGE | 255 | 293 | 843 | 550 |
| NEXT_OBSERVED_PRIMARY | REBOUND | 173 | 186 | 502 | 316 |
| NEXT_OBSERVED_PRIMARY | SHARP_DROP | 34 | 4 | 53 | 49 |
| NEXT_OBSERVED_PRIMARY | DROP | 491 | 437 | 1597 | 1160 |
| NEXT_OBSERVED_PRIMARY | DROP_STOP | 17 | 24 | 133 | 109 |

| task | model | V2 accuracy | V3 accuracy | V4 accuracy |
| --- | --- | --- | --- | --- |
| NEXT_DISTINCT_PRIMARY | R1 | 45.59% | 44.56% | 42.23% |
| NEXT_DISTINCT_PRIMARY | R2 | 63.31% | 69.53% | 50.76% |
| NEXT_DISTINCT_PRIMARY | R3 | 60.44% | 70.13% | 55.19% |
| NEXT_OBSERVED_PRIMARY | R1 | 67.85% | 79.12% | 77.61% |
| NEXT_OBSERVED_PRIMARY | R2 | 63.05% | 71.19% | 77.24% |
| NEXT_OBSERVED_PRIMARY | R3 | 63.62% | 77.78% | 77.57% |

## 必須21問への回答

| 番号 | 問い | 回答 |
| --- | --- | --- |
| 1 | R2の12.78%改善再現 | 危険FP改善はV3と同方向、95%差CIは正。ただし絶対率12.78%は未再現：V4 R2 15.38%。別cohort比較で、最終認証は BLOCKED_V4_INTEGRITY。 |
| 2 | R1→R2改善量 | +3.15 pp、95%CI +1.19 pp–+6.32 pp |
| 3 | R2→R3/R4 | 危険率は点推定でR3 +0.65 pp／R4 +1.08 pp 改善したが、両差CIは0を含む。DOWN F1は各低下、R2超えのincremental promotionなし。 |
| 4 | DOWN P/R/F1 | R2 46.24%/25.75%/33.08% |
| 5 | UP P/R/F1 | R2 68.08%/93.32%/78.72% |
| 6 | calibration | V4内ではtrain-only較正で日均等LL改善モデルなし。R2 0.908501→1.13406、R1比calibration gate未達。V3比較は別cohort。 |
| 7 | OOF日数 | 27 |
| 8 | fold数 | 2 |
| 9 | DOWN support | 167 |
| 10 | UP support | 569 |
| 11 | 1日／1銘柄集中 | R2集中gate True。risk減少・correctness gainを各shareで保存。 |
| 12 | TRUE NULLに勝ったか | R2/R4はmatched日均等LLでTRUE NULLより良い。R3はTRUE NULLの方が良く、固定§12で全WorkをBLOCK。未来leakageの直接立証ではない。 |
| 13 | Path Anatomy傾向 | 共通 66 sequenceのcohort相対傾向はUP 50／DOWN 54 が同方向。下降傾向は一様な再現ではない。V4支持基準合格は全長さで 7、rule化なし。 |
| 14 | 9State精度 | R2 V3→V4：next-distinct 69.53%→50.76%、next-observed 71.19%→77.24%。別cohort、secondaryのみ。 |
| 15 | rare State support | 全9Stateのactual supportは両taskでV3より増加。SHARP_RISEは NEXT_DISTINCT_PRIMARY 2→68／NEXT_OBSERVED_PRIMARY 5→31。小Nをpromotion根拠にしない。 |
| 16 | Development未取得 | 選択済み旧新 109件。metadata未選択capacity 0枠は別計上。 |
| 17 | Entryへ渡せるか | 不可 |
| 18 | 渡すモデル | R2/R3/R4いずれもなし |
| 19 | EXIT再利用Evidence | causal Path/context/stop/gap anatomy、riskとsupport、provenance。EXIT/HOLD/利益は未研究。 |
| 20 | 禁止exposure | Holdout/Protected/Entry/EXIT/profit今回delta各0。過去unknown/nonzero保持。 |
| 21 | identity変更 | State9/Path/profile/M0各0、family/targetも0。 |
