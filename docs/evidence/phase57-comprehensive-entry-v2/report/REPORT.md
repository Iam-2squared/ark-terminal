# Comprehensive LONG Entry Intelligence v2 — one-step sequential research

**COMPREHENSIVE_LONG_ENTRY_V2_DEVELOPMENT_LIMIT_REACHED / DO_NOT_FREEZE**

事前固定した3 architectureを終了。全候補KILL。既存Frozen Opportunity Generatorをfallback保持する。新Entryの完成・利益化・PIT情報全体の不可能性は主張しない。

開始HEAD `adbdf457bca863f4615521ec791b16e1cc007930`。Protocol commit `5b857b6a86d20aacfff4a15732ef9e898eafdb32`。最終exact HEAD・CI identityは final-ci-receipt.json。

## Frozen lineage / exposure

`FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75` → `phase57-new-long-entry-two-opportunity-v1`。Selector、¥75 policy、Opportunity Generator、Candidate A `NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1` は無変更。v1 Evidenceも無変更。

| Partition | sessions | opportunities | dates |
| --- | --- | --- | --- |
| TRAIN | 38 | 1760 | 2024-09-17 … 2024-11-12 |
| VALIDATION | 19 | 863 | 2024-11-13 … 2024-12-09 |
| DEVELOPMENT_TEST | 19 | 885 | 2024-12-10 … 2025-01-09 |

全3,508 = INITIAL2,841 + DIP667。TRAIN complete common60=633 episodes / 4,431 states、WAIT head=3,798 one-step transitions。VALIDATION863中336 complete (INITIAL259 / DIP77)。内部DEV TEST19sessions/885件はv1/v2候補評価に未使用。以前の一般診断では76sessionsすべてexposedでありFresh扱いしない。

## v1 teacher → v2 objective

v1はfuture-best-entryのmax価値をWAIT教師に使い、BUYより楽観的なWAIT→EXPIREに偏った。v2は現在OPENと厳密に5分後のOPENの差だけを教師にする。未来値はTRAIN label/evaluatorだけに使用。

- U(now) = common-end close return − 0.05pp cost + 0.25×MAE。
- WAIT advantage = U(next OPEN) − U(now) − 0.05pp delay cost − lost-threshold penalty − 1pp fast-winner chase penalty。
- SKIP advantage = −U(now) − missed-opportunity penalty − 1pp FAST_WINNER penalty。
- +1/+2/+3/+5のpenaltyは0.25/0.5/2/3ppに事前固定。結果を見たweight調整なし。
- BUY advantage=0。WAIT/SKIPと比較し、同点はBUY→WAIT→SKIP。上限30分・session境界ではWAITをmask。
- FAST_WINNERはfirst5m HIGH>=1%かつcommon60 MFE>=3%のevaluator label。第三候補のguardはPIT特徴から予測した確率>=0.5のみでBUYを優先。future labelで直接guardしない。

これはone-step delayed-purchase surrogateを毎5分再評価する設計であり、最適な多段階continuation valueを学習できたという主張ではない。

## Models / fixed gates

同じ43 PIT特徴（欠測indicator込み86入力）。TRAINだけでmedian/scaler/modelをfit。S1はWAIT/SKIPのRidge alpha10、S2はdepth3/min_leaf100の木2本、S3はS1固定＋LogisticRegression C1のguard。合計5 fits。feature追加、hyperparameter sweepなし。

TRAIN catastrophic gate: ENTER/+3/+5各50%以上。Validation: ENTER70%、+1 80%、+2 85%、+3/+5 90%、Immediate/Fast winner90%、価格mean改善0.10pp、strict30 MAE median0.10pp/p05 0.25pp改善、deep5削減10%ほか。Contract全文にcohort/chronological/concentration条件を固定。

| Candidate | status | TRAIN entry coverage % | Validation evaluated |
| --- | --- | --- | --- |
| S1_LINEAR | KILL_ENTRY_GATE | 57.1880 | True |
| S2_TREE | KILL_TRAIN_ABSTENTION_OR_WINNER_LOSS | 9.6367 | False |
| S3_GUARDED_LINEAR | KILL_ENTRY_GATE | 57.3460 | True |

## Validation B0/B1/B2/v2

| Policy | ENTER all863 | ENTER complete336 | coverage % | +1 % | +2 % | +3 % | +5 % | price improvement mean % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0_IMMEDIATE | 667 | 336 | 100.0000 | 100.0000 | 100.0000 | 100.0000 | 100.0000 | 0.0000 |
| B1_FIXED_WAIT_1 | 607 | 336 | 100.0000 | 78.8991 | 76.3359 | 76.9231 | 84.3750 | -0.0230 |
| B2_V1_LINEAR | 24 | 17 | 5.0595 | 2.2936 | 1.5267 | 1.2821 | 3.1250 | 1.5081 |
| B2_V1_TREE | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | — |
| S1_LINEAR | 291 | 197 | 58.6310 | 62.3853 | 68.7023 | 74.3590 | 81.2500 | 0.0000 |
| S3_GUARDED_LINEAR | 292 | 197 | 58.6310 | 62.3853 | 68.7023 | 74.3590 | 81.2500 | 0.0000 |

B2は既存v1 ledgerのdecisionをそのまま再利用し、モデルを再学習していない。B1は診断のみで採用候補にしない。

## Main result / KEEP-KILL

**v1のほぼ全abstentionは線形系で緩和したが、v2の全候補はWAITを一度も選ばず、即BUYまたは即SKIPへ退化した。** S1 Validation291 ENTER、S3は292 ENTER。ただし完全paired336では両方197 ENTER。同一197件のEntry価格・MAEはB0と完全同じであり、timing/location改善はない。

Guardによる差はValidationのcommon60不完全な1件だけ。完全pairedでincremental valueなし。S2はTRAIN633中61 ENTER=9.64%でKILLし、Validationを評価していない。

- KEEP: 一歩先のteacherとoracle-maxの分離、WAIT期限でのaction mask、PIT projection、missing fail-closed、winner-preservation gate。
- KILL: 3 policy architectures。threshold/weight/guard probabilityを調整して救済しない。
- deep tail件数が減っても、単なるSKIPによる件数減と、同じtradeのEntry Location改善を区別。後者は線形系で0。

## S1_LINEAR

| Source | complete n | ENTER | +3 preserved/base | +5 preserved/base |
| --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 77 | 30 | 9/16 | 3/5 |
| INITIAL_ENTRY_OPPORTUNITY | 259 | 167 | 49/62 | 23/27 |

| Class | n | ENTER | remaining+3 | remaining+3 % | price mean | baseline strict30 MAE median | entry strict30 MAE median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CONTINUED_FAILURE | 70 | 38 | 0 | 0.0000 | 0.0000 | -3.6608 | -3.6608 |
| DEEP_PULLBACK_THEN_WINNER | 5 | 4 | 4 | 80.0000 | 0.0000 | -4.4782 | -4.4782 |
| FAST_WINNER | 41 | 32 | 32 | 78.0488 | 0.0000 | -0.6696 | -0.6696 |
| IMMEDIATE_WINNER | 14 | 9 | 9 | 64.2857 | 0.0000 | 0.0000 | 0.0000 |
| PULLBACK_WINNER | 57 | 43 | 43 | 75.4386 | 0.0000 | -1.5670 | -1.5670 |

CONTINUED_FAILUREのremaining+3欄は定義上0であり、quality preservation指標として解釈しない。failureへのENTER38/70、SKIP32/70。代わりにImmediate winner5/14、FAST winner9/41、Pullback winner14/57を喪失。

| Action outcome | count | all-emitted % |
| --- | --- | --- |
| COUNTERFACTUAL_ENTER | 291 | 33.7196 |
| EXPIRE_REFERENCE | 196 | 22.7115 |
| MODEL_SKIP | 376 | 43.5689 |

| Delay minutes / no entry | n |
| --- | --- |
| 0 | 291 |
| EXPIRE_OR_SKIP | 572 |

WAIT transitions=0。Entry delay mean/median=0/0.0000min。価格改善 mean/median/p25/p75=0.0000/0.0000/0.0000/0.0000%。favorable/worse rate=0.0000/0.0000。

| Risk/Upside | n | mean | median | p10 | p05 | worst(min) |
| --- | --- | --- | --- | --- | --- | --- |
| baselineCommonMAE | 336 | -2.1204 | -1.4867 | -5.0920 | -6.3491 | -14.3012 |
| baselinePairedMAE | 197 | -2.1333 | -1.5551 | -4.9697 | -6.0315 | -14.3012 |
| entryPairedMAE | 197 | -2.1333 | -1.5551 | -4.9697 | -6.0315 | -14.3012 |
| baselineStrict30MAE | 197 | -1.7931 | -1.2987 | -4.0902 | -4.9602 | -11.7010 |
| entryStrict30MAE | 197 | -1.7931 | -1.2987 | -4.0902 | -4.9602 | -11.7010 |
| baselinePairedMFE | 197 | 2.7263 | 1.7637 | 0.4153 | 0.0000 | 0 |
| entryPairedMFE | 197 | 2.7263 | 1.7637 | 0.4153 | 0.0000 | 0 |

| tail | baseline all | baseline entered pair | entry pair | strict30 baseline pair | strict30 entry pair |
| --- | --- | --- | --- | --- | --- |
| 10 | 3 | 2 | 2 | 1 | 1 |
| 3 | 78 | 45 | 45 | 36 | 36 |
| 5 | 36 | 20 | 20 | 10 | 10 |

| Gate | PASS |
| --- | --- |
| FAST_WINNER | False |
| IMMEDIATE_WINNER | False |
| chronological | False |
| cohorts | False |
| coverage | False |
| deep5 | True |
| preserve1 | False |
| preserve2 | False |
| preserve3 | False |
| preserve5 | False |
| price | False |
| pullback | False |
| remainingMFE | True |
| sample | True |
| strict30Median | False |
| strict30P05 | False |
| top3Exclusion | False |

| Chronological block | complete n | coverage % | +3 % | +5 % | price mean |
| --- | --- | --- | --- | --- | --- |
| 1 | 98 | 73.4694 | 85.7143 | 90.0000 | 0.0000 |
| 2 | 80 | 58.7500 | 72.0000 | 71.4286 | 0.0000 |
| 3 | 97 | 55.6701 | 75.0000 | 100.0000 | 0.0000 |
| 4 | 61 | 39.3443 | 58.3333 | 75.0000 | 0.0000 |

TRAIN頻度top3固定除外=['25860', '48830', '190A0']。symbol HHI=0.0040、session HHI=0.0530。除外後gateもFAIL。

| Breadth | complete n | coverage % | +3 % | +5 % |
| --- | --- | --- | --- | --- |
| 1 | 22 | 50.0000 | 66.6667 | 0.0000 |
| 2 | 30 | 43.3333 | 66.6667 | 50.0000 |
| 3 | 62 | 51.6129 | 72.2222 | 88.8889 |
| 4 | 75 | 56.0000 | 68.7500 | 100.0000 |
| 5 | 147 | 67.3469 | 80.0000 | 76.9231 |

session別・anchor context欠測別・全minute観測別はsummaryに保存。subgroupでのrule追加なし。

## S3_GUARDED_LINEAR

| Source | complete n | ENTER | +3 preserved/base | +5 preserved/base |
| --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 77 | 30 | 9/16 | 3/5 |
| INITIAL_ENTRY_OPPORTUNITY | 259 | 167 | 49/62 | 23/27 |

| Class | n | ENTER | remaining+3 | remaining+3 % | price mean | baseline strict30 MAE median | entry strict30 MAE median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CONTINUED_FAILURE | 70 | 38 | 0 | 0.0000 | 0.0000 | -3.6608 | -3.6608 |
| DEEP_PULLBACK_THEN_WINNER | 5 | 4 | 4 | 80.0000 | 0.0000 | -4.4782 | -4.4782 |
| FAST_WINNER | 41 | 32 | 32 | 78.0488 | 0.0000 | -0.6696 | -0.6696 |
| IMMEDIATE_WINNER | 14 | 9 | 9 | 64.2857 | 0.0000 | 0.0000 | 0.0000 |
| PULLBACK_WINNER | 57 | 43 | 43 | 75.4386 | 0.0000 | -1.5670 | -1.5670 |

CONTINUED_FAILUREのremaining+3欄は定義上0であり、quality preservation指標として解釈しない。failureへのENTER38/70、SKIP32/70。代わりにImmediate winner5/14、FAST winner9/41、Pullback winner14/57を喪失。

| Action outcome | count | all-emitted % |
| --- | --- | --- |
| COUNTERFACTUAL_ENTER | 292 | 33.8355 |
| EXPIRE_REFERENCE | 196 | 22.7115 |
| MODEL_SKIP | 375 | 43.4531 |

| Delay minutes / no entry | n |
| --- | --- |
| 0 | 292 |
| EXPIRE_OR_SKIP | 571 |

WAIT transitions=0。Entry delay mean/median=0/0.0000min。価格改善 mean/median/p25/p75=0.0000/0.0000/0.0000/0.0000%。favorable/worse rate=0.0000/0.0000。

| Risk/Upside | n | mean | median | p10 | p05 | worst(min) |
| --- | --- | --- | --- | --- | --- | --- |
| baselineCommonMAE | 336 | -2.1204 | -1.4867 | -5.0920 | -6.3491 | -14.3012 |
| baselinePairedMAE | 197 | -2.1333 | -1.5551 | -4.9697 | -6.0315 | -14.3012 |
| entryPairedMAE | 197 | -2.1333 | -1.5551 | -4.9697 | -6.0315 | -14.3012 |
| baselineStrict30MAE | 197 | -1.7931 | -1.2987 | -4.0902 | -4.9602 | -11.7010 |
| entryStrict30MAE | 197 | -1.7931 | -1.2987 | -4.0902 | -4.9602 | -11.7010 |
| baselinePairedMFE | 197 | 2.7263 | 1.7637 | 0.4153 | 0.0000 | 0 |
| entryPairedMFE | 197 | 2.7263 | 1.7637 | 0.4153 | 0.0000 | 0 |

| tail | baseline all | baseline entered pair | entry pair | strict30 baseline pair | strict30 entry pair |
| --- | --- | --- | --- | --- | --- |
| 10 | 3 | 2 | 2 | 1 | 1 |
| 3 | 78 | 45 | 45 | 36 | 36 |
| 5 | 36 | 20 | 20 | 10 | 10 |

| Gate | PASS |
| --- | --- |
| FAST_WINNER | False |
| IMMEDIATE_WINNER | False |
| chronological | False |
| cohorts | False |
| coverage | False |
| deep5 | True |
| preserve1 | False |
| preserve2 | False |
| preserve3 | False |
| preserve5 | False |
| price | False |
| pullback | False |
| remainingMFE | True |
| sample | True |
| strict30Median | False |
| strict30P05 | False |
| top3Exclusion | False |

| Chronological block | complete n | coverage % | +3 % | +5 % | price mean |
| --- | --- | --- | --- | --- | --- |
| 1 | 98 | 73.4694 | 85.7143 | 90.0000 | 0.0000 |
| 2 | 80 | 58.7500 | 72.0000 | 71.4286 | 0.0000 |
| 3 | 97 | 55.6701 | 75.0000 | 100.0000 | 0.0000 |
| 4 | 61 | 39.3443 | 58.3333 | 75.0000 | 0.0000 |

TRAIN頻度top3固定除外=['25860', '48830', '190A0']。symbol HHI=0.0040、session HHI=0.0530。除外後gateもFAIL。

| Breadth | complete n | coverage % | +3 % | +5 % |
| --- | --- | --- | --- | --- |
| 1 | 22 | 50.0000 | 66.6667 | 0.0000 |
| 2 | 30 | 43.3333 | 66.6667 | 50.0000 |
| 3 | 62 | 51.6129 | 72.2222 | 88.8889 |
| 4 | 75 | 56.0000 | 68.7500 | 100.0000 |
| 5 | 147 | 67.3469 | 80.0000 | 76.9231 |

session別・anchor context欠測別・全minute観測別はsummaryに保存。subgroupでのrule追加なし。

## Economics / DEV TEST

**Entry gate通過候補0。Candidate Aの新規economic pairingは実行0回、DEV TEST候補評価0回。** n/mean/PF/p05/Win/HOLDのv2経済結果はNOT_RUN_ENTRY_GATE_FAILED。ゼロ利益やPASSと置き換えない。v1経済比較は旧Evidenceとして保持し、v2成績へ転用しない。

## Model/source/deterministic audit

| Candidate | model SHA256 | wait scaler SHA256 | skip scaler SHA256 |
| --- | --- | --- | --- |
| S1_LINEAR | 1abf8e0241932b957f3e59f68884742cf248c599590321d3119ce498bc50dc3e | 8d23349c493f01890b113ccfc7407164bc077c822baad8dd7e398a6c4bfa4c15 | f2556ffbea96da0a3ef1590c7a3e67fb940b38eabe9da713f0e2be162c528e0f |
| S2_TREE | ca625ee39c4bdadc5ad5eaa66692aeb8eea034df621ca54d7f848a2bc8bda268 | 8d23349c493f01890b113ccfc7407164bc077c822baad8dd7e398a6c4bfa4c15 | f2556ffbea96da0a3ef1590c7a3e67fb940b38eabe9da713f0e2be162c528e0f |
| S3_GUARDED_LINEAR | b52d8299acb2e589c1635976aaf52e352deae4b45e80f8f16bbd5446521ab924 | 8d23349c493f01890b113ccfc7407164bc077c822baad8dd7e398a6c4bfa4c15 | f2556ffbea96da0a3ef1590c7a3e67fb940b38eabe9da713f0e2be162c528e0f |

| Policy | saved-model replay episodes | identity / causal / terminal audit |
| --- | --- | --- |
| S1_LINEAR | 2623 | PASS |
| S2_TREE | 1760 | PASS |
| S3_GUARDED_LINEAR | 2623 | PASS |

保存modelの係数/木/scalerから別実装でdecisionを再現。PIT特徴はcompleted prefixのみ。execution OPEN参照は未来HIGH/LOW/CLOSEを使用しない。one-step teacherはnow/next購入だけで、後続の最良Entry検索なし。未来outcomeはteacher/evaluatorに隔離。TRAIN-only fitting、同一inputのcanonical数値再生成。単一Opportunity内の重複ENTERとterminal後resurrectionなし。INITIAL/DIPの独立episode間で同じsymbol-sessionを再利用し得るため、実保有や再エントリー許可とはしない。

全9 safety flags=false、LONG-only cash equity。Frozen artifacts不変、既存Evidence上書きなし。Fresh/OOS未開封。Capital/Portfolio/main merge/Paper/Live/注文接続なし。tests・regression・CI artifact hashはfinal-ci-receiptに固定。CI greenはperformance PASSではない。

## Limitation and next information

3つの事前固定architectureと今回のone-step teacherでは、Immediateを安定改善できなかった。これは、同じ5m保存substrateからのEntry Timing全体が不可能という証明ではない。今回のモデルは初回時点でWAIT価値を発見できず、遅延stateを学習してもon-policyでそこへ到達しなかった。TRAINのoffset別教師/予測/action分布をaudit-appendixへ保存した。

次に進むなら、このone-step surrogateとon-policy到達stateの不一致、shared terminalのrisk/skip trade-off、PIT snapshot coverageを別研究契約で検討する必要がある。今回Validationに合わせてteacherやthresholdを作り直さない。

**COMPREHENSIVE_LONG_ENTRY_V2_DEVELOPMENT_LIMIT_REACHED。DO_NOT_FREEZE。既存Opportunity Generatorを保持しSTOP。**
