# Ark Terminal — Persistent Watchlist Uptrend FIRST ENTRY v2

Document ID: WORK_PERSISTENT_WATCHLIST_STATE_UPTREND_FIRST_ENTRY_V2_20261003

保存時刻: 2026-10-03T12:47:38.972489+09:00 / basis HEAD: `340f7f1aa30cf9a2c55f8bd401cbb461b24714f0` / base HEAD: `bd9c34a67650467c68feaa631779f4095fac77ac`

今回のstatusは **BLOCKED_SPLIT_OR_LINEAGE_MISMATCH**。修正Evaluatorの機械的rankingはQUALITY **P0_Q80**、BALANCED **P1_Q70**。両candidateは異なる。

teacher calendarの実装ミスを修正したが、20 head fitsのtraining eligibilityが一致しない。所定designの修復は合計50 fitsでhard cap36を超えるため、追加fit0でintegrity STOP。品質確定・candidate Freeze・State正式採用・EXIT研究への移行は行わず、生成済みFIRST ENTRYと修正Evaluatorを診断用に保持する。

**Model/teacher lineageがBLOCKのため、以下のscore・Entry outcome・candidateは診断値である。正常な30-fit designのDevelopment candidateとしてFreeze／promotionできない。** Entry decision・fill・High・Captureの記録は保存したが、修正teacherで再fitしたOOF成果物が完成したとは主張しない。

Developmentのouter OOFから新しいFIRST ENTRYを生成した。修正teacher/evaluatorをfit0で再評価し、original training labels/modelsも保持した。前WorkのSAFE_UPSIDE FAILは閉じたまま保持し、threshold緩和・LR再fit・V6 R2 score/rank復活を行っていない。

Primaryは58 sessionsの2,155 unique(session,symbol) watch。既存canonical 2,155 Opportunity自体がfirst-selection watchへ一対一だった。対応する実際のSelector eventは2,900件。後続745件は同じwatchのrefreshとしてappendし、464 watch（21.53%）が再選出された。旧canonical event-level2155は別のreference欄に保持し、2900 eventや2155 watchを加算していない。

| 単位 | 総数 | 1 session平均 | 中央値 |
| --- | --- | --- | --- |
| Selector events | 2900 | 50.00 | 50.00 |
| Unique watches | 2155 | 37.16 | 37.00 |
| Repeat events | 745 | 12.84 | — |
| Repeated watches | 464 | 8.00 | — |

全133 development sessionsのtraining+OOF populationは4,931 watches。first selectorから同session regular closeまでの実測closed 1mを使い、30 active-minuteでwatchを捨てない。lunchとclosing auction pauseはactive minuteへ加えない。refresh featureはそのevent timestamp以降だけ。

| Policy | FIRST ENTRY N | 平均/day | 中央値/day | 0 Entry日 | Entry rate % | Path known N | Path unknown N |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0_Q70 | 1693 | 29.19 | 28.0 | 0 | 78.56 | 393 | 1300 |
| P0_Q80 | 1429 | 24.64 | 24.5 | 0 | 66.31 | 307 | 1122 |
| P0_Q90 | 949 | 16.36 | 16.0 | 0 | 44.04 | 125 | 824 |
| P0_Q95 | 619 | 10.67 | 11.0 | 0 | 28.72 | 59 | 560 |
| P1_Q70 | 1682 | 29.00 | 29.0 | 0 | 78.05 | 374 | 1308 |
| P1_Q80 | 1429 | 24.64 | 25.0 | 0 | 66.31 | 304 | 1125 |
| P1_Q90 | 930 | 16.03 | 16.0 | 0 | 43.16 | 128 | 802 |
| P1_Q95 | 622 | 10.72 | 11.0 | 0 | 28.86 | 60 | 562 |

Entry数/dayは結果として測定した。10/day Gateは置いていない。各policyの0／1–5／6–10／11–15／>15の日数、Entry clock、simultaneous FIRST ENTRY demand、peak ACTIVE watchlistをDAILY_FIRST_ENTRY_ACTIVITY.jsonに保存した。

| Policy | 0 | 1–5 | 6–10 | 11–15 | >15 | 最大同時Entry | peak watchlist |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0_Q70 | 0 | 0 | 0 | 0 | 58 | 4 | 20 |
| P0_Q80 | 0 | 0 | 0 | 0 | 58 | 4 | 24 |
| P0_Q90 | 0 | 0 | 0 | 22 | 36 | 3 | 27 |
| P0_Q95 | 0 | 0 | 25 | 33 | 0 | 2 | 33 |
| P1_Q70 | 0 | 0 | 0 | 0 | 58 | 5 | 21 |
| P1_Q80 | 0 | 0 | 0 | 0 | 58 | 4 | 24 |
| P1_Q90 | 0 | 0 | 0 | 25 | 33 | 3 | 29 |
| P1_Q95 | 0 | 1 | 22 | 35 | 0 | 3 | 32 |

peak watchlistはfirst selectionでactivateしFIRST ENTRYでこのWorkの監視評価を終了する未完了watch数。position releaseやCapital capacityを仮定した値ではない。

| Selector→High exclusive bucket | watch N |
| --- | --- |
| <1% | 596 |
| 1–<2% | 442 |
| 2–<3% | 293 |
| 3–<4% | 217 |
| 4–<5% | 136 |
| >=5% | 408 |
| missing | 63 |

以下は各bucketにおけるFIRST ENTRY後のstrictly later observed Highまでの値幅中央値（%）。Selector future MFEは保存済みcanonical full-day evaluatorのfirst-selector値をreuseした。全bucket×policyのEntry rate／no-entry／delay／mean／p25／p75／retention／Q／D／TV／reversal／time-to-peakはSELECTOR_WATCH_BUCKET_EVALUATION.jsonに保存した。

| Policy | 1–<2% | 2–<3% | 3–<4% | 4–<5% | >=5% |
| --- | --- | --- | --- | --- | --- |
| P0_Q70 | 1.122 | 2.097 | 2.846 | 3.920 | 7.048 |
| P0_Q80 | 1.140 | 2.149 | 2.762 | 3.948 | 7.319 |
| P0_Q90 | 1.121 | 2.152 | 2.733 | 3.760 | 7.299 |
| P0_Q95 | 1.121 | 2.035 | 2.814 | 3.439 | 7.273 |
| P1_Q70 | 1.121 | 2.108 | 2.955 | 3.988 | 7.198 |
| P1_Q80 | 1.121 | 2.156 | 2.719 | 3.920 | 7.212 |
| P1_Q90 | 1.138 | 2.178 | 2.868 | 3.975 | 7.268 |
| P1_Q95 | 1.110 | 1.996 | 2.857 | 3.432 | 7.251 |

Big Winner Captureは全Selector winnerを分母にし、Entry後に同じthresholdへstrictly later Highで実際に届いた割合。no-entryも分母に残し、欠測下の未到達はunknownとして別保存した。既存baselineでも比較用strictly-later条件を合わせた。旧saved Entry-bar-inclusive Captureを置換・再計算していない。

| Policy | >=1 Capture % | >=2 | >=3 | >=4 | >=5 |
| --- | --- | --- | --- | --- | --- |
| P0_Q70 | 63.90 | 64.23 | 61.89 | 63.60 | 64.71 |
| P0_Q80 | 55.82 | 56.17 | 53.88 | 55.33 | 55.64 |
| P0_Q90 | 38.03 | 38.24 | 35.74 | 36.58 | 37.75 |
| P0_Q95 | 26.14 | 25.71 | 23.92 | 24.26 | 25.98 |
| P1_Q70 | 64.17 | 64.99 | 63.21 | 63.60 | 64.22 |
| P1_Q80 | 55.35 | 56.26 | 53.88 | 55.88 | 56.13 |
| P1_Q90 | 37.43 | 37.19 | 35.09 | 35.48 | 35.78 |
| P1_Q95 | 25.94 | 25.43 | 24.05 | 24.08 | 26.23 |
| IMMEDIATE | 84.69 | 85.58 | 85.28 | 86.58 | 87.25 |
| R1 | 70.45 | 70.11 | 67.81 | 70.04 | 69.85 |

| Selector threshold | Winner denominator |
| --- | --- |
| >=1% | 1496 |
| >=2% | 1054 |
| >=3% | 761 |
| >=4% | 544 |
| >=5% | 408 |

| Candidate | >=3 Entryあり | >=3 hit | >=3 no-entry | >=3 unknown | >=5 Entryあり | >=5 hit | >=5 no-entry | >=5 unknown |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_Q80 | 553 | 410 | 208 | 133 | 291 | 227 | 117 | 58 |
| P1_Q70 | 633 | 481 | 128 | 141 | 341 | 262 | 67 | 70 |

| Policy | Entry→High % | Retention % | Q | pre-peak MAE % | TV % | Reversal | peak active min | Entry delay min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_Q70 | 1.603 | 90.516 | 0.191 | 0.504 | 1.872 | 1.000 | 39.000 | 4.000 |
| P0_Q80 | 1.719 | 92.958 | 0.225 | 0.508 | 1.751 | 1.000 | 44.000 | 6.000 |
| P0_Q90 | 1.786 | 91.454 | 0.088 | 0.517 | 1.520 | 1.000 | 55.000 | 7.000 |
| P0_Q95 | 1.880 | 88.618 | 0.050 | 0.181 | 1.002 | 1.000 | 59.000 | 13.000 |
| P1_Q70 | 1.619 | 90.964 | 0.225 | 0.554 | 1.761 | 1.000 | 40.000 | 4.000 |
| P1_Q80 | 1.719 | 91.630 | 0.213 | 0.569 | 1.640 | 1.000 | 43.000 | 6.000 |
| P1_Q90 | 1.783 | 91.812 | 0.068 | 0.472 | 1.443 | 1.000 | 56.000 | 7.000 |
| P1_Q95 | 1.919 | 89.222 | 0.100 | 0.281 | 1.011 | 1.000 | 62.000 | 12.000 |
| IMMEDIATE | 1.872 | 95.760 | 0.203 | 0.701 | 3.375 | 3.000 | 39.000 | 0.000 |
| R1 | 1.672 | 88.316 | 0.192 | 0.534 | 2.780 | 2.000 | 35.000 | 20.000 |

Q/D/TV/reversalは欠測を跨がないcomplete pre-peak pathのみ。Highはobserved値であり、一部source不足のwatchでは真の最大Highに対する下限。filled cohortの中央値同士だけで改善を断言しない。共通watchのpaired比較を下に示す。

IMMEDIATE/R1は同じWATCH_KEY・first-selector anchorの既存fillをreuse。既存canonical Geometryは引用と数値parityだけで、新しく定義したQ/D/TV/reversalを同じfillから測定した。旧Geometryのtime clockもreferenceとして保持し、Primary clockはfinal RC2のdated regular active minutesへ合わせた。

**P0_Q80のpaired比較**。同一watchで両armがfilledかつ該当metric knownの場合だけ。Δはwatchごとの差の中央値で、列の中央値の単純差とは異なる。

| Baseline | Metric | paired N | 新Entry median | baseline median | paired Δ median |
| --- | --- | --- | --- | --- | --- |
| IMMEDIATE | entry_to_high_pct | 1329 | 1.848 | 2.132 | 0.000 |
| IMMEDIATE | path_efficiency | 224 | 0.217 | 0.196 | 0.000 |
| IMMEDIATE | pre_peak_mae_abs_pct | 224 | 0.566 | 0.782 | 0.000 |
| IMMEDIATE | total_variation_pct | 224 | 2.066 | 2.758 | 0.000 |
| IMMEDIATE | reversal_count | 224 | 1.000 | 2.000 | 0.000 |
| IMMEDIATE | upside_retention_pct | 1244 | 93.512 | 95.956 | 0.000 |
| IMMEDIATE | selector_to_entry_active_delay | 1343 | 5.000 | 0.000 | 2.000 |
| R1 | entry_to_high_pct | 1280 | 1.895 | 1.852 | 0.000 |
| R1 | path_efficiency | 205 | 0.193 | 0.164 | 0.000 |
| R1 | pre_peak_mae_abs_pct | 205 | 0.616 | 0.652 | 0.000 |
| R1 | total_variation_pct | 205 | 2.493 | 2.368 | 0.000 |
| R1 | reversal_count | 205 | 1.000 | 1.000 | 0.000 |
| R1 | upside_retention_pct | 1198 | 93.673 | 90.441 | 0.000 |
| R1 | selector_to_entry_active_delay | 1292 | 5.000 | 20.000 | 0.000 |

**P1_Q70のpaired比較**。同一watchで両armがfilledかつ該当metric knownの場合だけ。Δはwatchごとの差の中央値で、列の中央値の単純差とは異なる。

| Baseline | Metric | paired N | 新Entry median | baseline median | paired Δ median |
| --- | --- | --- | --- | --- | --- |
| IMMEDIATE | entry_to_high_pct | 1545 | 1.751 | 2.018 | 0.000 |
| IMMEDIATE | path_efficiency | 304 | 0.226 | 0.177 | 0.000 |
| IMMEDIATE | pre_peak_mae_abs_pct | 304 | 0.647 | 0.794 | 0.000 |
| IMMEDIATE | total_variation_pct | 304 | 2.149 | 3.010 | -0.026 |
| IMMEDIATE | reversal_count | 304 | 1.000 | 2.000 | 0.000 |
| IMMEDIATE | upside_retention_pct | 1441 | 91.704 | 95.619 | 0.000 |
| IMMEDIATE | selector_to_entry_active_delay | 1562 | 3.000 | 0.000 | 1.000 |
| R1 | entry_to_high_pct | 1484 | 1.819 | 1.750 | 0.000 |
| R1 | path_efficiency | 264 | 0.240 | 0.169 | 0.000 |
| R1 | pre_peak_mae_abs_pct | 264 | 0.652 | 0.689 | 0.000 |
| R1 | total_variation_pct | 264 | 2.571 | 2.947 | 0.000 |
| R1 | reversal_count | 264 | 2.000 | 2.000 | 0.000 |
| R1 | upside_retention_pct | 1383 | 91.921 | 89.172 | 0.000 |
| R1 | selector_to_entry_active_delay | 1499 | 3.000 | 20.000 | -2.000 |

既存canonical event-level 2,155件の引用reference。Primary watch-levelの表とは別で、denominatorを加算しない。saved Geometryだけを使い、旧clockも保持した。

| Canonical event arm | event N | saved filled N | Entry→High median % | Retention median % | saved delay median min |
| --- | --- | --- | --- | --- | --- |
| IMMEDIATE | 2155 | 1963 | 1.872 | 95.760 | 0.000 |
| R1 | 2155 | 1885 | 1.672 | 88.316 | 20.000 |

| Family | Head | known original-mask OOF N | MAE | Spearman |
| --- | --- | --- | --- | --- |
| P0 | UPSIDE | 221734 | 1.614 | 0.423 |
| P0 | QUALITY | 94547 | 0.277 | 0.018 |
| P0 | ADVERSE | 94547 | 0.573 | 0.410 |
| P1 | UPSIDE | 221734 | 1.614 | 0.423 |
| P1 | QUALITY | 94547 | 0.277 | 0.019 |
| P1 | ADVERSE | 94547 | 0.574 | 0.410 |

上のhead統計はoriginal training-label maskの診断で、正しいteacher populationの評価としては無効。prediction decile actual targetとsession stabilityも同じ制約を明記して保存した。percentile transformは各foldのtraining-side predicted distributionだけを使用し、UPTREND_SCOREはU percentile／Q percentile／1−D percentileのequal-weight平均。absolute probabilityとは呼ばない。

Stateの機械的比較status: **STATE9_NO_INCREMENTAL_UPTREND_ENTRY_VALUE_ON_DEVELOPMENT**。lineage BLOCKによりState incremental valueの正式結論には使えない。P1をState9正式採用へ昇格していない。各fixed quantileでのP1−P0診断差を以下へ保存した。

| Quantile | Δ High % | Δ Q | Δ MAE % | Δ >=3 Capture pp | Δ >=5 pp | Δ Entry rate pp |
| --- | --- | --- | --- | --- | --- | --- |
| Q70 | 0.015 | 0.034 | 0.050 | 1.31 | -0.49 | -0.51 |
| Q80 | 0.000 | -0.012 | 0.061 | 0.00 | 0.49 | 0.00 |
| Q90 | -0.003 | -0.020 | -0.046 | -0.66 | -1.96 | -0.88 |
| Q95 | 0.039 | 0.050 | 0.100 | 0.13 | 0.25 | 0.14 |

QUALITY rankingはmedian Q→lower median D→higher median High→>=5 Capture→Entry rate。BALANCEDは>=5 Capture最大値から2pp以内のpolicyを対象にQ→D→>=3 Capture→Entry rate。global 8 policiesと各family 4 policiesの両方を保存し、新threshold・profit criterion・Entry数合わせは使っていない。QUALITY=P0_Q80、BALANCED=P1_Q70。

Source支持はPrimary {'EVALUABLE_FULL_GRID': 218, 'PARTIALLY_EVALUABLE': 1929, 'SOURCE_UNAVAILABLE': 8}、observed rows 223,940／scheduled rows 377,450。欠測minuteを生成せず、source missingを0にせず、semantic UNKNOWNとsource missingを分離した。修正後の全training+OOF Q/D target knownは204,471／462,752 rows。Path unknownはEntryの品質が悪いと確定した意味ではない。

限界は、historical actual knownAtがUNKNOWNでbar-end availabilityを仮定していること、missing sourceのPathをunknownにしていること、High touchのintrabar順序がUNKNOWNでpeak-bar Lowを保守的に含めていること、U teacherがmaximum observed Highであること。新しいprovider・Protected・Fresh Validation・OOS・Prospectiveを開いていない。

Independent audit: **BLOCKED_SPLIT_OR_LINEAGE_MISMATCH**, mismatch 20。grid全462,752 rows、teacher全462,752 rows、4 policy×2 familyの全17,240 recordsを照合した。Stateは事前固定indexの51 watchをfrozen independent RC2 API＋120精度で別再生し、4,245 State rowsを照合した。model direct predictionは7,680 samples、全rowのpercentile／threshold lineage、全training rowのmedian／one-hot scopeを確認した。audit fit=0。有限sample範囲を超えた完全な独立性や実データarrival timestamp証明は主張しない。

実際のfitsは30。P1 fold5の配列準備でメモリ停止したが、27 completed fitsを保存して残り3のみを実行した。completed fitの再fitは0。独立auditがteacher calendarの実装ミスを検出したため、corrected teacher maskは元のmodel training maskと一致しない。hard cap36、hyperparameter／model family／weight／threshold search／bootstrapは0。

calendar実装ではAM continuous→PM continuous→AM terminal690の順にexpected sourceを並べてしまい、正常な昼跨ぎPathを欠測へ誤分類した。Q/D各13,948 rowsがNULLから正しいknown値へ変わる。元々finiteだったtraining値の変更は0だが、eligible training maskが20 head fitsで変わる。元のlabels／modelsを保存し、calendarとEvaluatorを修正した。所定designを正しいteacherで再fitすると30+20=50 fitsとなり、user指定hard cap36を超える。追加fitは0で停止した。性能の低さを停止理由としていない。

| 必須回答 | 回答 |
| --- | --- |
| 1 | Selector events平均50.00/day、unique watch平均37.16銘柄/day。 |
| 2 | 745 repeat events、464/2155 watch（21.53%）にrefresh。first eventと全refresh時刻を保存。 |
| 3 | 平均/dayはP0 Q70/Q80/Q90/Q95 = 29.19 / 24.64 / 16.36 / 10.67。P1 = 29.00 / 24.64 / 16.03 / 10.72。 |
| 4 | 全8 policiesで0 Entry日は0/58日。 |
| 5 | 1–<2% bucketのEntry→High中央値: QUALITY 1.140% / BALANCED 1.121%。全8 policiesは上表。 |
| 6 | 2–<3% bucketのEntry→High中央値: QUALITY 2.149% / BALANCED 2.108%。全8 policiesは上表。 |
| 7 | 3–<4% bucketのEntry→High中央値: QUALITY 2.762% / BALANCED 2.955%。全8 policiesは上表。 |
| 8 | 4–<5% bucketのEntry→High中央値: QUALITY 3.948% / BALANCED 3.988%。全8 policiesは上表。 |
| 9 | >=5% bucketのEntry→High中央値: QUALITY 7.319% / BALANCED 7.198%。全8 policiesは上表。 |
| 10 | >=3 / >=5 Winnerは761 / 408 watch。QUALITYのCaptureは53.88 / 55.64%、BALANCEDは63.21 / 64.22%。全8 policies・baseline・no-entry・unknownを保存。 |
| 11 | known paired cohortではQ中央値に改善傾向があるが、両ranking候補のpaired Q差中央値はIMMEDIATE/R1とも0。TV/reversalも保存した。lineage BLOCKとPath欠測のため一貫した改善を確定できない。 |
| 12 | 両ranking候補でpaired cohortのMAE中央値はIMMEDIATE/R1より低いが、watch別差の中央値は全て0。QUALITY対R1の平均差は+0.025ppで悪化。正常designの改善結論は確定不可。 |
| 13 | QUALITY / BALANCEDのHigh中央値は1.719 / 1.619%、retention中央値92.96 / 90.96%、Entry delay中央値6 / 4 active min。>=5 CaptureはIMMEDIATE87.25%、R1 69.85%を下回る。確認待ちとno-entryによるWinner損失があり、品質確定には至らない。 |
| 14 | 確定不可。State comparisonは診断値だけで、正式採用なし。 |
| 15 | P0_Q80（診断ranking、lineage BLOCK） |
| 16 | P1_Q70（診断ranking、lineage BLOCK） |
| 17 | 異なる。 |
| 18 | teacher calendarの実装ミスを修正したが、20 head fitsのtraining eligibilityが一致しない。所定designの修復は合計50 fitsでhard cap36を超えるため、追加fit0でintegrity STOP。品質確定・candidate Freeze・State正式採用・EXIT研究への移行は行わず、生成済みFIRST ENTRYと修正Evaluatorを診断用に保持する。 |
| 19 | teacher calendarの実装ミスによる20 head fitsのtraining eligibility不一致。修復後再fitには合計50 fits必要でcap36を超える。 |
| 20 | EXIT policy／R50 adapter／EXIT Replay／Re-entry／2回目Entry／Capital Replayを一度も実行していない。orders=0、main merge=0。 |

FIRST ENTRY→EXIT→watchlist再開→Re-entryという将来工程は今回の結果へ混ぜていない。このWorkからEXIT研究へは渡さない。corrected teacherに整合するモデルが別の明示的budgetで完成し監査を通った場合にだけFIRST ENTRY candidateのFreeze候補化を検討できる。North Star約+3%/sessionからteacher・threshold・candidateを逆算していない。

常に executionAllowed=false、brokerWriteAllowed=false、excelOrderWriteAllowed=false、rssOrderFunctionAllowed=false、liveTradingAllowed=false、paperTradingAllowed=false、automaticPromotionAllowed=false、productionUpdateAllowed=false、transmitted=false、productionReady=false。LONG-only／cash-equity-only、Selector変更0、EXIT設計0、Capital変更0。
