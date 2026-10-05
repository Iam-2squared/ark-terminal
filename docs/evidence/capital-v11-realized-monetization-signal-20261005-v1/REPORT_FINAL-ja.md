# Capital v11 Realized Monetization Signal — Final Report

## A. Executive / v10 authority

**V11_CONTRACT_FAIL。8 fitsを完了し、Capital replay0で固定STOP。** MRETの統計条件S1–S8は全てPASSしたが、独立監査でtraining scaleの差1件が固定許容1e-12を超えた（最大1.5774048733874224e-12）。S9 FAILのためMRET_STRONGを認証せず、M1/M2を実行しない。失敗receiptを保持し、refit・再評価・監査再実行・許容拡張による救済0。

v10 actual terminal HEAD `fe300dadf75867e3437cecfadd7e5317beaaa397`。CURRENT_STATE=CAPITAL_V10_M15_CLOSURE_FIXED_STOP / V10_REALIZED_MONETIZATION_LIMIT / diagnosticArm=S1 / NEXT_BOTTLENECK=REALIZED_MONETIZATION_SIGNAL。private SHA256 `c4e64c6f8c4657509b530419b52cabcefc3e000d2db85cd521b97f0720327f04` を含むnested Main/Quality manifest全一致。v10 canonical close timeはM15 checkpointの2026-10-05T11:42:18.983693+09:00。旧cycleはread-only。

Exposure=ITERATIVE_DEVELOPMENT_EVIDENCE。同じ58 Development sessions（warmup20、OOF38）を再利用。Fresh/OOS成功、将来収益、production readinessの主張なし。

## B. Quality-v3 HF1/HL0 negative history

HF1（realized>=1%）AUC=0.522519、HL0（realized<=0）AUC=0.502645、OOF各1016、CORE27+7。旧composite QはTOP3_SELECTION_WORSE / CAPITAL_QUALITY_V3_WORSE。HF1/HL0/LSAFE/Q1–Q8再実行0。今回はabsolute thresholdをteacherにせず、Potential bucket内のcompleted-train中央値を基準にする。Xはraw pre-entry Movement46+7、pP/q2/q3のstackingなし、I2 selectionは永久Freeze。

## C. MRET Teacher

Label=1 iff Frozen EXIT realized > block completed-past bucket median。exact tie=0。通常のempirical median（偶数supportは中央2値の平均）。bucket support>=10、backoff/merge0。missing realized / incomplete potentialを除外し、0-imputeしない。trainは既存Movementのpre15:20 candidate universe、heldout teacherをtrainerに渡さない。

OOF common-supportedかつMRET評価可能N=1016、positive=495、exact tie=16、current1039からの除外=23。全56 block×bucket cellの最小support=23。

|Block|Train N|Positive|Missing realized excluded|Potential incomplete excluded|
|---|---:|---:|---:|---:|
|1|544|270|6|0|
|2|674|333|9|0|
|3|805|398|11|0|
|4|939|464|13|0|
|5|1069|525|14|0|
|6|1200|594|15|0|
|7|1343|666|18|0|
|8|1483|734|18|0|

各cellは `median realized% / support / exact ties`。

|Bucket|B1|B2|B3|B4|B5|B6|B7|B8|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|<1|-0.913803% / 230 / 0|-0.931921% / 276 / 0|-0.862546% / 329 / 1|-0.840673% / 384 / 0|-0.866055% / 435 / 1|-0.823863% / 491 / 2|-0.825326% / 542 / 0|-0.827378% / 592 / 0|
|1–<2|0.002302% / 93 / 1|-0.099950% / 123 / 10|-0.099950% / 146 / 11|-0.099950% / 170 / 13|-0.099950% / 193 / 15|-0.099950% / 221 / 16|-0.099950% / 252 / 18|-0.099950% / 276 / 24|
|2–<3|0.685122% / 70 / 0|0.683580% / 89 / 1|0.776366% / 107 / 1|0.834022% / 124 / 0|0.816564% / 143 / 1|0.737819% / 158 / 0|0.683580% / 179 / 1|0.686665% / 195 / 1|
|3–<4|1.061678% / 47 / 1|1.054964% / 53 / 1|1.049766% / 62 / 0|1.054964% / 71 / 1|1.075507% / 84 / 0|1.099537% / 92 / 0|1.089336% / 105 / 1|1.075507% / 114 / 0|
|4–<5|2.064094% / 30 / 0|2.032942% / 37 / 1|1.662195% / 45 / 1|1.497031% / 49 / 1|1.392952% / 55 / 1|1.390174% / 60 / 0|1.440925% / 67 / 1|1.574857% / 76 / 0|
|5–<10|2.646793% / 51 / 1|2.420754% / 64 / 0|2.241457% / 77 / 1|2.108583% / 94 / 0|2.239630% / 101 / 1|2.038753% / 112 / 0|1.994918% / 126 / 0|2.029067% / 147 / 1|
|>=10|6.073649% / 23 / 1|5.616598% / 32 / 0|5.642967% / 39 / 1|5.539569% / 47 / 1|5.591268% / 58 / 0|5.211817% / 66 / 0|5.375053% / 72 / 0|5.642967% / 83 / 1|

## D. MRET Signal Result

BEST_EXISTING_CONTROL=q3：C0–C3のMRET-target AUC最大というprecommitted rule。全scoreを同じ1016 identitiesで比較。raw Logistic scoreはordering用途でありtrue probabilityとは呼ばない。PR-AUCはaverage precision。

|Score|MRET AUC|PR-AUC|Brier|realized>0 AUC|>=1 AUC|bucket concordance|block improved vs best|
|---|---:|---:|---:|---:|---:|---:|---:|
|pP|0.340782|0.391011|0.428280|0.489771|0.559286|0.370631|2/8|
|q2|0.336164|0.396324|0.385139|0.484360|0.549776|0.369528|2/8|
|q3|0.353206|0.398058|0.391165|0.488838|0.550970|0.386281|0/8|
|consensus|0.336313|0.388370|0.421163|0.491000|0.552084|0.374698|2/8|
|mP|0.631424|0.606552|0.247935|0.516828|0.434478|0.598276|8/8|

|Block|mP MRET AUC|q3 control AUC|Delta|
|---|---:|---:|---:|
|1|0.440242|0.393455|+0.046788|
|2|0.584897|0.372535|+0.212362|
|3|0.672768|0.411161|+0.261607|
|4|0.630952|0.349286|+0.281667|
|5|0.753032|0.274487|+0.478545|
|6|0.641765|0.372157|+0.269608|
|7|0.585580|0.362949|+0.222631|
|8|0.780556|0.241667|+0.538889|

Top enrichmentと全score decileはMRET_PRIMARY_RESULT.jsonに保存。

## E. Session Bootstrap

seed5701105 / 1999 resamples / OOF38 session clusters / PCG64 / 2.5–97.5 linear CI。best q3を全resampleで固定。session multiplicityを行・pairへ適用。pairや19 rolling windowsを独立標本とは呼ばない。

|Delta mP − q3|Valid N|95% CI|
|---|---:|---|
|MRET_AUC_delta|1999|[+0.220024, +0.337895]|
|MRET_PR_delta|1999|[+0.161437, +0.252389]|
|Spearman_delta|1999|[+0.000103, +0.185738]|
|conditional_delta|1999|[+0.152982, +0.281985]|
|realized_positive_AUC_delta|1999|[-0.031658, +0.085930]|

realized>0 AUC delta CIは0を跨ぐ。MRET-targetとpotential-conditional orderingのpoint改善から、Frozen EXIT全体の実現利益識別やCapital成功までを主張しない。

## F. Potential-bucket conditional realized ordering

|Score|Bucket×block concordance|Valid pairs|Same-session×bucket concordance|Valid pairs|
|---|---:|---:|---:|---:|
|consensus|0.374698|14505|0.363281|2944|
|mP|0.598276|14505|0.624660|2944|
|pP|0.370631|14505|0.358356|2944|
|q2|0.369528|14505|0.356318|2944|
|q3|0.386281|14505|0.365829|2944|

realizedが異なるunique unordered pairのみ。score tie credit0.5。aggregateはvalid pair weighted、bootstrap unit=session。pair countは独立sample Nではない。

## G. I2 funded/admission realized diagnostics

|Subset|N|Score|>0 AUC|>=1 AUC|<=0 AUC|Spearman|
|---|---:|---|---:|---:|---:|---:|
|I2_admission|488|consensus|0.537060|0.532784|0.462940|0.020092|
|I2_admission|488|mP|0.546586|0.486684|0.453414|0.043419|
|I2_admission|488|pP|0.525390|0.541317|0.474610|0.002555|
|I2_admission|488|q2|0.520674|0.519733|0.479326|0.009140|
|I2_admission|488|q3|0.521154|0.522227|0.478846|0.007756|
|I2_funded|161|consensus|0.542097|0.551171|0.457903|0.077175|
|I2_funded|161|mP|0.565571|0.542523|0.434429|0.042496|
|I2_funded|161|pP|0.534272|0.564324|0.465728|0.048941|
|I2_funded|161|q2|0.521440|0.510811|0.478560|0.027089|
|I2_funded|161|q3|0.515180|0.510631|0.484820|0.025090|
|whole_common|1016|consensus|0.491000|0.552084|0.509000|-0.055943|
|whole_common|1016|mP|0.516828|0.434478|0.483172|0.032891|
|whole_common|1016|pP|0.489771|0.559286|0.510229|-0.059033|
|whole_common|1016|q2|0.484360|0.549776|0.515640|-0.065211|
|whole_common|1016|q3|0.488838|0.550970|0.511162|-0.054854|

<=0 AUCはraw scoreの方向を反転せず表示。Secondary diagnosticsでありMRET teacherと別target。

## H. Signal Gate / Independent Audit

|Condition|Result|
|---|---|
|S1|PASS|
|S2|PASS|
|S3|PASS|
|S4|PASS|
|S5|PASS|
|S6|PASS|
|S7|PASS|
|S8|PASS|
|S9|FAIL|

Independent signal audit: 180,380 checks、mismatch=1、最大float差=1.5774048733874224e-12、固定許容1e-12。Trainer/evaluator imports0、optimizer refit0。coef/intercept NPZ snapshot exact。OOF score/metrics/bootstrap比較は許容内だが、numeric scale index5（selector/first_clock）の比較1件が許容を超えた。audit check名にblock番号は保存されていない。

Primaryはfrozen MovementのNumPy population std、Independentはmath.fsumによる中心偏差和を使った。reductionの丸め差であっても、固定contractを緩和しない。失敗したR8 receiptは書き換えない。再監査・refit・再評価0。

## I. Closure / certification blocker

monetizationSignal=MRET_NO_GOはS9を含む固定Gateの結果。**統計条件は8/8 PASSであり、情報不足が統計的に確定したという結論ではない。** status=V11_CONTRACT_FAILをcontrolling resultとする。NEXT_BOTTLENECK=REALIZED_MONETIZATION_INFORMATION_GAPはprecommitted not-STRONG taxonomyをそのまま保持し、実務上のblockerは独立preprocessing numeric認証。次の独立Workでcontractを整理するまではsignal/capital adoption不可。EXIT bottleneckとは命名しない。

R10 runtime percentile、R11 65-canary、R12 cap audit、M1/M2 Main claim/replay、Capital full auditはSTRONG条件を満たさず未実行。Capital metricやquality-retention PASSを捏造しない。control replay0、M1=0、M2=0、orders0、main merge0、force push0、provider0、Claude0。Safety10全false。

```text
selectedBigWinnerRank = EXISTING_MOVE_P5
selectedAuxiliaryHeads = ["MOVE_U2","MOVE_U3"]
selectionPolicy = QUALITY_PARETO_U2_U3_TENURE_MAX3_V1
monetizationSignal = MRET_NO_GO
status = V11_CONTRACT_FAIL
selectedCapitalCandidate = null
diagnosticArm = I2 saved reference (Capital not executed)
NEXT_BOTTLENECK = REALIZED_MONETIZATION_INFORMATION_GAP
newFits = 8
CapitalReplays = 0
fresh_OOS_claim = false
productionReady = false
CURRENT_STATE = CAPITAL_V11_R10_SIGNAL_NO_GO_CLOSURE_FIXED_STOP
```
