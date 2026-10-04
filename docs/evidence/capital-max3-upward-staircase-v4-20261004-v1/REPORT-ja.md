# Capital v4 MAX3 Upward Staircase Result



作成: 2026-10-04T19:11:14.984845+09:00



1日幾何平均: **0.9526%**

100万円→20日中央値: **¥1,145,849**

100万円→20日最大: **¥1,281,381**

200万円: **NO**（rolling20 0/19）

Medium capture: **31/127 = 24.4094%**

BigWinner5 capture: **42/170 = 24.7059%**

MegaWinner10 capture: **23/67 = 34.3284%**

<2% contamination: **44.7674%**

Loser rate: **54.0698%**



選別判定: **UPWARD_SELECTION_MIXED**。経済判定: **CAPITAL_V4_MIXED**。North Starは独立判定。



## A. Control vs v4



| Metric | Control: CORE_P5 MAX3 Liquidity OFF | UPWARD_STAIRCASE_V4 MAX3 |

|---|---:|---:|

| daily geometric | 1.0960% | 0.9526% |

| rolling20 median | 1.14191559x | 1.14584896x |

| rolling20 max | 1.30866363x | 1.28138096x |

| Final Equity | ¥1,513,160 | ¥1,433,740 |

| 2x | 0/19 | 0/19 |

| MaxDD | 12.3006% | 11.5772% |

| utilization mean | 53.0040% | 49.1563% |

| funded N | 167 | 172 |

| U2 capture | 97/432 = 22.4537% | 95/432 = 21.9907% |

| U3 capture | 73/297 = 24.5791% | 73/297 = 24.5791% |

| Medium capture | 28/127 = 22.0472% | 31/127 = 24.4094% |

| U5 capture | 45/170 = 26.4706% | 42/170 = 24.7059% |

| U10 capture | 26/67 = 38.8060% | 23/67 = 34.3284% |

| <2 contamination | 41.9162% | 44.7674% |

| <3 contamination | 56.2874% | 57.5581% |

| realized >=+1% | 32.3353% | 30.2326% |

| realized >0% | 46.7066% | 45.9302% |

| realized =0% | 0.0000% | 0.0000% |

| realized loser <=0% | 53.2934% | 54.0698% |

| tail <=-1% | 34.7305% | 34.3023% |

| tail <=-3% | 13.1737% | 12.7907% |

| realized mean | 0.9717% | 0.7313% |

| realized median | -0.1000% | -0.1000% |

| worst | -17.5170% | -17.5170% |

| p05 | -5.2648% | -5.6323% |



| Success criterion | Result |

|---|---|

| S1 | FAIL |

| S2 | PASS |

| S3 | FAIL |

| S4 | FAIL |

| S5 | FAIL |

| S6 | FAIL |



上方向の選別改善はS1/S2/S3で判定: UPWARD_SELECTION_MIXED。Loser抑制への波及はS5=FAIL、利益+1%以上はS6=FAILとして分けて評価する。

実測上、Loser率は53.2934%→54.0698%、realized >=+1%率は32.3353%→30.2326%。両指標への改善波及は確認できなかった。単一のDevelopment比較で因果効果・将来収益は確立していない。



## B. Entry→High buckets



| Potential | candidate N | funded N | capture | realized mean | median | >=+1% | loser <=0% | tail <=-1% | actual PnL |

|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|

| 1-<2% | 197 | 39 | 19.7970% | -0.7326% | -0.5343% | 7.6923% | 76.9231% | 35.8974% | ¥-72,167 |

| 2-<3% | 135 | 22 | 16.2963% | -1.0283% | 0.2909% | 27.2727% | 40.9091% | 27.2727% | ¥-53,521 |

| 3-<4% | 73 | 18 | 24.6575% | 0.4339% | 1.6643% | 55.5556% | 27.7778% | 5.5556% | ¥-315 |

| 4-<5% | 54 | 13 | 24.0741% | 0.1947% | 0.8337% | 38.4615% | 23.0769% | 23.0769% | ¥8,571 |

| 5-<10% | 103 | 19 | 18.4466% | 1.9390% | 1.9786% | 68.4211% | 21.0526% | 15.7895% | ¥80,292 |

| <1% | 410 | 38 | 9.2683% | -2.3387% | -1.9900% | 0.0000% | 92.1053% | 65.7895% | ¥-225,918 |

| >=10% | 67 | 23 | 34.3284% | 9.5070% | 10.0503% | 65.2174% | 30.4348% | 30.4348% | ¥696,798 |



## C. Milestone model / PAVA / ML



| Head | own-label OOF ROC AUC | Brier | observed base | top20 enrichment |

|---|---:|---:|---:|---:|

| H2 | 0.646836 | 0.233927 | 41.5784% | 1.387553x |

| H3 | 0.651034 | 0.196754 | 28.5852% | 1.530513x |

| H5 | 0.656590 | 0.136187 | 16.3619% | 1.616092x |



PAVA raw violation: 81/1039 (7.7960%); projection mean L1=0.00217832, max absolute=0.09665921。補正後monotonic違反0。

PAVAはoutcomeを読まず、3確率の和を保存する。そのためMLのAdmissionと一次順位は和の補正前後で数学的に同じであり、補正は累積確率の整合性とtie-breakを担う。

ML cross-target AUC: {"U10": 0.6863829003132487, "U2": 0.6489375495759351, "U3": 0.6569468267581475, "U5": 0.6642388140526637}

ML top20 (N=208) milestone rates: {"Medium": 0.16346153846153846, "U10": 0.14903846153846154, "U2": 0.5721153846153846, "U3": 0.46634615384615385, "U5": 0.30288461538461536}; <2 contamination 42.7885%。

全decile observed rates、8 block AUC/base rates、H2/H3/H5 cross-target AUCはHEAD_DIAGNOSTICS.json。同cycle tuningへの利用0。



## D. Missed Winners / low-upside / slot regret



| Cohort | below baseline | MAX3 | cash/lot | cutoff | symbol open |

|---|---:|---:|---:|---:|---:|

| Medium | 54 | 37 | 5 | 0 | 0 |

| U10 | 20 | 21 | 3 | 0 | 0 |

| U2 | 174 | 146 | 17 | 0 | 0 |

| U3 | 111 | 103 | 10 | 0 | 0 |

| U5 | 57 | 66 | 5 | 0 | 0 |



同時刻batchのfuture-known評価。全missedとAdmission済みMAX3 rejectionのみを別集計し、各々batch/selected/missed/pair Nを示す。



| Slot regret | batch N | selected N | missed N | pair N |

|---|---:|---:|---:|---:|

| all_missed/selected_below2_missed_U3 | 0 | 0 | 0 | 0 |

| all_missed/selected_below2_missed_U5 | 0 | 0 | 0 | 0 |

| all_missed/selected_below3_missed_U5 | 2 | 2 | 2 | 2 |

| all_missed/selected_lower_bucket_higher_missed | 6 | 6 | 6 | 6 |

| eligible_MAX3_only/selected_below2_missed_U3 | 0 | 0 | 0 | 0 |

| eligible_MAX3_only/selected_below2_missed_U5 | 0 | 0 | 0 | 0 |

| eligible_MAX3_only/selected_below3_missed_U5 | 1 | 1 | 1 | 1 |

| eligible_MAX3_only/selected_lower_bucket_higher_missed | 2 | 2 | 2 | 2 |



MAX3によるmissed U5=66、U10=21。HELD_SLOT_BLOCKED_WINNER: U3=103、U5=66、U10=21。

MAX3-rejected U3 within first3 eligible batch candidates when older positions occupied slots; removing held slots would permit capacity selection, without modeling fills/replacement.

future outcomeによるposition replacement0。Capital eligibility rejectとしてのLiquidity理由0。



## E. Thin liquidity diagnostic



Hard reject OFF / position-size cap OFF。historical statusはeligibility・score・rank・quantityに使用0。



| Historical status | funded | U5 | U10 | mean | median | >=+1% | loser | no-trade MTM windows | PnL |

|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|

| EXTREME_ILLIQUIDITY_REJECT | 38 | 10 | 8 | 0.7363% | -0.0668% | 28.9474% | 52.6316% | 474 | ¥132,861 |

| LIQUIDITY_ELIGIBLE | 134 | 32 | 15 | 0.7298% | -0.1000% | 30.5970% | 54.4776% | 650 | ¥300,879 |

| LIQUIDITY_UNKNOWN | 0 | 0 | 0 | NA | NA | NA | NA | 0 | ¥0 |



旧Liquidity reject52 cohort: funded 10/52、actual PnL ¥245,626。Missed理由 {"MAX_POSITION_CAP": 17, "UPWARD_BELOW_BASELINE": 25}。

各statusのtail、worst、p05、stale marks、Frozen/EOD fill内訳、旧52の全qualityはSELECTION_ANALYSIS.json。



## F. Economic daily / rolling20 / asset curve



Daily geometric 0.9526%、arithmetic 1.0224%、median 0.1930%。

rolling20 valid N=19、min=1.08669814x、mean=1.16573674x、median=1.14584896x、max=1.28138096x、2x=0/19、earliest2x=None。

Final Equity ¥1,433,740、total return 43.3740%、MaxDD 11.5772%、utilization mean/median 49.1563%/58.6366%、time>=80/90% 0.0000%/0.0000%。

minimum cash ¥214,409、turnover ¥89,919,261、recycled cash used ¥7,020,365、funded/session 4.526316。

session max-concurrent 0/1/2/3 counts: {"0": 1, "1": 0, "2": 0, "3": 37}。

paired daily delta: {"equal": 1, "max_deterioration": -0.06104289024989218, "max_gain": 0.027642687162720947, "mean": -0.00175581872985671, "median": 0.0009487340608832788, "negative": 16, "positive": 21}（return units、×100でpercentage points）。

PAIRED_DAILY_RETURNS.csv、ROLLING20.csv、ASSET_CURVE_DAILY.csvを添付。minute-level actual mark/equity/cashはprivate CURVE.jsonl.gz。



## G. Integrity / Exposure / Safety



H2 new fits8、H3 exact reuse8/new fit0、H5 exact reuse8/new fit0。HF1/HL0/H10/Movement fit/use0。Main MAX3 full replay1、Control replay0、MAX4/MAX5 0、S-only/A+/B+ rerun0。

Canary 36/36 PASS、independent checks 101571、mismatch=0。Independent imports Primary=false。

独立auditはscalar確率、4分割候補のisotonic projection、Fractionの配分/BUY/SELL/MTM/cash recycling、daily/rolling20、capture/contamination/realized qualityを再計算。共有IOの外部取得時点や取引所原本自体の真正性を新たに証明するauditではない。

決定性はscore再materialization、synthetic ledger再実行、独立実装による全38-session ledger一致で検証。追加のPrimary Development full replay0。

Exposure: **ITERATIVE_DEVELOPMENT_EVIDENCE**。この58 sessionsは既に複数Capital cycleの設計判断へ使用済み。rolling-origin予測であってもfresh/OOS性能ではなく、研究反復によるoverfit riskがある。North Star hitの有無に関わらずproductionReady=false。

Protected/Holdout/Fresh/Validation/OOS/Prospective開封0、new provider requests0、Claude0、retune0、orders0、main merge0、force push0。Frozen Entry/EXIT変更0、Re-entry使用0、EXIT v4 rejected維持。

Safety: {"executionAllowed": false, "brokerWriteAllowed": false, "excelOrderWriteAllowed": false, "rssOrderFunctionAllowed": false, "liveTradingAllowed": false, "paperTradingAllowed": false, "automaticPromotionAllowed": false, "productionUpdateAllowed": false, "transmitted": false, "productionReady": false}。

既存teacherのstrictly-later actual High支援なし54件（うちpre-cutoff32件）は保存済みPotential=0を継承。新しい補完/ラベル変更は行っていない。実Highを持つ1546件の独立再計算差異0。この境界の原本定義は将来の別cycleで扱う必要があり、今回の結果の制約として残す。



GitHub research branch: capital-state9-vnext-20261004。全checkpointのactual HEAD/tree/JSTはCHECKPOINT_INDEX.jsonとreceipts。

Main v4 1 run + audit + reportで結果を固定してSTOP。同cycleの閾値・weight・rank・MAX・Entry/EXIT変更0。次の判断はユーザーへ返す。
