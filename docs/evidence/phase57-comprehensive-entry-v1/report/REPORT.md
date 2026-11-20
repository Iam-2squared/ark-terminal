# Comprehensive LONG Entry Intelligence — bounded Development result

**判定: COMPREHENSIVE_LONG_ENTRY_DEVELOPMENT_LIMIT_REACHED / 新EntryはFreezeしない。**

この判定は、事前固定した2モデルと共有BUY/WAIT教師設計・利用可能な保存済みsubstrateに限定する。Entry研究全体やPIT情報全体の不可能性を証明していない。既存Frozen Opportunity Generatorを保持。Fresh/OOS、EXIT変更、Capitalへ進まずSTOP。

Protocol commit: `862f851d1895ced65fa508292fc6f4554b50935f`。開始HEAD: `175c96b195c955afa927f9cd0caf588bc638525b`。

## Lineage / population

`FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75` → `phase57-new-long-entry-two-opportunity-v1` → 新しい独立counterfactual Entry episode。

EXITは `NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1` を無変更で呼び出す。BUY_NOWは研究上の価格参照でありbroker fillではない。INITIAL/DIPを別episodeで診断し、合計資本成績とはしない。

| Partition | sessions | Opportunities | date range |
| --- | --- | --- | --- |
| DEVELOPMENT_TEST | 19 | 885 | 2024-12-10 … 2025-01-09 |
| TRAIN | 38 | 1760 | 2024-09-17 … 2024-11-12 |
| VALIDATION | 19 | 863 | 2024-11-13 … 2024-12-09 |

全体3,508 = INITIAL 2,841 + DIP 667。TRAIN: 1,760件中633 complete episodes / 4,431 correlated state rows。1episode内のstate weight合計1。独立サンプルが4,431あるという主張はしない。VALIDATION: 863件中common60評価可能336。DEV TEST 885件は今回新たに評価していない。76 sessions自体は過去研究ですでにexposed。

## PIT inventory

| Status | Count |
| --- | --- |
| AVAILABLE_PIT | 16 |
| DERIVABLE_PIT | 27 |
| FUTURE_ONLY_FORBIDDEN | 8 |
| MISSING | 15 |

合計66項目。承認43特徴 = Selector/time 10、price15 + path12、legacy context6。正確な名前・算式・coverageは feature-inventory.csv / train-diagnostics.json。旧anchorの一致は2,484/3,508 opportunities。旧featureはanchor時点のcontextであり、DIP/WAIT時点に更新された指標ではない。

MISSINGは現在の全母集団にidentity整合で接続できる保存substrateがないことを意味し、Repoのどこにも存在しないという主張ではない。全銘柄のvolume/sector/market系列を新取得していない。欠測はTRAIN medianとmissing indicatorで表現。reference/missing prefixはfail-closed。

## TRAIN family diagnostics

| Family累積 | features | BUY MAE | WAIT MAE | BUY RMSE | WAIT RMSE |
| --- | --- | --- | --- | --- | --- |
| BASE | 10 | 2.3130 | 0.9142 | 3.3390 | 1.4822 |
| LEGACY | 43 | 2.4450 | 1.0254 | 3.4596 | 1.5653 |
| PATH | 37 | 2.3211 | 0.9430 | 3.3158 | 1.4811 |
| PRICE | 25 | 2.2946 | 0.9280 | 3.2888 | 1.4725 |

最初26 TRAIN sessions fit / 次12 TRAIN sessions診断。Validationを見たfeature選択なし。全43特徴を両候補へ事前指定通り投入。情報群追加の安定した増分価値は今回示せなかった。

## TRAIN paired wait diagnostic（採用候補ではない）

| Delay | paired n | 価格改善mean | common-end MAE median | strict30 MAE median | +3 preserved/base | +5 preserved/base |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 633 | 0.0000 | -1.8182 | -1.2048 | 151/151 | 60/60 |
| 5 | 633 | -0.0717 | -1.7128 | -1.2579 | 104/151 | 48/60 |
| 10 | 633 | -0.0931 | -1.6447 | -1.3423 | 92/151 | 39/60 |
| 15 | 633 | -0.0500 | -1.5625 | -1.2048 | 83/151 | 28/60 |
| 20 | 633 | 0.0281 | -1.2813 | -1.1067 | 72/151 | 22/60 |
| 30 | 633 | 0.0879 | -1.1364 | -1.1364 | 47/151 | 15/60 |

common-endは待つほど保有可能時間が短くなる。MAE改善には時間短縮効果が含まれるのでstrict30も併記。元のtrain-location-study.jsonのoffset別nは異なるため、そのraw hit count比をpaired preservationとして使わない。Oracle最良OPENは改善余地の上限で、decisionには使わない。

## Candidate lineage / KEEP-KILL

| Candidate | architecture | Status | reason |
| --- | --- | --- | --- |
| LINEAR | Ridge alpha10 / 2 utility outputs | KILL | Coverageと+3/+5 preservation壊滅 |
| TREE | depth3 / min_leaf100 / seed57 | KILL | Validation ENTER 0、winnerを全て捨てる |

KEEP: 固定上流、PIT prefix projection、欠測明示、3状態ledger、paired preservationを必須にする評価。KILL: 今回の2モデル。係数・木・scalerを失敗再現用に保存し、active Entryへ昇格しない。

## Validation outcome

| Metric | LINEAR | TREE |
| --- | --- | --- |
| all emitted | 863 | 863 |
| counterfactual ENTER all | 24 | 0 |
| complete baseline | 336 | 336 |
| complete entered | 17 | 0 |
| entry coverage | 0.0506 | 0.0000 |
| delay median min | 30.0000 | — |
| paired price improvement mean | 1.5081 | — |
| paired price improvement median | 0.8863 | — |
| +3 remaining preservation | 0.0128 | 0.0000 |
| +5 remaining preservation | 0.0312 | 0.0000 |

### LINEAR

| source | complete n | ENTER complete | +3 preserved/base | +5 preserved/base |
| --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 77 | 7 | 0/16 | 0/5 |
| INITIAL_ENTRY_OPPORTUNITY | 259 | 10 | 1/62 | 1/27 |

| Economic arm | n | mean net % | median | PF | p05 | Win fraction |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 334 | -0.0562 | -0.1172 | 0.9456 | -4.5626 | 0.4491 |
| candidateCashIncluded | 334 | 0.0241 | 0.0000 | 3.4706 | 0.0000 | 0.0359 |
| executedOnlyBaseline | 15 | -1.3748 | -0.8444 | 0.1487 | -4.7003 | 0.3333 |
| executedOnlyCandidate | 15 | 0.5361 | 0.8735 | 3.4706 | -1.0845 | 0.8000 |

Cash includedは見送りを0配分とした機会単位比較。未観測trade returnを0補完していない。各候補でeconomic evaluable denominatorは別（LINEAR 334 / TREE 336）。この差を隠して候補winnerを選ばない。全てKILL。

| Risk/Upside entered pair | baseline | candidate |
| --- | --- | --- |
| common MAE median | -2.3041 | -0.9461 |
| common MAE p05 | -6.7491 | -2.2441 |
| strict30 MAE median | -2.3041 | -0.9461 |
| strict30 MAE p05 | -5.9243 | -2.2441 |
| MFE median | 1.1111 | 1.2299 |

| tail | baseline all | baseline entered pair | candidate entered |
| --- | --- | --- | --- |
| 10 | 3 | 0 | 0 |
| 3 | 78 | 6 | 0 |
| 5 | 36 | 3 | 0 |

| Class | n | decision outcomes |
| --- | --- | --- |
| CHOP_THEN_WINNER | 1 | {"EXPIRE_WAIT_CAP": 1} |
| CONTINUED_FAILURE | 70 | {"COUNTERFACTUAL_ENTER": 6, "EXPIRE_WAIT_CAP": 64} |
| DEEP_PULLBACK_THEN_WINNER | 5 | {"EXPIRE_WAIT_CAP": 5} |
| IMMEDIATE_WINNER | 14 | {"EXPIRE_WAIT_CAP": 14} |
| INCONCLUSIVE | 533 | {"COUNTERFACTUAL_ENTER": 7, "EXPIRE_BOUNDARY": 83, "EXPIRE_MISSING_OPEN": 1, "EXPIRE_MISSING_PREFIX": 144, "EXPIRE_REFERENCE": 196, "EXPIRE_WAIT_CAP": 102} |
| OPPORTUNITY_EXPIRED | 188 | {"COUNTERFACTUAL_ENTER": 10, "EXPIRE_WAIT_CAP": 178} |
| PULLBACK_THEN_WINNER | 52 | {"COUNTERFACTUAL_ENTER": 1, "EXPIRE_WAIT_CAP": 51} |

| Gate | PASS |
| --- | --- |
| PF | True |
| chronological | True |
| cohorts | False |
| coverage | False |
| deep5 | True |
| maeMedian | True |
| maeP05 | True |
| meanNet | True |
| netP05 | True |
| plus3 | False |
| plus5 | False |
| price | True |
| sample | True |
| top3Exclusion | True |

| Chronological validation block | n | net delta |
| --- | --- | --- |
| 1 | 98 | 0.2547 |
| 2 | 80 | 0.0123 |
| 3 | 97 | 0.1144 |
| 4 | 61 | -0.1617 |

Top3 exclusion ['45830', '260A0', '265A0']: net delta 0.0996pp。symbol HHI 0.0040。

session別はaudit-appendix、breadth/source/morning-afternoon別はsummaryに固定。これらを見た個別rule作成なし。

### TREE

| source | complete n | ENTER complete | +3 preserved/base | +5 preserved/base |
| --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 77 | 0 | 0/16 | 0/5 |
| INITIAL_ENTRY_OPPORTUNITY | 259 | 0 | 0/62 | 0/27 |

| Economic arm | n | mean net % | median | PF | p05 | Win fraction |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 336 | -0.0721 | -0.1417 | 0.9308 | -4.6984 | 0.4464 |
| candidateCashIncluded | 336 | 0 | 0.0000 | — | 0.0000 | 0.0000 |
| executedOnlyBaseline | 0 | — | — | — | — | — |
| executedOnlyCandidate | 0 | — | — | — | — | — |

Cash includedは見送りを0配分とした機会単位比較。未観測trade returnを0補完していない。各候補でeconomic evaluable denominatorは別（LINEAR 334 / TREE 336）。この差を隠して候補winnerを選ばない。全てKILL。

| Risk/Upside entered pair | baseline | candidate |
| --- | --- | --- |
| common MAE median | — | — |
| common MAE p05 | — | — |
| strict30 MAE median | — | — |
| strict30 MAE p05 | — | — |
| MFE median | — | — |

| tail | baseline all | baseline entered pair | candidate entered |
| --- | --- | --- | --- |
| 10 | 3 | 0 | 0 |
| 3 | 78 | 0 | 0 |
| 5 | 36 | 0 | 0 |

| Class | n | decision outcomes |
| --- | --- | --- |
| CHOP_THEN_WINNER | 1 | {"EXPIRE_WAIT_CAP": 1} |
| CONTINUED_FAILURE | 70 | {"EXPIRE_WAIT_CAP": 70} |
| DEEP_PULLBACK_THEN_WINNER | 5 | {"EXPIRE_WAIT_CAP": 5} |
| IMMEDIATE_WINNER | 14 | {"EXPIRE_WAIT_CAP": 14} |
| INCONCLUSIVE | 533 | {"EXPIRE_BOUNDARY": 83, "EXPIRE_MISSING_PREFIX": 148, "EXPIRE_REFERENCE": 196, "EXPIRE_WAIT_CAP": 106} |
| OPPORTUNITY_EXPIRED | 188 | {"EXPIRE_WAIT_CAP": 188} |
| PULLBACK_THEN_WINNER | 52 | {"EXPIRE_WAIT_CAP": 52} |

| Gate | PASS |
| --- | --- |
| PF | False |
| chronological | False |
| cohorts | False |
| coverage | False |
| deep5 | True |
| maeMedian | False |
| maeP05 | False |
| meanNet | True |
| netP05 | True |
| plus3 | False |
| plus5 | False |
| price | False |
| sample | True |
| top3Exclusion | True |

| Chronological validation block | n | net delta |
| --- | --- | --- |
| 1 | 98 | 0.2323 |
| 2 | 80 | -0.0064 |
| 3 | 97 | 0.1218 |
| 4 | 61 | -0.1617 |

Top3 exclusion ['45830', '260A0', '265A0']: net delta 0.0941pp。symbol HHI 0.0040。

session別はaudit-appendix、breadth/source/morning-afternoon別はsummaryに固定。これらを見た個別rule作成なし。

## Interpretation / important limits

- 少数の遅いEntryでは価格・MAE改善が見られるが、winnerを大量に失った。17件だけの良い数字をEntry完成と扱わない。
- WAIT教師は将来のbest utilityという楽観的な上限。BUYと対等な実行可能継続価値ではなく、WAITを過大評価してexpiryへ偏らせ得る。これはshared objectiveの失敗でもあり、2モデルの失敗だけからPIT情報限界を一般化しない。
- Opportunity分類のCHOP/IMMEDIATEの文章上の優先度には曖昧さがある。保存コードは「prior negative LOWがないbranch内でCHOP判定後にIMMEDIATE」。分類は説明用のみでmodel feature/gateには未使用。既存測定を書き換えて件数を整えない。
- 同一5分barのHIGH/LOW順序は不明。adverseとfirst winnerが同一barのみならINCONCLUSIVE。到達時刻はhit bar終端の上限。
- training coverage633/1760、validation336/863。session end・reference欠測・path欠測があるため、全3,508への有効性は認定できない。
- 指定のvolatility別/missingness感度の十分な最終候補監査まで進めるsurvivorがない。固定subgroup集計は保存したが、Strong Candidate robustness PASSは主張しない。
- 今回のbounded budgetは消化。次に検討するなら、WAITの実行可能continuation targetと完全なPIT snapshot coverageを別契約で設計する必要がある。今回それらを後付け変更してvalidationへ再適合しない。

## Audit / STOP

SOURCE pinsとFrozen artifactsは不変。signalはcompleted prefixだけ、BUY referenceは次regular OPEN。Candidate Aはlater-bar signal→next OPEN、無signalはexact Fixed12。各Opportunityのdecisionは一度のみterminal。現物LONGのみ。Safety全9項目false。Fresh/OOS未開封。内部DEV TESTも新たなcandidate測定なし。

tests / deterministic regeneration / GitHub CIの正確なHEADとrun identityは final-ci-receipt.json に記録。CI成功はperformance PASSではない。

**DO_NOT_FREEZE。既存Opportunity Generatorをfallback保持し、この研究をSTOP。**
