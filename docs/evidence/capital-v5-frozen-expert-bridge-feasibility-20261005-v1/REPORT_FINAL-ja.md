# Ark Terminal V5 Frozen Expert Bridge — 最終報告

文書ID: V5_EXPERT_BRIDGE_FEASIBILITY_V1_20261005 / 作成実時計: 2026-10-05T21:28:36.121657+09:00

総合判定: **EXPERT_BRIDGE_INCONCLUSIVE**。L1/L2保存・adapter監査はPASS。pP Winner、q2 Weak、q3 Medium+の設計候補screenは支持。独立した実現損失防御、Reserve専用条件と実fundabilityは未確立。新policyは固定せず、F9でSTOPする。

## A. 20-session V5基準と未実行candidate

| 指標 | 保存V5 | 新candidate |
|---|---:|---|
| min | ¥1,082,366 | 未実行 |
| mean | ¥1,190,646 | 未実行 |
| median | ¥1,199,154 | 未実行 |
| max | ¥1,297,031 | 未実行 |
| 2x / 全窓 | 0 / 19 | NOT_EVALUATED |
| Capital / Control Replay | 保存原本を再利用 | 0 / 0 |

連結38-session系列の、開始前EODを100万円へ正規化した対応20-session窓。各窓100万円・保有0へresetするReplayではない。評価session列を連続する全市場営業日とは仮定しない。厳密分子/分母は原V5 authorityを保持。North Starは100万円→200万円/20 sessions。24/31/38を代替にしない。Champion=V5、selectedCapitalCandidate=null、championUpdated=false。CapitalImprovedはfalseではなく **NOT_EVALUATED**。

## B. 既存原精度の保存

| head / 元target | 元N | 原AUC（精密値） | 今回同mask再集計 | 判定 |
|---|---:|---:|---:|---|
| pP / U5 | 1028 | 0.7096462361168244 | 0.7096462361168243 | PRESERVED |
| pP / U10 | 1028 | 0.7402425955550034 | 0.7402425955550034 | PRESERVED |
| MOVE_U2 / U2 | 1028 | 0.6903352597564006 | 0.6903352597564006 | PRESERVED |
| MOVE_U3 / U3 | 1028 | 0.6974395113929996 | 0.6974395113929998 | PRESERVED |
| MRET / original relative MRET label | 1016 | 0.6314236414044475 | 0.6314236414044475 | PRESERVED |

MRET元bucket/block内concordance=0.5982764563943468、比較pair=14505（独立Nではない）。旧STRONG、S1–S8、旧S9 FAIL、新S9R/numerical certificationは変更していない。元head bootstrapは再生成0。

packet1039候補・4156 raw-scoreコピーはcanonical R1 streamにbinary64 exact。funded表は600行→150取引、slot=41/59/50。元1028 scoreとR1 canonical materialization間の約1e-16差は既存固定1e-12の再推論同等性として別記し、コピー許容差と混同しない。training32集合のscore-reference hashとidentity-order hashを別々に照合し、MRETのNを他headへ揃えていない。元mask performance保存は新Capitalの保証ではない。

## C. V5内部の役割別精度とunknown

| 母集団 / head→target | total/known/unknown | AUC | session95%CI | valid /1999 | 判定範囲 |
|---|---|---:|---|---:|---|
| C2 / pP→U5 | 150/150/0 | 0.596200 | [0.497338, 0.692990] | 1999 | role screen |
| C2 / pP→U10 | 150/150/0 | 0.635546 | [0.514177, 0.753989] | 1999 | role screen |
| C2 / -MOVE_U2→Weak | 150/150/0 | 0.636807 | [0.529653, 0.750112] | 1999 | role screen |
| C2 / MOVE_U3→U3 | 150/150/0 | 0.674969 | [0.577492, 0.771008] | 1999 | role screen |
| C2 / MRET→positive | 150/150/0 | 0.601327 | [0.489929, 0.703317] | 1999 | role screen |
| C3 / pP→U5 | 494/494/0 | 0.619701 | [0.568985, 0.670153] | 1999 | role screen |
| C3 / pP→U10 | 494/494/0 | 0.655386 | [0.571872, 0.734206] | 1999 | role screen |
| C3 / -MOVE_U2→Weak | 494/494/0 | 0.621584 | [0.578945, 0.666035] | 1999 | role screen |
| C3 / MOVE_U3→U3 | 494/494/0 | 0.633553 | [0.586125, 0.682144] | 1999 | role screen |
| C3 / MRET→positive | 494/492/2 | 0.552996 | [0.512678, 0.600196] | 1999 | role screen |
| C4_SLOT_RESERVE_REJECT / pP→U5 | 181/181/0 | 0.607285 | [0.489950, 0.717692] | 1999 | Reserve条件付きdiagnostic |
| C4_SLOT_RESERVE_REJECT / pP→U10 | 181/181/0 | 0.692398 | [0.446675, 0.842120] | 1998 | Reserve条件付きdiagnostic |
| C4_SLOT_RESERVE_REJECT / -MOVE_U2→Weak | 181/181/0 | 0.613231 | [0.532287, 0.694528] | 1999 | Reserve条件付きdiagnostic |
| C4_SLOT_RESERVE_REJECT / MOVE_U3→U3 | 181/181/0 | 0.564401 | [0.460691, 0.663722] | 1999 | Reserve条件付きdiagnostic |
| C4_SLOT_RESERVE_REJECT / MRET→positive | 181/181/0 | 0.543505 | [0.450425, 0.632335] | 1999 | Reserve条件付きdiagnostic |

| 役割 | 固定screen結果 |
|---|---|
| Absolute-Loss Defense via MRET | INCONCLUSIVE |
| Medium+ Priority | SUPPORTED_FOR_DESIGN |
| Weak Risk | SUPPORTED_FOR_DESIGN |
| Winner Priority | SUPPORTED_FOR_DESIGN |

Winner screenはC3のpP U5/U10両CI下限>.5、WeakはC2の-q2→Weak、Medium+はC3のq3→U3。全coverageと時点/mask監査PASS、valid>=1900を要求した。C2 funded150は37session、C3 rankpass494は38session。sampling frameは事前固定の全38 OOF sessionsで、空subset sessionを保持。

C2では全score/outcome既知。C3 realizedは492既知・2未知、全current1039ではrealized12未知。MRET公式mask1016はC0から12IDを除く別mask。欠測補完0、未来source availabilityをruntime条件にしていない。C3 mP positiveの既知subsetCI下限>.5だけではfull-cohort SUPPORTEDにしない。MRETは **RELATIVE_MONETIZATION_ONLY / NUMERICALLY_CERTIFIED_BUT_INCREMENTAL_VALUE_NOT_ESTABLISHED**。

U5は将来Potential、U2はPotential>=2、U3はPotential>=3の累積target。Medium3–<5専用分類ではなく、絶対利益の保証でもない。U5/U10とLoserは重なる。AUC .7を「7割儲かる」と解釈しない。元全母集団での研究成功は保持、V5条件内の追加利用価値はrole別に判断する。

### Slot別（補助的診断、全slot介入の許可ではない）

| slot / N | pP→U5 | pP→U10 | -q2→Weak | q3→U3 | mP→positive |
|---|---:|---:|---:|---:|---:|
| 1 / 41 | 0.741758 | 0.712121 | 0.700000 | 0.818182 | 0.585714 |
| 2 / 59 | 0.598997 | 0.606061 | 0.586835 | 0.635294 | 0.624424 |
| 3 / 50 | 0.531250 | 0.697674 | 0.668269 | 0.645320 | 0.584559 |

全target（U5/U10 AP・固定budget density/capture、U2/Weak、U3、元MRET label/原bucket concordance、全headのnet>0/net>=1%/net<=0/Spearman）、全slotとraw terminal reason別の精密値/CIはPRIVATEのEXPERT_TARGET_MATRIX・FIXED_BUDGET_CAPTURE_DENSITY等に保存。各metricのtotal/known/unknown/positive/negative/session/mask hashは本体とMETRIC_COHORT_METADATA_INDEXで追跡できる。ONE_CLASS/NO_PAIRはnull。Brier/loglossを異種targetの確率精度比較に並べていない。

## D. 固定同budget FLAGのLoserとWinner誤排除

| risk / K | Loser N/rate | negative PnL寄与 | positive N/PnL | Weak / Medium | U5（元50比） | U10（元26比） | unknown |
|---|---|---:|---|---|---|---|---:|
| -MOVE_U2 / 30 | 16 / 53.33% | ¥-70,131.40 | 14 / ¥53,973.30 | 18 / 5 | 2 (4.00%) | 0 (0.00%) | 0 |
| -MOVE_U2 / 45 | 25 / 55.56% | ¥-123,178.25 | 20 / ¥125,444.05 | 25 / 8 | 4 (8.00%) | 0 (0.00%) | 0 |
| -MOVE_U3 / 30 | 17 / 56.67% | ¥-106,743.70 | 13 / ¥110,146.10 | 17 / 4 | 6 (12.00%) | 1 (3.85%) | 0 |
| -MOVE_U3 / 45 | 24 / 53.33% | ¥-136,496.80 | 21 / ¥197,027.05 | 23 / 7 | 8 (16.00%) | 3 (11.54%) | 0 |
| -MRET / 30 | 22 / 73.33% | ¥-198,679.75 | 8 / ¥163,638.85 | 11 / 5 | 13 (26.00%) | 6 (23.08%) | 0 |
| -MRET / 45 | 32 / 71.11% | ¥-245,977.55 | 13 / ¥248,640.85 | 19 / 5 | 19 (38.00%) | 9 (34.62%) | 0 |

K=ceil(20%/30%×score-known150)=30/45、stable tieはFrozen Entry time→symbol→entry_id。これらは事後cohort rankingの固定診断集合であり、runtime cutoffではない。他Kを追加していない。LoserとU5/U10は重なり得るため、図でも積み上げていない。

FLAG Loser件数は実回避件数ではない。PnLは保存台帳のfixed-ledger contributionで、cash release・後続競合・数量・再投資を含む新Capitalでも回避利益でもない。合成equity curveなし。TopK集合は1999 resamplesで再最適化せず、CIは元集合を条件とする。同budget差のpaired CIも全て保存し、良いK/headだけを残していない。

## E. モデル間順位衝突と統合限界

| cohort | pair N（独立Nではない） | pP×q2 conflict | pP×q3 conflict | pP×mP conflict | 4head Pareto不比較 | pP exact tie |
|---|---:|---:|---:|---:|---:|---:|
| C0 | 527878 | 98851 | 91001 | 351397 | 407570 | 0 |
| C2 | 11175 | 2698 | 2817 | 6704 | 8391 | 0 |
| C3 | 121771 | 31869 | 28365 | 73428 | 93051 | 0 |
| C5_same_batch | 157 | 38 | 33 | 105 | 128 | 0 |

| C2 Top budget | all4 intersection | all4 union | same-budget保持 |
|---|---:|---:|---|
| 30 | 1 | 68 | 不可（union>K） |
| 45 | 5 | 91 | 不可（union>K） |

pP(i)>pP(j)かつq2(i)<q2(j)では、単一total orderで双方の厳密順位を同時保存できない。AND/OR/Pareto/tie-breakも新しい購入規則なら別評価が必要。Pareto不比較は同順位・安全・同利益を意味しない。全head一致edge（優越/劣後）も保存したが、介入条件に自動採用していない。

| raw pP vs block-local r | cross-block反転pair | raw差がr tieへ潰れるpair |
|---|---:|---:|
| C0 | 11795 | 527 |
| C2 | 161 | 6 |
| C3 | 2110 | 61 |

同block内の順序反転0だがstrict-lessによるtie増加はある。全headのraw/r sign、tie/反転、共通/差分IDはPRIVATE ledgerに保存。pPのraw DESCをglobal r順位へ置き換えていない。

## F. MRET逆向き対照と増分情報

| C1同mask1016 / score | MRET AUC | 元bucket/block concordance | mP−control AUC | paired95%CI |
|---|---:|---:|---:|---|
| -MOVE_U2 | 0.663836 | 0.630472 | -0.032412 | [-0.060935, -0.001366] |
| -MOVE_U3 | 0.646794 | 0.613719 | -0.015371 | [-0.046064, 0.017907] |
| -pP | 0.659218 | 0.629369 | -0.027794 | [-0.056263, 0.002291] |
| MOVE_U2 | 0.336164 | 0.369528 | 0.295260 | [0.236966, 0.357797] |
| MOVE_U3 | 0.353206 | 0.386281 | 0.278218 | [0.22374, 0.338764] |
| MRET | 0.631424 | 0.598276 | — | — |
| pP | 0.340782 | 0.370631 | 0.290642 | [0.23419, 0.354394] |

AUC(-s)=1-AUC(s)はties含め実測/synthetic双方で一致。mP−(-q2)は負でCIも0を跨がない。一方mP−(-pP)、mP−(-q3)はCIが0を跨ぐ。旧正向きcontrolとの差だけでは独立増分優位を示せない。全方向を報告し、runtime反転0・best方向選択0・旧研究status改変0。未来Potential帯を条件にしたconcordanceはruntimeでその帯が既知という証拠ではない。

| C2 positive target / 対照 | mP−control | paired95%CI |
|---|---:|---|
| -MOVE_U2 | 0.144548 | [0.023697, 0.259849] |
| -MOVE_U3 | 0.149211 | [0.01511, 0.281555] |
| -pP | 0.155308 | [0.045587, 0.266842] |
| MOVE_U2 | 0.058106 | [-0.094441, 0.216312] |
| MOVE_U3 | 0.053443 | [-0.103183, 0.204259] |
| pP | 0.047346 | [-0.111353, 0.199265] |

C2 mP→positive CI下限は.5未満。正方向pP/q2/q3との差もCIが0を跨ぐため、全六対照に対する固定screenは非成立。INCONCLUSIVEであり、旧relative-target skillの破棄や再fit、情報不存在の証明ではない。C3 known492・unknown2のabsolute targetと全方向concordanceも別保存。

## G. EXITを変えないchannel到達可能性

| channel | population→score→比較→現在制約→構造選択余地 | sessions / blocks | U5 / U10（評価専用） |
|---|---|---|---|
| CH1_PRE_BUY_SAME_BATCH | 109→109→109→109→109 | 28 / 8 | 26 / 10 |
| CH2_PRE_BUY_DEFENSE | 150→150→150→150→150 | 37 / 8 | 50 / 26 |
| CH3_VACANT_SLOT_RESERVE | 181→181→181→181→181 | 35 / 8 | 30 / 10 |
| CH4_FULL_MAX3 | 139→139→139→139→0 | 29 / 8 | 28 / 9 |
| CH5_CASH_OR_LOT | 15→15→15→15→0 | 10 / 6 | 5 / 2 |
| CH6_RANK_REJECT_OTHER | 545→545→545→545→0 | 38 / 8 | 57 / 20 |

CH1は他channelと重なるため合計しない。rankpass494中、funded150・見送り344。保存raw terminal理由はReserve181、MAX3 148、cash/lot15。MAX3のうち到着batch前から3枠保有は139、残り9は同batchの予定枠競合であり、保有replacement139件と混ぜない。9件にU5/U10は0、保存winner MAX3 28/9は全て実際のFULL_MAX3側。

U5:113=50 funded+30 Reserve+28 MAX3+5 cash/lot。U10:47=26+10+9+2。同一legacy rankpassを分母とし、ALL170/67やOracle分母と混ぜていない。

CH3 Reserve181・35sessions・8blocksは防御tokenなしで棚卸し。raw slot2 reason76、slot3 reason105。同batch他picked空167／非空14。cash/lot既知181、snapshot100株払える176、native picks後100株払える175。ただし固定allocation規則で実fundできる件数は **UNMEASURABLE**、実追加回収は **NOT_EVALUATED**。30U5/10U10を架空の回収数にしない。

FULL_MAX3139では到着候補と3保持者の元Entry scoreを比較し、各Entry時点/horizonの違いを記録。保持者の元scoreは残余return予測ではない。新時刻再推論、早売り・部分売り・replacement0。自然EXIT後の古いEntry再購入なし。CH5/6は元制約を維持、rank/cash cap救済なし。

## H. 次実験仕様草案（2枚、未実行）

| card | 完成判定 | 支持・反証 | 最小不足Evidence |
|---|---|---|---|
| A: V5_PRE_BUY_DEFENSE | UNRESOLVED。MRET独立損失防御経路はDO_NOT_IMPLEMENT | q2 Weak対応は支持だがLoser予測と同義でない。pP/q3をguardへ使う場合もWinner/Medium/positive誤排除が生じる | past-only実現Loss規則、誤排除契約、独立session support、pending/allocation契約 |
| B: V5_VACANT_SLOT_WINNER_RECOVERY | UNRESOLVED。別precommitted設計検討のみ | C3 pP役割は支持、Reserve内pP両CIは.5を跨ぐ。181の構造機会、実追加fund未測定 | Reserve-specific past OOF、冷開始abstain、未選択threshold/guards、native allocation proof |

両cardは解析結果閲覧後のarchitecture draft。threshold=null、minimum support=null、runtime policy selected=null。FLAG Kや当cycleのscore切点を採用閾値にしていない。pPをWinner順位authorityに維持し、q2/q3の拒否・保護・tie-break優先契約は未決定。mPはrelative診断専用、防御tokenへ回収を従属させない。2cards以外のEXIT変更/新head案なし。

block1は保存past OOFがなくNO_PAST_OOF_SUPPORT。training resubstitutionはpercentile referenceのみでOOF性能ではない。将来bridgeはhead fit→保存past score→past-only bridge基準→current actionのDAGを事前監査し、current結果で同block thresholdを決めない。発動0でその場の緩和は禁止。

未来first-divergenceはSPECのみ。全decision入力/初期state/拡張counterを保存prefix上で再構成でき、全action差0の場合だけ帰納的NO_EFFECTとして新full replay省略可。未復元はUNMEASURABLE、差分非zeroは可能性確認に過ぎない。本Workではpolicyが無いためNOT_EVALUATED。synthetic仮条件0supportのNO_REPLAY_REQUIREDを実policyのNO_EFFECTと混同しない。

別cycleでも全19窓growth>=V5、mean/median双方strict改善、対応窓/全minute-MTM DD非悪化、38 COMPLETE/unresolved0を維持。QualityはU5>=50/U10>=26/Medium>=27、Weak<=58かつ率<=58/150、below3<=73かつ率<=73/150、Loser<82かつ率<82/150、positive>=68、gross loss/negative session/worst day非悪化、元slot1/2 100IDsとslot別PnL保存、全causal PASS/独立mismatch0。全部PASSでも人間承認までChampion=V5。将来無損失保証ではない。

## I. 独立監査・予算・Exposure・固定STOP

別実装は主adapter/evaluator/metricsをimportせず、元saved inputsから検算した。同じ研究者・原source・NumPy/SciPy primitiveを共有し、完全盲検外部独立性は主張しない。初回7900 checksで194件のAUC CI比較差を検出。同session pairをm²で数えたバグを、固定指示のm一回へ修復した。元失敗出力/code hashを保存し、AUC resample・paired delta CI・依存screenだけを修復、completed stages全体を再走行していない。point AUC/AP、score/mask、TopK/方向/seed/1999/linear CI/閾値/許容差は変更0。

修復後444比較、全1999 AUC/signed delta/concordance検算、全660981 pair signとpair重複0、全18 synthetic PASS、final mismatch0。identity/分数/money exact、scoreコピーbinary64 exact、metric1e-12固定。F2では全scored1039とMRET公式mask1016のschema差、F3ではteacherの無いflat source_minute列を推測した実装差を記録し、定義を変えないschema修復のみ。

| 予算項目 | 今回 |
|---|---:|
| new fit/refit/calibration/teacher regeneration | 0 |
| new current inference | 0 |
| Capital/Control/Oracle/replacement replay | 0 |
| runtime policy / 新売買intent | 0 |
| primary diagnostic batch / independent verification | 1 / 1（stage再開・純粋修復履歴あり） |
| provider / Fresh / Claude / orders / main merge / force push | 全0 |
| 次実験card / runtime execution authorization | 2 / 0 |

Safety10は全false。Exposure=ITERATIVE_DEVELOPMENT_EVIDENCE、fresh_OOS_claim=false、future_no_loss_guarantee=false。58 Development sessionsを反復使用済みで、新branch/precommit/bootstrapでもFreshへ戻らない。

記録上の制限: F0/F1/F2各receiptには個別code hashがなく、最初の明示的なadapter/setup hashはpacket固定後・新outcome join前のPRIMARY_DIAGNOSTIC_CLAIMに保存された。F9の最終code hashを過去checkpoint時点の事前固定hashとは主張しない。F1はF2との共同checkpointとして追跡し、存在しない別時刻を作っていない。

開始actual GETでは同名branchに設計handoffのみ（a60c659...、V5親710656...）、実行claim/closure無しを確認した。本作業claimを追加し旧design/R1/strategy/注文codeを上書きしていない。353 workflowsはimmutable同一treeのtrigger parseを再利用しbranch push該当0を確認。[skip ci]だけの証明ではない。明示dispatch/cancel0。

入力A/D外側hashと選択member manifest、C nested archiveとmember hashes、pinned4head authorityを確認。B単独ZIPは今回mountedでないため外側hash再検証とは主張せず、C/R1内の同head原スコアとRank GET/certificateを再利用。designer期待全文添付のbytehashは未検証、現在ユーザーが貼付した完全指示本文を権威としF0で解析定義を固定した。このtransport不足はcore score/teacher authority不足と混同しない。全archive全member再監査や新再推論を行ったとは主張しない。

F9_CLOSURE_FIXED_STOP。新Capital policyを作動させず、改善を捏造せず、Champion=V5・selectedCapitalCandidate=nullを維持する。次はユーザーが別設計を承認した場合だけ。

### 出典・計測・設計の区別

出典値: 保存V5厳密EOD/台帳、原1028/1016指標、旧R1 NO_EFFECT。新計測: このWorkの固定subset/FLAG/順位/方向対照/channel。設計判断: SUPPORT screenと未実行2cards。出典値を新Capital成績として表示しない。

- [R1 closure / review3910](https://github.com/Iam-2squared/ark-terminal/blob/3910db03d0a134a27efea1b947e40d93b08fbb38/docs/evidence/capital-v5-anchor-slot3-intelligence-r1-20261005-v1/CLOSURE.json)
- [Rank authorityda8dc](https://github.com/Iam-2squared/ark-terminal/blob/da8dc67b3100ddb7abd7ff95ed336fb9d55470c6/docs/evidence/capital-rank-bigwinner-vnext-20261005-v1/SELECTED_RANK_CONTRACT.json)
- [Quality authoritya977](https://github.com/Iam-2squared/ark-terminal/blob/a977e30aa3318f639569f806f389acb99b3596e4/docs/evidence/capital-quality-anti-weak-medium-v1r1-recovery-20261005/PRIMARY_QUALITY_EVAL.json)
- [MRET fit489 / original result](https://github.com/Iam-2squared/ark-terminal/blob/489fc4f9bc164b3150e374e9f4011a9888ad2d55/docs/evidence/capital-v11-realized-monetization-signal-20261005-v1/MRET_PRIMARY_RESULT.json)
- [MRET numerical certificatea225](https://github.com/Iam-2squared/ark-terminal/blob/a225782aad5a48abea1e332e0eee1d93a0481f0b/docs/evidence/capital-v11r1-numeric-cert-recovery-20261005-v1/FROZEN_V11_SIGNAL_EVIDENCE.json)

精密全値・mask hash・code/input hash・unknown・CI conditioning・失敗履歴はPRIVATE manifestとcheckpointに格納。報告内の小数/円表示のみ丸め、判定は精密値を使う。
