# Capital v11R1 Numerical Certification Recovery — 最終報告

## A. Executive / old v11 failure preserved


status = `V11R1_NUMERIC_CERTIFIED_PARTIAL_CAPITAL_PROGRESS`。S9R 14条件PASSによりMRETは`MRET_STRONG_CERTIFIED_V11R1`。正式採用はnull、diagnosticArmはM2、NEXT_BOTTLENECKは`MONETIZATION_SIGNAL_STRENGTH_OR_CAPITAL_MAPPING`。

旧v11の`V11_CONTRACT_FAIL`、old S9 FAIL、CapitalReplay0は変更していない。branch baseは開始時actual latest terminal HEAD `489fc4f9bc164b3150e374e9f4011a9888ad2d55`。新branchは`capital-v11r1-numeric-cert-recovery-20261005`。Main/Quality lineage、Selector/Entry/EXIT、I2 selectionは凍結した。

既存MRET 8 fitsをexact reuse。new fit/refit/audit optimizer callは全て0。M1/M2各1回のみ実行。M1は29日目の売却source不足でfail-closedし、28 COMPLETE sessionsの後で停止した。M2は38 sessions完走。M1のCapitalを補完せず、M2の結果で固定Gateを判定した。

## B. Numeric Contract Root Cause


旧Independentはpopulation scaleをmath.fsum中心化二乗偏差で構築し、fit時のNumPy reduction operatorをexactにinstantiateしていなかった。Block6、`selector/first_clock`のscale差1.5774048733874224e-12が旧1e-12を超過した。artifact/snapshot/OOF behavior/statistical result failureではなく、`NUMERIC_AUDIT_OPERATOR_MISMATCH`として固定した。差を無視した判定ではない。

`FIT_NUMERIC_OPERATOR_V1`はfloat64 C-order raw46列、missing0＋missing indicator46列、column_stackのX0、NumPy float64 mean(axis=0)、std(axis=0,ddof=0)、exact zero scale→1。Independentはrow選択・field抽出・行列・vocabを別実装し、このcontract-defined primitiveを呼ぶ。trainer/model/teacher/evaluator importは0。

mean/scaleのhard gateはfloat64 uint64 viewのbit一致。旧1e-12を拡張していない。scoreの1e-12 contractは維持した。

## C. Environment Fingerprint


|項目|値|
|---|---|
|Python|3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]|
|NumPy|2.3.5|
|sklearn|1.8.0|
|platform|Linux-6.18.44-x86_64-with-glibc2.39|
|machine / byteorder|x86_64 / little|
|float64 mantissa / epsilon|53 / 2.220446049250313e-16|
|np.show_config SHA256|d458c673e553c8556cf4904a3955b48e93356e7d85da83d2b28b03f28d237c4d|

fit当時のshow_config本体は旧authorityに記録されていない。既存version authorityと今回fingerprintを保存し、環境互換性はartifactとのbit一致で認証した。

## D. Canonical Matrix / Bit Certification


|Block|X0 shape|mean exact|scale exact|model/NPZ exact|OOF max delta|
|---|---|---|---|---|---|
|1|[544, 92]|92/92|92/92|PASS|3.3306690738754696e-16|
|2|[674, 92]|92/92|92/92|PASS|3.3306690738754696e-16|
|3|[805, 92]|92/92|92/92|PASS|1.1102230246251565e-15|
|4|[939, 92]|92/92|92/92|PASS|2.7755575615628914e-16|
|5|[1069, 92]|92/92|92/92|PASS|3.3306690738754696e-16|
|6|[1200, 92]|92/92|92/92|PASS|2.220446049250313e-16|
|7|[1343, 92]|92/92|92/92|PASS|2.220446049250313e-16|
|8|[1483, 92]|92/92|92/92|PASS|2.220446049250313e-16|

独立raw value照合370,622件。mean736要素・scale736要素は全てbit exact。coef/intercept/classesもsnapshot一致。OOF1039件の最大score差は1.1102230246251565e-15、train8057件は1.2212453270876722e-15。OOF ordering、Top20/Top30、decile orderingは一致。completed certificate再実行0。

|Block|reused train N|test N|positive N|iterations|new optimizer|
|---|---|---|---|---|---|
|1|544|134|270|77|0|
|2|674|136|333|81|0|
|3|805|137|398|86|0|
|4|939|131|464|93|0|
|5|1069|132|525|95|0|
|6|1200|147|594|100|0|
|7|1343|144|666|108|0|
|8|1483|78|734|107|0|

## E. Alternate fsum / Decimal diagnostic


|Block|feature|canonical np scale|fsum scale|abs delta|relative delta|ULP|
|---|---|---|---|---|---|---|
|6|selector/first_clock|106.78903267657996|106.78903267658154|1.5774048733874224e-12|1.4771225413800055e-14|111|

全736 scaleのfsum比較をprivate保存。Decimal.from_float、precision80 referenceもBlock1–8のfirst_clockで保存した。alternate結果は感度診断のみで、hard gate/runtimeには使用0。canonical operatorの差替え0。

## F. Frozen Signal Evidence


以下は旧v11のhash/body verified `FROZEN_V11_SIGNAL_EVIDENCE`。primary fit/evaluate/bootstrap/control再選定を実行していない。BEST_EXISTING_CONTROL=q3を固定reuseした。

|Metric|mP|q3|Delta / frozen95% CI|
|---|---|---|---|
|MRET AUC|0.631424|0.353206|[0.22002366561306444, 0.33789468032625536]|
|MRET PR-AUC|0.606552|0.398058|[0.16143651030725029, 0.2523885376795685]|
|Potential-bucket realized concordance|0.598276|0.386281|[0.15298229134719324, 0.2819845066770388]|
|realized>0 AUC|0.516828|0.488838|[-0.03165802349667033, 0.08592983577094483]|
|realized>=1% AUC|0.434478|0.550970|Secondary diagnostic|
|block MRET AUC improvement|8/8|q3 control|S1–S8 frozen PASS|

bootstrapはseed5701105、1999、OOF38 session cluster。realized>0 AUC delta CIは0を跨ぐ。MRET teacherはbucket内の相対monetizationであり、絶対利益の確率とは呼ばない。58 Development sessionsを多数cycleで反復利用したITERATIVE_DEVELOPMENT_EVIDENCEで、Fresh/OOS成功ではない。

## G. S9R decision


R1–R14全PASS。private/source、8 fits、train identity/order、independent X0、mean/scale bits、JSON/NPZ、coef/intercept/classes、train/OOF score、frozen primary/bootstrap body/hash、no refit/re-eval/tolerance relaxation、Safetyを確認した。old S9 FAILとnew S9R PASSを別記録に保存した。

## H. North Star / rolling20


|Profile|20d min|mean|median|max|2x|
|---|---|---|---|---|---|
|v5 saved|1.0823662751|1.1906460126|1.1991541915|1.2970310262|0/19|
|I2 saved|0.8439496722|0.9443465262|0.9146242057|1.0972839118|0/19|
|v10 S1 saved|0.8603202085|0.9542671531|0.9283112455|1.1058223900|0/19|
|M1|未測定|未測定|未測定|未測定|未測定|
|M2|0.9650812909|1.0903763331|1.0674062203|1.2936642936|0/19|

M1のCapital gate/relative gateは未測定。M2は相対median>.9283112455、mean>.9542671531、daily geometric>-.00179924717を全PASSし、v5 floorもPASS。official v5 Capital3条件は全FAIL。2x=0/19。19 windowsは重なっており、独立19標本とは呼ばない。

## I. Quality Retention


|Profile|N|Medium|U5|U10|Weak N / <2|<3|Retention|
|---|---|---|---|---|---|---|---|
|v5 saved|150|27|50|26|58 / 38.666667%|48.666667%|reference|
|I2 saved|161|32|53|26|58 / 36.024845%|47.204969%|reference|
|M1 observed prefix|102|17|28|15|43 / 42.156863%|55.882353%|38d未評価 / execution FAIL|
|M2|170|32|57|28|62 / 36.470588%|47.647059%|FAIL Q4/Q5|

M2: Q1/Q2/Q3/Q6/Q7 PASS、Q4/Q5 FAIL。v5最低floor全PASS。Weak絶対NはI2より+4、Lowは+1で、Quality countの改善だけで正式採用にはしない。M1のQ1–Q5/v5 floorをpartial cohortから判定していない。未決済1件でQ6 FAIL、Q7監査mismatch0はPASS。

M2 U5/U10 reason conservation: {"U10": {"CAPACITY_RESERVE_REJECT": 15, "CASH_OR_LOT": 2, "FUNDED": 28, "MAX3_FULL": 10, "RANK_BASE_REJECT": 12}, "U5": {"CAPACITY_RESERVE_REJECT": 40, "CASH_OR_LOT": 5, "FUNDED": 57, "MAX3_FULL": 22, "RANK_BASE_REJECT": 46}}。M1 conservationは観測prefix母集団だけを表示し、170/67全体とは比較しない。

## J. MRET Decile Capital Exposure


training percentile区間[0,.1),…,[.9,1]。test cross-sectional rankは0。M1は29 sessions観測prefix、1件未決済のdecile PnLは未確定。

### I2 saved


|decile|N|lots|BUY notional ¥|share|Medium|U5|U10|Weak|positive|>=1%|loser|actual PnL ¥|return/notional|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|1|39|521|10,993,293.90|27.025804%|7|13|7|14|13|11|26|-76,455.05|-0.695470%|
|10|9|37|2,328,563.70|5.724518%|3|1|1|5|4|3|5|-48,804.15|-2.095891%|
|2|26|136|6,275,436.15|15.427470%|4|8|4|10|10|5|16|12,718.20|0.202666%|
|3|21|225|5,252,524.95|12.912755%|5|7|3|5|12|10|9|-20,542.25|-0.391093%|
|4|17|147|3,588,393.30|8.821670%|4|6|1|6|8|3|9|-61,557.60|-1.715464%|
|5|19|48|4,885,041.30|12.009337%|2|9|6|7|7|6|12|-27,171.45|-0.556217%|
|6|13|116|3,168,983.70|7.790598%|1|7|3|4|10|7|3|131,165.40|4.139037%|
|7|4|12|1,167,383.40|2.869884%|1|0|0|3|0|0|4|-45,744.50|-3.918550%|
|8|8|26|1,826,512.80|4.490281%|3|1|0|2|3|2|5|-27,412.80|-1.500827%|
|9|5|31|1,190,895.15|2.927685%|2|1|1|2|4|3|1|97,660.25|8.200575%|

### M1 observed prefix


|decile|N|lots|BUY notional ¥|share|Medium|U5|U10|Weak|positive|>=1%|loser|actual PnL ¥|return/notional|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|1|10|17|188,194.05|1.278931%|1|2|2|4|3|3|7|-1,887.25|-1.002821%|
|10|12|61|3,174,786.60|21.575240%|4|1|1|6|5|4|7|-48,950.30|-1.541845%|
|2|4|18|235,917.90|1.603253%|1|0|0|3|0|0|4|-2,334.75|-0.989645%|
|3|9|74|743,771.70|5.054530%|2|3|1|1|5|5|4|5,053.70|0.679469%|
|4|14|102|1,592,095.65|10.819576%|3|4|1|6|5|3|9|-54,165.00|-3.402120%|
|5|18|42|2,341,270.05|15.910822%|2|8|6|7|7|5|11|-17,132.70|-0.731769%|
|6|15|107|2,417,708.25|16.430281%|1|6|3|7|8|6|6|未決済を含むため未確定|未測定|
|7|4|17|717,858.75|4.878430%|0|1|0|2|2|1|2|-617.55|-0.086027%|
|8|7|21|1,238,118.75|8.414017%|1|2|0|2|3|1|4|-30,622.80|-2.473333%|
|9|9|39|2,065,232.10|14.034921%|2|1|1|5|7|4|2|100,484.50|4.865531%|

### M2


|decile|N|lots|BUY notional ¥|share|Medium|U5|U10|Weak|positive|>=1%|loser|actual PnL ¥|return/notional|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|1|42|42|3,374,886.60|12.692607%|7|16|9|14|15|13|27|4,223.00|0.125130%|
|10|9|45|2,822,610.60|10.615553%|2|1|1|6|4|3|5|-48,798.20|-1.728832%|
|2|24|24|3,184,991.70|11.978432%|4|8|4|8|11|6|13|31,699.15|0.995266%|
|3|21|21|2,049,524.25|7.708053%|5|7|3|5|12|10|9|2,649.15|0.129257%|
|4|18|18|1,425,812.55|5.362337%|4|6|1|7|9|4|9|-20,315.65|-1.424847%|
|5|22|22|3,144,371.40|11.825663%|3|10|6|8|9|7|13|30,240.50|0.961734%|
|6|14|164|4,694,446.05|17.655337%|1|6|3|6|9|6|5|166,722.15|3.551477%|
|7|5|14|1,483,641.45|5.579825%|1|0|0|3|1|0|4|-32,467.40|-2.188359%|
|8|10|36|2,847,423.00|10.708870%|3|2|0|3|4|3|6|-40,627.10|-1.426802%|
|9|5|37|1,561,680.45|5.873322%|2|1|1|2|4|3|1|110,583.00|7.081026%|

|arm|rM half|notional delta vs matched I2 ¥|PnL delta ¥|
|---|---|---|---|
|M1 prefix|high|536,468.10|未決済を含むため未確定|
|M1 prefix|low|-17,990,690.85|73,553.90|
|M2|high|3,727,462.80|48,548.25|
|M2|low|-17,815,103.10|221,504.30|

M2はlow-rM notionalを17,815,103.10円減らし、high-rMは3,727,462.80円増加。high半分もcash/occupancy pathによって数量が変わるため、個別identityの因果replacementとは断定しない。

## K. Potential Bucket Attribution / Paired Delta


|Profile|Potential bucket|N|lots|BUY notional ¥|share|actual PnL ¥|realized mean|median|loser|U5|U10|
|---|---|---|---|---|---|---|---|---|---|---|---|
|v5|1-<2|31|382|9,114,254.85|20.516049%|-174,327.05|-1.409791%|-0.862546%|23|0|0|
|v5|2-<3|15|213|4,200,499.20|9.455260%|-1,199.90|-0.219535%|0.177550%|7|0|0|
|v5|3-<4|18|158|5,600,498.85|12.606637%|20,189.40|0.361340%|1.664296%|6|0|0|
|v5|4-<5|9|50|3,273,135.75|7.367779%|-872.70|0.045498%|0.283789%|4|0|0|
|v5|5-<10|24|258|7,503,950.10|16.891277%|95,948.05|1.664755%|0.895081%|8|24|0|
|v5|<1|27|234|7,116,056.25|16.018134%|-153,339.35|-1.939783%|-1.875951%|25|0|0|
|v5|>=10|26|278|7,616,606.40|17.144865%|691,037.70|8.212788%|5.375053%|9|26|26|
|I2|1-<2|27|312|6,786,991.80|16.685073%|-125,224.35|-1.637875%|-0.862546%|21|0|0|
|I2|2-<3|18|184|4,400,299.05|10.817651%|-95,652.45|-1.897030%|-0.099950%|10|0|0|
|I2|3-<4|20|110|5,159,978.70|12.685240%|-58,430.75|-0.483214%|1.473572%|7|0|0|
|I2|4-<5|12|97|2,577,688.20|6.336963%|-25,964.70|-0.664990%|0.652846%|5|0|0|
|I2|5-<10|27|136|6,540,168.45|16.078285%|-65,707.30|-0.651228%|0.318626%|11|27|0|
|I2|<1|31|199|7,960,378.20|19.569714%|-237,741.45|-2.983840%|-2.516887%|29|0|0|
|I2|>=10|26|261|7,251,523.95|17.827074%|542,577.05|7.788054%|5.375053%|7|26|26|
|M1 prefix|1-<2|22|148|2,960,179.35|20.116810%|未決済を含むため未確定|-0.588618%|-0.534298%|14|0|0|
|M1 prefix|2-<3|14|70|1,591,095.15|10.812777%|-23,779.20|-1.083141%|0.553766%|6|0|0|
|M1 prefix|3-<4|10|33|1,936,767.90|13.161903%|-48,612.45|-3.379570%|0.380694%|5|0|0|
|M1 prefix|4-<5|7|40|1,048,323.90|7.124208%|-1,747.45|0.230469%|0.471997%|3|0|0|
|M1 prefix|5-<10|13|58|1,789,094.10|12.158340%|-21,378.40|-0.898403%|0.250576%|6|13|0|
|M1 prefix|<1|21|86|3,380,389.35|22.972477%|-61,749.50|-2.191411%|-1.763960%|17|0|0|
|M1 prefix|>=10|15|63|2,009,104.05|13.653485%|165,608.05|5.772948%|3.590625%|5|15|15|
|M2|1-<2|28|96|3,513,155.70|13.212623%|-24,700.80|-1.480013%|-0.438382%|20|0|0|
|M2|2-<3|19|40|2,608,803.75|9.811447%|-66,175.70|-1.819857%|-0.099950%|11|0|0|
|M2|3-<4|21|31|3,722,460.30|13.999797%|-16,314.30|-0.425736%|1.307093%|7|0|0|
|M2|4-<5|11|17|1,193,296.35|4.487867%|-32,477.05|-0.861537%|0.471997%|5|0|0|
|M2|5-<10|29|63|4,558,077.90|17.142470%|22,430.70|-0.228750%|0.365242%|11|29|0|
|M2|<1|34|93|6,011,504.25|22.608660%|-136,143.40|-2.785168%|-2.052017%|31|0|0|
|M2|>=10|28|83|4,982,089.80|18.737136%|457,289.15|7.230972%|5.324598%|7|28|28|

M1 prefixは同じ観測範囲のI2 subsetへpairedし、未観測後半をLOSTと数えていない。M1 unresolved PnLに0を入れていない。

|arm / scope|common|gained N / U5 / U10 / Medium / Weak|lost N / U5 / U10 / Medium / Weak|common quantity PnL delta ¥|total actual PnL delta ¥|
|---|---|---|---|---|---|
|M1 prefix|75|27 / 4 / 2 / 2 / 17|48 / 16 / 9 / 11 / 17|31,736.85|未決済を含むため未確定|
|M2 full38|154|16 / 7 / 3 / 1 / 7|7 / 3 / 1 / 1 / 3|232,324.85|270,052.55|

|arm|diagnostic|N|U5|U10|Medium|Weak|
|---|---|---|---|---|---|---|
|M1 prefix|NEW_MAX3_MISS_vs_I2|0|0|0|0|0|
|M1 prefix|CASH_RECOVERY_vs_I2|1|0|0|0|1|
|M1 prefix|NEW_CASH_MISS_vs_I2|64|25|13|14|20|
|M2|NEW_MAX3_MISS_vs_I2|9|2|1|3|4|
|M2|CASH_RECOVERY_vs_I2|15|7|3|1|6|
|M2|NEW_CASH_MISS_vs_I2|2|1|1|0|1|

M2 net counts = {"Medium": 0, "U10": 2, "U5": 4, "Weak": 4, "realized_loser_le0_N": 2, "realized_positive_N": 7}。common数量差のPnL +232,324.85円、gain/lost identity差を合わせたtotal PnL差 +270,052.55円。これはpolicy counterfactual diagnosticで、一意の因果分解ではない。

M1でfundした`2025-08-12|45560`はsaved I2ではReserve。new actual stateはoccupancy0でI2 pressure5/45、rM=.5195670274771024、100株BUY125,462.70円。有効なFrozen sellと15:20 regular/15:30 exact auction売却sourceが存在せず、29日目EOD義務を持ってfail-closed。EXIT price補完、forced EXIT、Admission filter追加、provider再取得、M1再実行は全て0。残りのM2はreceipt確認後に既存claimの未実行armとして1回だけ実行した。

## L. Capital Secondary


|Profile|daily geometric|arithmetic|daily median|Final38 ¥|total return|minute MTM MaxDD|util mean / median|cash min ¥|
|---|---|---|---|---|---|---|---|---|
|v5 saved|1.032420%|1.107940%|0.188228%|1,477,436.15|47.743615%|10.225325%|41.986827% / 48.260213%|221,811.10|
|I2 saved|-0.179925%|-0.125972%|-0.278734%|933,856.05|-6.614395%|21.242600%|41.435765% / 49.268072%|200,242.35|
|v10 S1 saved|-0.185934%|-0.130018%|-0.261604%|931,722.10|-6.827790%|19.790095%|42.061982% / 51.421657%|198,095.70|
|M1|未測定|未測定|未測定|未決済を含むため未確定|未測定|未測定|未測定 / 未測定|未測定|
|M2|0.489546%|0.520001%|0.112344%|1,203,908.60|20.390860%|10.315733%|23.025365% / 19.803519%|238,593.95|

|Profile|idle cash mean ¥|turnover ¥|recycled cash ¥|funded/session|
|---|---|---|---|---|
|v5 saved|未決済を含むため未確定|89,327,438.95|6,728,380.05|3.947368|
|I2 saved|589,217.18|81,287,912.75|7,916,975.30|4.236842|
|v10 S1 saved|574,346.76|80,155,814.10|7,855,886.00|4.263158|
|M1|未決済を含むため未確定|未決済を含むため未確定|未決済を含むため未確定|未測定|
|M2|900,266.74|53,382,684.70|597,413.50|4.473684|

Final38は38 Development sessionsの連結結果で、1か月成績ではない。M1の欄は全38日経済指標を未測定とする。

## M. Independent Audit


80 causal canaries PASS。pre-main 155,253 checks、full available-ledger/Capital audit 226,341 checks、いずれもmismatch0。Primary runtime/replay/evaluator import0。Money/quantity exact、score/metric float<=1e-12。preprocessingはcompleted canonical bit certificateをread-only reuse。M2の38-session decision/cap/lot/cash/MTM/exposure/rolling20/gatesは全検証。M1の全保存ledger・未決済100株・source blockerも独立に再現したが、M1のFinal38/rolling20をcertifyしていない。

pre-main監査に1件の未完了処理例外があった。v9 pressure tableにはpP列がないため照合でKeyErrorとなった。結果決定前・Main前の既知中断receiptを保存し、pPは元rank authorityで照合、pressure tableのrはそのtableで照合して最初の未完了監査を完了した。completed numerical certificate再実行0、Gate変更0。

## N. Winner / Next Bottleneck / Fixed STOP


selectedCapitalCandidate=null。diagnosticArm=M2。M2はrelative progressとv5 floorを満たす研究上の部分改善で、I2 Retentionとofficial v5 Capitalを満たさない。NEXT_BOTTLENECK=`MONETIZATION_SIGNAL_STRENGTH_OR_CAPITAL_MAPPING`。M1のexecution source不足は別途blocking receiptとしてhandoffし、数値認証やM2成績の失敗へ混同していない。EXIT bottleneckとは命名しない。

private pack: `Ark_Capital_v11R1_Numeric_Cert_Recovery_20261005_PRIVATE.zip`、SHA256 `bca2ba95b095132ce69eef2f207d1980ce2cc8ae688a1aad313c59f37a2c3e86`。旧v11 private ZIP SHA134977744baab20ea75310d8c263322281d4f8289ad60afdd1a6b83e3875156fをbyte-exact nested authorityとして含む。全member hash一致。

```text
oldV11Status = V11_CONTRACT_FAIL
oldS9 = FAIL
newS9R = PASS
selectedBigWinnerRank = EXISTING_MOVE_P5
selectedAuxiliaryHeads = ["MOVE_U2","MOVE_U3"]
selectionPolicy = QUALITY_PARETO_U2_U3_TENURE_MAX3_V1
monetizationSignal = MRET_STRONG_CERTIFIED_V11R1
selectedCapitalCandidate = null
diagnosticArm = M2
NEXT_BOTTLENECK = MONETIZATION_SIGNAL_STRENGTH_OR_CAPITAL_MAPPING
newFits = 0
reusedMRETFits = 8
CapitalReplays = 2
M1 invocation = 1 (execution measurement blocked)
M2 invocation = 1 (38 sessions complete)
fresh_OOS_claim = false
productionReady = false
CURRENT_STATE = CAPITAL_V11R1_N18_CLOSURE_FIXED_STOP
```

Safety全10項目false。orders/main merge/force push/provider/Claude/Fresh/M3/threshold tuning/teacher変更/model refit/Selector/Entry/EXIT変更/Admission/I2変更/MAX4/5/replacement/result rescueは全て0。N18で固定STOPし、次の独立Workへ引き継ぐ。
