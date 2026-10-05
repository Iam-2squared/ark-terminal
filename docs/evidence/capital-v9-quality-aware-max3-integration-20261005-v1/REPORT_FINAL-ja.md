# Ark Terminal — Capital v9 Quality-Aware MAX3 Integration

## A. Executive / Parent Authorities

作成: 2026-10-05T10:46:57.748338+09:00。status = **V9_QUALITY_PRESERVED_CAPITAL_FAIL**。selectedCapitalCandidate = `None`。diagnosticArm = `I2`。NEXT_BOTTLENECK = **CAPITAL_MONETIZATION_OR_SIZING**。

Main parent: `b1abed001c8d8918d4a40776068a0eff384c7b18` (`CAPITAL_V8R1_R15_CLOSURE_FIXED_STOP / V8R1_NO_GO`)。Quality parent: `a977e30aa3318f639569f806f389acb99b3596e4` (`ANTI_WEAK_MEDIUM_STRONG / QUALITY_RECOVERY_PASS / R12_CLOSURE_FIXED_STOP`)。Mainから新branchを作成し、Qualityの履歴はmergeせず、model/artifactをhash固定したread-only inputとして使用した。

I1は future r > current r AND future q2 >= current q2。I2はさらに future q3 >= current q3。pPがPrimary ordering authorityであり、batch順・tenure・0.5閾値・sizing・executionは凍結。raw Logistic scoreはordering/dominance用であり、真の確率とは呼ばない。

Exposure = **ITERATIVE_DEVELOPMENT_EVIDENCE**。同じ58 Development sessionsを反復利用している。Fresh/OOS成功ではない。QualityのpP-conditional deltaのCIは0を跨ぎ、MOVE_U3 Big/Mega guardはPARTIAL。成功・不成功を問わず同cycleでの救済・再調整は行わない。

## B. North Star / rolling20

|Profile|20d min|mean|median|max|2x N/rate|
|---|---|---|---|---|---|
|v5 saved|1.0823662751|1.1906460126|1.1991541915|1.2970310262|0/19 (0.000000%)|
|v8R1 B2 saved|0.8083747195|0.9200316452|0.9144601076|1.0322967466|0/19 (0.000000%)|
|I1|0.8295076482|0.9305468287|0.9231834682|1.0625358372|0/19 (0.000000%)|
|I2|0.8439496722|0.9443465262|0.9146242057|1.0972839118|0/19 (0.000000%)|

¥1,000,000から38 OOF Development sessionsを連結。同ledgerの19 rolling20 windowsは重複しており独立19標本ではない。Final38を1か月成績とは呼ばない。

## C. Medium-to-Big Quality Preservation

|Profile|Funded N|Medium3–<5|U5|U10|<2|<3|
|---|---|---|---|---|---|---|
|v5 saved|150|27|50|26|38.666667%|48.666667%|
|v8R1 B2 saved|147|25|47|24|40.136054%|51.020408%|
|I1|158|30|50|26|38.607595%|49.367089%|
|I2|161|32|53|26|36.024845%|47.204969%|

|Gate|I1|I2|
|---|---|---|
|P1_U5_gt50|False|True|
|P2_U10_ge26|True|True|
|P3_Medium_ge27|True|True|
|P4_below2_le38_666667pct|True|True|
|P5_below3_le48_666667pct|False|True|
|P6_integrity0|True|True|
|P7_independent_mismatch0|True|True|

全7条件を満たす場合だけQUALITY_CAPACITY_PRESERVATION_PASS。U5増加だけでは採用しない。Primaryはpotential quality、realizedはSecondary diagnostic。

|Profile|U2 N/rate|U3 N/rate|Medium rate|Big5–<10|Mega≥10|Weak<2|Low2–<3|realized≤0|realized mean|realized median|
|---|---|---|---|---|---|---|---|---|---|---|
|I1|97/61.392405%|80/50.632911%|18.987342%|24|26|61|17|90|-0.136407%|-0.229255%|
|I2|103/63.975155%|85/52.795031%|19.875776%|27|26|58|18|90|-0.022398%|-0.099950%|

## D. U5/U10 reason conservation

|Profile|Label|Funded|Rank reject|Reserve|MAX3|cash/lot|other|total|
|---|---|---|---|---|---|---|---|---|
|B2|U5|47|46|55|13|9|0|170|
|B2|U10|24|12|22|5|4|0|67|
|I1|U5|50|46|42|19|13|0|170|
|I1|U10|26|12|15|9|5|0|67|
|I2|U5|53|46|38|21|12|0|170|
|I2|U10|26|12|14|10|5|0|67|

Primary common supported OOF N=1028。U5=170/U10=67。Admission490 identities、exact executable488、Admission U5=124/U10=55。保存済Physical Oracle U5=149/U10=67、Admission Oracle U5=116/U10=55は再solveしていない。

## E. Capacity Reserve reduction

|Profile|Reserve U5|Reserve U10|MAX3 U5|MAX3 U10|cash U5|cash U10|Rank U5|Rank U10|
|---|---|---|---|---|---|---|---|---|
|B2|55|22|13|5|9|4|46|12|
|I1|42|15|19|9|13|5|46|12|
|I2|38|14|21|10|12|5|46|12|

同一stateの全1,960 support casesでpressure_I2 ≤ pressure_I1 ≤ pressure_B2、ACCEPT implicationを確認。実Replayでは早期fundingによるoccupancy pathが変わるため、globalのB2 funded setのsupersetとは主張しない。

## F. Gained/Lost funding vs B2

|Profile/group|N|Medium|U5|U10|Weak|Low|realized PnL diagnostic|
|---|---|---|---|---|---|---|---|
|I1 GAINED_FUNDING_vs_B2|30|6|9|4|12|3|-76778.45000|
|I1 LOST_FUNDING_vs_B2|19|1|6|2|10|2|-28869.35000|
|I2 GAINED_FUNDING_vs_B2|39|8|12|5|15|4|-65307.00000|
|I2 LOST_FUNDING_vs_B2|25|1|6|3|16|2|-63506.55000|

|Profile|Net U5|Net U10|Net Medium|Net Weak|
|---|---|---|---|---|
|I1|3|2|5|2|
|I2|6|2|7|-1|

各groupのpP/q2/q3 mean・median、Entry hour別N/quality/PnLは[POLICY_DELTA_RESULT.json](POLICY_DELTA_RESULT.json)に保存。個々のlost candidateを特定gained candidateの因果replacementとは断定しない。

## G. Induced occupancy cost

|Profile/group|N|Medium|U5|U10|Weak|
|---|---|---|---|---|---|
|I1 NEW_MAX3_MISS_vs_B2|19|0|6|4|9|
|I1 RESERVE_RECOVERY|28|5|9|4|11|
|I2 NEW_MAX3_MISS_vs_B2|34|2|8|5|19|
|I2 RESERVE_RECOVERY|34|7|10|5|14|

NEW_MAX3_MISSはB2ではMAX3でなかったidentityがIntegrationでMAX3_FULLになった件数。RESERVE_RECOVERYはB2 Reserve→Integration Funded。事前固定countを表示し、結果後にnet-value定義を追加していない。詳細は[INDUCED_OCCUPANCY_RESULT.json](INDUCED_OCCUPANCY_RESULT.json)。

## H. Slot1/2/3 quality

|Profile/slot|N|Medium|U5|U10|<2|<3|
|---|---|---|---|---|---|---|
|I1 slot1|45|8|21|12|28.888889%|35.555556%|
|I1 slot2|63|11|18|10|39.682540%|53.968254%|
|I1 slot3|50|11|11|4|46.000000%|56.000000%|
|I2 slot1|45|9|20|12|28.888889%|35.555556%|
|I2 slot2|66|12|20|11|37.878788%|51.515152%|
|I2 slot3|50|11|13|3|40.000000%|52.000000%|

## I. pP / q2 / q3 score diagnostics

|Profile|score|funded mean|funded median|missed U5 mean|
|---|---|---|---|---|
|I1|pP|0.3971969537|0.3725038207|0.1715361694|
|I1|q2|0.7113083485|0.7350882994|0.4795948629|
|I1|q3|0.5538074176|0.5475553597|0.3245698890|
|I2|pP|0.3908872510|0.3664982754|0.1676915996|
|I2|q2|0.7117856029|0.7328571302|0.4747468863|
|I2|q3|0.5600876053|0.5754281582|0.3185844065|

|Profile|LOWER_P_ACCEPT_AFTER_HIGHER_P_RESERVE_SAME_BATCH|
|---|---|
|I1|2|
|I2|2|

Qualityでbatch reorderせず、higher pPが先にReserveされた後のlower pP ACCEPTを許可。training q2/q3は8 frozen block-modelのcompleted past trainへのresubstitution score。teacher fieldsはpressure build input objectに存在しない。saved predictionsはauditにだけ使用し、Mainにはcausal featureから再構築したscoreを使用した。

## J. pP clairvoyant saved reference

selected234 / U5=81 / U10=38 / <2=92 (39.316239%)。cash-constrained pP-only label-blind diagnosticであり、U5 upper boundでもwinner gateでもない。新solve=0。Quality signal追加後のU5>81やpP utility低下をエラーとはみなさない。

## K. Capital Secondary

|Profile|Final38 JPY|total return|daily geo|daily arith|daily median|minute MTM MaxDD|util mean/median|idle cash JPY|turnover JPY|recycled cash JPY|funded/session|
|---|---|---|---|---|---|---|---|---|---|---|---|
|v5 saved|1477436.15|47.743615%|1.032420%|1.107940%|0.188228%|10.225325%|41.986827%/48.260213%|saved未収録|89327438.95|6728380.05|3.947368|
|v8R1 B2 saved|923254.50|-7.674550%|-0.209912%|-0.149159%|-0.250158%|25.941206%|38.447762%/38.428327%|601108.68|75891019.40|6852102.00|3.868421|
|I1|922425.95|-7.757405%|-0.212270%|-0.153414%|-0.251479%|23.196250%|41.126797%/46.973885%|581683.04|78548119.15|7262797.00|4.157895|
|I2|933856.05|-6.614395%|-0.179925%|-0.125972%|-0.278734%|21.242600%|41.435765%/49.268072%|589217.18|81287912.75|7916975.30|4.236842|

|Profile|rolling20 median >v5|rolling20 mean >v5|daily geometric >v5|Preservation PASS|Capital PASS|
|---|---|---|---|---|---|
|I1|False|False|False|False|False|
|I2|False|False|False|True|False|

## L. Independent Audit

causal canary 60/60 PASS。Pre-main独立監査 208,552 checks / 3,920 action cases、mismatch0。numeric 82,464 pair、near-tie 0、boundary disagreement0。Full audit 213,794 checks、mismatch 0、max float delta 8.8817841970012523e-16 ≤1e-12。money/quantity exact。

Primary runtime/replay/evaluator import0。独立scalar inference・past table・tenure・dominance・actionとFraction accountingで、BUY/SELL/MTM/cash/quantity/occupancy/daily/rolling20/Final38/MaxDD、quality conservation、paired gained/lost、induced MAX3、gates、winner、bottleneckを検証。実装独立性を主張し、共有upstream市場データの独立性は主張しない。actual arrivalは未知で、継承したbar-end as-of boundaryを使用した。

## M. Winner / Next Bottleneck

status=V9_QUALITY_PRESERVED_CAPITAL_FAIL、selectedCapitalCandidate=None、diagnosticArm=I2。diagnostic armは採用ではない。NEXT_BOTTLENECK=CAPITAL_MONETIZATION_OR_SIZING。

|Observed exclusive U5 miss|N|
|---|---|
|CAPACITY_RESERVE|38|
|CASH_SIZING|12|
|MAX3_ONLINE_OCCUPANCY|21|
|RANK_ADMISSION|46|

次の検証は別の独立Workでのみ行う。今cycleではAdmission、I3、blend、threshold、tenure、sizing、MAX4/5、replacement、Freshへの変更を行わない。Quality head自体の再fitを結論にしない。orders=0 / main merge=0 / force push=0 / provider request=0 / Claude=0。Safetyは全false。

```text
selectedBigWinnerRank = EXISTING_MOVE_P5
selectedAuxiliaryHeads = ["MOVE_U2","MOVE_U3"]
selectedCapitalCandidate = None
diagnosticArm = I2
NEXT_BOTTLENECK = CAPITAL_MONETIZATION_OR_SIZING
newFits = 0
CapitalReplays = 2
fresh_OOS_claim = false
productionReady = false
CURRENT_STATE = CAPITAL_V9_V14_CLOSURE_FIXED_STOP
```
