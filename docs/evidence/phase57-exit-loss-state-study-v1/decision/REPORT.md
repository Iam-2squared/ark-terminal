# Phase57 NEW LONG EXIT — Development limit receipt

Date: 2026-09-18 JST

**EXIT_ARCHITECTURE_DEVELOPMENT_LIMIT_REACHED**

Strong Candidateは成立しなかった。新しいLoss Defense候補は実装・Freezeしていない。
Candidate Aを既存Frozen fallbackとして保持し、exposed Developmentでのarchitecture探索を停止する。
この結論は今回の有限の研究範囲に対する限界であり、あらゆる5m手法の不可能性を証明するものではない。

## Provenance / scope

- 開始GitHub HEAD: `e6b98886a35524c98ae4b6ec5913210de9525c80`。PR #587 open / Draft / unmergedを直接確認。
- 測定前protocol公開: `655880937f29aa691fdc44f3d1f445aa93500fc5`。3仮説・判定時刻・候補化gateを固定。
- 76 Development sessions / 2024-09-17〜2025-01-09。全3,284 opportunityのcoverageを保持。
- 比較はexact Frozen Fixed12で評価可能なINITIAL 1,072 + DIP 397 = 1,469件。全Opportunityへの外挿は禁止。
- Entry source `6fabde7dfe208e19d5611e0a290b4df6724e562e`、Selector/Entryの既存pinsを検証。
- 保存Fixed12 ledger・Path Studyを再利用。旧研究workflow・旧候補測定を手動再実行していない。
- 最初の実行はriskTagsに追加の母集団タグがあるためschema assertionで停止し、出力を生成しなかった。
  106/21のnamed tag検証に修正。state・gate・thresholdは変更していない。

## Candidate lineage / KEEP / KILL

| 系統 | 処分 | 学習・理由 |
| --- | --- | --- |
| Loss Defense v0 lower-close | KILL維持 | recovery winner破壊、106群改善なし |
| v1 prior-low breakdown | KILL維持 | winner/loser両方に悪化 |
| v2 recovery window | KILL維持 | DIPの救済が遅い。window再調整禁止 |
| v3 fixed tail boundary | KILL維持 | winner保護は良いが106/21を悪化 |
| Candidate A | KEEP frozen fallback | Profit Protectionのみ。mean<0、PF<1、tail未解決 |
| Candidate B | KILL維持 | INITIAL悪化。旧数値はhistorical evidence扱い |
| Candidate C | KILL維持 | causal +5 / same-bar contract / INITIAL ledger監査FAIL |
| 新3仮説 | 候補化却下 | 以下のseparation gate FAIL。EXIT性能を測った候補ではない |

## Separation diagnosis: A / B / C / D

A: 今回のobservable stateから、Recovery Winnerを残しdeep loserを安定分離できる根拠は得られなかった。
B: failed reclaim / failed bounce / normalized deteriorationの遷移は測定可能だが、候補化を支持しなかった。
C: INITIAL/DIPで悪化継続率と回復率が異なる。後付けcohort routingによる救済はしない。
D: +10/+15まで待っても一様な識別改善はない。待つ間にdeep-loser救済余地も減る。

| Hypothesis | INITIAL n | DIP n | deep failures | disposition |
| --- | ---: | ---: | ---: | --- |
| RECLAIM_REJECTION | 6 | 3 | 0 | SCREEN FAIL |
| FAILED_BOUNCE | 10 | 1 | 3 | SCREEN FAIL |
| NORMALIZED_ACCELERATION | 5 | 8 | 3 | SCREEN FAIL |

+15 negative/A-still-held母集団: INITIAL448、DIP181。以下は将来labelを用いた診断率でありEXIT成績ではない。

| State / cohort | later >=2pp drop | baseline | future recovery +3 | future recovery +5 |
| --- | --- | --- | --- | --- |
| RECLAIM_REJECTION / INITIAL | 2/6 (33.33%) | 155/448 (34.60%) | 0/6 (0.00%) | 0/6 (0.00%) |
| RECLAIM_REJECTION / DIP | 1/3 (33.33%) | 62/181 (34.25%) | 1/3 (33.33%) | 0/3 (0.00%) |
| FAILED_BOUNCE / INITIAL | 4/10 (40.00%) | 155/448 (34.60%) | 0/10 (0.00%) | 0/10 (0.00%) |
| FAILED_BOUNCE / DIP | 0/1 (0.00%) | 62/181 (34.25%) | 0/1 (0.00%) | 0/1 (0.00%) |
| NORMALIZED_ACCELERATION / INITIAL | 3/5 (60.00%) | 155/448 (34.60%) | 1/5 (20.00%) | 1/5 (20.00%) |
| NORMALIZED_ACCELERATION / DIP | 2/8 (25.00%) | 62/181 (34.25%) | 0/8 (0.00%) | 0/8 (0.00%) |

全3仮説とも3/4時系列blockでの悪化継続enrichment gateを満たさない。
top-frequency3除外でもcandidate eligibilityは回復しない。full underlying-minute coverage感度も保存。
単純にnだけを理由に落としたのではない。reclaim rejectionはdeep failure 0件、bounce failureはDIP1件。
normalized accelerationはINITIALで後の+3/+5 winnerを1/5含み、DIPの追加悪化率は母集団より低い。

raw rangeのt+5 rank AUCはINITIAL約0.770、DIP約0.783で、リスクの記述情報はある。
一方でこれは大きな値幅/既発生損失の大きさを表す可能性があり、winnerを壊さないEXIT条件の証明ではない。
cutoff選択やfeature winner選択は行っていない。全19 featureの固定方向AUC・分布・block感度を保存。
KEEP: volatility contextの必要性、実回復の履歴、厳密next-OPEN評価。KILL: 今回の3状態をEXITへ直結する案。

## Latency: same identities at t+5/+10/+15

全3時点でnegative/A-still-heldのmatched群内で、A net<=-5%の同一identityを追跡。
rescueは「将来loserと知ってその時点のnext OPENで退出した場合」のoracle proxy。実行可能な収益ではない。

| Cohort / deep n | t+5 incurred / rescue pp | t+10 incurred / rescue pp | t+15 incurred / rescue pp |
| --- | --- | --- | --- |
| INITIAL / 47 | -2.842397 / 4.404311 | -3.950663 / 3.440226 | -4.186062 / 3.039315 |
| DIP / 12 | -1.862899 / 5.026882 | -2.347813 / 4.539197 | -3.326201 / 3.500260 |

## Retained final logic / paired baseline

`NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1` remains `DEVELOPMENT_CANDIDATE_FROZEN_NOT_OOS_VALIDATED`.
HOLD → completed HIGHで初めて+3%確認 → PROTECT → 後続completed CLOSE<=+1% → next regular 5m OPEN退出。
signalなしはexact Frozen Fixed12。cost .05pp、Loss Defenseなし、cohort thresholdなし、re-entryなし。
Aに対する今回の改善は0。新候補は未実装なので、A比の改善を主張しない。

| Panel / policy | n | mean % | median % | PF | p05 % | Win | worst5% mean % |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| Overall / fixed | 1469 | -0.328364 | -0.101387 | 0.757107 | -5.764286 | 602/1469 (40.98%) | -8.727314 |
| Overall / candidateA | 1469 | -0.264701 | -0.050000 | 0.787412 | -5.494837 | 617/1469 (42.00%) | -8.288728 |
| INITIAL / fixed | 1072 | -0.328572 | -0.050000 | 0.762478 | -5.855764 | 442/1072 (41.23%) | -9.173831 |
| INITIAL / candidateA | 1072 | -0.263220 | -0.050000 | 0.793880 | -5.607821 | 446/1072 (41.60%) | -8.768430 |
| DIP / fixed | 397 | -0.327801 | -0.241571 | 0.741270 | -5.343625 | 160/397 (40.30%) | -7.433058 |
| DIP / candidateA | 397 | -0.268698 | -0.152987 | 0.768168 | -5.189149 | 171/397 (43.07%) | -6.950817 |

## Strict winner preservation / adverse subsets

| Panel | +3 | +5 | recovery +3 | recovery +5 | fast +3 | fast +5 |
| --- | --- | --- | --- | --- | --- | --- |
| Overall | 420/420 (100.00%) | 175/186 (94.09%) | 99/99 (100.00%) | 38/40 (95.00%) | 79/79 (100.00%) | 26/26 (100.00%) |
| INITIAL | 314/314 (100.00%) | 136/145 (93.79%) | 65/65 (100.00%) | 24/26 (92.31%) | 68/68 (100.00%) | 25/25 (100.00%) |
| DIP | 106/106 (100.00%) | 39/41 (95.12%) | 34/34 (100.00%) | 14/14 (100.00%) | 11/11 (100.00%) | 1/1 (100.00%) |

退出OPENの後のHIGHはpreservedと数えない。INITIAL +5は旧137/145から厳密136/145へ。
旧A Freeze artifactは変更していない。recovery=first bar negativeかつ未到達後のmilestone、fast=first bar到達。

| Evaluator-only risk subset | n | Fixed12 mean % | A mean % |
| --- | ---: | ---: | ---: |
| CHEAPER_PRIMARY_299 | 295 | -0.288008 | -0.268249 |
| CHEAPER_PRIMARY_D30_2 | 106 | -1.484893 | -1.417007 |
| CHEAPER_PRIMARY_D30_5 | 21 | -4.001442 | -3.684735 |
| MAE_MINUS_2 | 711 | -2.150443 | -2.001223 |
| MAE_MINUS_5 | 222 | -4.823248 | -4.380998 |

A large-loss<=-5%: 97件（Fixed12 112）。最悪-29.461765%で未改善。
A exit reasons: PROTECT 188 / Fixed12 fallback HOLD 1281。
これらはProfit Protectionの既存効果。Loss Defenseが改善した数字ではない。MAE/realized lossはidentity ledgerに保存。

## Chronological / concentration robustness

| Cohort | Block1 A−Fixed pp | Block2 | Block3 | Block4 | exclude top3 A−Fixed pp |
| --- | ---: | ---: | ---: | ---: | ---: |
| INITIAL | 0.017784 | 0.108921 | 0.180892 | -0.057226 | 0.028252 |
| DIP | -0.158602 | 0.169017 | 0.016589 | 0.222554 | 0.066130 |

Aは両cohortで3/4block非負。これは既存fallbackの頑健性で、新Loss DefenseのPASSではない。
symbol/session集中、全session成績、top3頻度除外、screen別集中をsummaryに保存。銘柄専用ruleなし。

## Deterministic / causal / ledger / tests

- saved Path Study prefix一致: 6,721。Fixed12/A ledger checks: 1,469。
- diagnostic future suffix/prefix perturbations: 4,407。A fill-bar H/L/C perturbations: 188。全PASS。
- summary / ledger / coverage / manifestを別directoryへ再生成し、全byte一致。既存Evidence不変。
- targeted causal/A/C regression: 26/26 PASS。LONG-only foundation regression: 39/39 PASS。
- 既存Development hash preservation: PASS。git diff check: PASS。
- CIは別のGitHub receiptでexact code HEADへ紐付ける。greenは研究performance PASSを意味しない。

## Safety / stop / next work

全9 flags false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed,
liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted。
Frozen Selector/Entry/A変更0、C復活0、model fit0、provider0、Fresh/OOS0、1m0、Capital/Portfolio0、main merge0。
現物LONG-only。SHORT/Margin/Leverageなし。オフライン診断のためorder/writeは実行していない。

次に必要なのは、同じDevelopmentでのthreshold調整ではなく、識別仮説に必要な情報の設計。
候補はEntry前のvolatility baseline、出来高/流動性、同時点の市場・sector context、観測欠測の品質情報。
これらが有効とは未検証で、取得・fit・接続は行っていない。新情報を使う場合はPIT定義と因果契約を先に固定する。
将来のvalidationは完全固定policyと一回限りの判定基準・日次/symbol依存を考慮した不確実性評価を事前に固定し、
ユーザーの明示許可後にのみ開く。Strong Final Freeze未成立なので、本WorkからFresh/OOSへ進まない。

**Development architecture mutation STOP。Candidate A fallback維持。完成・実用・利益化の主張なし。**
