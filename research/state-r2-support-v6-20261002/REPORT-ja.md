# Ark Terminal State Predictiveness V6

Final status: `STATE_R2_SIGNAL_NOT_REPLICATED`。JST 2026-10-02T21:11:52.692240+09:00。

V6-only DOWN 270／UP 1457、pooled DOWN 345／UP 1811。pooled危険率 11.03% → 9.67%、改善 1.3541 pp。

Lane H integrity PASS／TRUE_NULL PASS／independent PASS（mismatch0）。Lane P calibration FAIL。V5はLIMITED_SAMPLEのまま、V4はBLOCKEDのまま。

## 必須25回答

| # | 問い | 原本に基づく結果 |
| ---: | --- | --- |
| 1 | V5原本hash／HEAD | branch `state-predictiveness-v5-r2-confirmation-20261002-v1`、実験C7 `28aa7b485fde800697806706fcdabdf8458c2f21`、納品HEAD `431a7c2b648e130550c11419a8508d2d6e143d84`。原本Contract／Precommit／scope／OOFのSHAは後表、全原本照合PASS。 |
| 2 | V6で追加できた日数 | 入力取得65日、evaluable V6-only OOF28日。V5 OOFと重ならない新しい日clusterは20日。完全未exposed日数と呼ばず、未exposed security-sessionとして登録。 |
| 3 | V6 security-session追加 | 213件／205security。OOF available targetのsecurity数44。A回収0/136件、B取得213/316件。 |
| 4 | V6-only DOWN support | 270 |
| 5 | pooled DOWN support | 345 |
| 6 | pooled UP support | 1811 |
| 7 | V6-only R1 dangerous FP | 120/1178 = 10.19% |
| 8 | V6-only R2 dangerous FP | 179/1852 = 9.67% |
| 9 | pooled R1 dangerous FP | 187/1696 = 11.03% |
| 10 | pooled R2 dangerous FP | 224/2316 = 9.67% |
| 11 | pooled improvement pp | 1.3541 |
| 12 | pooled95%CI | [-0.1713, 2.7240] pp。pooled日cluster1000 once、同日付を期間で分けない。 |
| 13 | V6-only改善方向 | 維持。R1−R2 0.5215 pp、95%CI [-1.6307, 2.3671] pp。 |
| 14 | R2 DOWN Precision／Recall／F1 | V6-only 36.03%／32.96%／34.43%。pooled 36.62%／34.49%／35.52%。 |
| 15 | R2 UP Precision／Recall／F1 | V6-only 72.62%／92.31%／81.29%。pooled 72.15%／92.27%／80.98%。 |
| 16 | TRUE_NULL PASSか | PASS。raw/cal対称candidate-local、V6-only／pooled別表。R3過去failureによる自動BLOCKなし。 |
| 17 | concentration PASSか | True。V6-onlyとpooledのgross dangerous reduction／class correctness gainにmax日／security share<=0.5。State/foldは参考開示。 |
| 18 | independent mismatch0か | 0、PASS。fit0／draw0、target／timestamps／purge／encoder／coefficients／alpha／T／予測／control／pooled／metric／CIを別logicで確認。 |
| 19 | calibration PASSか | False。V5固定rolling方式を変更0で適用。R2 date-equalLLとROW Brierのraw比5%gate、ECE／bucketも保存。 |
| 20 | hard signalだけでEntry researchへ進めるか | いいえ。V6固定gateを満たしていない。 |
| 21 | Entryへ渡してよい情報 | promotionされたState representationなし。保存Evidenceのみ。 |
| 22 | 禁止probability解釈 | calibration未達なら「DOWN probability=8.3%」等の確率解釈、probability Entry threshold／position sizingを禁止。calibration PASSでもV6内のEntry rule／sizing／注文は0。 |
| 23 | State9／Path／target変更0か | 各0。profile／M0／family mapping／R2 feature schema／base mathsも0。V5原本上書き0。 |
| 24 | Holdout／Protected exposure0か | V6 delta各0。Fresh reserve／OOS／Prospective／Entry／EXIT／profit／broker write等も0、過去unknown／nonzero履歴は保持。 |
| 25 | 次はHybrid Entryへ進むか | 進まない。追加承認scopeまたは今回の固定failure理由を別Workで扱う。 |

## R1／R2比較

| population | model | N | DOWN | UP | dangerous numerator/denominator | rate | DOWN P/R/F1 | UP P/R/F1 | balanced accuracy | macro F1 |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- | --- | ---: | ---: |
| V5_ONLY | R1 | 542 | 75 | 354 | 67/518 | 12.93% | 33.33%/10.67%/16.16% | 66.99%/98.02%/79.59% | 27.17% | 23.94% |
| V5_ONLY | R2 | 542 | 75 | 354 | 45/464 | 9.70% | 38.46%/40.00%/39.22% | 70.26%/92.09%/79.71% | 33.02% | 29.73% |
| V6_ONLY | R1 | 2110 | 270 | 1457 | 120/1178 | 10.19% | 16.09%/55.56%/24.96% | 75.30%/60.88%/67.32% | 29.11% | 23.07% |
| V6_ONLY | R2 | 2110 | 270 | 1457 | 179/1852 | 9.67% | 36.03%/32.96%/34.43% | 72.62%/92.31%/81.29% | 31.80% | 29.86% |
| V5_V6_POOLED | R1 | 2652 | 345 | 1811 | 187/1696 | 11.03% | 16.53%/45.80%/24.29% | 72.76%/68.14%/70.37% | 28.48% | 23.67% |
| V5_V6_POOLED | R2 | 2652 | 345 | 1811 | 224/2316 | 9.67% | 36.62%/34.49%/35.52% | 72.15%/92.27%/80.98% | 32.06% | 29.85% |

## Probability Lane P

| V6 R2 | row LL | date-equal LL | row Brier | ECE |
| --- | ---: | ---: | ---: | ---: |
| raw | 0.750642 | 0.826728 | 0.409836 | 0.125930 |
| calibrated | 0.877076 | 0.905497 | 0.487066 | 0.246589 |

positive temperatureはhard argmaxと同一row内class順序を変えない。異なるrow間のrelative rank stabilityは今回は評価していないのでhandoffしない。calibration PASSは固定relative悪化gateの合格であり、実運用確率の全面保証ではない。

## 固定scope・取得・split

136件の原順序、fresh retry許可60件、prior raw／label／protected76件は明示skip。Bはmetadata79日・最大4security/day、finite316上限。metadataで実選択316件を全minute取得前に固定、結果によるrefill0。入力65日／213security-session、OOF28日／2fold。calendar92日first5 warmup+3 blocks、空fold／空日も保持。status counts `{'OTHER_EXPLICIT_REASON': 76, 'PROVIDER_FAILURE': 95, 'RAW_UNAVAILABLE': 37, 'ACQUIRED': 213, 'U_UNAVAILABLE': 31}`。

新provider1493/2000HTTP、frozen kernel68001/125000steps、fresh72/160fits、research0、Actions1、V6-only1000+pooled1000 exactly once（actual 2000）。independent fit/draw0。V1 3000/cap1000 breach、V2 gap、old16FAIL/88workflow incident等は消さない。

## 観測の限界

V5+V6はユーザー指定のregistered cumulative support completion。V5をfreshに見せ直していない。V6は未exposed security-sessionで、同日other-security exposureや同じmarket regimeを含む。pooled union日clusterを利用し、V5/V6の同日を二重clusterにしない。OOFはpast-only trainでprequential、厳密な全期間未exposed OOSではない。V5絶対危険率とV6絶対危険率の上下をそのまま改善量と呼ばず、各populationのR1−R2を比較する。

historical known_atはUNKNOWN。bar-end因果availability仮定とprefix/timestamp監査を分離し、全State9 semantic kernel再auditはしていない。DOWN Recallとdangerous率は異なる分母。DOWNを見逃すriskとUP recall低下も表で開示。profit／cost／Entry／EXITルールの実測Evidenceにはしない。provider原ページは安全なrunner一時領域からpurge済み、原ページそのものの復元を保証しない。features／trace／source hash／M0照合を保持し、復元目的の新再取得はしない。

## V5原本identity

| identity | SHA256 |
| --- | --- |
| contract | `c7137749c452bba934efd33d31b9840464f2722580c6f6c86028aa9ec5a1dd56` |
| precommit | `f40ff4d5155677594a8e1e7dcac44b5588e2cf2a5746377ff15ceaa3c97b1ccd` |
| scope | `193c437ebd7b747c7b3e07faa921bb7c8d3f70f4d0d5484795a05adc9615bd64` |
| OOF | `e847cba71e7d3d5140525856c666c1f8a28586f8c7347176df6f94363090a1f8` |

公開CSVはV5のp.read_text()公開処理によりCRLF→LF変換、原本ZIPのbyte/SHAが優先。V5 source indexはexperiment C7とdelivery snapshotを明示区分。これらは数値／label／予測の書換えではなく、原本hash照合PASS。

## Handoff

次Work: 新しい事前固定確認またはfailureレビュー。自動実行0。HYBRID_ENTRY_INTELLIGENCE_HANDOFF.mdとSTATE_INTELLIGENCE_FREEZE_V6.jsonに受け渡し許可／禁止を固定。

## 納品

2〜3個の通常ZIPを同じfolderに展開。V6報告／CSV／OOF／labels／fits／feature／trace／control／bootstrapvectors／audit／取得reasonを保持。V5 COMPLETE原本3 ZIPは変更せず同梱、元V4/V3 evidenceまで保持。Git-backed codeはSOURCE_CODE_LOCATION_INDEX_V6.jsonのexact commit/path/hash。再fit／再label／新draw／再取得は納品検証に不要。
