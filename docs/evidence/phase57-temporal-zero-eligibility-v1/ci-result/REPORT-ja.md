# Temporal Reliability Zero-Eligibility Diagnostic

**最終判定 D: TEMPORAL_RELIABILITY_BLOCKED_BY_MIXED_CAUSES**

旧GateはBLOCKEDのまま。今回は原因診断であり、新たなPASS認定・window選択・Entry/EXIT設計は行わない。

## 1. Funnel（現在のUSABLE H/M候補コホート）

| stage | symbols | symbol×lane-traits | dropped cells | candidate symbols % |
|---|---:|---:|---:|---:|
| ALL_USABLE_SYMBOL_TRAITS | 4080 | 36720 | — | 161.07 |
| CURRENT_HIGH_MEDIUM | 2533 | 8910 | 27810 | 100.00 |
| TEMPORAL_TEST_TARGET | 2533 | 8910 | 0 | 100.00 |
| PERIOD1_ELIGIBLE | 0 | 0 | 8910 | 0.00 |
| PERIOD1_AND_PERIOD2_COMPARABLE | 0 | 0 | 0 | 0.00 |
| ALL_THREE_PERIODS_COMPARABLE | 0 | 0 | 0 | 0.00 |
| TEMPORAL_COMPUTABLE | 0 | 0 | 0 | 0.00 |
| TEMPORAL_PASS | 0 | 0 | 0 | 0.00 |
| HANDOFF_ELIGIBLE | 0 | 0 | 0 | 0.00 |

最初に0となる段階は **PERIOD1_ELIGIBLE**。候補2533銘柄 / 8910セルは、最初のfoldのeligibilityで全て落ちる。PASS0、FAIL0、INSUFFICIENTは候補全セル。Period2単独とPeriod3も別集計した。

## 2. 根本原因

1. 第1fold（anchor2025-04-21）の60取引所calendar-position内に許可されたDevelopment日は5日しかない。source最低20日も、H/Mのcoverage>=0.5（60中30日）も数学的に不可能。history resetとscale warm-upで実有効日はさらに減る。
2. 第2fold（anchor2025-05-22）は60中25日。仮に全日有効でも25/60<0.5なのでH/M不能。実Profileのpeer fitも成立しない。
3. 第3foldは60中45許可日。実source confidence、target support、posterior条件のどれが落としたかを下表/CSVに記録した。数値を見て条件を緩めない。
4. target明示条件nEff>=8/観測>=8のほか、共通snapshot()は適格session>=20・peer cohort>=100を要求し、有限target posteriorが比較条件に追加される。19有効日・110銘柄の合成例で「観測8を満たすがposteriorなし」を再現。研究仕様に曖昧さがあるため修正せず別specへの提案とした。

## 3. USABLE9の個別診断

| lane/trait | available sessions | observed symbols | H/M current | P1 eligible | P2 eligible | P3 eligible | all3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| daily/inside | 723 | 4078 | 0 | 0 | 0 | 0 | 0 |
| daily/gap_fill | 723 | 4076 | 34 | 0 | 0 | 0 | 0 |
| daily/gap_cont | 723 | 4076 | 18 | 0 | 0 | 0 | 0 |
| daily/amihud | 723 | 4078 | 2235 | 0 | 0 | 0 | 0 |
| intraday/amihud | 126 | 3888 | 2222 | 0 | 0 | 0 | 0 |
| intraday/value_O30 | 126 | 3665 | 1510 | 0 | 0 | 0 | 0 |
| intraday/value_AM | 126 | 3668 | 1440 | 0 | 0 | 0 | 0 |
| intraday/value_PM1 | 126 | 3677 | 1318 | 0 | 0 | 0 | 0 |
| intraday/pdh_break | 126 | 3443 | 133 | 0 | 0 | 0 | 0 |

必要minimum・実min/max/p10/median/p90、最初/最後の日、source/target日数・nEff・coverage・peer人数、prediction origin/computedThroughはdiagnostic/02_usable9.json。銘柄別の正確なtimestampと理由はsymbol-trait-fold.csv.gz。

| lane/trait/fold | source base-mask | peer fit | source H/M | target explicit8 | target posterior finite | first drop reasons |
|---|---:|---|---:|---:|---:|---|
| daily/inside/1 | 0 | False | 0 | 3715 | 3383 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| daily/inside/2 | 0 | False | 0 | 3688 | 3361 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| daily/inside/3 | 3739 | True | 0 | 3566 | 0 | {"SOURCE_COVERAGE_BELOW_0_5": 38, "SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 315, "SOURCE_NOT_HIGH_MEDIUM": 3701, "SOURCE_TRAIT_OBSERVATIONS_BELOW_MIN": 26} |
| daily/gap_fill/1 | 0 | False | 0 | 122 | 144 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| daily/gap_fill/2 | 0 | False | 0 | 146 | 167 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| daily/gap_fill/3 | 1611 | True | 2 | 22 | 0 | {"SOURCE_COVERAGE_BELOW_0_5": 19, "SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 315, "SOURCE_NOT_HIGH_MEDIUM": 1590, "SOURCE_TRAIT_OBSERVATIONS_BELOW_MIN": 2154, "TARGET_NEFF_BELOW_8": 2} |
| daily/gap_cont/1 | 0 | False | 0 | 129 | 144 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| daily/gap_cont/2 | 0 | False | 0 | 147 | 167 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| daily/gap_cont/3 | 1611 | True | 2 | 20 | 0 | {"SOURCE_COVERAGE_BELOW_0_5": 19, "SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 315, "SOURCE_NOT_HIGH_MEDIUM": 1590, "SOURCE_TRAIT_OBSERVATIONS_BELOW_MIN": 2154, "TARGET_NEFF_BELOW_8": 2} |
| daily/amihud/1 | 0 | False | 0 | 3643 | 3383 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| daily/amihud/2 | 0 | False | 0 | 3609 | 3361 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| daily/amihud/3 | 3739 | True | 2201 | 3192 | 0 | {"MISSING_TARGET_OR_SOURCE_POSTERIOR": 1931, "SOURCE_COVERAGE_BELOW_0_5": 38, "SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 315, "SOURCE_NOT_HIGH_MEDIUM": 1500, "SOURCE_TRAIT_OBSERVATIONS_BELOW_MIN": 26, "TARGET_NEFF_BELOW_8": 270} |
| intraday/amihud/1 | 0 | False | 0 | 3643 | 3383 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| intraday/amihud/2 | 0 | False | 0 | 3609 | 3361 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| intraday/amihud/3 | 3739 | True | 2170 | 3192 | 0 | {"MISSING_TARGET_OR_SOURCE_POSTERIOR": 1904, "SOURCE_COVERAGE_BELOW_0_5": 38, "SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 315, "SOURCE_NOT_HIGH_MEDIUM": 1531, "SOURCE_TRAIT_OBSERVATIONS_BELOW_MIN": 26, "TARGET_NEFF_BELOW_8": 266} |
| intraday/value_O30/1 | 0 | False | 0 | 1576 | 861 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| intraday/value_O30/2 | 0 | False | 0 | 1570 | 874 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| intraday/value_O30/3 | 1563 | True | 1321 | 1201 | 0 | {"MISSING_TARGET_OR_SOURCE_POSTERIOR": 986, "SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 315, "SOURCE_NOT_HIGH_MEDIUM": 242, "SOURCE_TRAIT_OBSERVATIONS_BELOW_MIN": 2202, "TARGET_NEFF_BELOW_8": 335} |
| intraday/value_AM/1 | 0 | False | 0 | 1564 | 863 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| intraday/value_AM/2 | 0 | False | 0 | 1553 | 874 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| intraday/value_AM/3 | 1563 | True | 1275 | 1216 | 0 | {"MISSING_TARGET_OR_SOURCE_POSTERIOR": 971, "SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 315, "SOURCE_NOT_HIGH_MEDIUM": 288, "SOURCE_TRAIT_OBSERVATIONS_BELOW_MIN": 2202, "TARGET_NEFF_BELOW_8": 304} |
| intraday/value_PM1/1 | 0 | False | 0 | 1579 | 860 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| intraday/value_PM1/2 | 0 | False | 0 | 1562 | 861 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| intraday/value_PM1/3 | 1562 | True | 1131 | 1195 | 0 | {"MISSING_TARGET_OR_SOURCE_POSTERIOR": 861, "SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 315, "SOURCE_NOT_HIGH_MEDIUM": 431, "SOURCE_TRAIT_OBSERVATIONS_BELOW_MIN": 2203, "TARGET_NEFF_BELOW_8": 270} |
| intraday/pdh_break/1 | 0 | False | 0 | 319 | 0 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| intraday/pdh_break/2 | 0 | False | 0 | 233 | 0 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 4080} |
| intraday/pdh_break/3 | 145 | True | 0 | 140 | 0 | {"SOURCE_ELIGIBLE_SESSIONS_BELOW_20": 315, "SOURCE_NOT_HIGH_MEDIUM": 145, "SOURCE_TRAIT_OBSERVATIONS_BELOW_MIN": 3620} |

first dropは排他的件数、全不成立conjunctは重複件数。混同しない。全32判定/全3foldの詳細は04_period_reasons.json。

## 4. WATCH23の時間順序

| lane/trait | actual mapping | nominal completion | validation2 origin | later authorized sessions | current design |
|---|---|---|---|---:|---|
| daily/body_range | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/large_up | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/doji | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/long_lower | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/outside | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/trend_day | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/range_s | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/range_exp | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/range_con | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/gap_up | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/gap_dn | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/overnight_var_share | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/value_shock | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| daily/jump | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| intraday/inside | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| intraday/trend_day | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| intraday/range_con | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| intraday/gap_fill | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| intraday/overnight_var_share | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| intraday/value_shock | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| intraday/value_CL | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| intraday/range_PM1 | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |
| intraday/volume_CL | False | 2025-05-29T15:30:00+09:00 | 2025-05-22T15:31:00+09:00 | 59 | 不成立 |

5/29 closeにfold1 targetを知ってから5/22起点へmappingを遡及適用できない。さらにfold1のfit pairsが0で、mappingそのものが未作成。5/29後の日付順序が成立する最初の時点と残存独立session数は03_watch23.json。trait別に補正可能性を確認したことにはならない。旧WATCHは不変。

## 5. Counterfactual（件数のみ・新Gateなし）

| lane/trait | fixed latest origin | source H/M | comparison support |
|---|---|---:|---:|
| daily/inside | 2025-07-17 | 0 | 0 |
| daily/gap_fill | 2025-07-17 | 39 | 2 |
| daily/gap_cont | 2025-07-17 | 34 | 1 |
| daily/amihud | 2025-07-17 | 2299 | 2168 |
| intraday/amihud | 2025-07-17 | 2255 | 2129 |
| intraday/value_O30 | 2025-07-17 | 1522 | 863 |
| intraday/value_AM | 2025-07-17 | 1467 | 845 |
| intraday/value_PM1 | 2025-07-17 | 1337 | 844 |
| intraday/pdh_break | 2025-07-17 | 138 | 0 |

固定した末尾1期間のUSABLE比較support総セル数: 6852。正式時間再現性PASSではなく、3fold成立や収益性も示さない。1条件ずつ除外するsupport診断も保存した。window探索・勝者選択なし。
連続許可分足日数の最長は60。理想的な60+5+20×3設計のcalendar下限は125日だが、warm-up・nEff・event頻度・peer人数を保証しない。最小追加データ量は現時点UNKNOWN。まず既存データで成立可能な仕様を確定し、再測定前に凍結する。

## 6. 実装監査と判定

DATA: 許可日間の穴・warm-up・条件付きevent不足がある。WINDOW: 60-position sourceと固定anchorsがcoverage不可能な期間を選んでいた。IMPLEMENTATION/ELIGIBILITY: target snapshot20/peer100/finite posteriorという追加条件が明示target8と重なる。よってMIXED。明白な仕様不変のsoftware repairは今回は実施していない。
symbol joinの欠落は0、session順序・重複・欠測・因果時刻は監査。永久的security identityやPIT availabilityを新たに認定していない。implementation-audit.json参照。
次工程はnext-validation-spec-proposal.jsonの論点を解消して新specを実測前に固定する工程。今回の診断からそのまま再測定やEntry/EXITへ進まない。

## 7. 境界・検証・停止

Focused 211 tests、既存回帰2949 PASS。診断2回manifest一致、旧Evidence hash不変。rawは取得済み許可Developmentだけ復元、保護日との交差0、新規provider request0。過去Exposure LedgerのREPORT19派生閲覧事故は維持し、完全未閲覧と表現しない。
Execution HEAD 84e456c49bc47f642c9e4c7312b4510576152ebc / PR587 Draft・未merge。Safety9項目は全false。CI run 35484934096。保存commitは実行HEADの子孫。
STOP. Handoff Gate BLOCKED維持。NEW Selector/Entry/EXIT/Capital変更なし。
