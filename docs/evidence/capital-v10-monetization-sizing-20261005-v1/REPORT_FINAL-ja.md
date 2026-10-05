# Capital v10 Monetization / Sizing — Final Report
作成: 2026-10-05T11:41:10.394576+09:00

## A. Executive / v9 authority

status = V10_REALIZED_MONETIZATION_LIMIT。selectedCapitalCandidate = null。diagnosticArm = S1。NEXT_BOTTLENECK = REALIZED_MONETIZATION_SIGNAL。
v9 actual terminal HEAD: `0672aa0fe04afb304f10391ed9634c1da08ee4f8`。Main parent `b1abed001c8d8918d4a40776068a0eff384c7b18` / Quality parent `a977e30aa3318f639569f806f389acb99b3596e4`。旧v9はV14固定STOPを保持。新branchは`capital-v10-monetization-sizing-20261005`。
Sizing weightのみ変更。S1=1、S2=min(rp,r2,r3)。percentile=(1+completed-past training score < currentの件数)/(N+1)。label/test cross-section0。I2 gate・tenure・cap・target・waterfill・Entry/EXIT・MAX3・cash executionはFreeze。
仕様JSONは診断前commit `53b2f58d6698828f4ab67b048570ba0a178ef294` のactual GETで固定。診断を理由にSizing候補変更0。
Exposure=ITERATIVE_DEVELOPMENT_EVIDENCE。同じ58 Development sessionsの反復利用、OOF38連結。Fresh/OOS成功ではなく将来収益保証なし。

## B. North Star

|Profile|20d min|mean|median|max|2x|
|---|---:|---:|---:|---:|---:|
|v5 saved|1.0823662751|1.1906460126|1.1991541915|1.2970310262|0/19|
|I2 saved|0.8439496722|0.9443465262|0.9146242057|1.0972839118|0/19|
|S1|0.8603202085|0.9542671531|0.9283112455|1.1058223900|0/19|
|S2|0.8586452450|0.9526717798|0.9267841378|1.1040546212|0/19|

19 rolling20 windowsは重なりがあり独立19標本ではない。Final38を1か月成績と呼ばない。

## C. Quality Retention

|Profile|N|Medium|U5|U10|<2|<3|
|---|---:|---:|---:|---:|---:|---:|
|v5 saved|150|27|50|26|38.666667%|48.666667%|
|I2 saved|161|32|53|26|36.024845%|47.204969%|
|S1|162|32|53|27|36.419753%|47.530864%|
|S2|162|32|53|27|36.419753%|47.530864%|
S1: I2 retention=FAIL / v5 floor=PASS / v5 Capital=FAIL / relative progress=FAIL。Gate詳細: {"I2_relative_gates": {"daily_geometric": false, "mean": true, "median": true}, "RELATIVE_CAPITAL_PROGRESS": false, "V10_CAPITAL_IMPROVED": false, "V10_QUALITY_RETENTION_PASS": false, "quality_retention_gates": {"Q1_U5_ge53": true, "Q2_U10_ge26": true, "Q3_Medium_ge32": true, "Q4_Weak_le36_024845pct": false, "Q5_below3_le47_204969pct": false, "Q6_integrity0": true, "Q7_independent_mismatch0": true}, "v5_capital_gates": {"C1_median_gt_v5": false, "C2_mean_gt_v5": false, "C3_daily_geo_gt_v5": false}, "v5_quality_floor": {"Medium_ge27": true, "U10_ge26": true, "U5_ge50": true, "Weak_le38_666667pct": true, "below3_le48_666667pct": true}, "v5_quality_floor_PASS": true}
S2: I2 retention=FAIL / v5 floor=PASS / v5 Capital=FAIL / relative progress=FAIL。Gate詳細: {"I2_relative_gates": {"daily_geometric": false, "mean": true, "median": true}, "RELATIVE_CAPITAL_PROGRESS": false, "V10_CAPITAL_IMPROVED": false, "V10_QUALITY_RETENTION_PASS": false, "quality_retention_gates": {"Q1_U5_ge53": true, "Q2_U10_ge26": true, "Q3_Medium_ge32": true, "Q4_Weak_le36_024845pct": false, "Q5_below3_le47_204969pct": false, "Q6_integrity0": true, "Q7_independent_mismatch0": true}, "v5_capital_gates": {"C1_median_gt_v5": false, "C2_mean_gt_v5": false, "C3_daily_geo_gt_v5": false}, "v5_quality_floor": {"Medium_ge27": true, "U10_ge26": true, "U5_ge50": true, "Weak_le38_666667pct": true, "below3_le48_666667pct": true}, "v5_quality_floor_PASS": true}

正式retentionはU5>=53,U10>=26,Medium>=32,<2<=36.024845%,<3<=47.204969%,integrity0,audit0。v5 floorのみPASSでもadoption対象ではない。PotentialがPrimary、realizedはdiagnostic。

## D. v5 vs I2 Identity Decomposition

|Group|N|Medium|U5|U10|Weak|loser<=0|realized>=1%|unit-lot PnL|actual PnL|mean realized|median realized|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|COMMON v5|77|18|30|18|22|38|30|¥171,941.35|¥371,012.40|1.613531%|0.037087%|
|COMMON I2|77|18|30|18|22|38|30|¥171,941.35|¥277,284.30|1.613531%|0.037087%|
|V5_ONLY|73|9|20|8|36|44|17|¥25,541.55|¥106,423.75|0.503940%|-0.579777%|
|I2_ONLY|84|14|23|8|36|52|20|¥-179,669.50|¥-343,428.25|-1.522000%|-1.039351%|

COMMON_QUANTITY_PNL_DELTA = ¥-93,728.10。identity-side actual PnL差 = ¥-449,852.00。合計差 = ¥-543,580.10。Decimal exact conservation PASS。
identity/quantity diagnosticであり一意の因果分解ではない。COMMONのEntry hour・slot・score分布はJSONに保存。

## E. Potential → Realized Monetization Matrix

|Profile / potential|N|lots|buy notional|share|unit-lot PnL|actual PnL|
|---|---:|---:|---:|---:|---:|---:|
|v5 / 1-<2|31|382|¥9,114,254.85|20.5160%|¥-20,659.50|¥-174,327.05|
|v5 / 2-<3|15|213|¥4,200,499.20|9.4553%|¥-60.75|¥-1,199.90|
|v5 / 3-<4|18|158|¥5,600,498.85|12.6066%|¥18,021.10|¥20,189.40|
|v5 / 4-<5|9|50|¥3,273,135.75|7.3678%|¥-4,117.40|¥-872.70|
|v5 / 5-<10|24|258|¥7,503,950.10|16.8913%|¥40,490.05|¥95,948.05|
|v5 / <1|27|234|¥7,116,056.25|16.0181%|¥-27,082.80|¥-153,339.35|
|v5 / >=10|26|278|¥7,616,606.40|17.1449%|¥190,892.20|¥691,037.70|
|I2 / 1-<2|27|312|¥6,786,991.80|16.6851%|¥-21,355.95|¥-125,224.35|
|I2 / 2-<3|18|184|¥4,400,299.05|10.8177%|¥-56,098.00|¥-95,652.45|
|I2 / 3-<4|20|110|¥5,159,978.70|12.6852%|¥-2,576.75|¥-58,430.75|
|I2 / 4-<5|12|97|¥2,577,688.20|6.3370%|¥-21,664.20|¥-25,964.70|
|I2 / 5-<10|27|136|¥6,540,168.45|16.0783%|¥-2,924.50|¥-65,707.30|
|I2 / <1|31|199|¥7,960,378.20|19.5697%|¥-102,583.00|¥-237,741.45|
|I2 / >=10|26|261|¥7,251,523.95|17.8271%|¥199,474.25|¥542,577.05|

|Profile / potential|realized mean|median|positive|>=1%|loser<=0|potential mean|giveback mean|ratio Q25 / median / Q75|
|---|---:|---:|---:|---:|---:|---:|---:|---|
|v5 / 1-<2|-1.409791%|-0.862546%|8/31|2/31|23/31|1.405843%|2.815634%|-1.275916 / -0.598701 / 0.053002|
|v5 / 2-<3|-0.219535%|0.177550%|8/15|4/15|7/15|2.484698%|2.704233%|-0.635979 / 0.071020 / 0.378352|
|v5 / 3-<4|0.361340%|1.664296%|12/18|10/18|6/18|3.523555%|3.162215%|-0.031297 / 0.440505 / 0.687663|
|v5 / 4-<5|0.045498%|0.283789%|5/9|3/9|4/9|4.369355%|4.323856%|-0.417159 / 0.061566 / 0.281708|
|v5 / 5-<10|1.664755%|0.895081%|16/24|12/24|8/24|6.897730%|5.232975%|-0.035965 / 0.165366 / 0.608884|
|v5 / <1|-1.939783%|-1.875951%|2/27|0/27|25/27|0.470333%|2.410116%|-4.148426 / -2.448776 / -1.103948|
|v5 / >=10|8.212788%|5.375053%|17/26|16/26|9/26|21.632327%|13.419539%|-0.027790 / 0.439471 / 0.687534|
|I2 / 1-<2|-1.637875%|-0.862546%|6/27|2/27|21/27|1.494342%|3.132216%|-1.556377 / -0.598701 / -0.054639|
|I2 / 2-<3|-1.897030%|-0.099950%|8/18|5/18|10/18|2.471816%|4.368845%|-0.996439 / -0.039290 / 0.335548|
|I2 / 3-<4|-0.483214%|1.473572%|13/20|11/20|7/20|3.555101%|4.038314%|-0.335972 / 0.399964 / 0.612045|
|I2 / 4-<5|-0.664990%|0.652846%|7/12|5/12|5/12|4.433075%|5.098065%|-0.478946 / 0.156635 / 0.289320|
|I2 / 5-<10|-0.651228%|0.318626%|16/27|10/27|11/27|6.642754%|7.293982%|-0.122897 / 0.053055 / 0.210739|
|I2 / <1|-2.983840%|-2.516887%|2/31|0/31|29/31|0.008173%|2.992013%|-8.851949 / -4.011313 / -1.139930|
|I2 / >=10|7.788054%|5.375053%|19/26|17/26|7/26|21.837749%|14.049694%|-0.006457 / 0.439471 / 0.625770|

ratioはpotential>0のみ。median/Q25/Q75を主表示しratio meanを使用しない。Weak/Low/Medium/Big/Mega coarse、return on deployed notional等の全fieldは`POTENTIAL_REALIZED_MONETIZATION_MATRIX.json`。

## F. Signal → Frozen EXIT Monetization

|Population|score|AUC >0|AUC >=1%|AUC <=0|Spearman realized|
|---|---|---:|---:|---:|---:|
|I2_funded N=161|consensus_minrank|0.542097|0.551171|0.457903|0.077175|
|I2_funded N=161|pP|0.534272|0.564324|0.465728|0.048941|
|I2_funded N=161|q2|0.521440|0.510811|0.478560|0.027089|
|I2_funded N=161|q3|0.515180|0.510631|0.484820|0.025090|
|I2_rank_native_admission N=488|consensus_minrank|0.537060|0.532784|0.462940|0.020092|
|I2_rank_native_admission N=488|pP|0.525390|0.541317|0.474610|0.002555|
|I2_rank_native_admission N=488|q2|0.520674|0.519733|0.479326|0.009140|
|I2_rank_native_admission N=488|q3|0.521154|0.522227|0.478846|0.007756|

decile別realized mean/median/loser rateは`SIGNAL_FROZEN_EXIT_MONETIZATION_DIAGNOSTIC.json`。admissionのmissing realizedは除外数を明示。fit0。scoreは真の確率と呼ばない。Quality conditional CIが0を跨ぐ親の制約を保持し、HF1/HL0再fit0。

## G. Sizing Algebraic Attribution

I2 actual PnL ¥-66,143.95 = session equal-lot algebraic ¥333,211.18 + sizing covariance contribution ¥-399,355.13。identity unit-lot edge ¥-7,728.15。Fraction exact conservation PASS。
sessionごとLbar=total lots/N。equal-lot referenceはfractional lotを含み、executable policyではない。価格・cap・session構成も含むため、このcovariance全額をbatch内weightだけで回収可能と解釈しない。

## H. 100-share Fixed-Identity Shadow

161 identities×100株、同Entry/EXIT。total PnL ¥-7,728.15 / Final38 ¥992,271.85 / cash min ¥362,005.80 / violations=0。
actual shadow-chain rolling20: {"2x_N": 0, "max": 1.0963447458838034, "mean": 1.0094201772688507, "median": 1.0312065251626032, "min": 0.926894807765923}。daily PnL/1mと固定1m additive rollingも保存。
selection-only・低utilization shadow。v5正式Capital gateとの直接policy比較に使用しない。

## I. Static Batch Hindsight Sizing Headroom

156 saved funded batches。actual PnL ¥-66,143.95 / local hindsight optimum ¥448,229.45 / difference ¥514,373.40。
HINDSIGHT_DIAGNOSTIC_ONLY。funded identities最低1 lot、saved budget/cap内integer。future realizedを使用。Primary recursive enumerationと独立別variable elimination solveでexact一致。将来cash feedback再最適化0、full-chain oracleでもrolling20 upper boundでもない。
151/156 batchesは単独funded identity、5件は2 identities。ただし元pickedにcash/lot失敗candidateを含むbatchでは新weightがfunding pathを変え得る。hindsightのidle/min-lot選択は固定targetのS1/S2で実行可能とは限らない。

## J. S1/S2 Paired Funding / Quantity Delta

|Arm / group|N|Medium|U5|U10|Weak|realized positive|loser<=0|actual PnL|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|S1 / GAINED_FUNDING_vs_I2|2|0|1|1|1|1|1|¥-7,059.25|
|S1 / LOST_FUNDING_vs_I2|1|0|1|0|0|0|1|¥-11,736.30|
|S1 / NEW_MAX3_MISS_vs_I2|5|0|1|0|3|4|1|¥0.00|
|S1 / CASH_RECOVERY_vs_I2|1|0|1|1|0|0|1|¥-8,819.60|
|S1 / NEW_CASH_MISS_vs_I2|1|0|1|0|0|0|1|¥0.00|
S1 COMMON N=160、quantity PnL delta ¥-6,811.00。Net {"Medium": 0, "U10": 1, "U5": 0, "Weak": 1, "realized_loser_le0_N": 0, "realized_positive_N": 1}。total PnL delta ¥-2,133.95。
|S2 / GAINED_FUNDING_vs_I2|2|0|1|1|1|1|1|¥-7,151.90|
|S2 / LOST_FUNDING_vs_I2|1|0|1|0|0|0|1|¥-11,736.30|
|S2 / NEW_MAX3_MISS_vs_I2|5|0|1|0|3|4|1|¥0.00|
|S2 / CASH_RECOVERY_vs_I2|1|0|1|1|0|0|1|¥-8,819.60|
|S2 / NEW_CASH_MISS_vs_I2|1|0|1|0|0|0|1|¥0.00|
S2 COMMON N=160、quantity PnL delta ¥-8,494.35。Net {"Medium": 0, "U10": 1, "U5": 0, "Weak": 1, "realized_loser_le0_N": 0, "realized_positive_N": 1}。total PnL delta ¥-3,909.95。

COMMON quantity deltaのWeak/Low/Medium/Big/Mega/U5/U10/realized<=0/>=1%内訳は`PAIRED_SIZING_DELTA.json`。個別replacement因果ではない。未funded miss groupのactual PnLは0で、そのpotential/realizedは評価後join。

## K. Slot / Band / Time / Notional Allocation

|Arm / group|N|buy notional|Medium|U5|U10|<2|<3|PnL|loser|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|S1 / slot:1|45|¥13,726,059.60|9|20|12|28.8889%|35.5556%|¥121,813.00|51.1111%|
|S1 / slot:2|65|¥18,178,484.70|12|20|11|36.9231%|50.7692%|¥-100,328.30|53.8462%|
|S1 / slot:3|52|¥8,207,501.70|11|13|4|42.3077%|53.8462%|¥-89,762.60|61.5385%|
|S1 / band:P_BASE|38|¥7,102,549.50|8|5|2|50.0000%|65.7895%|¥-91,456.80|68.4211%|
|S1 / band:P_HIGH|35|¥11,357,475.90|8|10|6|37.1429%|48.5714%|¥-182,666.10|60.0000%|
|S1 / band:P_MID|89|¥21,652,020.60|16|38|19|30.3371%|39.3258%|¥205,845.00|48.3146%|
|S1 / Entry_hour:10|59|¥14,662,127.40|13|20|11|32.2034%|44.0678%|¥-109,307.45|50.8475%|
|S1 / Entry_hour:11|14|¥3,186,292.35|3|1|0|50.0000%|71.4286%|¥12,707.35|57.1429%|
|S1 / Entry_hour:12|20|¥3,749,874.00|1|5|1|55.0000%|70.0000%|¥-89,505.10|65.0000%|
|S1 / Entry_hour:13|14|¥2,616,307.50|2|3|0|42.8571%|64.2857%|¥-39,496.55|71.4286%|
|S1 / Entry_hour:14|7|¥1,860,629.85|1|3|1|42.8571%|42.8571%|¥-38,741.25|42.8571%|
|S1 / Entry_hour:15|3|¥762,381.00|2|0|0|33.3333%|33.3333%|¥-6,858.95|100.0000%|
|S1 / Entry_hour:9|45|¥13,274,433.90|10|21|14|26.6667%|31.1111%|¥202,924.05|51.1111%|
S1 quantity: {"candidate_cap_hit_N": 109, "candidate_cap_hit_definition": "next one lot would exceed frozen band equity cap", "first_pass_zero_N": 23, "mean_lots": 7.938271604938271, "median_lots": 3.0, "waterfill_lot_N": 3}
|S2 / slot:1|45|¥13,738,866.00|9|20|12|28.8889%|35.5556%|¥121,700.25|51.1111%|
|S2 / slot:2|65|¥18,164,877.90|12|20|11|36.9231%|50.7692%|¥-101,714.00|53.8462%|
|S2 / slot:3|52|¥8,185,190.55|11|13|4|42.3077%|53.8462%|¥-90,040.15|61.5385%|
|S2 / band:P_BASE|38|¥7,102,549.50|8|5|2|50.0000%|65.7895%|¥-91,456.80|68.4211%|
|S2 / band:P_HIGH|35|¥11,357,475.90|8|10|6|37.1429%|48.5714%|¥-182,666.10|60.0000%|
|S2 / band:P_MID|89|¥21,628,909.05|16|38|19|30.3371%|39.3258%|¥204,069.00|48.3146%|
|S2 / Entry_hour:10|59|¥14,662,127.40|13|20|11|32.2034%|44.0678%|¥-109,307.45|50.8475%|
|S2 / Entry_hour:11|14|¥3,186,292.35|3|1|0|50.0000%|71.4286%|¥12,707.35|57.1429%|
|S2 / Entry_hour:12|20|¥3,739,168.65|1|5|1|55.0000%|70.0000%|¥-89,794.25|65.0000%|
|S2 / Entry_hour:13|14|¥2,616,307.50|2|3|0|42.8571%|64.2857%|¥-39,496.55|71.4286%|
|S2 / Entry_hour:14|7|¥1,860,629.85|1|3|1|42.8571%|42.8571%|¥-38,741.25|42.8571%|
|S2 / Entry_hour:15|3|¥762,381.00|2|0|0|33.3333%|33.3333%|¥-6,858.95|100.0000%|
|S2 / Entry_hour:9|45|¥13,262,027.70|10|21|14|26.6667%|31.1111%|¥201,437.20|51.1111%|
S2 quantity: {"candidate_cap_hit_N": 109, "candidate_cap_hit_definition": "next one lot would exceed frozen band equity cap", "first_pass_zero_N": 23, "mean_lots": 7.919753086419753, "median_lots": 3.0, "waterfill_lot_N": 1}

|Profile|Weak notional share|Medium+ share|U5 share|U10 share|
|---|---:|---:|---:|---:|
|v5|36.5342%|54.0106%|34.0361%|17.1449%|
|I2|36.2548%|52.9276%|33.9054%|17.8271%|
|S1|36.1688%|53.2470%|34.1599%|18.2655%|
|S2|36.2034%|53.2438%|34.1457%|18.2131%|

各bucketのbuy notional/share/PnL/return-on-deployed-notionalは同JSONに全保存。countとcapital exposureを分離。

## L. Capital Secondary

|Profile|daily geometric|arithmetic|median|Final38|maxDD|util mean|turnover|
|---|---:|---:|---:|---:|---:|---:|---:|
|v5 saved|1.032420041%|1.107940%|0.188228%|¥1,477,436.15|10.225325%|41.9868%|¥89,327,438.95|
|I2 saved|-0.179924717%|-0.125972%|-0.278734%|¥933,856.05|21.242600%|41.4358%|¥81,287,912.75|
|S1|-0.185933993%|-0.130018%|-0.261604%|¥931,722.10|19.790095%|42.0620%|¥80,155,814.10|
|S2|-0.190945497%|-0.135006%|-0.261629%|¥929,946.10|19.953371%|42.0954%|¥80,107,815.00|
S1: utilization median=51.4217%、idle cash mean=¥574,346.76、recycled cash=¥7,855,886.00、funded/session=4.263158、total return=-6.827790%。
S2: utilization median=51.4985%、idle cash mean=¥573,514.35、recycled cash=¥7,851,531.30、funded/session=4.263158、total return=-7.005390%。

## M. Independent Audit

61/61 causal canary PASS。pre-main141,476 checks / mismatch0。full audit 224,935 checks / mismatch=0。float max delta=8.88178419700125232e-16 (<=1e-12)。money/quantity exact。
Primary sizing/runtime/replay/evaluator import0。raw frozen model scalar inference、past-only percentile、tenure、I2 action、Fraction portfolio、identity/quantity/matrix/signal/algebraic/shadow、別integer solver、quality/Capital/winner/bottleneckを照合。completed pre-main inference artifactsを再生成せずimmutable reuse。
implementation independenceでありupstream market source independenceを主張しない。親のbar-end as-of / actual arrival unknown制約を継承。

## N. Winner / Next Bottleneck

selectedCapitalCandidate=null。diagnosticArm=S1。NEXT_BOTTLENECK=REALIZED_MONETIZATION_SIGNAL。
REALIZED_MONETIZATION_SIGNALの場合の意味は、Frozen EXIT下でpre-entry情報からpotential winnersのうち実際にmonetizeされる候補を区別する情報不足。EXIT研究への移行ではない。次の独立WorkでQuality v3 HF1/HL0 negative historyを必ず読み、同じ実験を繰り返さない。
M15で固定STOP。S3/threshold/blend/model fit/cap/target/Admission/Rank/EXIT変更、Fresh開封、orders、main mergeは行わない。

```
selectedBigWinnerRank = EXISTING_MOVE_P5
selectedAuxiliaryHeads = ["MOVE_U2","MOVE_U3"]
selectionPolicy = QUALITY_PARETO_U2_U3_TENURE_MAX3_V1
selectedCapitalCandidate = null
diagnosticArm = S1
NEXT_BOTTLENECK = REALIZED_MONETIZATION_SIGNAL
newFits = 0
SizingReplays = 2
fresh_OOS_claim = false
productionReady = false
CURRENT_STATE = CAPITAL_V10_M15_CLOSURE_FIXED_STOP
```
