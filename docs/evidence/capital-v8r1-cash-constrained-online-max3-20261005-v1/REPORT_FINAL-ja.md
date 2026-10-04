# Capital v8R1 最終Report

## A. North Star / rolling20

|Profile|20d min|20d mean|20d median|20d max|2x hit|
|---|---|---|---|---|---|
|v5 saved|1.0823662751x|1.1906460126x|1.1991541915x|1.2970310262x|0/19 (0%)|
|v7 A1 saved|0.9894268413x|1.0759537031x|1.0480741764x|1.2254908119x|0/19 (0%)|
|v7 A2 saved|0.8638211957x|0.9641337276x|0.9396052222x|1.1311273645x|0/19 (0%)|
|B1|0.7813670808x|0.8933243648x|0.8871356447x|1.0189571769x|0/19 (0%)|
|B2|0.8083747195x|0.9200316452x|0.9144601076x|1.0322967466x|0/19 (0%)|

最終status=V8R1_NO_GO。selectedCapitalCandidate=null。v5をCapital benchmarkとして保持する。
North Starは¥1,000,000→¥2,000,000 / rolling20。全profileで2x=0/19。38 OOF Development sessionsを連結し、新B1/B2は各1回のみ実行した。
これはITERATIVE_DEVELOPMENT_EVIDENCEであり、fresh/OOS成功ではない。19 rolling windowsは重複し、独立19標本ではない。

## B. U5/U10 preservation

|Profile|U5/170|U10/67|Admission recovery U5/U10|Physical recovery U5/U10|<2|Reserve U5|MAX3 U5|Rank reject U5|
|---|---|---|---|---|---|---|---|---|
|v5 saved|50/170|26/67|43.103448% / 47.272727%|33.557047% / 38.805970%|38.666667%|30|28|57|
|v7 A1 saved|50/170|27/67|43.103448% / 49.090909%|33.557047% / 40.298507%|43.274854%|0|67|46|
|v7 A2 saved|51/170|25/67|43.965517% / 45.454545%|34.228188% / 37.313433%|41.875000%|41|26|46|
|B1|42/170|20/67|36.206897% / 36.363636%|28.187919% / 29.850746%|42.758621%|59|13|46|
|B2|47/170|24/67|40.517241% / 43.636364%|31.543624% / 35.820896%|40.136054%|55|13|46|

v5のRank reject 57は旧rank-pass U5=113からの差であり、新rank-native admissionの46とは別lineage。v5は保存済み結果のみで再replayしていない。

|Arm / target|FUNDED|RANK_BASE_REJECT|CAPACITY_RESERVE_REJECT|MAX3_FULL|CASH_OR_LOT|SAME_SYMBOL|EXECUTION_BLOCKED|OTHER|Total|
|---|---|---|---|---|---|---|---|---|---|
|B1 U5|42|46|59|13|10|0|0|0|170|
|B1 U10|20|12|26|6|3|0|0|0|67|
|B2 U5|47|46|55|13|9|0|0|0|170|
|B2 U10|24|12|22|5|4|0|0|0|67|

|Arm / admission target|FUNDED|Reserve|MAX3|Cash/lot|Others|Total|
|---|---|---|---|---|---|---|
|B1 U5|42|59|13|10|0|124|
|B1 U10|20|26|6|3|0|55|
|B2 U5|47|55|13|9|0|124|
|B2 U10|24|22|5|4|0|55|

|Arm|Funded N|U5 capture|U10 capture|<3|Medium3–<5|Funded/session|
|---|---|---|---|---|---|---|
|B1|145|24.705882%|29.850746%|53.103448%|26|3.815789|
|B2|147|27.647059%|35.820896%|51.020408%|25|3.868421|

## C. Cash-constrained pP diagnostic

PPRANK_CLAIRVOYANT_ADMISSION_DIAGNOSTIC_CASH_JOINT_V1 = CERTIFIED / UNIQUE_CANONICAL。

|Metric|Result|
|---|---|
|Executable / runtime admission|488 / 490|
|Stage1 integer utility|193795278|
|Stage2 selected N|234|
|Stage3 stable ordinal sum|58834|
|U5 / U10 / <2 N|81 / 38 / 92|
|<2 selected density|39.316239%|
|Exact minimum cash|¥15,747.85|
|Integerization|scale=100; exact ticks; rounding=0|
|MAX3 / same-symbol violations|0 / 0|
|Primary stages|3/3 OPTIMAL|
|Optional NO-GOOD|1; alternative Stage3-optimal identity infeasible|
|Independent objective / cash / identity mismatch|0|

未来pP arrivalsとFrozen releaseを知るminimum-lot 100株scheduleの診断であり、U5 upper boundではない。U5/U10/realized PnLはobjectiveに使っていない。売却価格はcash feasibilityにのみ使う。結果・selected identity・diagnostic statusはruntimeとB1/B2 tableへ一切渡していない。
cash-relaxed optimumの後付けwitnessではなく、累積cash、MAX3、same-symbolを最初からMILP hard constraintへ入れた。全38 sessionを連結し、same-minute confirmed exits→Entry buysの順序でDecimal exact certificationを行った。

|Profile|Selected/funded N|sum r|pP utility efficiency|U5|U10|<2 N|
|---|---|---|---|---|---|---|
|Clairvoyant diagnostic|234|193.795272550615|100%|81|38|92|
|B1|145|127.528555957161|65.805814%|42|20|62|
|B2|147|129.870917746599|67.014492%|47|24|59|

Diagnostic training-r decile（10が最高）: 10=93、9=58、8=39、7=23、6=21。後述のcommon-cohort raw-pP decile（1が最高）とは定義を混同しない。

## D. Preservation Gate

|Arm|P1 U5>50|P2 U10≥26|P3 <2≤38.666667%|P4 U5/116>50/116|P5 integrity|P6 independent|All|
|---|---|---|---|---|---|---|---|
|B1|FAIL|FAIL|FAIL|FAIL|PASS|PASS|FAIL|
|B2|FAIL|FAIL|FAIL|FAIL|PASS|PASS|FAIL|

R11のP6=PENDING recordは上書きせず、R13独立監査PASSをFINAL_GATE_RESULT.jsonで追記解決した。両armはP1–P4がFAIL、P5/P6がPASSで採用不可。

## E. Capital Gate

|Arm|Preservation|20d median>1.1991541915|20d mean>1.1906460126|Daily geom>1.032420041%|Capital|
|---|---|---|---|---|---|
|B1|FAIL|FAIL|FAIL|FAIL|FAIL|
|B2|FAIL|FAIL|FAIL|FAIL|FAIL|

両armともCapital3条件も全FAIL。診断solverの修正成功はpolicy成功を意味しない。旧v8はV8_CONTRACT_FAILの固定STOPを維持し、旧v8でB1/B2は未評価だった事実を0成績に置換しない。

## F. Physical / Admission / Runtime waterfall

|Stage|U5|Difference|
|---|---|---|
|Primary potential winners|170|—|
|Saved Physical Oracle|149|Physical unavoidable=21|
|Saved Admission Oracle|116|Admission ceiling loss=33|
|B1 runtime funded|42|Admission Oracle→runtime=74|
|B2 diagnostic arm runtime funded|47|Admission Oracle→runtime=69|

Counterfactual waterfall: B2は170 = 21 + 33 + 69 + 47。保存済みv7 Oracleは再solveしていない。
Observed exclusive waterfall: B2は170 = Rank reject46 + Reserve55 + MAX3 13 + cash/lot9 + funded47。counterfactual21/33とobserved46/55/13/9を足してはならない。
Admission実候補U5=124とAdmission Oracle116の差8はadmission内部のphysical overlap等による。Admission実候補からのmiss77とOracle→runtime gap69も別定義。U10は67→67 Physical→55 Admission→24 B2 funded。

## G. False Reserve / Bad Fill

|Arm|False Reserve U5|False Reserve U10|Bad Fill blocked U5/U10|Higher-pP blocked by lower held U5/U10|
|---|---|---|---|---|
|B1|59|26|2 / 1|3 / 2|
|B2|55|22|3 / 1|4 / 2|

Bad Fillは<2 holdingがhigher-pP winnerのMAX3_FULL missと重なったunique missed candidate数。単一の因果責任、replacement利益、EXIT変更の正当化を意味しない。
B2はB1よりReserve U5を59→55へ4件減らしfunded U5を42→47へ増やしたが、v5の50/26とcontamination guardを超えなかった。

### 保存済み51 higher-pP blocked U5 anatomy（再生成0）

|Metric|Saved result|
|---|---|
|Events / blocked U10|51 / 16|
|Lowest-pP blocker <2 / U5 / U10 event N|25 / 14 / 6|
|Lowest-pP blocker unique N|31|
|Blocker age median wall minutes|63|
|Actual overlap median wall minutes|58|
|pP gap median|0.137943025280|
|Miss hour09/10/11/12/13/14|2 / 21 / 5 / 12 / 8 / 3|

旧v8のBLOCKED_WINNER_ANATOMY.json/.csvをread-only authorityとして再利用。anatomy結果からB1/B2仕様は変更していない。

## H. Slot quality

|Arm|Slot|N|U5|U10|<2 N / rate|<3 N / rate|Medium3–<5|
|---|---|---|---|---|---|---|---|
|B1|1|45|19|10|15 / 33.333333%|17 / 37.777778%|9|
|B1|2|64|17|7|29 / 45.312500%|39 / 60.937500%|8|
|B1|3|36|6|3|18 / 50.000000%|21 / 58.333333%|9|
|B2|1|46|21|12|16 / 34.782609%|18 / 39.130435%|7|
|B2|2|62|16|7|26 / 41.935484%|37 / 59.677419%|9|
|B2|3|39|10|5|17 / 43.589744%|20 / 51.282051%|9|

## I. pP decile / Entry hour

Common supported 1028候補をfrozen raw pP DESC / Entry timestamp ASC / symbol ASCへ並べたdecile。1が最高。各cellはfunded N / U5 / U10。runtime thresholdには使わない。

|pP decile|B1 N / U5 / U10|B2 N / U5 / U10|
|---|---|---|
|1|81 / 26 / 11|80 / 25 / 10|
|2|34 / 11 / 8|39 / 16 / 12|
|3|12 / 1 / 0|11 / 2 / 1|
|4|10 / 2 / 1|11 / 2 / 1|
|5|8 / 2 / 0|6 / 2 / 0|
|6|0 / 0 / 0|0 / 0 / 0|
|7|0 / 0 / 0|0 / 0 / 0|
|8|0 / 0 / 0|0 / 0 / 0|
|9|0 / 0 / 0|0 / 0 / 0|
|10|0 / 0 / 0|0 / 0 / 0|

|Entry hour JST|B1 N / U5 / U10|B2 N / U5 / U10|
|---|---|---|
|9|29 / 14 / 10|29 / 14 / 10|
|10|51 / 15 / 7|55 / 18 / 10|
|11|15 / 1 / 0|15 / 1 / 0|
|12|22 / 6 / 1|22 / 7 / 1|
|13|14 / 2 / 1|14 / 3 / 2|
|14|10 / 4 / 1|9 / 4 / 1|
|15|4 / 0 / 0|3 / 0 / 0|

|Arm|Funded r mean / median|Missed-U5 r mean / median|
|---|---|---|
|B1|0.879507282463 / 0.923585598824|0.613274564855 / 0.652845428151|
|B2|0.883475630929 / 0.920000000000|0.603870816738 / 0.634827332843|

## J. Final38 / MaxDD / utilization（Secondary）

|Metric|v5 saved|v7 A1 saved|v7 A2 saved|B1|B2|
|---|---|---|---|---|---|
|Daily geometric|1.032420%|0.734165%|0.131206%|-0.387471%|-0.209912%|
|Daily arithmetic|—（saved benchmark概要に未収録）|0.803091%|0.214960%|-0.327797%|-0.149159%|
|Daily median|—（saved benchmark概要に未収録）|0.060418%|-0.586287%|-0.321298%|-0.250158%|
|Final38|¥1,477,436.15|¥1,320,438.35|¥1,051,087.75|¥862,841.05|¥923,254.50|
|Total return|—（saved benchmark概要に未収録）|32.043835%|5.108775%|-13.715895%|-7.674550%|
|Minute MTM MaxDD|10.225325%|12.224148%|21.202388%|28.899191%|25.941206%|
|Utilization mean|—（saved benchmark概要に未収録）|47.544540%|44.850448%|37.405516%|38.447762%|
|Utilization median|—（saved benchmark概要に未収録）|54.005944%|48.145494%|36.076703%|38.428327%|
|Idle fraction mean|—（saved benchmark概要に未収録）|52.455460%|55.149552%|62.594484%|61.552238%|
|Idle cash mean|—（saved benchmark概要に未収録）|¥608,005.26|¥592,338.16|¥600,686.90|¥601,108.68|
|Turnover BUY+SELL|—（saved benchmark概要に未収録）|¥88,923,117.55|¥83,624,453.55|¥74,517,949.95|¥75,891,019.40|
|Recycled cash used|—（saved benchmark概要に未収録）|¥6,818,319.10|¥7,192,429.15|¥6,734,867.20|¥6,852,102.00|
|Funded/session|—（saved benchmark概要に未収録）|4.500000|4.210526|3.815789|3.868421|

Final38は38 Development sessionsの連結結果であり「1か月成績」ではない。全38 day COMPLETE / execution unresolved=0。daily38・rolling20の19全windowは各arm RESULT.jsonへ保存し、同一ledgerから計算した。MaxDDはminute MTMを使用し、hard gateには追加していない。

## K. Independent Audit / count / Safety

|Check|Result|
|---|---|
|Synthetic diagnostic preflight|12/12 PASS|
|Causal canary|43/43 PASS|
|Pre-main independent policy audit|37,458 checks / 3,920 action cases / mismatch=0|
|Full independent audit|229,820 checks / mismatch=0|
|Money / quantity tolerance|0 (exact)|
|Score/r/pressure tolerance|≤1e-12; observed maximum delta=0|
|New Rank / Slot ML fits; teacher regeneration|0 / 0 / 0|
|Primary cash diagnostic packages / independent|1 / 1|
|Optional uniqueness NO-GOOD|1|
|B1 / B2 primary replays|1 / 1|
|Independent full recalculations|2|
|v5/v6/v7/old-v8 replay; old Oracle solve|0; 0|
|Threshold sweep / grid / B3 / retune / rescue|0 / 0 / 0 / 0 / 0|
|Orders / provider requests / Claude / main merge / force push|0 / 0 / 0 / 0 / 0|
|Protected/Holdout/Fresh/Validation/OOS/Prospective open|0|
|Cash negative / MAX3 / same-symbol / after15:20 funded violations|0 / 0 / 0 / 0|
|Leakage / future test access / identity mismatch|0 / 0 / 0|

独立実装はPrimary runtime/replay/evaluatorをimportせずraw sourceからpolicy、quantity、Fraction cash、MTM、preservation、rolling20、selectionを再計算した。同じmarket source/Scipy backendを使うため外部source truthの独立証明ではない。
Safety: executionAllowed=false; brokerWriteAllowed=false; excelOrderWriteAllowed=false; rssOrderFunctionAllowed=false; liveTradingAllowed=false; paperTradingAllowed=false; automaticPromotionAllowed=false; productionUpdateAllowed=false; transmitted=false; productionReady=false。
本新cycleの未完了table buildで欠損release fieldはUNKNOWN/非completeとして除外するinput parserを修正した。既存teacherを書換えずtenureのknown-release contractを維持し、完成済みtable/diagnostic/replayを再生成していない。
Rank contract SHA256=6e8687f36f6f60fc9e9921e1ef29e0520cf1ea8bc01f14386963f1020b209518。
pP score stream SHA256=14c48e61554bd58c6d5289b410d6a8c859cb37efd0dbc5d98987fcb440aac2ed。
Band map SHA256=bbe73fd89a4f045fff7de768877aed670c8d343c026ac94557af151e643eef1d。
Frozen B1/B2 runtime.py SHA256=f9232d8d501832c15344f7f5f125dab929814c5285406c3a932a027c498aa32e（旧v8とbyte exact）。POLICY_B1_B2_PRECOMMIT source/hashはB1_B2_SEMANTIC_FREEZE.jsonへ保存済み。
Main前claimはR9のcommit→actual GET→single executionで管理し、各checkpointのHEAD/tree/JST/actual GET receiptをappend-onlyで保存した。old branchとold Evidenceはread-only。

## L. Next Bottleneck / fixed handoff

|Diagnostic arm B2: observed exclusive actionable U5 miss|Count|
|---|---|
|RANK_ADMISSION|46|
|CAPACITY_RESERVE|55|
|MAX3_ONLINE_OCCUPANCY|13|
|CASH_SIZING|9|

NEXT_BOTTLENECK=CAPACITY_RESERVE（55）。事前固定ruleでobserved exclusive miss最大countを選んだ。Physical unavoidable21 / Admission ceiling loss33 / Admission Oracle→runtime gap69は別counterfactualとして併記する。
pP clairvoyantのU5=81は解釈補助のみでbottleneck選定には使用していない。新Rankを戻す根拠でもない。RankはEXISTING_MOVE_P5のまま保持し、Capitalはv5 benchmarkを保持する。
このcycleでB3、0.5/support10/median/bucket、Admission、Rank、Selector/Entry/EXITを変更しない。次Workは独立した新指示が必要。Fresh開封、MAX4/MAX5、replacement、main merge、ordersは行わない。R15で固定STOP。

```text
selectedRankCandidate = EXISTING_MOVE_P5
selectedCapitalCandidate = null
diagnosticArm = TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1
NEXT_BOTTLENECK = CAPACITY_RESERVE
fresh_OOS_claim = false
productionReady = false
CURRENT_STATE = CAPITAL_V8R1_R15_CLOSURE_FIXED_STOP
```
