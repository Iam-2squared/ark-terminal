## A. North Star / rolling 20 sessions

|Profile|20d min|20d mean|20d median|20d max|2x hit|
|---|---:|---:|---:|---:|---:|
|v5 saved|1.0823662751x|1.1906460126x|1.1991541915x|1.2970310262x|0/19|
|v7 A1 saved|0.9894268413x|1.0759537031x|1.0480741764x|1.2254908119x|0/19|
|v7 A2 saved|0.8638211957x|0.9641337276x|0.9396052222x|1.1311273645x|0/19|
|B1|未評価|未評価|未評価|未評価|未評価|
|B2|未評価|未評価|未評価|未評価|未評価|

Status = **V8_CONTRACT_FAIL**。pP clairvoyant diagnosticのcash-only証明が失敗したため、事前commit済みSTOP ruleで停止。B1/B2 Main replayは0回。policyのNO_GOとは判定しない。

## B. U5/U10 preservation

|Profile|U5/170|U10/67|Admission recovery U5|Physical recovery U5|<2|Reserve U5|MAX3 U5|Rank reject U5|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|v5 saved|50/170|26/67|50/116|50/149|38.666667%|30|28|57|
|v7 A1 saved|50/170|27/67|50/116|50/149|43.274854%|0|67|46|
|v7 A2 saved|51/170|25/67|51/116|51/149|41.875000%|41|26|46|
|B1|未評価|未評価|未評価|未評価|未評価|未評価|未評価|未評価|
|B2|未評価|未評価|未評価|未評価|未評価|未評価|未評価|未評価|

v7 savedのみを表示。旧Oracleは再solveしていない。Admissionはruntime 490件、実行ソース完備488件。差の2 negative候補を削除せず、未来のexecution availabilityをruntime gateへ追加しなかった。

## C. Preservation Gate

B1/B2ともNOT_EVALUATED。U5>50、U10>=26、<2<=38.666667%、Admission recovery>50/116、integrity0、独立mismatch0のPASS claimは0。

## D. Capital Gate

B1/B2ともNOT_EVALUATED。rolling20 median/mean/daily geometricは生成していない。2x hit=0とは扱わず未評価とする。

## E. Physical / Admission / Runtime waterfall

|段階|U5|今回の扱い|
|---|---:|---|
|Primary|170|common supported OOF固定|
|Physical Oracle|149|v7 savedのみ|
|Admission Oracle|116|v7 savedのみ|
|B1/B2 runtime|未評価|Main 0回|

Physical unavoidable=21、Admission ceiling loss=33は別のcounterfactual分解。新runtime gapは計算不可。

## F. Blocked Winner Anatomy

保存済みA1の51 higher-pP blocked U5を解析した。これはnew policy設計やthreshold変更には使っていない。

最低pP blockerの<2 event=25/51、U5 event=14/51、U10 event=6/51。minimum blocker unique=31。age中央値=63 wall minutes、actual overlap中央値=58 wall minutes。

|Miss到着時台|09|10|11|12|13|14|
|---|---:|---:|---:|---:|---:|---:|
|N|2|21|5|12|8|3|

event数は重複holdingを含む診断。minimum blockerは一意の因果責任やreplacement利益を意味しない。JSON/CSVに全held position、pP/r/band、age、release、overlap、potential bucket、realized returnを保存。

## G. False Reserve / Bad Fill

B1/B2未評価。v7のsaved anatomy以外の新policy結果を生成していない。

## H. pP Clairvoyant Scheduling Diagnostic

1 solve invocationを開始し、区間/MAX3だけのrelaxed optimumを生成したが、100株minimum-lot cash witnessのcash>=0 assertionでexit code 1。cash-only制約を満たすdiagnostic scheduleとして認定できなかった。selected N / utility / U5 / U10 / <2は未保存・未認定であり、推測や再solveで穴埋めしない。

今回の原因はevaluation solverのcash制約不足。これはB1/B2の失敗、cash sizing bottleneck、pP signal不在の証明ではない。U5/U10 labelはobjectiveに使っていない。未来scheduleはruntimeへ渡していない。

主solve code/claim hashは一致。事前commit済み「cash witness失敗ならSTOP、second solveなし」を守り、cash-constrained solverへの変更やrerunを同cycleで行わなかった。

## I. Slot1/2/3

B1/B2未評価。slot qualityは生成なし。

## J. pP decile / Entry hour

B1/B2 funded/missed decile・hourは未評価。保存済み51件のanatomyだけをD3として保存。

## K. Final38 / MaxDD / utilization Secondary

|Profile|Final38|Minute MTM MaxDD|daily geometric|utilization mean|
|---|---:|---:|---:|---:|
|v5 saved|¥1,477,436.15|10.225325%|1.032420%|既存authority参照|
|v7 A1 saved|¥1,320,438.35|12.224148%|0.734165%|47.544540%|
|v7 A2 saved|¥1,051,087.75|21.202388%|0.131206%|44.850448%|
|B1/B2|未評価|未評価|未評価|未評価|

Final38を1か月成績とは呼ばない。19 rolling windowsは独立19標本ではない。

## L. Independent Audit / Safety

Input/ZIP/GitHub contract byte mismatch=0。Required full independent auditはNOT_RUNでありmismatch0を主張しない。40 canary、training tables、pre-main independent policy auditは未実行、Mainを許可しなかった。

|Count|N|
|---|---:|
|primary pP diagnostic attempted / certified|1 / 0|
|independent pP diagnostic solve|0|
|B1 / B2 primary replay|0 / 0|
|Rank / Slot ML fits|0 / 0|
|teacher regeneration / old Oracle rerun|0 / 0|
|v5 / v6 / v7 replay|0 / 0 / 0|
|provider / Claude / orders|0 / 0 / 0|
|main merge / force push / protected-fresh open|0 / 0 / 0|

Selector / Entry / EXIT changes=0。Rank / Admission / Sizing / Liquidity changes=0。全Safety false。Exposure=ITERATIVE_DEVELOPMENT_EVIDENCE。

D5-labelled GitHub publicationは実装source/旧receiptの保存であり、successful solve resultではない。D6には仕様precommitのみが存在する。append-only correctionで明示し、過去recordは書換えない。D7-D15は未完了のままterminal contract-failureとしてD16で固定STOP。

## M. Next Bottleneck

経済・preservationのNEXT_BOTTLENECKは未判定。B1/B2のobserved exclusive reasonが無いため、指定winner/diagnostic/bottleneck ruleを適用できない。solverのcash witness失敗からCASH_SIZINGを選ぶこともしない。

次に必要なのは独立した新cycleでのcash制約付きevaluation diagnostic solverの設計・precommitであり、このcycleのsolve/replay再実行やpolicy rescueは認めない。v5 official Capital benchmarkとEXISTING_MOVE_P5 Rankを保持。

selectedRankCandidate = EXISTING_MOVE_P5
selectedCapitalCandidate = null
diagnosticArm = null
NEXT_BOTTLENECK = null (CONTRACT_BLOCKED_NOT_EVALUATED)
fresh_OOS_claim = false
productionReady = false
CURRENT_STATE = CAPITAL_V8_D16_CLOSURE_FIXED_STOP
