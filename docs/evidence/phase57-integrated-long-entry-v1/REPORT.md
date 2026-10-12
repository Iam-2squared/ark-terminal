# COMPREHENSIVE INTEGRATED LONG ENTRY v1 — First Measurement

Decision: **FIRST_INTEGRATED_MEASUREMENT_COMPLETE**  
OVERALL_STATUS: **HARD_FAIL**  
Candidate status: **INTEGRATED_LONG_ENTRY_V1_VALIDATION_HARD_FAIL_NOT_FROZEN**

今回は統合候補1本の初回性能測定。結果後の修正・再学習は0。CandidateのFreeze/KILL判断を自動化せず、結果を固定してSTOP。DEV TEST / Fresh / OOSは評価していない。

## Git・固定契約・上流

| 項目 | 固定値 |
| --- | --- |
| 開始HEAD | 88d9623dda24c5201dadea666c0ec74e4a29ddf1 |
| Protocol precommit | b20aec53bb318e1db119758b018b8c4f8bc0b128 |
| Protocol SHA256 | 93dab410a6116d52bc70489a1322bcc16e041c43591e6a94bf7eba4d96ef004c |
| Feature manifest SHA256 | 9e052344fa5eabf792a377101f050a13e3dfd1965d63f628da95276e7e782026 |
| Model SHA256 | a2d571685879e02468daa1338efbdbecf0d7046cea3099262cce4e19c14b2eb4 |
| Training manifest SHA256 | 05d334c89ab105e0da12ae247c2225099b365ae945981946301e4462a9a319ed |
| Validation ledger SHA256 | 6dbcb978ea2dfe159d8789f63683ff16b86a93ad4ee3690fa0a53b9a05af78d9 |
| PR | Iam-2squared/ark-terminal #587 / Open / Draft / unmerged at start |
| Branch | research/phase57-long-only-cash-equity |
| Final checked HEAD | GitHub Actions final-ci-receipt.json; exact SHA in final user report |

¥75 Selector、Frozen NEW Opportunity Generator、INITIAL/DIP identity、Candidate A、Fixed12 fallback・cost0.05ppはsource pinsと既存freeze pinsで照合。変更なし。v1/v2/v3の失敗Evidenceは保存したまま。

## 単一Architectureと情報制約

DecisionTreeRegressorの3出力共有木。max_depth=4、min_samples_leaf=100、criterion=squared_error、random_state=57。最大16葉、TRAINのみ1 fit、calibration0、sweep0。出力はurgent/viable/failureの葉内重み付き比率であり、校正済み確率とは扱わない。TRAIN中央値補完＋全入力missing indicator、scalingはidentity。各Opportunityの学習weight合計1。

既存Inventory66項目 = AVAILABLE_PIT16 / DERIVABLE_PIT27 / MISSING15 / FUTURE_ONLY_FORBIDDEN8。モデル入力66は別の数え方で、利用可能な従来43入力＋既存v3状態記述23。欠損15・禁止8を投入していない。66という数の一致は偶然。

| 入力family | 入力数 |
| --- | --- |
| anchorVolumeMomentumVWAP | 6 |
| pathVolatility | 12 |
| postOpportunityState | 23 |
| priceTrend | 15 |
| selectorOpportunityTime | 10 |

Selector / time / breadth、trend・range・momentum、path・volatility、anchorのrelativeVolume/VWAP等、post-opportunity Pullback/Stabilization/Reclaim/Reversal/Continuationを統合。動的volume・VWAP・market/sector・order-bookは利用不能。anchor情報を最新値に見せかけていない。provider publication latencyは保存sourceから独立検証できず、completed-bar availabilityの研究上の意味に限定。

| Route | 固定意味 |
| --- | --- |
| A | t0: urgent>=.25 OR viable>=.40 & failure<.50 →即時BUY |
| B | delay>0: observed pullback＋support/reclaim/turn＋viable>=.20 & failure<.50 →BUY |
| C | 5分ずつWAIT、最大15分。途中のurgent/continuation、またはcapのviable contextでBUY |
| D | failure>=.75 & viable<.10でSKIP。cap非適格、missing、boundaryでEXPIRE |

優先順はProtocol exact。Pullback単体ではBUYしない。Route A/B/C/D terminal attributionは互いに排他的だが、WAIT membershipはA/B/C/D terminalと別の集計。NO_EVENTから一律SKIPする規則はない。同じOpportunityに複数Entryしない。

## Datasetと分母

| partition | sessions | 全Opportunity | common60完全評価 | 実際のcounterfactual ENTER | 完全評価ENTER |
| --- | --- | --- | --- | --- | --- |
| TRAIN | 38 | 1760 | 633 | 344 | 216 |
| VALIDATION | 19 | 863 | 336 | 159 | 95 |
| DEV TEST | 19 | 885 | 未評価 | 未評価 | 未評価 |

TRAIN fitは633 episodes / 2532 states。全76 Developmentのsource bundleをidentity確認後、対象partitionへ絞ってからPIT・label・outcome処理。DEV TESTはintegrated candidateの推論・outcome評価0。過去の一般Development exposureと区別し、Freshとは呼ばない。今回Validation19は明示的にexposedと記録。

性能主分母はoriginal opportunity+60 clock minutesを同一segment内で完全評価できた機会。Entry側も同じ終点。MAEは自分のEntry後30分のstrict30もpaired比較し、短い残存期間だけによる改善を区別する。全発行機会は欠損・打切りを含め全件ledgerに残す。価格・MFE・MAEのpaired指標はEntryしたsubsetであり、逃したwinnerを含むpreservation指標と必ず同時に読む。

## Target / Observed / Gap / Status

| metric | target | observed | gap | unit | status |
| --- | --- | --- | --- | --- | --- |
| FAST_WINNER | 0.900 | 0.341 | -0.559 | fraction | HARD_FAIL |
| IMMEDIATE_WINNER | 0.900 | 0.143 | -0.757 | fraction | HARD_FAIL |
| completeN | 100 | 336 | 236 | count | PASS |
| deep5Reduction | 0.100 | 0.611 | 0.511 | fraction | PASS |
| economicEvaluable | 0.900 | 0.994 | 0.094 | fraction | PASS |
| economicMeanDeltaPP | 0.050 | 0.054 | 0.004 | pp | PASS |
| economicP05DeltaPP | 0 | 1.014 | 1.014 | pp | PASS |
| economicPFDelta | 0 | 0.021 | 0.021 | pp | PASS |
| entryCoverage | 0.700 | 0.283 | -0.417 | fraction | HARD_FAIL |
| preservation1 | 0.800 | 0.289 | -0.511 | fraction | HARD_FAIL |
| preservation2 | 0.850 | 0.298 | -0.552 | fraction | HARD_FAIL |
| preservation3 | 0.900 | 0.295 | -0.605 | fraction | HARD_FAIL |
| preservation5 | 0.900 | 0.344 | -0.556 | fraction | HARD_FAIL |
| priceImprovementPP | 0.100 | 0.572 | 0.472 | pp | PASS |
| remainingMFE | 0.900 | 0.997 | 0.097 | fraction | PASS |
| strict30MedianImprovementPP | 0.100 | 0.761 | 0.661 | pp | PASS |
| strict30P05ImprovementPP | 0.250 | 1.222 | 0.972 | pp | PASS |

| Composite gate | status |
| --- | --- |
| delayedEntryUsed | PASS |
| economic_blocks | FAIL |
| economic_cohorts | PASS |
| economic_top3 | PASS |
| entry_chronological | FAIL |
| entry_cohorts | FAIL |
| entry_pullback | FAIL |
| entry_top3Exclusion | FAIL |
| waitUsed | PASS |

Near-Miss幅はfraction0.05 / pp0.05 / count10を事前固定。全PASSだけPASS。非定義分母はHARD_FAIL。CompositeはPASS/FAIL、Integrity不成立はHARD_FAIL。Near-Missは修正許可を意味しない。

## B0 Immediateとの比較

| metric | B0 Immediate | Integrated |
| --- | --- | --- |
| Opportunity n | 863 | 863 |
| Reference outcome evaluable | 667 | 667 |
| Complete n | 336 | 336 |
| Actual ENTER on complete | 336 | 95 |
| Entry coverage on complete | 100% | 28.27% |
| ENTER all emitted | 参考: reference evaluable 667 | 159 |
| Coverage all emitted | baseline reference 77.29% | 18.42% |
| Mean delay minutes | 0 | 8.113 |
| Median delay minutes | 0 | 5.000 |
| Mean Entry price on same entered pairs | 785.947 | 782.726 |
| Mean price improvement pp | 0 | 0.572 |
| Common MAE mean paired | -3.672 | -2.720 |
| Common MAE median paired | -2.786 | -2.162 |
| Common MAE p10 paired | -6.923 | -5.893 |
| Common MAE p05 paired | -9.115 | -6.941 |
| Worst common MAE paired | -14.301 | -10.092 |
| Strict30 MAE median paired | -2.514 | -1.753 |
| Strict30 MAE p05 paired | -7.644 | -6.422 |
| Mean remaining MFE paired | 3.077 | 3.067 |
| Remaining MFE ratio paired | 100% | 99.69% |

| Entry improvement distribution | pp/rate |
| --- | --- |
| max | 7.909 |
| mean | 0.572 |
| median | 0.000 |
| min | -6.000 |
| n | 95 |
| p05 | -2.782 |
| p10 | -1.376 |
| p25 | -0.308 |
| p75 | 1.711 |
| p90 | 3.003 |
| p95 | 3.827 |
| positiveRate | 0.495 |
| favorableRate | 49.47% |
| worseRate | 28.42% |

| delay min | ENTER count |
| --- | --- |
| 0 | 31 |
| 10 | 28 |
| 15 | 51 |
| 20 | 0 |
| 25 | 0 |
| 30 | 0 |
| 5 | 49 |
| SKIP | 0 |
| EXPIRE | 704 |

| Threshold | Baseline winner n | entered | remaining preserved | preservation | missed | no-entry winner | winner before Entry |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 218 | 71 | 63 | 28.90% | 155 | 147 | 37 |
| 2 | 131 | 49 | 39 | 29.77% | 92 | 82 | 22 |
| 3 | 78 | 30 | 23 | 29.49% | 55 | 48 | 10 |
| 5 | 32 | 16 | 11 | 34.38% | 21 | 16 | 3 |

| Class | n | entered | remaining +3 | rate +3 |
| --- | --- | --- | --- | --- |
| CONTINUED_FAILURE | 70 | 40 | 2 | 2.86% |
| DEEP_PULLBACK_THEN_WINNER | 5 | 4 | 4 | 80.00% |
| FAST_WINNER | 41 | 17 | 14 | 34.15% |
| IMMEDIATE_WINNER | 14 | 4 | 2 | 14.29% |
| PULLBACK_WINNER | 57 | 21 | 17 | 29.82% |

## Risk attribution

| tail | B0 all | B0 same entered | Integrated entered | BETTER_ENTRY_LOCATION reduction | SKIP_AVOIDANCE reduction | strict30 same-pair reduction |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | 3 | 3 | 2 | 1 | 0 | 1 |
| 3 | 78 | 46 | 33 | 13 | 32 | 13 |
| 5 | 36 | 29 | 14 | 15 | 7 | 9 |

SKIP_AVOIDANCEは実際のMODEL_SKIPに加え、WAIT cap / boundary / missingによる非Entryも含む会計上の名称。理由別件数は以下。総件数減少だけを良いEntry Locationの証明に使わない。

| tail | 非Entry理由別 |
| --- | --- |
| 10 | {} |
| 3 | {"EXPIRE_WAIT_CAP": 32} |
| 5 | {"EXPIRE_WAIT_CAP": 7} |

## Routes・WAIT・Path classes

| terminal route | 全発行n | 割合 | BUY0 | delayed BUY | WAIT経験 | SKIP | EXPIRE | price pp | MAE median strict30差 | MFE ratio | +3 rate | +5 rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 31 | 3.59% | 31 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 100.00% | 100.00% | 100.00% |
| B | 21 | 2.43% | 0 | 21 | 21 | 0 | 0 | 0.035 | 1.019 | 101.41% | 50.00% | 0.00% |
| C | 107 | 12.40% | 0 | 107 | 107 | 0 | 0 | 0.782 | 0.922 | 99.40% | 78.26% | 69.23% |
| D | 704 | 81.58% | 0 | 0 | 508 | 0 | 704 | UNKNOWN / n=0 | UNKNOWN / n=0 | UNKNOWN | 0.00% | 0.00% |

| WAIT membership | value |
| --- | --- |
| 開始 | 636 |
| eventual BUY | 128 |
| eventual SKIP | 0 |
| eventual EXPIRE | 508 |
| WAIT mean actual elapsed | 13.522 |
| WAIT median actual elapsed | 15.000 |
| WAIT max actual elapsed | 15 |
| price improvement pp | 0.679 |
| remaining MFE ratio | 99.63% |
| missed +3 | 55 |
| missed +5 | 21 |

WAITが最後にmissing stateへ進んだ場合、保存summaryのwaitDurationAllは最後のscored timestampを示す。上表はintegrity auditで最後のattempted5分も含めた実経過時間。policy/evidenceの変更はしていない。

| Path class | 完全評価n | BUY0 | delayed BUY | WAIT経験 | SKIP | EXPIRE | Entry coverage | price pp | MAE median差 | MFE ratio | +3 preserve | +5 preserve |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHOP_THEN_WINNER | 1 | 0 | 0 | 1 | 0 | 1 | 0.00% | UNKNOWN / n=0 | UNKNOWN / n=0 | UNKNOWN | 0.00% | 0.00% |
| CONTINUED_FAILURE | 70 | 6 | 34 | 64 | 0 | 30 | 57.14% | 1.866 | 1.415 | 155.11% | UNKNOWN | UNKNOWN |
| DEEP_PULLBACK_THEN_WINNER | 5 | 1 | 3 | 4 | 0 | 1 | 80.00% | 1.442 | 1.610 | 134.38% | 80.00% | 100.00% |
| IMMEDIATE_WINNER | 14 | 1 | 3 | 13 | 0 | 10 | 28.57% | -1.596 | -0.265 | 73.89% | 14.29% | 20.00% |
| INCONCLUSIVE | 6 | 16 | 53 | 321 | 0 | 464 | 83.33% | -3.274 | -0.887 | 73.89% | 66.67% | 80.00% |
| OPPORTUNITY_EXPIRED | 188 | 6 | 19 | 182 | 0 | 163 | 13.30% | 0.215 | 0.505 | 109.56% | UNKNOWN | UNKNOWN |
| PULLBACK_THEN_WINNER | 52 | 1 | 16 | 51 | 0 | 35 | 32.69% | -0.512 | 0.819 | 90.06% | 25.00% | 25.00% |

PULLBACK_THEN_WINNERとDEEP_PULLBACK_THEN_WINNERは別行で示す。上昇前に押し目があったというEvaluator classはruntime入力ではない。INCONCLUSIVEは不完全期間を含むため、その行のactionsは全発行、完全評価nは別分母。

| Route | Immediate n/entered/+3 | Fast n/entered/+3 | Pullback n/entered/+3 | ContinuedFailure n/entered |
| --- | --- | --- | --- | --- |
| A | 1 / 1 / 1 | 2 / 2 / 2 | 2 / 2 / 2 | 6 / 6 |
| B | 0 / 0 / 0 | 0 / 0 / 0 | 4 / 4 / 2 | 2 / 2 |
| C | 3 / 3 / 1 | 15 / 15 / 12 | 15 / 15 / 13 | 32 / 32 |
| D | 10 / 0 / 0 | 24 / 0 / 0 | 36 / 0 / 0 | 30 / 0 |

## Exact Candidate A economic counterfactual

Entry Gateが不成立でも、今回の明示指示に従って経済比較を実施。資本配分・Portfolioではない。Entry後のexact Fixed12はregular bars基準であり、昼休みを挟む場合のclock HOLDは120分となり得る。Entry WAITはoriginal segmentを越えない。EXIT semanticsは変更していない。

| 比較母集団 | n |
| --- | --- |
| common baseline | 336 |
| economic paired incl cash | 334 |
| 両側Entry outcome paired | 93 |
| UNKNOWN excluded | 2 |

| metric | B0 all evaluable | Integrated incl cash0 | B0 entered same-pairs | Integrated entered same-pairs |
| --- | --- | --- | --- | --- |
| n | 334 | 334 | 93 | 93 |
| mean | -0.075 | -0.021 | -0.771 | -0.075 |
| median | -0.142 | 0.000 | -0.759 | -0.050 |
| PF | 0.928 | 0.949 | 0.636 | 0.949 |
| winRate | 0.446 | 0.123 | 0.387 | 0.441 |
| p05 | -4.702 | -3.688 | -7.434 | -5.322 |
| min | -12.184 | -7.809 | -12.184 | -7.809 |

| metric | B0 entered same-pairs | Integrated entered same-pairs |
| --- | --- | --- |
| MFE mean | 3.021 | 3.278 |
| MFE median | 2.096 | 2.211 |
| MFE p05 | 0.029 | 0.276 |
| MFE min | 0 | 0 |
| MFE max | 28.365 | 24.424 |
| MAE mean | -3.708 | -2.843 |
| MAE median | -2.963 | -2.116 |
| MAE p05 | -9.138 | -7.211 |
| MAE min | -14.301 | -10.092 |
| MAE max | 0 | 0 |
| HOLD mean | 56.667 | 66.505 |
| HOLD median | 60.000 | 60.000 |
| HOLD p05 | 33.000 | 29.000 |
| HOLD min | 10 | 15 |
| HOLD max | 60 | 120 |

| economic delta attribution | pp |
| --- | --- |
| enteredTimingContributionMeanPP | 0.194 |
| enteredTimingDeltaSumPP | 64.697 |
| nonEntryAvoidanceDeltaSumPP | -46.650 |
| nonEntryContributionMeanPP | -0.140 |
| paired mean net delta | 0.054 |

enteredTimingはlocationに加えてEntry開始時刻変更に伴うEXIT評価期間差も含む。非Entry寄与はcoverage/cash effect。両者を厳密な因果帰属と断定しない。Candidate A比改善と、絶対net正/PF>1/実運用収益成立は別。

| Economic Gate | PASS |
| --- | --- |
| PF | PASS |
| blocks | FAIL |
| cohorts | PASS |
| coverage | PASS |
| mean | PASS |
| p05 | PASS |
| top3 | PASS |

Economic: routes

| group | paired n | entered n | B0 mean | Integrated cash mean | delta | PF | p05 | entered HOLD mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 15 | 15 | -1.022 | -1.022 | 0.000 | 0.509 | -6.036 | 60 |
| B | 11 | 11 | -0.135 | -0.731 | -0.596 | 0.495 | -3.710 | 73.636 |
| C | 67 | 67 | -0.819 | 0.244 | 1.063 | 1.182 | -5.201 | 66.791 |
| D | 241 | 0 | 0.194 | 0 | -0.194 | UNKNOWN / n=0 | 0.000 | UNKNOWN / n=0 |

Economic: INITIAL/DIP

| group | paired n | entered n | B0 mean | Integrated cash mean | delta | PF | p05 | entered HOLD mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 76 | 25 | -0.265 | -0.223 | 0.042 | 0.593 | -3.907 | 56.600 |
| INITIAL_ENTRY_OPPORTUNITY | 258 | 68 | -0.019 | 0.039 | 0.058 | 1.105 | -3.484 | 70.147 |

Economic: chronological blocks

| group | paired n | entered n | B0 mean | Integrated cash mean | delta | PF | p05 | entered HOLD mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 97 | 30 | -0.229 | 0.287 | 0.516 | 2.303 | -1.345 | 69.333 |
| 2 | 80 | 30 | 0.006 | -0.366 | -0.373 | 0.572 | -5.455 | 64.333 |
| 3 | 96 | 22 | -0.137 | -0.104 | 0.034 | 0.692 | -3.637 | 66.818 |
| 4 | 61 | 11 | 0.162 | 0.073 | -0.089 | 1.298 | -2.347 | 64.091 |

## Robustness — 悪いcohort/blockも保持

INITIAL/DIP

| group | emitted | complete | entered | coverage | routes A/B/C/D | +3 | +5 | price pp | strict30 median差 | strict30 p05差 | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 153 | 77 | 26 | 33.77% | 31/7/14/101 | 37.50% | 60.00% | 0.584 | 0.664 | 0.636 | 109.08% |
| INITIAL_ENTRY_OPPORTUNITY | 710 | 259 | 69 | 26.64% | 0/14/93/603 | 27.42% | 29.63% | 0.567 | 0.737 | 1.893 | 96.81% |

Validation chronology

| group | emitted | complete | entered | coverage | routes A/B/C/D | +3 | +5 | price pp | strict30 median差 | strict30 p05差 | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 238 | 98 | 31 | 31.63% | 14/5/36/183 | 38.10% | 50.00% | 1.031 | 1.100 | 1.689 | 114.60% |
| 2 | 213 | 80 | 30 | 37.50% | 6/7/32/168 | 32.00% | 28.57% | 0.437 | 0.270 | 1.073 | 92.00% |
| 3 | 230 | 97 | 23 | 23.71% | 5/4/27/194 | 20.00% | 0.00% | 0.203 | 1.047 | 2.120 | 82.97% |
| 4 | 182 | 61 | 11 | 18.03% | 6/5/12/159 | 25.00% | 50.00% | 0.416 | 0.932 | 1.762 | 106.45% |

TRAIN chronology

| group | emitted | complete | entered | coverage | routes A/B/C/D | +3 | +5 | price pp | strict30 median差 | strict30 p05差 | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 462 | 149 | 54 | 36.24% | 15/18/55/374 | 33.33% | 50.00% | 0.203 | 0.085 | 0.837 | 88.96% |
| 2 | 440 | 157 | 47 | 29.94% | 13/10/53/364 | 31.25% | 30.00% | 0.659 | 0.612 | 1.418 | 95.48% |
| 3 | 397 | 135 | 40 | 29.63% | 10/17/41/329 | 43.33% | 53.85% | -0.038 | 0.026 | 0.474 | 85.42% |
| 4 | 461 | 192 | 75 | 39.06% | 23/14/75/349 | 44.68% | 33.33% | 0.449 | 0.383 | 1.503 | 100.50% |

candidate breadth

| group | emitted | complete | entered | coverage | routes A/B/C/D | +3 | +5 | price pp | strict30 median差 | strict30 p05差 | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 59 | 22 | 9 | 40.91% | 17/3/5/34 | 66.67% | 100.00% | 0.178 | -0.502 | 0.000 | 96.53% |
| 2 | 96 | 30 | 11 | 36.67% | 12/2/8/74 | 33.33% | 50.00% | 0.452 | 0.032 | 1.432 | 99.67% |
| 3 | 192 | 62 | 12 | 19.35% | 1/4/17/170 | 27.78% | 33.33% | 1.153 | 1.474 | 3.046 | 115.52% |
| 4 | 216 | 75 | 23 | 30.67% | 1/7/28/180 | 31.25% | 42.86% | -0.219 | 0.684 | 0.619 | 83.43% |
| 5 | 300 | 147 | 40 | 27.21% | 0/5/49/246 | 25.71% | 23.08% | 0.974 | 0.973 | 1.659 | 108.14% |

session time

| group | emitted | complete | entered | coverage | routes A/B/C/D | +3 | +5 | price pp | strict30 median差 | strict30 p05差 | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFTERNOON | 425 | 123 | 30 | 24.39% | 12/5/34/374 | 40.91% | 58.33% | 0.706 | 1.268 | 3.917 | 105.38% |
| MORNING | 438 | 213 | 65 | 30.52% | 19/16/73/330 | 25.00% | 20.00% | 0.510 | 0.481 | 0.072 | 95.31% |

volatility context

| group | emitted | complete | entered | coverage | routes A/B/C/D | +3 | +5 | price pp | strict30 median差 | strict30 p05差 | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HIGH | 90 | 54 | 25 | 46.30% | 31/4/13/42 | 38.46% | 50.00% | 0.567 | 0.449 | 0.644 | 108.21% |
| LOW_OR_EQUAL | 63 | 23 | 1 | 4.35% | 0/3/1/59 | 33.33% | 100.00% | 1.015 | 1.282 | 1.282 | 118.12% |
| MISSING | 710 | 259 | 69 | 26.64% | 0/14/93/603 | 27.42% | 29.63% | 0.567 | 0.737 | 1.893 | 96.81% |

Chronological dates: `[["2024-11-13", "2024-11-14", "2024-11-15", "2024-11-18", "2024-11-19"], ["2024-11-20", "2024-11-21", "2024-11-22", "2024-11-25", "2024-11-26"], ["2024-11-27", "2024-11-28", "2024-11-29", "2024-12-02", "2024-12-03"], ["2024-12-04", "2024-12-05", "2024-12-06", "2024-12-09"]]`

Concentration: `{"sessionHHI": 0.05299495548284099, "symbolHHI": 0.003997212558524858, "top10": [["45830", 10], ["260A0", 9], ["265A0", 9], ["42550", 9], ["52470", 9], ["70740", 9], ["25860", 8], ["38250", 8], ["55870", 8], ["56160", 8]], "top3Train": ["25860", "48830", "190A0"], "uniqueSymbols": 415}`

| TRAIN-top3除外診断 | value |
| --- | --- |
| complete n | 321 |
| coverage | 26.79% |
| +3 | 28.95% |
| +5 | 32.26% |
| price pp | 0.527 |
| MAE median差 | 0.724 |
| economic mean delta | 0.011 |

TRAIN頻度top3のみ事前ルールで除外した診断。再fitやsymbol ruleなし。全session別指標はvalidation/summary.jsonのsessions。volatility区分はTRAIN t0 rangeMean中央値 1.149 を固定し、欠損も別群に保持。

## Missingness

| feature | t0 available/n | t0 missing rate | all available states missing rate |
| --- | --- | --- | --- |
| acceleration | 0/667 | 100.00% | 71.36% |
| afternoon | 667/667 | 0.00% | 0.00% |
| anchorAge | 667/667 | 0.00% | 0.00% |
| anchorPrice | 667/667 | 0.00% | 0.00% |
| bounce | 153/667 | 77.06% | 20.45% |
| candidateBreadth | 667/667 | 0.00% | 0.00% |
| closeLocation | 153/667 | 77.06% | 20.45% |
| closeVolatility | 153/667 | 77.06% | 20.45% |
| directionalMomentum3Pct | 393/667 | 41.08% | 38.42% |
| directionalMomentumAccelerationPct | 261/667 | 60.87% | 58.75% |
| directionalPersistence | 153/667 | 77.06% | 20.45% |
| directionalPullback6Pct | 341/667 | 48.88% | 46.14% |
| directionalReturnFromOpenPct | 365/667 | 45.28% | 45.39% |
| directionalVwapDistancePct | 217/667 | 67.47% | 65.67% |
| displacement | 153/667 | 77.06% | 20.45% |
| efficiency | 153/667 | 77.06% | 20.45% |
| elapsed | 667/667 | 0.00% | 0.00% |
| failedReclaim | 153/667 | 77.06% | 20.45% |
| higherHigh | 0/667 | 100.00% | 46.98% |
| higherLow | 0/667 | 100.00% | 46.98% |
| isDip | 667/667 | 0.00% | 0.00% |
| lastBody | 153/667 | 77.06% | 20.45% |
| lastRange | 153/667 | 77.06% | 20.45% |
| lowExtension | 153/667 | 77.06% | 20.45% |
| lowerHigh | 0/667 | 100.00% | 46.98% |
| lowerLow | 0/667 | 100.00% | 46.98% |
| lowerWick | 153/667 | 77.06% | 20.45% |
| minutesSinceOpen | 667/667 | 0.00% | 0.00% |
| minutesUntilSegmentEnd | 667/667 | 0.00% | 0.00% |
| momentum3 | 153/667 | 77.06% | 20.45% |
| newLowCount | 153/667 | 77.06% | 20.45% |
| normalizedDisplacement | 153/667 | 77.06% | 20.45% |
| rangeMean | 153/667 | 77.06% | 20.45% |
| rangeRatio | 153/667 | 77.06% | 20.45% |
| recentHighDistance | 153/667 | 77.06% | 20.45% |
| recentLowDistance | 153/667 | 77.06% | 20.45% |
| reclaim | 153/667 | 77.06% | 20.45% |
| relativeVolume5 | 341/667 | 48.88% | 46.14% |
| selectorRank | 667/667 | 0.00% | 0.00% |
| selectorScore | 667/667 | 0.00% | 0.00% |
| signReversals | 153/667 | 77.06% | 20.45% |
| slope | 153/667 | 77.06% | 20.45% |
| state_adverseAcceleration | 0/667 | 100.00% | 77.21% |
| state_closeDeteriorationStopped | 0/667 | 100.00% | 53.06% |
| state_closeLocation | 0/667 | 100.00% | 26.53% |
| state_closeLocationChange | 0/667 | 100.00% | 53.06% |
| state_closeVolatility | 0/667 | 100.00% | 53.06% |
| state_consecutiveLowerCloses | 0/667 | 100.00% | 26.53% |
| state_continuation | 0/667 | 100.00% | 26.53% |
| state_drawdownClose | 0/667 | 100.00% | 26.53% |
| state_drawdownLow | 0/667 | 100.00% | 26.53% |
| state_failedBreakdown | 0/667 | 100.00% | 53.06% |
| state_higherClose | 0/667 | 100.00% | 53.06% |
| state_higherLow | 0/667 | 100.00% | 53.06% |
| state_lowExtension | 0/667 | 100.00% | 53.06% |
| state_lowExtensionChange | 0/667 | 100.00% | 77.21% |
| state_lowerWick | 0/667 | 100.00% | 26.53% |
| state_momentumTurn | 0/667 | 100.00% | 26.53% |
| state_newLowStopped | 0/667 | 100.00% | 53.06% |
| state_priorHighReclaim | 0/667 | 100.00% | 53.06% |
| state_pullbackAge | 0/667 | 100.00% | 63.96% |
| state_pullbackFromRunningHigh | 0/667 | 100.00% | 26.53% |
| state_rangeContraction | 0/667 | 100.00% | 56.40% |
| state_recentRangeLocation | 0/667 | 100.00% | 26.53% |
| state_volatilityNormalizedPullback | 0/667 | 100.00% | 29.87% |
| upperWick | 153/667 | 77.06% | 20.45% |

route別・Entry/non-Entry別のvisited-state missingnessはvalidation/missingness.json。未観測のpost-opportunity stateはt0で欠損するのが因果上正しい。missing indicatorはPIT欠損のみ。将来のoutcome可否をindicatorにしていない。

## Integrity・Tests・CI

PIT state regeneration、独立Route evaluator、tree各nodeのweighted momentsとeligible split impurity、ledger ID、Entry価格、risk/economic attribution加法整合をPASS。学習再実行0。TRAIN/Validation artifact hash固定。no future-low/MFE/MAE/outcome feature、UNKNOWN_INTRABAR_ORDER、missing fail-closed、session boundary、no duplicate Entryはtargeted testsで確認。

| partition | state/policy regeneration episodes | independent route decisions |
| --- | --- | --- |
| TRAIN | 1760 | 4384 |
| VALIDATION | 863 | 2298 |

Targeted tests30件。Offline predict regression結果はverification/regression.json。最新HEADのCI確認はGitHub Actions final-ci-receipt.jsonと最終報告に記録。全PRの既存EXIT CC Freeze Auditの失敗は、新Entryの性能判定と区別する。CIがGREENでも性能PASSにはしない。

| Safety | value |
| --- | --- |
| automaticPromotionAllowed | false |
| brokerWriteAllowed | false |
| excelOrderWriteAllowed | false |
| executionAllowed | false |
| liveTradingAllowed | false |
| paperTradingAllowed | false |
| productionUpdateAllowed | false |
| rssOrderFunctionAllowed | false |
| transmitted | false |

## Final decision

**FIRST_INTEGRATED_MEASUREMENT_COMPLETE / HARD_FAIL**。CandidateはNOT_FROZEN。Validation後のthreshold/feature/model/objective/routing/waitCap/gate/symbolRule/timeRule変更は全0。学習1回、候補1本、Validation初回測定1回。DEV TEST / Fresh / OOS未評価。

今回の実測範囲で、価格位置・同一Entry機会のMAE改善と、upside Opportunityの高率維持を同時に満たせなかった。WAITは実際に発生したが、非Entry・winner lossが大きい。これは今回固定した統合版の結果であり、Entry Timing一般の不可能性とはしない。次候補、再学習、新データ、Capital/Portfolio、EXIT研究、main mergeへ進まずSTOP。
