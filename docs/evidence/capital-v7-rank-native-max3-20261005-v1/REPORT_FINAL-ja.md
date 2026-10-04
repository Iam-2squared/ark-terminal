## A. North Star / rolling 20 sessions

|Profile|20d min|20d mean|20d median|20d max|2x hit|
|---|---|---|---|---|---|
|v5|1.0823662751x|1.1906460126x|1.1991541915x|1.2970310262x|0/19|
|A1 Greedy|0.9894268413x|1.0759537031x|1.0480741764x|1.2254908119x|0/19|
|A2 Last-slot|0.8638211957x|0.9641337276x|0.9396052222x|1.1311273645x|0/19|

結論: **NO_GO**。A1/A2ともPreservation GateとCapital Gate未達。selectedCapitalCandidate=null。保存済みv5をCapital benchmarkとして保持し、D15で固定STOPする。Rank vNext=EXISTING_MOVE_P5 / pP DESCは変更しない。

North Starは¥1,000,000→¥2,000,000 / 20 sessions。19 rolling windowsは重複し、独立19標本ではない。同じDevelopmentの反復利用Evidenceであり、fresh/OOS成功、production-ready、将来市場収益の保証ではない。

## B. U5/U10 preservation

|Profile|U5 funded /170|U10 funded /67|Oracle recovery U5 / U10|<2|Reserve miss U5/U10|MAX3 miss U5/U10|Rank reject U5/U10|
|---|---|---|---|---|---|---|---|
|v5|50 /170|26 /67|33.5570% / 38.8060%|38.666667%|30 /10|28 /9|57 /20|
|A1 Greedy|50 /170 (29.4118%)|27 /67 (40.2985%)|33.5570% / 40.2985%|43.274854%|0 /0|67 /24|46 /12|
|A2 Last-slot|51 /170 (30.0000%)|25 /67 (37.3134%)|34.2282% / 37.3134%|41.875000%|41 /17|26 /10|46 /12|

Oracle recoveryは新ALL ceiling U5=149/U10=67を分母とする。v5の57/20 Rank rejectは、固定primary170/67から保存済み旧rank-pass113/47を引いた診断値であり、Control replayは0。旧104/47 ceilingは新母集団へ流用していない。

|Gate|v5 benchmark|A1|A2|
|---|---|---|---|
|P1 U5|>50|False|True|
|P2 U10|>=26|True|False|
|P3 <2|<=38.666667%|False|False|
|P4 integrity|違反0|True|True|
|P5 independent|mismatch0|True|True|

A1はU5が50で増加せず、<2混入が悪化。A2はU5+1だがU10−1、<2混入も悪化。採用可能armは0。A2のU5 MAX3 miss減少41件はReserve miss41件で相殺され、Net Slot MissはA1/A2とも67。

## C. v5比較

|Metric|v5|A1|A2|Winner|
|---|---|---|---|---|
|U5 funded|50|50|51|none; v5保持|
|U10 funded|26|27|25|none; v5保持|
|Funded N|150|171|160|none; v5保持|
|<2 contamination|38.666667%|43.274854%|41.875000%|none; v5保持|
|rolling20 median|1.1991541915|1.0480741764|0.9396052222|none; v5保持|
|rolling20 mean|1.1906460126|1.0759537031|0.9641337276|none; v5保持|
|daily geometric|1.032420%|0.734165%|0.131206%|none; v5保持|

|Arm|Preservation|Capital median/mean/geom|Final status|
|---|---|---|---|
|A1 Greedy|FAIL|FAIL / FAIL / FAIL|NO_GO|
|A2 Last-slot|FAIL|FAIL / FAIL / FAIL|NO_GO|

## D. Oracle gap waterfall

|Profile|U5 funded|U10 funded|新admission Oracle U5/U10|新ALL Oracle U5/U10|
|---|---|---|---|---|
|v5|50|26|参考のみ: 116 /55|149 /67|
|A1 Greedy|50|27|116 /55|149 /67|
|A2 Last-slot|51|25|116 /55|149 /67|

|Oracle|原母集団|Executable N|U5 maximum|U10 maximum|Exact min cash witness|
|---|---|---|---|---|---|
|ADMISSION_U10|新percentile admission|488|U10-only目的|55|707494.45000|
|ADMISSION_U5|新percentile admission|488|116|55|477739.00000|
|ALL_U10|1028|1016|U10-only目的|67|712527.00000|
|ALL_U5|1028|1016|149|67|346814.45000|

ALL_U5はU5最大149の下でU10=67も保存。ALL_U10は別目的で最大67。ADMISSION_U5はU5最大116の下でU10=55、ADMISSION_U10の別最大も55。Cash-relaxed interval upper boundに100株のexact cash/MAX3 witnessが到達し、無制限整数lotを含むphysical count最適性を証明した。独立binary occupancy MILPでも上限一致。Oracleはevaluation-onlyでruntimeへ渡していない。

12候補はFrozen EXIT/EOD source unavailable（全てU5/U10=0）。original1028 identityは維持し、Oracleではexact execution availabilityによりfund不能。runtimeにはこの未来availability gateを追加せず、実際に12件はいずれもfundされず、両armのexecution unresolvedは0。

### U5: 排他的reason waterfall

|Profile|All|After admission|After reserve|After MAX3|Funded|Other misses|
|---|---|---|---|---|---|---|
|A1 Greedy|170|124|124|57|50|7 cash/lot; same-symbol/execution/other=0|
|A2 Last-slot|170|124|83|57|51|6 cash/lot; same-symbol/execution/other=0|

これは排他的reasonを順に引く表示であり、candidateの時系列を集約順に入れ替えてreplayしたものではない。

### U10: 排他的reason waterfall

|Profile|All|After admission|After reserve|After MAX3|Funded|Other misses|
|---|---|---|---|---|---|---|
|A1 Greedy|67|55|55|31|27|4 cash/lot; same-symbol/execution/other=0|
|A2 Last-slot|67|55|38|28|25|3 cash/lot; same-symbol/execution/other=0|

これは排他的reasonを順に引く表示であり、candidateの時系列を集約順に入れ替えてreplayしたものではない。

|Profile|Physical unavoidable|Admission ceiling loss|Runtime-to-admission gap|Funded|Total|
|---|---|---|---|---|---|
|A1 Greedy|21|33|66|50|170|
|A2 Last-slot|21|33|65|51|170|

U5 ceiling waterfall: 170 → ALL149 → ADMISSION116 → A1 funded50 / A2 funded51。21+33+66+50=170、21+33+65+51=170。これは別のcounterfactual telescoping分解であり、observed Rank/Reserve/MAX3/cash reasonと重複加算しない。個々のmissにunavoidableとの因果ラベルを付けていない。

|Profile|G1 Rank|G2 Reserve|G3 MAX3|G4 cash/lot|G5 unavoidable (別分解)|G6 ALL−funded (別分解)|
|---|---|---|---|---|---|---|
|A1 Greedy|46|0|67|7|21|99|
|A2 Last-slot|46|41|26|6|21|98|

## E. Slot1/2/3 quality

|Profile|Slot|Funded N|U5 N|U10 N|<2 N/rate|<3 N/rate|Medium3-<5|
|---|---|---|---|---|---|---|---|
|A1 Greedy|1|38|15|10|14 / 36.8421%|16 / 42.1053%|7|
|A1 Greedy|2|54|16|7|27 / 50.0000%|34 / 62.9630%|4|
|A1 Greedy|3|79|19|10|33 / 41.7722%|46 / 58.2278%|14|
|A2 Last-slot|1|38|15|10|14 / 36.8421%|16 / 42.1053%|7|
|A2 Last-slot|2|71|22|9|33 / 46.4789%|43 / 60.5634%|6|
|A2 Last-slot|3|51|14|6|20 / 39.2157%|26 / 50.9804%|11|

slotはFrozen v5と同じfund時のconcurrent+1定義。後日slot品質の結果からReserve閾値は変更していない。A2はoccupancy0/1ではReserve0。

## F. Rank-regret / higher-pP blocked winner

|Profile|Higher-pP U5 blocked by lower-pP holding|U10 same diagnostic|
|---|---|---|
|A1 Greedy|51|16|
|A2 Last-slot|16|8|

A1の67 MAX3-missed U5中51件は、held最小pPよりmissed pPが高い。held count、score、Entry/arrival、実際のoverlap duration、reasonはprivate RANK_REGRET_LEDGERに保存。これはreplacementやEXIT変更を正当化しない。

### Legacy comparable subset: 旧rank-pass U5=113 / U10=47

|Profile/target|Funded|New rank reject|Reserve|MAX3|cash/lot|Total|
|---|---|---|---|---|---|---|
|v5 /U5|50|0|30|28|5|113|
|v5 /U10|26|0|10|9|2|47|
|A1 Greedy/U5|43|13|0|52|5|113|
|A1 Greedy/U10|25|3|0|17|2|47|
|A2 Last-slot/U5|44|13|35|17|4|113|
|A2 Last-slot/U10|23|3|13|7|1|47|

## G. Daily / Final38 / MaxDD / utilization — Secondary

|Metric|v5 saved|A1|A2|
|---|---|---|---|
|Daily geometric|1.032420%|0.734165%|0.131206%|
|Daily arithmetic|1.107940%|0.803091%|0.214960%|
|Daily median|0.188228%|0.060418%|-0.586287%|
|38-session Final Equity|¥1,477,436.15|¥1,320,438.35|¥1,051,087.75|
|Total return|47.743615%|32.043835%|5.108775%|
|Minute MTM MaxDD|10.225325%|12.224148%|21.202388%|
|Mean utilization|41.986827%|47.544540%|44.850448%|
|Median utilization|48.260213%|54.005944%|48.145494%|
|Mean idle fraction|58.013173%|52.455460%|55.149552%|
|Turnover JPY|¥89,327,438.95|¥88,923,117.55|¥83,624,453.55|
|Recycled cash used JPY|¥6,728,380.05|¥6,818,319.10|¥7,192,429.15|
|Funded/session|3.947368|4.500000|4.210526|

|Profile|Mean idle cash JPY|
|---|---|
|A1 Greedy|¥608,005.26|
|A2 Last-slot|¥592,338.16|

38 OOF sessionsの連結Final Equityであり「1か月成績」ではない。start=¥1,000,000。BUY1.0005、SELL0.9995、commission0、MTMのbar-close availability、cash release、15:20 cutoff、lot100、MAX3、cash LONG-onlyを維持。Liquidityはv5と同じdiagnostic-onlyでhard gate追加0。

## H. Integrity / counts / Safety / lineage

|Item|Result|
|---|---|
|Canaries|28/28 PASS; synthetic only, Main前|
|Independent checks|233907|
|Independent mismatches|0|
|Money/quantity tolerance|0|
|Score/probability tolerance|1e-12|
|Observed max scalar float delta|1.1102230246251565e-15|
|Primary replay|A1=1, A2=1, total2|
|Control/v6 replay|0|
|Oracle solves|4; separate independent upper-bound audit4|
|New / Rank / Slot fits|0|
|Teacher regeneration|0|
|Rank/model/preprocessing/score change|0|
|Orders/main merge/force push/provider/Claude|0|
|Protected/fresh/holdout/validation/OOS/prospective open|0|
|Selector/Entry/EXIT changes|0|
|MAX3/cash/same-symbol/replacement violations|0|
|Both arms COMPLETE|38/38; execution unresolved0|
|11 post-cutoff identities|retained in runtime, funded0|

|Authority|SHA256|
|---|---|
|Rank contract|6e8687f36f6f60fc9e9921e1ef29e0520cf1ea8bc01f14386963f1020b209518|
|Frozen pP stream|14c48e61554bd58c6d5289b410d6a8c859cb37efd0dbc5d98987fcb440aac2ed|
|Common mask|e369d4000ec1c9083cc428a3a318c5d936763ee5497f2dca06213e52ec9e89d8|
|Band map|bbe73fd89a4f045fff7de768877aed670c8d343c026ac94557af151e643eef1d|
|Future max rank table|44f1b4bae260bef971f2c9076f33f9dfdb5201bcad728708994fc13d1664b74a|
|Main claim|fe1bfd8c09f27167ce71510fcd966c1d5f13c029b87923a0232fd4d53c995225|
|Independent audit|2909c10b43da39c8e6d1f0825b8594ba69126bc57b4e806b818cfc489a4c9255|

全input/model/score/ledger hashはINPUT_BYTE_AND_SOURCE_FREEZE、BAND_VOLUME_IDENTITY_AUDIT、MAIN_REPLAY_RESULTに保存。8 rolling-originのsame completed train IDsを利用し、test volumeは強制しない。pPはordering authority / Rank Research Candidateであり、calibrated true probabilityとは呼ばない。training-only future tableにU5/U10 labelやtest未来arrivalはない。

Historical actual arrivalはUNKNOWNのまま、継承したclosed-bar availability/source/PIT boundaryを維持。独立実装は同じmarket sourceを利用するため、外部market source独立性は意味しない。teacher support contractのknown/unknown、empty future complete-captureの旧契約は変更・再生成していない。

Safety: executionAllowed=false, brokerWriteAllowed=false, excelOrderWriteAllowed=false, rssOrderFunctionAllowed=false, liveTradingAllowed=false, paperTradingAllowed=false, automaticPromotionAllowed=false, productionUpdateAllowed=false, transmitted=false, productionReady=false.

## I. Next Bottleneck

NEXT_BOTTLENECK = **MAX3_PHYSICAL_OCCUPANCY**。採用可能arm0のため、事前固定winner順でdiagnostic arm=A1を選んだだけで、A1を採用していない。A1の排他的missはRank46、Reserve0、MAX3 67、cash/lot7。最大reason67が該当する。

真にcount上限上unavoidableなU5は21であり、67全てが不可避ではない。51件のhigher-pP winnerがlower-pP holdingに塞がれ、ADMISSION Oracle116−funded50=66のruntime gapが残る。次の独立Workではこのoccupancy/early-fill構造を診断する境界をhandoffするが、本cycleで新policy・threshold・modelを足さない。Selector/Entry/EXITは永久Freeze。

### pP decile別funding（全primaryのpP DESCを10分割、診断のみ）

|Decile 1=highest|Candidate U5/U10|A1 funded U5/U10|A2 funded U5/U10|
|---|---|---|---|
|1|33/12|14/8|22/11|
|2|36/21|19/13|16/10|
|3|26/9|5/0|6/1|
|4|17/7|7/4|3/2|
|5|17/7|5/2|4/1|
|6|16/5|0/0|0/0|
|7|9/1|0/0|0/0|
|8|8/4|0/0|0/0|
|9|2/0|0/0|0/0|
|10|6/1|0/0|0/0|

### Entry時刻別funding（hourは診断表示のみ、runtime time bucketは追加0）

|Entry hour JST|Candidate U5/U10|A1 funded U5/U10|A2 funded U5/U10|
|---|---|---|---|
|09:00|39/21|30/17|27/16|
|10:00|57/22|13/8|14/7|
|11:00|16/2|1/1|0/0|
|12:00|20/8|3/1|4/1|
|13:00|26/10|2/0|2/0|
|14:00|12/4|1/0|4/1|
|15:00|0/0|0/0|0/0|

selectedCapitalCandidate = null
selectedRankCandidate = EXISTING_MOVE_P5
NEXT_BOTTLENECK = MAX3_PHYSICAL_OCCUPANCY
fresh_OOS_claim = false
productionReady = false

Rank vNextは固定したまま。新Allocator/Capital候補はNO_GOで、v5を保持。D15 CLOSURE_FIXED_STOP。
