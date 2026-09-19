# MSH-Entry LONG v2 — Root Cause Review

**MSH_ENTRY_LONG_V2_ROOT_CAUSE_REVIEW_COMPLETE**

**Primary: RC9 MULTIPLE。次の設計判断: D — SEPARATE_OPPORTUNITY_AND_RISK_AXES。**

中心問題は、D30だけの採用条件でv1のOpportunity品質判定を置き換え、低Opportunityの候補を大量に追加したこと。局所的なwinnerの誤棄却と、早いENTERによる後続判断のlatchも併存する。D30が無意味とは断定しないが、平均D30のv1比改善だけでRisk modelの有効性が証明されたとも扱わない。

COMPLETEは保存された採用集合の不成立理由と次の設計要件の整理完了を意味する。個々のfeatureの因果効果、D30予測の銘柄横断性能、Portfolio改善は未証明。

## Identity / scope

| Item | Value |
| --- | --- |
| Branch | `research/phase57-long-only-cash-equity` |
| PR | [#587](https://github.com/Iam-2squared/ark-terminal/pull/587), Draft / unmerged |
| Source Development head | `f1453bd99bafd4e17bcc4810d665e538c9206b32` |
| Latest main at direct start audit | `d00af22145f624dc16eb7d9e625a0f7c2f5eb1e1` |
| Final head / final CI | Publication後にWork最終報告へ記載。自己参照commit hashはこの文書へ埋め込まない。 |
| Contract SHA | `18818ffd1157c7ba15c93eb4723c3e28945c238e0e2f6a2440bee98c7ad1267f` |
| Development Evidence SHA | `35cec58faedcebfd09190ed5c404e2e874647eca90b92e12bc9021ff80385a75` |
| Root Cause Evidence SHA | [manifest.sha256](manifest.sha256) |
| Previous run | 24 successful inner fits / 10,000 calibration rows / 96 threshold evaluations |
| Reconfirmed | 24 NONE / outer OOF 0 / selected v2 Portfolioなし |
| This review | new fit=0 / new prediction=0 / new OOF=0 / new Portfolio replay=0 |

Historical / Development / IN-SAMPLE / Outcome-exposedの76-session conditional universeのみ。Frozen Selector、v1、EXIT、Equal、cash ledger、5入力、Target、λ、CV、missing、weighting、thresholds、Gatesを一切変更していない。前Evidenceの82ファイルのSHAを照合した。

## 保存不足と解析方法

**前回の保存不足:** innerモデルとENTER ID・集計値は保存されているが、10,000行のrawPrediction / predictedD30自体は未保存。今回の新prediction禁止に従い再生成していない。連続予測値との相関・残差・数値calibrationはN/A。

保存ENTER IDと固定state・入力有効性から、ENTER前のRISK_REJECTと、ENTER後のSTATE_ALREADY_ENTEREDを分離した。後者をリスク棄却に数えない。全入力が有効でmissing stateも既存modelに対応することを確認した上での論理的なstate復元であり、予測値や新しい判断の生成ではない。

入力寄与は保存係数・scale・medianを使用した各入力単独の加算項の分布。5項とinterceptを足し合わせず、個別予測値を復元していない。Feature ablation、因果効果の推定、新しいEntry ruleは行っていない。

## 1. 全thresholdの不成立再確認

各fold/groupの完全な理由は [threshold-failure-reproduction.csv](threshold-failure-reproduction.csv)。保存された96組の全ENTER集合から主要metricを再集計し、全Gate判定を独立に照合した。

| τ | +1 Precision FAIL | +2 Precision FAIL | Mean D30 FAIL | Coverage FAIL | Throughput FAIL |
| --- | --- | --- | --- | --- | --- |
| 1 | 6 | 6 | 2 | 10 | 23 |
| 2 | 24 | 23 | 7 | 21 | 0 |
| 5 | 24 | 23 | 8 | 20 | 0 |
| 10 | 24 | 23 | 8 | 20 | 0 |

分母は各24組。FAIL以外にも未定義のINCONCLUSIVEがあり、残りをPASSとみなさない。τ1はthroughput FAIL23組、+5 Preservation FAIL23組。τ2/5/10は+1 Precisionが24/24 FAIL、+2は23/24 FAIL。全24組で全条件を満たす候補なし。Gateが厳しすぎたという後付け判断はしない。

## 2. Threshold2 — chronological inner結果

| Fold | v1→v2 ENTER | Mean D30 v1→v2 | D30改善 | +1 Precision v1→v2 | +2 Precision v1→v2 | +3/+5 Preservation v2 | Throughput比 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 12→133 | 1.5306→1.3528 | 11.62% | 80.00%→51.67% | 60.00%→36.67% | 84.62% / 75.00% | 11.08× |
| 2 | 25→297 | 2.2437→1.4112 | 37.11% | 81.25%→62.79% | 75.00%→35.66% | 96.55% / 92.31% | 11.88× |
| 3 | 65→446 | 2.3558→1.9426 | 17.54% | 84.44%→67.91% | 66.67%→40.00% | 95.16% / 96.88% | 6.86× |
| 4 | 63→556 | 1.8353→1.6168 | 11.90% | 84.78%→65.85% | 78.26%→40.85% | 96.25% / 94.59% | 8.83× |

全24組の+1/+2/+3/+5 Precision・Preservation、ENTER/strict数、棄却数は [threshold2-by-unit.csv](threshold2-by-unit.csv)。ここはinner calibrationでありouter OOFではない。PreservationはFrozen Contractのfirst Top5 anchorから元の30分endpointまでのremaining opportunity定義。v1比で+3/+5 Preservationはchronological4/4を満たすが、Precisionは満たさない。

## 3. SKIP理由 / A–F cohort

| Fold | ENTER | Risk rejection | 既ENTERのstate SKIP | A risk棄却 | B +1/+2未満3棄却 | C +3/+5棄却 | D adverse採用 | E good accept | F censor全候補 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 133 | 7 | 60 | 2 | 2 | 2 | 14 | 30 | 109 |
| 2 | 297 | 5 | 98 | 1 | 1 | 2 | 34 | 66 | 216 |
| 3 | 446 | 11 | 143 | 2 | 5 | 4 | 80 | 104 | 307 |
| 4 | 556 | 6 | 238 | 2 | 1 | 3 | 83 | 150 | 408 |

A=D30>=2の直接棄却、B=1<=MFE<3の直接棄却、C=MFE>=3の直接棄却、D=ENTERかつD30>=2、E=ENTERかつD30<2・MFE>=1。AとB/Cは重複する。低risk・低Opportunityの採用/棄却はOTHERとして保存し、無理にgood/badにしない。Fは全候補のlabel未観測で、0や負例へ変換しない。全候補の排他的分類も [candidate-attribution.ndjson.gz](candidate-attribution.ndjson.gz) に保存。

## 4. Opportunity sacrifice / risk benefit

| Fold | Risk棄却 known / censored | 棄却+1 | 棄却+2 | 棄却+3 | 棄却+5 | 棄却D30>=2/5/10 | 採用D30>=2/5/10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4 / 3 | 4 (11.43%) | 3 (12.00%) | 2 (14.29%) | 1 (20.00%) | 2/1/0 | 14/2/0 |
| 2 | 4 / 1 | 3 (3.57%) | 3 (6.12%) | 2 (6.67%) | 2 (14.29%) | 1/1/0 | 34/5/0 |
| 3 | 9 / 2 | 9 (5.81%) | 5 (5.49%) | 4 (6.35%) | 1 (3.12%) | 2/1/0 | 80/22/2 |
| 4 | 4 / 2 | 4 (2.09%) | 4 (3.33%) | 3 (3.61%) | 2 (5.13%) | 2/0/0 | 83/16/3 |

括弧内はそのfoldのactive decisionに存在する評価可能winnerを分母とする棄却率。stateで既にlatchされた後続行を分母に足さない。

| Fold | State | N | Mean D30 | Median | p90 | p95 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ENTER | 60 | 1.3528 | 0.6976 | 2.8436 | 3.7273 |
| 1 | RISK_REJECT | 4 | 2.6250 | 1.9628 | 5.3902 | 5.9823 |
| 2 | ENTER | 129 | 1.4112 | 1.0924 | 3.2645 | 4.3220 |
| 2 | RISK_REJECT | 4 | 2.6748 | 0.6767 | 6.9481 | 8.1469 |
| 3 | ENTER | 215 | 1.9426 | 1.1474 | 4.9673 | 6.3790 |
| 3 | RISK_REJECT | 9 | 1.6734 | 0.9615 | 3.4417 | 4.7696 |
| 4 | ENTER | 284 | 1.6168 | 0.9930 | 3.8787 | 5.2049 |
| 4 | RISK_REJECT | 4 | 1.2099 | 1.0309 | 2.5630 | 2.6704 |

直接棄却の評価可能21 memberships（unique20）中、+1は20、+2は15、+3は11、+5は6。D30>=2は7、>=5は3、>=10は0。採用側には>=10が5 memberships残った。後半2foldは棄却側のmean D30が採用側より低く、棄却が安定して高riskを分離できたとは言えない。

| Fold | 既存τ5のMean D30 | τ2−τ5 D30差 | τ5比改善率 |
| --- | --- | --- | --- |
| 1 | 1.4090 | -0.0563 | 3.99% |
| 2 | 1.4637 | -0.0525 | 3.59% |
| 3 | 1.9393 | 0.0033 | -0.17% |
| 4 | 1.6355 | -0.0186 | 1.14% |

既に保存されたτ5との差は小さく、fold3では悪化。v1比11.62〜37.11%のmean D30改善の全てを「Risk Vetoが悪いEntryを落とした効果」とは帰属できない。採用母集団と時刻の変化を含む。新control・新thresholdは作っていない。

## 5. Rejected Risk × Opportunity matrix

行=実現D30、列=strict30m MFE。P0の既存境界をdiagnosticに使用。highRisk>=2、highOpportunity>=3。

Fold 1（censored 3件は表外）

| D30 \ MFE | <1 | 1–<2 | 2–<3 | 3–<5 | >=5 |
| --- | --- | --- | --- | --- | --- |
| <1 | 0 | 0 | 0 | 0 | 1 |
| 1–<2 | 0 | 1 | 0 | 0 | 0 |
| 2–<5 | 0 | 0 | 1 | 0 | 0 |
| 5–<10 | 0 | 0 | 0 | 1 | 0 |
| >=10 | 0 | 0 | 0 | 0 | 0 |

Fold 2（censored 1件は表外）

| D30 \ MFE | <1 | 1–<2 | 2–<3 | 3–<5 | >=5 |
| --- | --- | --- | --- | --- | --- |
| <1 | 0 | 0 | 0 | 0 | 2 |
| 1–<2 | 0 | 0 | 1 | 0 | 0 |
| 2–<5 | 0 | 0 | 0 | 0 | 0 |
| 5–<10 | 1 | 0 | 0 | 0 | 0 |
| >=10 | 0 | 0 | 0 | 0 | 0 |

Fold 3（censored 2件は表外）

| D30 \ MFE | <1 | 1–<2 | 2–<3 | 3–<5 | >=5 |
| --- | --- | --- | --- | --- | --- |
| <1 | 0 | 2 | 1 | 2 | 0 |
| 1–<2 | 0 | 1 | 0 | 0 | 1 |
| 2–<5 | 0 | 0 | 0 | 1 | 0 |
| 5–<10 | 0 | 1 | 0 | 0 | 0 |
| >=10 | 0 | 0 | 0 | 0 | 0 |

Fold 4（censored 2件は表外）

| D30 \ MFE | <1 | 1–<2 | 2–<3 | 3–<5 | >=5 |
| --- | --- | --- | --- | --- | --- |
| <1 | 0 | 0 | 0 | 0 | 2 |
| 1–<2 | 0 | 0 | 0 | 0 | 0 |
| 2–<5 | 0 | 0 | 1 | 1 | 0 |
| 5–<10 | 0 | 0 | 0 | 0 | 0 |
| >=10 | 0 | 0 | 0 | 0 | 0 |

計21 known membershipsではHighRisk/HighOpp3、HighRisk/LowOpp4、LowRisk/HighOpp8、LowRisk/LowOpp6。HighRisk/HighOppの重なりはあるが、unique8件のLowRisk/HighOpp棄却もあるため、winner sacrificeの全てが不可避なintrinsic overlapではない。同一bar内順序・執行可能性は判定していない。

## 6. Precision guardrailの分解

| Fold | 共通ENTER known | v1のみ known | v2追加 known | 追加群+1 Precision | 追加群+2 Precision | v1のみの理由 Risk / latch |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 4 | 59 | 52.54% | 37.29% | 5 / 2 |
| 2 | 12 | 4 | 117 | 60.68% | 31.62% | 2 / 6 |
| 3 | 33 | 12 | 182 | 65.93% | 34.62% | 10 / 5 |
| 4 | 35 | 11 | 249 | 63.45% | 36.14% | 6 / 9 |

| Fold | Level | v1除去効果 pt | 追加効果 pt | 総Precision差 pt |
| --- | --- | --- | --- | --- |
| 1 | +1 | -80.00 | 51.67 | -28.33 |
| 1 | +2 | -60.00 | 36.67 | -23.33 |
| 2 | +1 | 2.08 | -20.54 | -18.46 |
| 2 | +2 | 0.00 | -39.34 | -39.34 |
| 3 | +1 | -5.66 | -10.88 | -16.54 |
| 3 | +2 | 3.03 | -29.70 | -26.67 |
| 4 | +1 | -1.93 | -17.01 | -18.94 |
| 4 | +2 | -3.98 | -33.44 | -37.42 |

除去効果=P(common)−P(v1)、追加効果=P(v2)−P(common)の順序固定の会計分解。因果ablationではない。Fold1はcommon knownが1件だけでwinner removalの影響が大きく、不安定。Fold2–4は+1/+2低下の大半を追加群が説明する。v2先行ENTERによるlatchを、後続v1 winnerのrisk rejectionとして誤認しない。

Coverage v1→v2は41.67→45.11%、64.00→43.43%、69.23→48.21%、73.02→51.08%。後半3foldは5ポイント差guardrailに違反。観測済みPrecisionの希薄化は直接確認できるが、未観測部分の真の精度は不明。全censoredを成功/不成功と置いた上下限だけをJSONへ保存し、補完はしていない。

## 7. 五入力の係数・scale・寄与

| Fold | Input | coefficient | scale | ENTER平均加算項 | Risk棄却平均加算項 |
| --- | --- | --- | --- | --- | --- |
| 1 | frozenSelectorRidgeScore | -0.013756 | 19.339816 | 0.004002 | -0.038473 |
| 1 | directionalMomentum3Pct | -0.117213 | 2.241224 | -0.023009 | 0.388488 |
| 1 | directionalPullback6Pct | -0.196595 | 2.427249 | -0.045478 | 0.626885 |
| 1 | momentum3Missing | 0.022673 | 1.000000 | 0.010228 | 0.000000 |
| 1 | pullback6Missing | 0.022750 | 1.000000 | 0.012487 | 0.000000 |
| 2 | frozenSelectorRidgeScore | 0.008464 | 20.287569 | -0.001281 | 0.026709 |
| 2 | directionalMomentum3Pct | -0.117508 | 2.066031 | -0.009770 | 0.497872 |
| 2 | directionalPullback6Pct | -0.130043 | 2.639267 | -0.003981 | 0.407178 |
| 2 | momentum3Missing | 0.020432 | 1.000000 | 0.009287 | 0.000000 |
| 2 | pullback6Missing | 0.016596 | 1.000000 | 0.008494 | 0.000000 |
| 3 | frozenSelectorRidgeScore | 0.041994 | 18.836335 | 0.014454 | 0.213636 |
| 3 | directionalMomentum3Pct | -0.096665 | 2.033367 | 0.000475 | 0.282765 |
| 3 | directionalPullback6Pct | -0.104837 | 2.596407 | 0.014510 | 0.489712 |
| 3 | momentum3Missing | 0.008575 | 1.000000 | 0.002980 | 0.000000 |
| 3 | pullback6Missing | 0.006963 | 1.000000 | 0.002998 | 0.000000 |
| 4 | frozenSelectorRidgeScore | 0.056149 | 23.633147 | -0.009883 | 0.240106 |
| 4 | directionalMomentum3Pct | -0.077953 | 2.043137 | -0.001152 | 0.285432 |
| 4 | directionalPullback6Pct | -0.084959 | 3.077659 | -0.007023 | 0.251019 |
| 4 | momentum3Missing | 0.005639 | 1.000000 | 0.001917 | 0.000000 |
| 4 | pullback6Missing | 0.025265 | 1.000000 | 0.010542 | 0.000000 |

全24組のcenter、median、raw-unit slope、群別分布は [input-attribution.csv](input-attribution.csv)。Momentum/Pullback係数は24/24で負。より深い直近下落/pullbackを大きいD30へ結びつけ、直接棄却群の正の加算項が大きい。winnerの反発局面も含むため、係数の方向だけで判定品質は認定できない。

Ridge Score係数は19/24で正、5/24で負。chronologicalでは−0.013756→+0.008464→+0.041994→+0.056149。Ridge ScoreとMFEの相関は+0.279〜+0.534、actual D30とは+0.043〜+0.147。Opportunity signalをrisk軸へ混ぜるtrade-offは示唆されるが、これが主因との因果証明はない。連続predicted D30との相関は未保存のためN/A。

## 8. Missingness

全24組の直接リスク棄却138 membershipsは全てMomentum/Pullback両方available。missing indicatorでwinnerを直接大量棄却した、という説明は支持されない。chronological missing係数の大きさは概ね0.006〜0.025で、Momentum/Pullbackの棄却群加算項より小さい。一方、欠損medianへの縮小が採用側でどの程度リスクを隠したかはcounterfactualなしでは未確定。

| Fold | Missing pattern | Rows | ENTER | Risk拒否 | Mean D30 known | MFE median known |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | both_available | 101 | 60 | 7 | 1.3291 | 1.3385 |
| 1 | both_missing | 81 | 60 | 0 | 1.0273 | 2.2637 |
| 1 | pullback_missing | 18 | 13 | 0 | 1.8967 | 0.7614 |
| 2 | both_available | 218 | 145 | 5 | 1.4405 | 1.3366 |
| 2 | both_missing | 164 | 135 | 0 | 1.5634 | 1.8843 |
| 2 | pullback_missing | 18 | 17 | 0 | 1.6215 | 1.7818 |
| 3 | both_available | 365 | 254 | 11 | 1.7623 | 1.6639 |
| 3 | both_missing | 193 | 155 | 0 | 1.5871 | 1.8604 |
| 3 | pullback_missing | 42 | 37 | 0 | 2.7736 | 1.6885 |
| 4 | both_available | 480 | 324 | 6 | 1.5003 | 1.7857 |
| 4 | both_missing | 265 | 189 | 0 | 0.5019 | 3.3333 |
| 4 | pullback_missing | 55 | 43 | 0 | 2.1332 | 1.3766 |

Momentum-only missingの群はこのデータに存在しない。群間差はavailability/session依存を含む記述値。新しいmissing対処、0埋め、median変更は行っていない。

## 9. Symbol attribution

| Fold | D30改善の正寄与 Top1 / Top3 | 最大正寄与symbol | false reject +1 Top1 / Top3 | false accept D30>=2 Top1 / Top3 |
| --- | --- | --- | --- | --- |
| 1 | 40.18% / 89.25% | 130A0 | 25.00% / 75.00% | 14.29% / 35.71% |
| 2 | 31.51% / 59.61% | 86140 | 66.67% / 100.00% | 8.82% / 20.59% |
| 3 | 11.56% / 32.08% | 70690 | 33.33% / 55.56% | 5.00% / 12.50% |
| 4 | 9.54% / 24.44% | 57590 | 50.00% / 100.00% | 9.64% / 18.07% |

D30寄与はsymbolごとの sum(v1 D30)/N_v1 − sum(v2 D30)/N_v2。総和が全体のmean改善と一致するが、採用集合の構成差でありsymbol固有のmodel効果ではない。表のshare分母は正寄与の合計。負寄与と相殺するnet改善とは別。全symbol値はreview.json.gzへ保存。

Chronologicalの棄却+5は6 memberships中5が89180、1が76150（89180は4 distinct sessionsの5 observations）。+3棄却11中5が89180。+5損失機会の集中は大きいが、89180の+12.5/+14.29%は1円刻みのhigh-touchであり実現利益ではない。57590はfold4のD30>=2採用83件中8件。両symbolはsupporting diagnosticのみで、blacklist/price filter/weight変更は作らない。

## 10. Chronological / symbol-complement stability

| Scope | Units | D30 10%改善 | +1 Precision PASS | +2 PASS | +3 Pres PASS | +5 Pres PASS | Throughput PASS | Coverage PASS | 棄却mean D30>採用 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chronological | 4 | 4 | 0 | 0 | 4 | 4 | 4 | 1 | 2 |
| symbolComplementInner | 20 | 13 | 0 | 1 | 19 | 19 | 20 | 2 | 12 |

**20組はheld symbolを除外した学習と、その補集合のinner calibration。held-symbol outer OOFではない。** +1 Precision低下は20/20で再現するが、未知銘柄への汎化性能は測れていない。Mean D30は13/20で10%以上改善、19/20で非悪化。Risk棄却側のD30が高いのは12/20。

時系列は2,000 memberships / unique1,950 candidate events。symbol側8,000 membershipsは重複した補集合。独立した10,000データとして数えない。棄却のknown21もunique20で、70740の同一eventがfold3/4に重複する。

## 11. Target / Architecture / Root Cause判定

**D30 Target Diagnosis: E INCONCLUSIVE。** D30自体の安定した予測価値を、採用母集団の変化から切り離して認定するEvidenceが足りない。A「signalはあるがdecisionが失敗」は部分的な仮説として残す。新fit・score復元・ablationで救済しない。

**Architecture Diagnosis: B RISK_AND_OPPORTUNITY_NEED_SEPARATE_DECISION_AXES。** A「Risk Vetoが強すぎる」は局所的なwinner棄却に当てはまるが、全体のτ2採用は広い。Feature不足やLinear capacity不足はINCONCLUSIVE。Risk Veto全般を廃棄する根拠もない。

| Root code | 判定 | Evidence / limit |
| --- | --- | --- |
| RC5_D30_TARGET_MISMATCH | SUPPORTED_FOR_SOLE_ENTRY_DECISION_ROLE | D30 measures adverse magnitude, not upside quality. This does not establish that D30 is an invalid risk target. |
| RC2_OPPORTUNITY_FEATURE_CONTAMINATION_IN_RISK_MODEL | PARTIAL | Ridge score has a positive risk coefficient in 19/24 models and positive association with opportunity. Aggregate term attribution supports a trade-off, but no ablation or numerical-score correlation was performed. |
| RC7_SYMBOL_CONCENTRATION_DRIVEN_FAILURE | PARTIAL_LOCAL_WINNER_SACRIFICE | 5 of 6 chronological rejected +5 memberships belong to 89180; broad precision failures persist across every complement-group calibration. No symbol rule is justified. |
| RC1_RISK_OPPORTUNITY_INTRINSIC_OVERLAP | PARTIAL_NOT_PRIMARY | There are high-risk/high-opportunity rejected paths, but 8 unique low-risk/high-opportunity rejected events show the sacrifice is not entirely unavoidable intrinsic overlap. |
| RC3_MARKET_STATE_FEATURES_INSUFFICIENT | INCONCLUSIVE | No feature augmentation, selection or ablation is permitted; saved evidence cannot establish that adding a field solves this problem. |
| RC4_LINEAR_RIDGE_CAPACITY_LIMIT | INCONCLUSIVE | No model-family comparison; numerical inner predictions were not persisted, so residual/calibration diagnostics cannot be regenerated here. |
| RC6_MISSINGNESS_DRIVEN_FAILURE | NOT_SUPPORTED_AS_PRIMARY | All direct risk rejections in 24 units have both market-state inputs available. Missing-input false accepts remain descriptive; their counterfactual effect is unknown. |
| RC8_GATE_INTERACTION_ONLY | NOT_SUPPORTED_AS_SOLE_CAUSE | Large measured precision shifts and real winner/tail errors exist. No gate relaxation is justified from these results. |

Primary RC9 MULTIPLEの内訳は、D30単独のEntry判断と複合品質目的の不一致、採用母集団・時刻の変化、局所的な低risk winner誤棄却。RC2/RC7は部分的な補助説明で、因果確定や例外ruleの根拠ではない。

## 12. 独立したPortfolio coverage問題

| Item | Saved value |
| --- | --- |
| v1 eval60 ENTER / accepted / closed / unresolved | 232 / 6 / 5 / 1 |
| Locked positions / purchase notional | 1 / 335,300 JPY |
| Position | 89180, 2024-10-15 10:30 JST, 47,900 shares |
| Reason | MISSING_BEFORE_EXIT; 2024-10-15 10:50 JST |
| Cash balance | 671,699.925 JPY（最終資産ではない） |
| Final Equity / MaxDD | N/A / N/A |
| 後続拒否 | CURRENT_EQUITY_UNKNOWN175 / SYMBOL_ALREADY_OPEN40 / NO_REMAINING_REGULAR_BAR11 |
| Recorded cash releases | 5 |
| 今回のPortfolio replay / engine変更 | 0 / 0 |

未解決1件の記録理由はmissing-before-exit。session-end0、explicit no-trade0、auction0、other0は記録上の分類であり、missingの起源がno-tradeかprovider gapかを判定できたという意味ではない。11件のNO_REMAINING_REGULAR_BARはEntry拒否で、locked positionの原因へ合算しない。以前の+23.05%は173 complete-case subset、今回のfull causal streamとは範囲が異なる。

**Problem1＝Entryのrisk/Opportunity品質、Problem2＝未解決positionによるcash lock。両者を混同しない。** 売却・価格補完・cash releaseを捏造せず、ledgerを変更していない。

## 13. 次工程とSTOP

**Recommendation D: SEPARATE_OPPORTUNITY_AND_RISK_AXES。** 別指示のPre-Development Contractで、Frozen Selectorを保持したまま最低限のOpportunity品質とadverse-risk controlの役割・Entry eligibilityを明確にする。D30を維持するかは未確定のまま別判断に残す。

Two-Head/第二model、v1 ENTER限定学習、Opportunity×Risk product、WAIT、XGBoost、追加feature、追加threshold、Gate緩和を自動採用しない。今回の実装はRoot Causeの集計と監査のみ。将来別途許可されたrunでは、per-candidate予測値・missing mask・decision reasonの保存を要件にする。今回の欠落値は再生成しない。

## Tests / Safety / counters

Root Cause用8 testsを追加: latchとrisk棄却の分離、risk/opportunity重複、censor、Gate境界、Precision分解、単入力寄与、model/runtime呼出禁止、Evidence chain。結果とfinal-head CIはWork最終報告へ記載。既存契約・実装はsource hashesで保護し、CIでもProject fit/predictionを実行しない。

new fit / new prediction / new OOF / threshold search / Contract change / Fresh / OOS / Prospective / J-Quants / Yahoo / other provider / SHORT evaluation = 全て0。価格データは追加取得せず、前Development Evidenceを再利用。

executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed / liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed / transmitted = 全9項目false。現物LONG-only、main未merge。

**STOP。** 次は別指示のv2.1/Alternative Architecture Contract。今回v2.1を作らず、Gateを緩めず、Freshを開かない。
