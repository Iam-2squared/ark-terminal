# Capital Quality Intelligence v1R1 — 最終報告

作成: 2026-10-05T08:40:13.963758+09:00 / branch: `capital-quality-v1r1-recovery-20261005` / 評価basis HEAD: `66bc884a180b42b1f552a45b319959face186054`

qualityStatus = **ANTI_WEAK_MEDIUM_STRONG**。MOVE_U2 / MOVE_U3はいずれも旧Point Gate全8項目PASSかつAUC差CI下限>0。Auxiliary候補としてFreezeする。pPを置換・blendせず、Allocator/Capitalへ投入しない。

## A. Recovery Integrity

旧v1の失敗はQ4 baseline byte/parse integrityであり、旧QUALITY_CONTRACT_FAIL / Q12は永久保存。破損prefixを修復せず、旧expected cb1 hashも再現しなかった。

Q4以前のCOMMON_SAVED_SCORES・QUALITY_TEACHERS_EVAL・P_P_DECILES_OUTCOME_FREE・COMMON_EVAL_MASKから新semantic baselineを1回構築。Publicはcompact/hash root、full/group/rowsはcanonical deterministic gzip。公開後actual GETはparse/byte/hash一致。

Baseline root SHA256: `e7869d507e4d220030b41d688fdf7678c26c066d1cbf72eb6bf89e0a5ea6e38b`。Primary/独立baseline mismatch0、最大差1.11e-16。16 completed fits exact reuse、new/refit/audit-refitすべて0。各head OOF1039→common1028、extra11、missing0。元predictionを書き換えていない。

## B. Executive Quality

|Head|Control AUC|Candidate AUC|AUC delta|PR delta|95% CI|Blocks improved|Status|
|---|---|---|---|---|---|---|---|
|MOVE_U2|0.640967|0.690335|0.049368|0.053363|[0.022035, 0.077733]|7/8|STRONG|
|MOVE_U3|0.646589|0.697440|0.050851|0.066658|[0.023897, 0.078765]|7/8|STRONG|

## C. Fixed Budget Quality

N=1028。K=ceil(N×fraction)。Mediumは3–<5%、U5は>=5%、U10は>=10%（U5に含む）。全候補で同じbudget。

### Top20

|score|N|<2 N/rate|<3 N/rate|Medium N|U5 N|U10 N|U3 capture|U5 capture|U10 capture|
|---|---|---|---|---|---|---|---|---|---|
|CORE_H2|206|88 / 42.72%|107 / 51.94%|35|64|30|33.33%|37.65%|44.78%|
|CORE_H3|206|93 / 45.15%|115 / 55.83%|31|60|32|30.64%|35.29%|47.76%|
|MOVE_U2|206|79 / 38.35%|101 / 49.03%|34|71|32|35.35%|41.76%|47.76%|
|MOVE_U3|206|78 / 37.86%|102 / 49.51%|35|69|32|35.02%|40.59%|47.76%|
|legacy_ML|206|87 / 42.23%|109 / 52.91%|34|63|31|32.66%|37.06%|46.27%|
|pP|206|81 / 39.32%|102 / 49.51%|35|69|33|35.02%|40.59%|49.25%|

### Top30

|score|N|<2 N/rate|<3 N/rate|Medium N|U5 N|U10 N|U3 capture|U5 capture|U10 capture|
|---|---|---|---|---|---|---|---|---|---|
|CORE_H2|309|143 / 46.28%|179 / 57.93%|46|84|37|43.77%|49.41%|55.22%|
|CORE_H3|309|141 / 45.63%|183 / 59.22%|45|81|39|42.42%|47.65%|58.21%|
|MOVE_U2|309|122 / 39.48%|153 / 49.51%|55|101|44|52.53%|59.41%|65.67%|
|MOVE_U3|309|124 / 40.13%|163 / 52.75%|52|94|42|49.16%|55.29%|62.69%|
|legacy_ML|309|142 / 45.95%|181 / 58.58%|42|86|38|43.10%|50.59%|56.72%|
|pP|309|127 / 41.10%|171 / 55.34%|43|95|42|46.46%|55.88%|62.69%|

### Top40

|score|N|<2 N/rate|<3 N/rate|Medium N|U5 N|U10 N|U3 capture|U5 capture|U10 capture|
|---|---|---|---|---|---|---|---|---|---|
|CORE_H2|412|196 / 47.57%|252 / 61.17%|59|101|43|53.87%|59.41%|64.18%|
|CORE_H3|412|198 / 48.06%|252 / 61.17%|63|97|41|53.87%|57.06%|61.19%|
|MOVE_U2|412|166 / 40.29%|224 / 54.37%|67|121|50|63.30%|71.18%|74.63%|
|MOVE_U3|412|173 / 41.99%|233 / 56.55%|69|110|50|60.27%|64.71%|74.63%|
|legacy_ML|412|199 / 48.30%|253 / 61.41%|59|100|43|53.54%|58.82%|64.18%|
|pP|412|182 / 44.17%|241 / 58.50%|59|112|49|57.58%|65.88%|73.13%|

## D. Anti-Weak MOVE_U2

AUC 0.640967 → 0.690335。PR-AUC 0.529488 → 0.582851。PR差95% CI [0.016078, 0.087772]。

|block|control AUC|candidate AUC|delta|
|---|---|---|---|
|1|0.654243|0.711439|0.057196|
|2|0.657343|0.709091|0.051748|
|3|0.500670|0.657143|0.156473|
|4|0.600238|0.632857|0.032619|
|5|0.704380|0.712891|0.008511|
|6|0.599462|0.721198|0.121736|
|7|0.736896|0.665233|-0.071663|
|8|0.711382|0.756098|0.044715|

旧gate: A1=PASS, A2=PASS, A3=PASS, A4=PASS, A5=PASS, A6=PASS, A7=PASS, A8=PASS。改善block=[1, 2, 3, 4, 5, 6, 8]。catastrophic/undefined=0。

|fraction|control metric|candidate metric|
|---|---|---|
|0.1|42.72%|33.98%|
|0.2|42.72%|38.35%|
|0.3|46.28%|39.48%|
|0.4|47.57%|40.29%|

Bottom Weak density/capture:

|budget|CORE_H2 density|MOVE_U2 density|CORE_H2 capture|MOVE_U2 capture|
|---|---|---|---|---|
|0.1|80.58%|80.58%|13.93%|13.93%|
|0.2|78.64%|80.10%|27.18%|27.68%|
|0.3|76.70%|77.99%|39.77%|40.44%|

## E. Medium+ MOVE_U3

AUC 0.646589 → 0.697440。PR-AUC 0.408264 → 0.474922。PR差95% CI [0.026203, 0.103279]。

|block|control AUC|candidate AUC|delta|
|---|---|---|---|
|1|0.638192|0.639067|0.000875|
|2|0.694257|0.759291|0.065034|
|3|0.526316|0.657089|0.130773|
|4|0.666763|0.698102|0.031340|
|5|0.748437|0.800937|0.052500|
|6|0.530081|0.672938|0.142857|
|7|0.742889|0.689333|-0.053556|
|8|0.634815|0.683704|0.048889|

旧gate: M1=PASS, M2=PASS, M3=PASS, M4=PASS, M5=PASS, M6=PASS, M7=PASS, M8=PASS。改善block=[1, 2, 3, 4, 5, 6, 8]。catastrophic/undefined=0。

|fraction|control metric|candidate metric|
|---|---|---|
|0.1|18.18%|19.87%|
|0.2|30.64%|35.02%|
|0.3|42.42%|49.16%|
|0.4|53.87%|60.27%|

## F. pP Conditional Incremental

pP decileはtest block内equal-count10 bins、outcome-freeで固定。集約はvalid positive-negative pair weighted。pairsは独立sample Nではない。paired session-cluster bootstrapの単位は38 sessions。

|target|variant|valid pairs|control|candidate|delta|95% CI|
|---|---|---|---|---|---|---|
|U2|pP_conditional|2817|0.532836|0.593539|0.060703|[-0.034844, 0.150638]|
|U3|pP_conditional|2360|0.541949|0.583475|0.041525|[-0.037025, 0.112775]|

## G. Same-Session

pP decileはtest block内equal-count10 bins、outcome-freeで固定。集約はvalid positive-negative pair weighted。pairsは独立sample Nではない。paired session-cluster bootstrapの単位は38 sessions。

|target|variant|valid pairs|control|candidate|delta|95% CI|
|---|---|---|---|---|---|---|
|U2|same_session|6593|0.639011|0.689823|0.050811|[-0.002735, 0.104230]|
|U2|same_session_pP_conditional|622|0.556270|0.622186|0.065916|[-0.062686, 0.191203]|
|U3|same_session|5458|0.645291|0.693294|0.048003|[-0.000010, 0.101986]|
|U3|same_session_pP_conditional|509|0.536346|0.575639|0.039293|[-0.056737, 0.134335]|

## H. 5-Bucket Ordinal / NDCG

診断のみ。gain=[0,1,3,7,15]、blend設計には使わない。

|score|bucket|N|mean percentile|median percentile|Top20 density|Top30 density|
|---|---|---|---|---|---|---|
|CORE_H2|Q0_WEAK|596|0.440703|0.414800|42.72%|46.28%|
|CORE_H2|Q1_LOW|135|0.524808|0.542356|9.22%|11.65%|
|CORE_H2|Q2_MEDIUM|127|0.571154|0.573515|16.99%|14.89%|
|CORE_H2|Q3_BIG|103|0.615158|0.640701|16.50%|15.21%|
|CORE_H2|Q4_MEGA|67|0.665582|0.749757|14.56%|11.97%|
|CORE_H3|Q0_WEAK|596|0.441700|0.403116|45.15%|45.63%|
|CORE_H3|Q1_LOW|135|0.527837|0.528724|10.68%|13.59%|
|CORE_H3|Q2_MEDIUM|127|0.575087|0.589094|15.05%|14.56%|
|CORE_H3|Q3_BIG|103|0.597990|0.628043|13.59%|13.59%|
|CORE_H3|Q4_MEGA|67|0.669549|0.777994|15.53%|12.62%|
|MOVE_U2|Q0_WEAK|596|0.419937|0.382668|38.35%|39.48%|
|MOVE_U2|Q1_LOW|135|0.525731|0.550146|10.68%|10.03%|
|MOVE_U2|Q2_MEDIUM|127|0.598088|0.617332|16.50%|17.80%|
|MOVE_U2|Q3_BIG|103|0.664259|0.725414|18.93%|18.45%|
|MOVE_U2|Q4_MEGA|67|0.721911|0.770204|15.53%|14.24%|
|MOVE_U3|Q0_WEAK|596|0.422642|0.389971|37.86%|40.13%|
|MOVE_U3|Q1_LOW|135|0.532345|0.554041|11.65%|12.62%|
|MOVE_U3|Q2_MEDIUM|127|0.596148|0.631938|16.99%|16.83%|
|MOVE_U3|Q3_BIG|103|0.642289|0.703019|17.96%|16.83%|
|MOVE_U3|Q4_MEGA|67|0.721970|0.791626|15.53%|13.59%|
|pP|Q0_WEAK|596|0.427403|0.388023|39.32%|41.10%|
|pP|Q1_LOW|135|0.540019|0.547225|10.19%|14.24%|
|pP|Q2_MEDIUM|127|0.563701|0.578384|16.99%|13.92%|
|pP|Q3_BIG|103|0.642847|0.712756|17.48%|17.15%|
|pP|Q4_MEGA|67|0.724803|0.794547|16.02%|13.59%|

|score|NDCG10|NDCG20|NDCG30|NDCG40|mean ideal order|median ideal order|
|---|---|---|---|---|---|---|
|CORE_H2|0.273141|0.378911|0.422580|0.475750|True|True|
|CORE_H3|0.294327|0.367619|0.418923|0.462781|True|True|
|MOVE_U2|0.409410|0.472264|0.549896|0.606379|True|True|
|MOVE_U3|0.416389|0.468041|0.527932|0.584195|True|True|
|pP|0.334325|0.444825|0.500426|0.554657|True|True|

## I. Big/Mega Preservation Guard

Top30（N=309）固定。Primary Gateは変更しない。pPはEXISTING_MOVE_P5でFreeze。

|head|U5 capture|pP U5 capture|U10 capture|pP U10 capture|guard|
|---|---|---|---|---|---|
|MOVE_U2|59.41%|55.88%|65.67%|62.69%|BIG_WINNER_PRESERVING|
|MOVE_U3|55.29%|55.88%|62.69%|62.69%|PARTIAL|

## J. Independent Audit

Baseline・source labels/mask/split・model state・OOF・AUC/AP・Top/Bottom・conditional・same-session・ordinal/NDCG・全bootstrap resample値/CI・gate・status/selected headsのmismatch=0。最大float差=3.3306690738754696e-16 <=1e-12。

Session draw stream SHA256: `3debaf84406582e1e7c9efba7274703cbd075e50c6f2e5a331bb423352306ee8`。seed5701005 / 1999、独立生成一致。Independentはtrainer/evaluator/metrics/primary builderをimportせず、optimizerも実行していない。44/44 canaries PASS。

## K. Firewall / Safety / Counts / Prior No-Repeat

Main v8/v8R1 research/B1/B2/Capital outcome read/import/export=0。旧Quality evidence/research subtree不変、prior 382 metadata entries不変。Safety全false。

CORE H2/H3/H5、pP、MOVE_R、HF1/HL0/LSAFE/Q1–Q8、Weak専用head、PRR566 join/fitは再実行0。new/refit/audit refit0、既存16 fitsのみreuse。Baseline Primary1/Independent1、性能Primary1/Independent1。Capital/MAX3 replay、threshold/blend、Fresh、orders、main merge、force push、provider、Claude=0。

同じ58 sessionsを複数cycleに利用したITERATIVE_DEVELOPMENT_EVIDENCEであり、fresh/OOS successでもproduction readinessでもない。source/PITは既存bar-end assumptionを継承し、actual arrivalは不明。Potentialと実現PnLは区別し、PnLはdiagnosticのみ。

```text
selectedBigWinnerRank = EXISTING_MOVE_P5
selectedAuxiliaryHeads = ["MOVE_U2", "MOVE_U3"]
qualityStatus = ANTI_WEAK_MEDIUM_STRONG
recoveryStatus = QUALITY_RECOVERY_PASS
newFits = 0
reusedCompletedFits = 16
CapitalReplay = 0
MAX3Replay = 0
fresh_OOS_claim = false
productionReady = false
NEXT_POLICY = "Wait until independent Main Allocation Work is closed. If Quality head(s) pass, integrate only in a new precommitted cycle; do not modify Main mid-run."
```

R12 CLOSURE_FIXED_STOP。以後、このcycleでfit/teacher/feature/gate/threshold/combined score/Rank/Allocatorを変更しない。
