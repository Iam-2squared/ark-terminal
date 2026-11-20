# Final handoff — STOP

# Frozen Selector Post-Selection Low/High Path Anatomy

全3800行 / 76 sessions。完全経路 686行 / 32 sessions / 238 symbols。不完全3114行はNO_VALID_PATHとして全行台帳に保持。

**基準は選定時Decision Price。以下は完全観測経路に条件付けた記述で、元Top5全体の分布・実現利益・未知性能ではない。** min/maxを0でclampせず、low→highは時間順序を問わないoracle range。

| metric % | mean | median | p05 | p10 | p25 | p75 | p90 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| selectionToLowPct | -3.270 | -2.504 | -8.861 | -7.534 | -4.671 | -1.055 | -0.330 | 0.000 |
| selectionToHighPct | 3.247 | 2.128 | 0.000 | 0.329 | 0.836 | 4.178 | 7.442 | 9.940 |
| lowToHighPct | 6.828 | 5.649 | 1.623 | 2.079 | 3.337 | 8.786 | 12.784 | 16.162 |
| sessionEndReturnPct | -0.823 | -0.518 | -7.345 | -5.826 | -2.906 | 0.999 | 3.630 | 5.163 |

順序は最初に極値へ到達したバーで分類。極値の再到達区間も台帳保存。同一バー内順序は推測しない。
- LOW_THEN_HIGH: 282行 / 41.1%
- HIGH_THEN_LOW: 398行 / 58.0%
- SAME_BAR_ORDER_UNKNOWN: 6行 / 0.9%

## 時間

5分バーの区間で測定。下表は取引時間の下限・上限それぞれの中央値（分）。昼休みを除外。実経過時間とCDFの確定/可能範囲は08番。

| elapsed | lower median | upper median | n |
|---|---:|---:|---:|
| lowInterval | 40.000 | 45.000 | 686 |
| highInterval | 25.000 | 30.000 | 686 |
| lowToHighElapsed | 45.000 | 55.000 | 282 |
| highToLowElapsed | 65.000 | 75.000 | 398 |

## Winner / nonwinner（将来条件付き）

| group | n | low median % | high median % | range median % | low→high rate | low upper median min | high upper median min | end median % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| +3 winner | 254 | -1.951 | 5.107 | 8.346 | 59.4% | 32.500 | 60.000 | 1.196 |
| +3 nonwinner | 432 | -2.760 | 1.096 | 4.066 | 30.3% | 55.000 | 15.000 | -1.214 |
| +5 winner | 132 | -1.640 | 7.496 | 10.466 | 68.2% | 25.000 | 72.500 | 3.367 |
| +5 nonwinner | 554 | -2.685 | 1.491 | 4.782 | 34.7% | 50.000 | 20.000 | -0.944 |

## 時間順序を要求した閾値イベント

閾値はすべて選定価格基準。別バーで先→後が確認できるものだけCONFIRMED。同一バーのみはUNKNOWN。大域的low/high順序とは異なり、途中の往復も検出する。

| pattern | confirmed | same-bar unknown | rate / valid | rate / first threshold | all-original bounds |
|---|---:|---:|---:|---:|---|
| down1_up3 | 142 | 4 | 20.7% | 27.3% | 3.7%, 85.8% |
| down1_up5 | 72 | 1 | 10.5% | 13.8% | 1.9%, 83.9% |
| down2_up3 | 69 | 6 | 10.1% | 17.6% | 1.8%, 83.9% |
| down2_up5 | 33 | 2 | 4.8% | 8.4% | 0.9%, 82.9% |
| down3_up3 | 38 | 3 | 5.5% | 12.8% | 1.0%, 83.0% |
| down3_up5 | 19 | 1 | 2.8% | 6.4% | 0.5%, 82.5% |
| up3_giveback0 | 158 | 10 | 23.0% | 62.2% | 4.2%, 86.4% |
| up5_giveback0 | 67 | 4 | 9.8% | 50.8% | 1.8%, 83.8% |

## Original Rank 1〜5

| rank | original n | valid n | low median % | high median % | range median % | low→high rate |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 760 | 172 | -3.247 | 2.262 | 6.603 | 38.4% |
| 2 | 760 | 154 | -2.979 | 2.267 | 5.882 | 36.4% |
| 3 | 760 | 134 | -2.367 | 2.354 | 6.112 | 51.5% |
| 4 | 760 | 105 | -1.905 | 1.924 | 4.444 | 40.0% |
| 5 | 760 | 121 | -2.256 | 1.556 | 4.369 | 40.5% |

## Random

元Top5全5銘柄同士: NOT_EVALUABLE (0 timestamps)。欠測を補完しない。補助の観測条件付き比較: 249 timestamps / 32 sessions / Selector 623行 / Random 574行。部分メンバー平均を元Top5成績と呼ばない。

| metric | Selector | Random | difference | pointwise 95% CI |
|---|---:|---:|---:|---|
| selectionToLowPct | -3.326 | -0.662 | -2.664 | [-3.0718642526730195, -2.294834071131356] |
| selectionToHighPct | 3.353 | 0.586 | 2.767 | [2.425391749416106, 3.1365168707707514] |
| lowToHighPct | 7.000 | 1.263 | 5.736 | [5.217716160467676, 6.292221272311887] |
| LOW_THEN_HIGH | 0.422 | 0.499 | -0.077 | [-0.15279234871031747, -0.003389214409722235] |
| HIGH_THEN_LOW | 0.572 | 0.485 | 0.088 | [0.01305441881613757, 0.16470248429232806] |

CIはsession-cluster bootstrap、順序率は0〜1。他は%。日内timestamp・日間session等重み。5-session block感度もJSON保存。欠測バイアス・銘柄反復・既知Developmentへの過適合を消すものではない。

## 判断 / Q1〜Q10

Q1〜Q3: 典型値は上表のmedian/quantiles。Q4: 順序率は完全観測集合限定。Q5〜Q7: winner/nonwinnerのlow・high・時刻および閾値順序を参照。「即上昇」か「反発」かを未来極値からPIT判定できるとは言わない。Q8: rank別の記述差を保存しcutoffは作らない。
Q9: 完全観測経路には、下落後の上昇という時間順序を確認できる事例が存在し、状態依存Entry/EXITの回収可能性を別診断する根拠はある。ただしoracle rangeを利益化できる根拠はまだない。
Q10 / 次工程候補: **A Causal Turning-Point / Entry Recoverability Diagnostic**。PIT情報だけで反発前の状態を識別できるか、固定nullと欠測契約の下で別途検証する。提案のみで未実行。
B EXIT Recoverabilityは今回実行しない。C Economic Selector v2も実装しない。Dの追加取得・測定も未開始。任意archetype分類は新しい境界を追加しないためNOT_APPLICABLE、閾値イベントの定量記述を代わりに保存。

専用テスト・全回帰・CIの最終receiptは17/18/19番。Safety9項目false、既存Developmentのみ、DEV TEST/Fresh/OOS未開封、新規J-Quants0、Selector/Entry/EXIT/Capital変更0、main mergeなし。ここでSTOP。


Protocol precommit: `225a6914611395cfe9a71c9da791d138fdca0a36`. Source start HEAD: `8ababb7cc412a7b7dd7e0d09611d1bb66a5dd8e8`. Producing HEAD and CI: 19_ci.json. No implementation, learning, Entry/EXIT/Capital changes or sealed-data opening. Next candidate is a proposal only.
