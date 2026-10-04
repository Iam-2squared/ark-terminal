# 🧪 C5 State9 / Path incremental diagnostic

日時: 2026-10-04T11:42:51+09:00。basis HEAD: ee92a0344d991a0905380d31255b1f5b455228dc。

結果: **CAPITAL_STATE9_INCREMENTAL_VALUE_NOT_DEMONSTRATED**。Developmentのみ。Capital layerでの追加直接参照の診断であり、P1自体はState9 current/historyを既に利用している。

| 追加情報 | 平均relative MSE改善 | 改善したteacher数 | positive folds | 最大1 sessionのpositive lift share | 判定 |
|---|---:|---:|---:|---:|---|
| current State9 vs A | -6.786% | 1 / 4 | 0 / 4 | 15.531% | FAIL |
| causal Path vs B | +11.014% | 3 / 4 | 3 / 4 | 73.197% | FAIL: 40%上限超過 |

## 📊 Teacher別比較

| Teacher | OOF評価N | current vs A relative改善 | Path vs B relative改善 |
|---|---:|---:|---:|
| ≥5 Winner binary regression | 166 | -25.572% | +43.156% |
| exact pre-peak MAE | 180 | +4.401% | +6.270% |
| Frozen EXIT v3 return | 1,058 | -4.168% | +1.594% |
| Frozen EXIT v3 active holding time | 1,058 | -1.805% | -6.963% |

Winner AUC: A 0.840934 / B 0.837912 / C 0.854945。binary-teacher Ridgeのranking diagnosticであり、calibrated probabilityやBrierではない。

## ⚠️ 解釈の境界

同一target-wise母集団、session-forward 4fold、1session purge、Ridge alpha=10固定、train-only preprocessing。fitは42 / 48、sweep 0。最初のfoldのWinner/MAE teacherはtrain support不足で全arm同時skipし、足りないラベルを0にしていない。

全1,600中のteacher complete NはWinner301 / MAE317 / EXIT return1,561 / holding time1,561。特にWinner-negativeとexact MAEは完全な保存済みminute sourceを要求するため、評価集団は選択的。Winner OOFはpositive140 / negative26である。したがって上記は全1,600の完全なCapital品質やFresh/OOSの証明ではない。

Pathの改善傾向は観測されたが、single-session依存の事前Gateで不採用。currentもGate FAILで、Path promotionにはcurrent PASSも必要。別bucket追加、teacher差替、threshold救済、追加fitは行わない。

C6 State9 Rank precommitは作成しない。C7 State-aware allocation / C8 State-aware MAX3/4/5も未実行。既にC3 current/fixed 6armはfunded MTM source不足で完全Portfolio測定BLOCKED。C9独立監査後、Freeze候補なしでclosureする。
