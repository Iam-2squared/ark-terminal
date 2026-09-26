# Final Pre-Gen3 Analysis / architecture precommit R44–R45

保存: 2026-09-26T21:51:58.009950+09:00。basis HEAD `0dfc9f12a90ac68e62f5e4775cfc026aaaa27e5c`。Gen3 fit/replay/性能閲覧=0。

## 既存研究とClaude disposition

R36/R39は24候補・144 fits・0 PASS、R41/R43は16候補・64 fits・0 PASS。Entry Dual Freeze、両研究のNO_SELECTIONは変更しない。今回の許可は独立Gen3の性能前設計・実装・CIまでであり、本学習起動ではない。Claude CONDITIONAL GOはユーザー経由の要約として記録。直接Claude実行や全文取得とは主張しない。Finding別ACCEPT/PARTIAL/REJECT/DEFERは`r44-result/claude-disposition.json`。DROP単独、負PnL単独、独自cost、Gate緩和はREJECT。候補数提案6–8はPARTIALとし、ユーザー許容範囲の最小4構造候補で研究者過適合を抑える。

## 1. ラベル重複・score相関・AUC

| Entry | fresh OOF | C coverage | F coverage | 同一full-window両label available N | C0F0 | C0F1 | C1F0 | C1F1 | label phi | HGB Pattern score相関 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| IM | 130968 | 29.25% | 43.98% | 20417 | 18.07% | 23.48% | 28.75% | 29.70% | -0.0563 | 0.9351 |
| R1 | 117552 | 29.42% | 43.32% | 17661 | 18.99% | 23.29% | 28.33% | 29.38% | -0.0414 | 0.9303 |

C/Fは同じcheckpointで比較し、fullはcalendar窓が60/15 barsから短縮されていないことを意味する。両ラベルが観測された共通母集団に条件付けると引継ぎの相関・AUCを再現した。一方、ラベル欠損を除かないfresh/full-calendar母集団の同モデルscore相関は0.8593／0.8583。これらは分母が異なる。強いscore相関を実現binary label相関と混同しない。両TRUE約30%は存在するが、label phiはほぼ0付近であり、重複だけを.93の因果説明にはできない。共通のvolatility/価格経路特性、目的関数、availabilityによる選択が関係し得るという診断であり、因果分解を証明したわけではない。

| Model | IM C AUC | IM F AUC | R1 C AUC | R1 F AUC |
|---|---:|---:|---:|---:|
| HGB_CORE_CALENDAR | 0.6866 | 0.7562 | 0.7015 | 0.7681 |
| HGB_CORE_CALENDAR_PATTERN187 | 0.7256 | 0.7760 | 0.7270 | 0.7887 |
| LOGISTIC_CORE_CALENDAR | 0.6542 | 0.7078 | 0.6619 | 0.7266 |
| LOGISTIC_CORE_CALENDAR_PATTERN187 | 0.6701 | 0.7335 | 0.6803 | 0.7623 |

各feature specは同一ラベルを使用するため、label 2×2自体はspec別に変化しない。State・時刻・volatility別の分解を保存。AUCはutilityやGate通過の証明ではない。

## 2. Missingness / survivorship

| Entry | 区分 | N | C coverage | F coverage |
|---|---|---:|---:|---:|
| IMMEDIATE | volumeBand=1-1k | 371 | 4.58% | 8.63% |
| IMMEDIATE | volumeBand=100k+ | 19136 | 70.00% | 87.93% |
| IMMEDIATE | volumeBand=nan | 48495 | 5.24% | 10.38% |
| IMMEDIATE | position.fullOwnedPrefix=0 | 91480 | 16.16% | 27.60% |
| IMMEDIATE | position.fullOwnedPrefix=1 | 39488 | 59.57% | 81.93% |
| ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF | volumeBand=1-1k | 336 | 5.06% | 8.04% |
| ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF | volumeBand=100k+ | 16783 | 70.01% | 87.36% |
| ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF | volumeBand=nan | 44432 | 5.47% | 10.64% |
| ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF | position.fullOwnedPrefix=0 | 84024 | 16.79% | 28.03% |
| ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF | position.fullOwnedPrefix=1 | 33528 | 61.05% | 81.62% |

全time-band、remaining bars、lunch境界、session、symbol、Entry、State、volatility、volume、owned-prefix、price freshness別を`missingness-breakdown.json.gz`へ保存。calendar短縮数とraw欠落理由を分離。R41はterminal近辺でhorizonを短縮するので、短縮自体をmissingと誤集計しない。低coverageはraw経路欠落と強く関連し、ランダム欠損とは扱えない。MNARは観測データだけでは識別できず、MARとも断定しない。availability-conditioned AUCにはliquidity/経路completeの選択がある。volumeは約定出来高のproxyで、板・spreadの証明ではない。

## 3. Winner / giveback / long loser separation

Evaluator-onlyの事前固定診断定義: A=resolved canonical>=5%, capture>=50%, net>0。B=resolved canonical>=5%, capture<50%, High→Exit gap>=2pp、かつobserved post-Entry High knownAt<=EXIT。C=resolved non->=5%, net<=-1%, active holding>=30。Bの観測Highは約定可能価格でもcomplete-prefix certificateでもない。その他・censoredは別扱い。Gen3候補はこの分類の前に作っていない。

| Generation | Entry | Group | policy観測N | unique opportunity N | current PnL中央値% | observed giveback中央値pp | momentum5中央値% |
|---|---|---|---:|---:|---:|---:|---:|
| R36 | IM | A_RETAINED_WINNER | 1744 | 231 | 4.035 | 0.397 | 1.222 |
| R36 | IM | B_GIVEBACK_WINNER | 1212 | 134 | -2.346 | 5.055 | 0.000 |
| R36 | IM | C_PROLONGED_LOSER | 2636 | 247 | -2.277 | 2.975 | 0.000 |
| R36 | R1 | A_RETAINED_WINNER | 1555 | 211 | 4.052 | 0.433 | 1.624 |
| R36 | R1 | B_GIVEBACK_WINNER | 919 | 108 | -1.002 | 5.466 | -0.099 |
| R36 | R1 | C_PROLONGED_LOSER | 2190 | 216 | -1.929 | 2.579 | -0.180 |
| R41 | IM | A_RETAINED_WINNER | 1915 | 196 | 4.795 | 1.089 | 0.156 |
| R41 | IM | B_GIVEBACK_WINNER | 2842 | 234 | -1.604 | 6.810 | 0.000 |
| R41 | IM | C_PROLONGED_LOSER | 3494 | 287 | -2.487 | 3.400 | 0.000 |
| R41 | R1 | A_RETAINED_WINNER | 1790 | 194 | 4.593 | 1.052 | 0.221 |
| R41 | R1 | B_GIVEBACK_WINNER | 2814 | 230 | -1.117 | 6.499 | 0.000 |
| R41 | R1 | C_PROLONGED_LOSER | 3227 | 265 | -2.147 | 2.815 | 0.000 |

各policy×Opportunityは独立標本ではない。表は重複policy観測を含み、unique数とmetric別eligible Nを別保存した。AにもDROP、B/CにもREBOUND/RISEがあるため、State単独で正解を作れない。R41 Bのobserved giveback中央値は約6.8/6.5ppで、利益保護の独立Authorityを設ける根拠になる。一時反発を含むLoser延命とWinner押し目を、負PnLやDROP一つで区別してはいけない。全40 policyのdecision直前のState/path/dwell/churn、6Signals/loss、Pattern family、momentum、volatility、PnL、peak由来MFE、giveback、time since peak、holdingを保存。Pattern187は保存済みdecision NOW 4,569 unique keysだけでcanonical closed-prefix再構成した。Family平均は異単位の診断要約であり、売買scoreとはしない。

## 4. Recovery semantics

| Entry | sequence | fresh adjacent N |
|---|---|---:|
| IM | RISE>PULLBACK>RISE | 247 |
| IM | RISE>DROP>REBOUND | 7 |
| IM | RISE>DROP>DROP | 40 |
| IM | DROP>REBOUND | 4609 |
| IM | DROP>RISE | 116 |
| IM | SHARP_RISE>RISE_STOP | 1 |
| R1 | RISE>PULLBACK>RISE | 221 |
| R1 | RISE>DROP>REBOUND | 6 |
| R1 | RISE>DROP>DROP | 36 |
| R1 | DROP>REBOUND | 4094 |
| R1 | DROP>RISE | 102 |
| R1 | SHARP_RISE>RISE_STOP | 1 |

全6 SignalでTRUE/FALSE/UNKNOWNと隣接遷移を別集計。欠損/stale/gapを越えてrecoveryやlossを推定しない。UNKNOWN→FALSEはTRUE→FALSEではない。Recoveryは方向の一時変化であり成功結果の保証ではなく、Gen3では有限fresh checkpointの猶予と、悪化Authority優先を組み合わせる。

## Gen3 architecture / labels / state machine Freeze

HGB＋Pattern187のみ、既存hyperparameterを維持。3 heads: CONTINUATION / PROTECTION / DETERIORATION。予測値は未校正classification score。新しいlabelはsell-now exact next OPENに対する、5/10/15 active bars後のexecutable reference utilityを使う（残りbarsに応じた3点短縮あり）。すべての差はFrozen effective Entry価格を分母とするpp。終点と中間2点を使うため、観測不能なintrabar oracle最大値を学習目的にしない。

| Head | target | 追加eligibility |
|---|---|---|
| C | 終点utility>=+.50pp、3点中2点以上が正 | fresh NOW・anchor＋3 referenceが存在 |
| P | 終点utility<=−.25pp | NOWのcomplete-prefix MFE>=1pp |
| D | 終点utility<=−.50pp、3点中2点以上が負 | fresh NOW・anchor＋3 referenceが存在 |

これはsampled holding utilityのproxyであり、全future pathの連続性を証明するtargetではない。未sampleバーが欠損しても3点が有効ならlabelは定義できるが、その意味をcomplete pathと言い換えない。C/D同時TRUEは不可能、P/D同時TRUEは合法。Future label/reference/maturity/availabilityはdecision input禁止。P対象外は0でなくnull。sample不足・exact reference欠落でnull、imputationなし。auction930を使うlabelのmaturityは930、全foldで同session内に満了し、purge2 sessions維持。

| 候補 | Profit protection | Deterioration |
|---|---|---|
| GEN3_R45_01 | CORROBORATED | MULTI_EVIDENCE |
| GEN3_R45_02 | RECOVERY_PROBATION | MULTI_EVIDENCE |
| GEN3_R45_03 | CORROBORATED | FAILED_RECOVERY |
| GEN3_R45_04 | RECOVERY_PROBATION | FAILED_RECOVERY |

4候補は構造比較で、全threshold共通・reserveなし・5個目禁止。Expected24 fits=1 spec×3heads×2Entry×4fold。PはC highでも独立発動、DはC/P conflictに優先。DにはState/price structure・負momentum・Signal deteriorationの複合証拠とmodel scoreが必要。Pにはcertified owned giveback・peak age・弱化証拠が必要。probation候補は実際の回復eventだけで2 fresh checkpoint猶予、永久vetoにしない。全head neutral状態は3 fresh観測後に、保有時間・負current PnL・persistent弱化・Signal・momentumが揃う場合のみD確認へ移る。DROP単独・負PnL単独でEXITしない。exact table、priority、null、counter、mode、terminal規則は機械可読protocol.policyが唯一の契約。

## Selection / Completion Gate

R36のpinned gate_candidateを無変更で再利用。両Entryでcoverage>=.95、Overall Mean>=2%、全bucket固定mean/median/capture、Winner aggregateと3/4fold、Retention aggregateと2/4改善、p05改善>=.25pp・worst悪化<=.25pp・3/4fold p10非劣後、PF@cost.10>=1/.20>=.95、既存集中度を要求。>=5%はMean>=3.25%,Median>=2%,Median Capture>=50%。全4candidate＋neutralのA/B、input/source/row identityも必須。Passingのみ3軸dense rankのworst rank→rank sum、同率はNO_SELECTION。0 PASSを採用で埋めない。

## Freeze / audit / CI boundary

Protocol SHA256 `e7b38e7e6aaf909926852467152fffef2532f58f960a95e6f2d18efd66f5d1b5`。`GEN3_FEATURE_CAUSALITY_AUDIT_R45.json`に全623 registry行のMODEL_ADMITTED/BLOCKEDとknownAt/null/lineageを保存。設計contract監査は完了、実装証明はこのFreezeの後にfocused tests/CIで行う。既存52 source hashはR41から同一。実装前にこのprotocolをGitHubへ保存する。

このWorkではDevelopment fit/Gen3 performance replayを実行しない。Label coverage/supportのみは実装後に非性能のcontract検証として測定し、support不足なら適応変更せずSTOP。独立CI branchで必要CIを実行し、旧PRの重複workflow起動を避ける。長時間learningは別launch markerが次回明示指示で保存された場合のみ起動し、今回はmarker自体を作らない。

Dataはoutcome-exposed Development2,155、40既閲覧候補を認識。新provider/protected data=0、Safety9全false、Entry変更/Capital/main merge/force push/live/paper/productionなし。

分析実行時の技術修正: 初回はR35保存順とR41整列順の違いをidentity guardが検知し停止。二回目はR36 ledgerにdecisionNow列がないため停止。R41の固定sortとR38の既証明execution→decision逆写像を使って修正し、三回目に全診断完了。モデル・policy replay・評価式は変更していない。

保存容量を抑えるためdetailのPattern familyをlosslessに正規化した。`separation-normalized.jsonl.gz`と`pattern-family-table.json.gz`から元の26,338行を復元でき、元gzip SHA一致を検証済み。`separation-storage.json`に復元規則と元hashを保存。
