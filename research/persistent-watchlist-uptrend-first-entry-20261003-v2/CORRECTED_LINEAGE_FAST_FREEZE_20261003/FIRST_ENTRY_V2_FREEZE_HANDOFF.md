# FIRST ENTRY v2 — P1_Q70 Official Freeze

正式status: **PERSISTENT_UPTREND_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE**。`EntryFrozen=true`、`productionReady=false`。

Work: `WORK_FIRST_ENTRY_V2_CORRECTED_LINEAGE_FAST_FREEZE_20261003`。actual saved_at_jst: `2026-10-03T15:09:21.658449+09:00`。actual basis_head: `31477bdc1b5972a57b0a7c814e5a8b59de27818c`。

Primaryは結果を見る前に固定したP1_Q70。P0はState9なしcontrol、Q80/Q90/Q95は既存selectivity referenceとして保持した。再選択・Entry/day調整・State incremental研究の再開は0。旧WorkのBLOCKと旧30 fitsは履歴として保持し、今回のcorrected-lineage Workで修復した。

calendar bugのexact root causeは、`source_starts`がAM continuous → PM continuous → AM terminal690の順になり、unsorted arrayとのchronology比較で正常なAM→PM pathをmissingと誤判定したこと。修復は`sorted(regular_starts(day)+[690,close_minute(day)])`のみ。133 sessionでscheduled source bar集合・個数の一致を独立確認した。

| 修復・lineage | 結果 |
|---|---:|
| teacher定義変更 | 0 |
| Q NULL→known | 13,948 |
| D NULL→known | 13,948 |
| 元finite Q/Dの値変更 | 各0 |
| U target / training mask変更 | 0 |
| P0 QUALITY / ADVERSE | 各5 fits完了 |
| P1 QUALITY / ADVERSE | 各5 fits完了 |
| 今回追加fit | 20/20 |
| historical / cumulative | 30 / 50 |
| UPSIDE追加fit | 0 |
| UPSIDE既存fit reuse | 10 |
| audit fit | 0 |
| 独立監査 mismatch / future leakage | 0 / 0 |
| Legacy State feature | 0 |

20 fitsだけでよい理由は、calendar bugがQ/Dのpath-completeness eligibilityだけに影響したため。2 families ×2 affected heads ×5 folds =20。U target・training maskは全行不変で、既存10モデル・preprocessor・training prediction referenceのSHA、2本のUPSIDE OOFファイルのbyte SHA、全OOF U prediction / percentileの一致を確認した。証明は[corrected teacher receipt](CORRECTED_TEACHER_FREEZE_RECEIPT.json)、[fit ledger](CORRECTED_FIT_LEDGER.json)、[OOF lineage receipt](CORRECTED_OOF_LINEAGE_RECEIPT.json)に保存した。

P1はP0 price/volume/path/Selector context + exact latest frozen RC2 State9 current +同じRC2のpast-only history。RC2 contract SHA `45859122a62ccdc946b31bb5709f3fc080ea4a4f935958afd8f1ca895f75b6ff`、profile SHA `77ee61ba1808a2c17614439fe7d14212a53cbfa7358c032ce16989eeb5248922`、Path SHA `fc3808cb7d3d161e85527d7ebf97f902df7f0c3463457beddf1a25d053cee268`。110 P0 numeric /148 P1 numeric /15 P1 categoricalをそのまま使用し、Legacy Stateは0。

独立監査は13,787,979 checks、grid/teacher各462,752行、FIRST ENTRY records 17,240件を検査した。Stateの別kernel確認は事前固定51-watch sample /4,245行、model direct predictionは7,680 samples。percentile・threshold・train-only preprocessingは全対象行を確認。

| P1_Q70 Activity / Entry単体品質 | 値 | evaluable N |
|---|---:|---:|
| FIRST ENTRY / watch | 1,600 / 2,155 | 58 sessions |
| 平均 / 中央値Entry per session | 27.586207 / 27 | 58 |
| Entry rate | 74.245940% | 2,155 |
| 0 Entry sessions | 0 | 58 |
| Selector→Entry delay中央値 | 5 active min | 1,600 |
| Entry→strictly-later High中央値 | 1.549225% | 1595 |
| Upside Retention中央値 | 89.515394% | 1448 |
| Pre-peak MAE中央値 | 0.517031% | 317 |
| Path Efficiency中央値 | 0.205770 | 317 |

MAE / Path Efficiencyはcomplete pre-peak path 317件だけの中央値。path unknown 1283件、strictly-later High unknown 5件を分離し、補間していない。保存sourceがpartialなEntry→Highはobserved Highまでの値幅であり、完全session Highに対する下限となり得る。Retentionはpositiveなsaved first-selector future MFEを分母とする。これらの性能値はFreeze最適化Gateに使用していない。

| Selector→High exclusive bucket | watch N | Entry N | Entry→High中央値 |
|---|---:|---:|---:|
| 1–<2% | 442 | 315 | 1.090139% |
| 2–<3% | 293 | 216 | 2.096607% |
| 3–<4% | 217 | 161 | 2.912970% |
| 4–<5% | 136 | 113 | 4.017759% |
| >=5% | 408 | 307 | 6.923283% |


Selector→High bucketはfuture evaluatorの分類で、Entry decision featureではない。

| 累積Selector winner | denominator | Entry | no-entry | confirmed same-threshold hit | unknown | Capture参考 |
|---|---:|---:|---:|---:|---:|---:|
| >=1% | 1496 | 1112 | 384 | 886 | 215 | 59.224599% |
| >=2% | 1054 | 797 | 257 | 616 | 164 | 58.444023% |
| >=3% | 761 | 581 | 180 | 426 | 140 | 55.978975% |
| >=4% | 544 | 420 | 124 | 306 | 100 | 56.250000% |
| >=5% | 408 | 307 | 101 | 226 | 69 | 55.392157% |


Captureはconfirmed same-threshold hit / all Selector winner denominator。no-entry / unknownをdenominatorから除外していない。参考値として保存し、policyを再選択していない。

Frozen state machine: first valid Selector → same-session persistent watch → observed closed1mごとP1 score → Q70最初のcross → BUY_INTENT → canonical next available regular raw open +5bps → FIRST ENTRY → このWorkではwatch評価終了。WATCH_KEY=session|symbol、repeat Selectorはrefresh、30分expiryなし、lunchはactive clockに加えない、FIRST ENTRY後decision停止。

監査準備時にP1 subset gzipの不完全な保存を検出し、完全なcorrected Q70 recordsから同一2,155 recordsをatomicに保存して内容一致を確認した。また監査のhistorical ledgerとactive-model ledgerの比較条件を分離した。teacher・features・モデル・score・threshold・record値の変更は0、追加fitは0。[serialization receipt](RECORDS_SERIALIZATION_RECEIPT.json)、[audit checker receipt](AUDIT_CHECKER_LINEAGE_VIEW_RECEIPT.json)に記録した。

OFFICIAL FREEZEの10 integrity gatesは全PASS。**PERSISTENT_UPTREND_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZEに到達した。** [formal Freeze receipt](FIRST_ENTRY_V2_FREEZE_RECEIPT.json)と[independent audit](INDEPENDENT_REPAIR_AUDIT.json)が正式Evidence。

EXIT / R50 / Re-entry / Capital / Portfolio Replay / provider / Protected-Fresh-Validation-OOS-Prospective open / orders / main mergeはすべて0。MAE p75/p90/p95、hard-stop、-1% Risk Line、bootstrap、全searchも0。executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed / liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed / transmitted / productionReadyはすべてfalse。

Entry研究はここで閉じてSTOP。EXIT_PENDING=true、REENTRY_PENDING=true、CAPITAL_PENDING=true。次の別WorkはState-aware EXIT。Pre-peak MAE中央値はFrozen Entry Evidenceとして引き継ぐ。今回のWorkからEXIT / Re-entry / Capitalへ自動進行していない。
