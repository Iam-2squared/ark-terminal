# Phase57 State v3 / 9-Pattern Price-Shape Entry v1 — 最終測定報告

Status: `MEASUREMENT_COMPLETE_NO_PROMOTION`; CI receiptは実装commit後にappendする。開始HEAD: `35e0b5ec20ca05940f34bbe23a5ba29d6d566f72`。

## 結論

State v3 classifierはFrozen Contractどおり実装でき、2,155件すべてを未来情報なしで9 Patternへ分類した。T0のState coverageは100%、INVALID/nullは0だった。しかし固定Entry policyは**不採用相当の明確な失敗**である。Immediate比でFill -282件/-13.09pp、paired買値 -0.198%、EntryPosition +0.048、Range Retention -4.28pp、+3 Capture -18.27pp、+5 Capture -19.12ppとなった。Entry v1比でもFill -176件/-8.17pp、paired買値 -0.138%、+3 Capture -4.20pp、+5 Capture -6.86ppで、改善していない。

BUY State 310件はFrozen Immediateと約定identityが完全一致し、悪化0だった。失敗は主にWAIT State 1,845件から生じた。WAIT群はImmediate比でFill -282件、paired買値 -0.237%、Low距離 +0.222pp、Range Retention -5.16pp、+3 Capture -21.32pp、+5 Capture -22.54ppである。30m/60m MAEはImmediate比で全体 +0.024/+0.079pp（負値が小さくなるため僅かに良好）だが、価格・位置・MFE・Capture・Fillの損失を補えない。

## 実装した固定pipeline

`previous session + today OPEN→NOW closed prefix → 9-Pattern State → T0 BUY/WAIT → WAIT中は既存6 Signalを毎分OR監視 + Stateを5 active-minuteごとに再認識 → intent後はFrozen fill proxyでretry`。固定fallbackは無い。BUY Stateは `RISE/SHARP_RISE/REBOUND`。同時刻のSignalとState transitionは全sourceを保存し、primaryは `SIGNAL_TRIGGER`。T0 BUY Stateは `INITIAL_STATE_BUY` をprimaryとした。

full historical pathはreplay substrateとして読み、classifierへ渡す前に必ず `raw barStart < NOW` でprefix化した。全2,155件のState・Signal・intentを確定しSHA-256化した後にのみ、quote/fill、Oracle、MFE/MAE、Outcomeを開いた。

## T0 State分布

| State | 件数 | 割合 |
|---|---:|---:|
| DROP | 1,403 | 65.10% |
| PULLBACK | 354 | 16.43% |
| REBOUND | 192 | 8.91% |
| RISE | 111 | 5.15% |
| RANGE | 57 | 2.65% |
| SHARP_DROP | 26 | 1.21% |
| SHARP_RISE | 7 | 0.32% |
| DROP_STOP | 5 | 0.23% |
| RISE_STOP | 0 | 0.00% |
| INVALID/null | 0 | 0.00% |

| 品質/確信度 | 件数 | 割合 |
|---|---:|---:|
| dataQuality OK | 711 | 32.99% |
| dataQuality DEGRADED | 1,444 | 67.01% |
| confidence HIGH | 688 | 31.93% |
| confidence MEDIUM | 1,113 | 51.65% |
| confidence LOW | 354 | 16.43% |

正常入力2,155/2,155を分類し、形式上RANGEへ一括退避していない。一方、保存価格系列の疎性によりDEGRADEDが67.01%を占める点は重要な弱点である。

## 5分State再認識

14,906 checkpoint、隣接transition 12,751件のうち、State変更は4,477件（35.11%）。主な変更は次のとおり。

| Transition | 件数 |
|---|---:|
| DROP → REBOUND | 1,384 |
| REBOUND → DROP | 964 |
| PULLBACK → RISE | 375 |
| RISE → PULLBACK | 278 |
| DROP → RANGE | 217 |
| RANGE → REBOUND | 161 |
| RANGE → DROP | 160 |
| REBOUND → RANGE | 136 |

WAIT後に最初のBUY Stateが現れたケースは1,491件。最初のBUY Stateまで平均12.89 active-minute、中央値10分。最終policy intentのtransition先はREBOUND 720、RISE 241、SHARP_RISE 5だった。DROP↔REBOUNDの往復が多く、現ContractのStateが5分ごとに大きく切り替わることがEntry解釈上の注意点である。

## Entry reason / 救済

| Causal intent | 件数 | 最終Fill |
|---|---:|---:|
| INITIAL_STATE_BUY | 310 | 277 |
| SIGNAL_TRIGGER | 572 | 572 |
| STATE_TRANSITION_BUY | 966 | 832 |
| NO_TRIGGER | 307 | 0 |
| 合計 | 2,155 | 1,681 |

最終 `NO_ENTRY` は474件。内訳はNO_TRIGGER window end 307件、trigger後retry exhausted 167件（INITIAL 33、STATE_TRANSITION 134）。fixed-time fallbackは0件。

- Signalが後続のBUY-State checkpointより先だったもの: 476件、全476件Fill。先行幅は平均7.39分、中央値5分。
- Signalは出たがBUY Stateが一度も出なかったもの: 47件、全47件Fill。
- Signalがwindow内で一度も無く、State transitionがintentを作ったもの: 786件。そのうち652件Fill。
- 同一timestampでSignalとState transitionが成立: 49件。priorityは成績・timestamp・価格を変更していない。
- Signal family（co-fire重複可）: HIGHER_LOW 191、LOWER_WICK 174、BREAKOUT 168、RECLAIM 88、COMPRESSION_EXPANSION 9、CONTINUATION 1。

Signalは5分State更新より早く転換を拾う機能を実際に持ち、State transitionもSignalなし652 Fillを救済した。ただし、両者を結合した最終Entry品質はbaselineを下回ったため、triggerの存在自体はpolicy有効性を意味しない。

## 4 policy比較

| Policy | Fill | Fill率 | NO_ENTRY | Delay 平均/中央値 | Selector比買値改善 | Low→Entry | EntryPosition | Range Retention |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Immediate | 1,963 | 91.09% | 192 | 1.45 / 0分 | -0.189% | 2.513% | 0.654 | 35.01% |
| 旧Signal-only | 1,857 | 86.17% | 298 | 9.63 / 10分 | -0.196% | 2.595% | 0.647 | 35.16% |
| Entry v1 | 1,857 | 86.17% | 298 | 9.13 / 10分 | -0.188% | 2.587% | 0.644 | 35.41% |
| State v3 Entry | 1,681 | 78.00% | 474 | 9.26 / 8分 | -0.378% | 2.800% | 0.673 | 33.11% |

買値改善は `100×(1−Entry/Selector)` なので負値はSelectorより高い約定。異なるFill集合の単純平均よりpaired比較を優先する。

| State v3 paired差 | vs Immediate | vs 旧Signal | vs Entry v1 |
|---|---:|---:|---:|
| Fill | -282 / -13.09pp | -176 / -8.17pp | -176 / -8.17pp |
| Both-filled N | 1,681 | 1,664 | 1,664 |
| 買値改善 | -0.198% | -0.130% | -0.138% |
| Low→Entry distance | +0.186pp | +0.129pp | +0.138pp |
| Entry→Later High余地 | -0.182pp | -0.119pp | -0.128pp |
| EntryPosition | +0.048 | +0.039 | +0.043 |
| Range Retention | -4.28pp | -2.86pp | -3.28pp |

すべての主要なEntry位置指標で、正の方向（安く・Low側・High余地大）ではなく逆方向へ動いた。State v3のpaired買値はImmediateより平均0.198%高い。

## Opportunity Capture

| Threshold | Denominator | Immediate | 旧Signal | Entry v1 | State v3 | v3−Immediate | v3−Entry v1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| +1% | 1,496 | 1,275 / 85.23% | 1,083 / 72.39% | 1,100 / 73.53% | 1,023 / 68.38% | -16.84pp | -5.15pp |
| +2% | 1,054 | 902 / 85.58% | 756 / 71.73% | 767 / 72.77% | 718 / 68.12% | -17.46pp | -4.65pp |
| +3% | 761 | 649 / 85.28% | 540 / 70.96% | 542 / 71.22% | 510 / 67.02% | -18.27pp | -4.20pp |
| +5% | 408 | 357 / 87.50% | 299 / 73.28% | 307 / 75.25% | 279 / 68.38% | -19.12pp | -6.86pp |

Fallback廃止後のFill/Capture維持には失敗した。特に+5% winnerでImmediate比78件、Entry v1比28件の追加未捕捉となった。

## 30m / 60m MFE・MAE

| Policy | 30m MFE | 30m MAE | 60m MFE | 60m MAE |
|---|---:|---:|---:|---:|
| Immediate | +1.769% | -1.870% | +2.546% | -2.513% |
| 旧Signal-only | +1.724% | -1.766% | +2.478% | -2.390% |
| Entry v1 | +1.730% | -1.772% | +2.520% | -2.379% |
| State v3 Entry | +1.683% | -1.844% | +2.428% | -2.445% |

State v3−Immediateのpaired差は30m MFE -0.148pp / MAE +0.024pp、60m MFE -0.178pp / MAE +0.079pp。MAEは僅かに改善したがMFEを失った。State v3−Entry v1は30m MFE -0.106pp / MAE -0.064pp、60m MFE -0.140pp / MAE -0.045ppで、Entry v1に対してはリスク側も悪化した。

WAIT中missed upsideは全体で平均0.648%、中央値0.317%（N=1,962）。初期WAIT群だけでは平均0.754%、中央値0.460%、75.07%で正の取り逃しがあった。

## BUY群とWAIT群の切り分け

| T0 cohort | N | State v3 Fill | Immediate Fill | paired買値 | +3 Capture差 | +5 Capture差 |
|---|---:|---:|---:|---:|---:|---:|
| BUY States | 310 | 277 | 277 | 0.000% | 0.00pp | 0.00pp |
| WAIT States | 1,845 | 1,404 | 1,686 | -0.237% | -21.32pp | -22.54pp |

BUY StatesはImmediateと完全同一で悪化なし。WAIT StatesではFill率が91.38%→76.10%、Low距離 +0.222pp、Range Retention -5.16ppとなった。例外的にRANGE 57件はpaired買値 +0.069%、Low距離 -0.083pp、Retention +0.76ppだったが、小標本かつ結果確認後のState別採用はpolicy変更になるため今回の成績には使わない。DROP 1,403件とPULLBACK 354件のWAIT悪化が全体を支配した。

## Causality / leakage / determinism

| Audit | 結果 |
|---|---:|
| State decision `barStart < NOW` | PASS / future violation 0 |
| Signal closed-bar assertion | PASS |
| HIGHER_LOW future pivot/backdating | violation 0 |
| Oracle Low/High decision use | 0 |
| MFE/MAE・Outcome decision use | 0 |
| State v2 reference decision use | 0 |
| Volume decision use | 0 |
| Evaluator open timing | 全2,155 intent固定後 |
| Baseline parity | PASS |
| Replay A vs B | 全file byte-identical |
| Provider requests | 0 |
| Protected Holdout/Fresh/OOS/Prospective | 0 / unopened |

Dedicated + preserved Entry local testsは29/29 PASS、STEP 1 Contract testsは7/7 PASS。GitHub dedicated CI、関連Signal regression、Predict regressionのreceiptは実装commit後にappendする。PR全体のunrelated workflowは別集計し、全体GREENとは事実確認なしに主張しない。

## 問いへの回答とSTOP判断

1. BUY StateはImmediateと約定identity一致で、悪化していない。
2. 6 WAIT Stateを一括で待つ価値はEvidence上ない。価格・Low距離・Retention・Capture・Fillが悪化した。
3. Signalは476件で5分Stateより平均7.39分早く、47件はBUY StateなしでFillしたため、高速triggerとしてのEvidenceはある。
4. SignalなしState transitionは786 intent / 652 Fillを作り、backup triggerとして機能した。
5. fixed fallbackなしではFill/Captureを維持できなかった。
6. State v3 EntryはEntry v1より明確に悪化した。
7. Immediateとの差を縮めず、広げた。
8. State認識・Signal先行・State rescueの機構は動作したが、この固定State×Entry policyに実用的なEntry Timing優位性はない。

今回のState v3 Entryを昇格せずSTOPする。結果を見てBUY State、Signal条件、閾値、fallbackを変更しない。Entry vNext、Volume、EXIT、Capital、Fresh/OOS、main mergeへ進まない。

Safety9: `executionAllowed=false`, `brokerWriteAllowed=false`, `excelOrderWriteAllowed=false`, `rssOrderFunctionAllowed=false`, `liveTradingAllowed=false`, `paperTradingAllowed=false`, `automaticPromotionAllowed=false`, `productionUpdateAllowed=false`, `transmitted=false`。
