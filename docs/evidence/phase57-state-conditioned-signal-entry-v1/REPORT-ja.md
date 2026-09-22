# Ark Terminal Phase57 — State-Conditioned Signal Entry v1 最終報告

## 🧭 結論

Entry v1 は、固定した policy のまま 2,155 Opportunities 全件を完走した。
ただし、**Immediate BUY を置き換える根拠は得られなかった**。Entry v1 は旧Signal-onlyより
小幅に改善したが、Immediate比では平均買値を 0.0184% 改善できず、Fillを106件
（-4.92pp）、+3% Captureを107件（-14.06pp）、+5% Captureを50件（-12.25pp）失った。

一方、paired MAEは30mで+0.115pp、60mで+0.146pp（負値が0へ近づく改善）、
EntryPositionは-0.017、Range Retentionは+1.734ppだった。つまり「少しLow側へ寄せ、
adverse excursionを抑える」効果はあるが、その代価としてCaptureを大きく落とした。

判定は **Entry v1を不採用のままEvidence固定し、EXITへはまだ進まず、Entryを1回だけ
最小修正する**。v1のruleを事後変更して再採点はしない。

## 🔧 1. Entry v1の仕組みと固定policy

```text
Frozen Selector
  → closed-bar 5分return符号によるcausal coarse State
  → State別に既存A/D/C/E armを固定選択
  → 必要なStateだけ既存6 Signalを待つ
  → BUY / fixed 10-active-minute fallback / NO ENTRY
  → Oracle・Outcomeを使う評価（決定完了後のみ）
```

| Initial State | Entry rule | 既存arm | Signal | Fallback |
|---|---|---:|---|---:|
| UP | BUY NOW | A | なし | 0m |
| DOWN | recovery待ち | D | HIGHER_LOW / LOWER_WICK / RECLAIM | 10 active min |
| NEUTRAL | upward transition待ち | C | BREAKOUT / COMPRESSION_EXPANSION | 10 active min |
| UNKNOWN | bullish扱いせずSignal待ち | E | 既存6 Signalすべて | 10 active min |

Policy lock SHA-256は
`794a1ff0c1dd43a145b6cc0c990572c5f343042db1a86523d7d457c0fcdfa3d3`。
Entry v1の結果を見る前に固定した。Signal detector、threshold、Selector、State v2、
Low/High Evidenceは変更していない。

## 🧠 2. Causal State方法と診断

`t`より前にclosedとなったbarだけから既存 `context.returnPct["5"]` を読み、正ならUP、
負ならDOWN、0ならNEUTRAL、欠損ならUNKNOWNとした。モデル学習・threshold sweepはない。
State v2 NOW referenceは全Entry arm決定後の答え合わせだけに使った。

| Entry時State | 件数 | 2,155比 | 選択arm |
|---|---:|---:|---:|
| UP | 218 | 10.12% | A |
| DOWN | 717 | 33.27% | D |
| NEUTRAL | 76 | 3.53% | C |
| UNKNOWN | 1,144 | 53.09% | E |
| 合計 | 2,155 | 100.00% | — |

| State診断 | 値 |
|---|---:|
| Signal census causal checkpoints | 377,450 |
| Frozen State v2 joined checkpoints | 77,214 / 77,214 |
| Decision coverage | 2,155 / 2,155 |
| Decision overall agreement | 93.55% |
| 両方DEFINED agreement | 91.49%（n=1,011） |
| UNKNOWN | 1,144 / 2,155（53.09%） |

Overall agreementはReference UNKNOWN 1,091件の一致に強く支えられるため、91.49%の
DEFINED agreementとUNKNOWN率を併記する。State分類精度を単独の成功指標にはしない。

## 🔗 3. State × 既存6 Signal

下表は同一Opportunity・同一checkpointでjoinした、各Stateを一度でも持つOpportunity中の
Signal発生Opportunity数/率である。Stateは時系列で変わるため各行の分母は重複する。

| Dynamic State（分母） | CONTINUATION | BREAKOUT | COMP/EXP | HIGHER_LOW | LOWER_WICK | RECLAIM |
|---|---:|---:|---:|---:|---:|---:|
| UP（1,402） | 185 / 13.20% | 936 / 66.76% | 353 / 25.18% | 666 / 47.50% | 278 / 19.83% | 391 / 27.89% |
| DOWN（1,442） | 26 / 1.80% | 55 / 3.81% | 0 / 0.00% | 261 / 18.10% | 499 / 34.60% | 204 / 14.15% |
| NEUTRAL（1,209） | 12 / 0.99% | 26 / 2.15% | 0 / 0.00% | 157 / 12.99% | 164 / 13.56% | 108 / 8.93% |
| UNKNOWN（2,019） | 20 / 0.99% | 49 / 2.43% | 0 / 0.00% | 0 / 0.00% | 56 / 2.77% | 238 / 11.79% |

実際のEntry v1 intentは次のとおり。Signal familyは同時発火があるためfamily合計は
unique Signal intent数を超えることがある。

| Initial State | BUY NOW | Signal intent | Fallback intent | NO ENTRY | intent時family内訳 |
|---|---:|---:|---:|---:|---|
| UP | 218 | 0 | 0 | 1 | — |
| DOWN | 0 | 283 | 434 | 4 | HL 139 / Wick 114 / Reclaim 50 |
| NEUTRAL | 0 | 18 | 58 | 0 | Breakout 18 |
| UNKNOWN | 0 | 31 | 1,113 | 293 | Breakout 9 / Comp-Exp 1 / Wick 11 / Reclaim 11 |
| 合計 | 218 | 332 | 1,605 | 298 | — |

## 📊 4. Immediate / 旧Signal / Entry v1

「価格差」は%を主指標とする。円単純平均は価格水準の違う銘柄を混ぜるため参考値である。

| KPI | A Immediate | B 旧Signal-only | C Entry v1 |
|---|---:|---:|---:|
| Population | 2,155 | 2,155 | 2,155 |
| Fill | 1,963（91.09%） | 1,857（86.17%） | 1,857（86.17%） |
| NO ENTRY | 192 | 298 | 298 |
| Mean delay | 1.453m | 9.627m | 9.125m |
| Selector→Entry price差 | +0.1891% | +0.1959% | +0.1879% |
| Selector→Entry 円差（参考） | +1.974 | +0.852 | +0.948 |
| Low→Entry distance | 2.5133% | 2.5950% | 2.5874% |
| Low→Entry 円差（参考） | 33.641 | 33.950 | 34.046 |
| Entry→Later High余地 | 2.7290% | 2.8561% | 2.8549% |
| Entry→Later High 円差（参考） | 31.432 | 33.546 | 33.342 |
| EntryPosition mean | 0.6540 | 0.6466 | 0.6435 |
| Range Retention mean | 35.012% | 35.159% | 35.408% |
| 待機中missed upside mean | 0.000% | 0.730% | 0.662% |

母集団差の影響を除くため、勝敗判断は次の完全paired値を優先する。

| Cのpaired差 | vs A Immediate | vs B 旧Signal-only | 良い向き |
|---|---:|---:|---|
| Fill | -106 / -4.919pp | 0 / 0.000pp | 大きい |
| Entry price improvement | **-0.0184%** | +0.0059% | 正 |
| Delay | +7.683m | -0.502m | 小 |
| Low→Entry distance | -0.0011pp | -0.0076pp | 負 |
| Entry→Later High余地 | +0.0162pp | +0.0050pp | 正 |
| EntryPosition | -0.0171 | -0.0031 | 負 |
| Range Retention | +1.734pp | +0.268pp | 正 |
| 30m MFE | -0.0328pp | +0.0062pp | 正 |
| 30m MAE | +0.1152pp | -0.0070pp | 正（0へ） |
| 60m MFE | -0.0293pp | +0.0327pp | 正 |
| 60m MAE | +0.1461pp | +0.0122pp | 正（0へ） |

Immediate比のsession-equal price improvementは-0.0177%、descriptive 95% bootstrap
区間は[-0.1009%, +0.0631%]。価格優位は確認できない。

## 🎯 5. +1/+2/+3/+5 Opportunity Capture

分母はSelector時点の各threshold winnerで固定し、NO ENTRYもmissとして保持した。

| Threshold | 分母 | A Immediate | B 旧Signal | C Entry v1 | C−A | C−B |
|---|---:|---:|---:|---:|---:|---:|
| +1% | 1,496 | 1,275 / 85.23% | 1,083 / 72.39% | 1,100 / 73.53% | -11.70pp | +1.14pp |
| +2% | 1,054 | 902 / 85.58% | 756 / 71.73% | 767 / 72.77% | -12.81pp | +1.04pp |
| +3% | 761 | 649 / 85.28% | 540 / 70.96% | 542 / 71.22% | **-14.06pp** | +0.26pp |
| +5% | 408 | 357 / 87.50% | 299 / 73.28% | 307 / 75.25% | **-12.25pp** | +1.96pp |

Entry v1の+3% miss 219件はNO ENTRY 55件＋Entry後threshold未達164件、+5% miss
101件はNO ENTRY 14件＋Entry後未達87件。旧Signalよりはわずかに保持したが、
Immediateからの取り逃しは大きい。

## 📈 6. 30m / 60m MFE・MAE

MAEは負値で、0へ近いほど良い。`n`は完全なhorizon label数。

| Horizon | Policy | n | MFE mean | MAE mean |
|---|---|---:|---:|---:|
| 30m | Immediate | 1,365 | 1.7692% | -1.8698% |
| 30m | 旧Signal | 1,336 | 1.7243% | -1.7655% |
| 30m | Entry v1 | 1,337 | 1.7296% | -1.7724% |
| 60m | Immediate | 1,117 | 2.5462% | -2.5134% |
| 60m | 旧Signal | 1,101 | 2.4784% | -2.3897% |
| 60m | Entry v1 | 1,104 | 2.5202% | -2.3790% |

Immediateとのpaired比較では、Entry v1はMAEを30m +0.115pp（n=1,302）、60m
+0.146pp（n=1,081）改善した一方、MFEはそれぞれ-0.033pp、-0.029pp低下した。

## 🧩 7. State別Entry Qualityと仮説

| Initial State | n | C Fill | paired買値改善 | EntryPosition差 | Retention差 | +3 Capture差 | +5 Capture差 | 30m MFE差 | 30m MAE差 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP | 218 | 217 | 0.0000% | 0.0000 | 0.000pp | 0.00pp | 0.00pp | 0.000pp | 0.000pp |
| DOWN | 717 | 713 | -0.0500% | +0.0029 | +0.481pp | -16.89pp | -15.91pp | -0.044pp | +0.124pp |
| NEUTRAL | 76 | 76 | -0.0019% | -0.0075 | -0.837pp | -15.38pp | -21.43pp | -0.101pp | +0.052pp |
| UNKNOWN | 1,144 | 851 | +0.0020% | -0.0395 | +3.559pp | -15.34pp | -12.34pp | -0.018pp | +0.175pp |

UP 218件ではEntry v1とImmediateのtimestamp/price/fillを含む7フィールドが
218/218で完全一致した。UPに旧Signal待ちを当てた反実仮比較では、delay +5.889m、
買値-0.0735%（悪化）、+3 Capture -7.45pp、+5 Capture -14.06ppだった。
よって **H1（UPはBUY NOW）を支持**する。

DOWNではrecovery待ちが買値を0.0500%悪化させ、Low距離+0.0252pp、EntryPosition
+0.0029、+3 Capture -16.89ppとなった。MAEだけは+0.124pp改善した。
よって **H2は不支持**。

NEUTRALでは価格はほぼ不変、Low距離-0.0098pp・EntryPosition-0.0075と小改善したが、
Retention -0.837pp、+3 Capture -15.38pp、+5 Capture -21.43pp。
よって **H3は総合不支持**。

Entry v1は旧Signal-only比でFillを維持し、買値+0.0059%、EntryPosition-0.0031、
Retention+0.268pp、+3 Capture+0.26pp、+5 Capture+1.96ppだった。しかしImmediate比の
大幅Capture低下を解消できず、**H4は弱い方向性のみで成功条件を満たさない**。

## 🧪 8. State × Signal別Quality

以下はEntry intentで発火したfamily別。co-fireを含み、小標本は探索結果ではなく診断である。

| Family | n | Selector比買値改善 | EntryPosition | Retention | +3 Capture | +5 Capture | 30m MFE | 30m MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HIGHER_LOW | 139 | -0.763% | 0.765 | 23.48% | 79.03% | 76.32% | 1.499% | -2.245% |
| LOWER_WICK | 125 | -0.166% | 0.639 | 36.40% | 91.23% | 78.13% | 2.144% | -2.178% |
| RECLAIM | 61 | -0.706% | 0.746 | 25.61% | 61.54% | 64.29% | 1.742% | -1.908% |
| BREAKOUT | 27 | -1.577% | 0.778 | 21.24% | 53.85% | 71.43% | 1.125% | -2.262% |
| COMPRESSION_EXPANSION | 1 | -13.203% | 0.650 | 31.00% | 100% | 100% | n/a | n/a |
| CONTINUATION | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

結果を見てLOWER_WICKだけを採用するなどの後選択はしていない。これは次案の診断であり、
v1成績を作り直す材料には使わない。

## 🔒 9. Look-ahead / Safety audit

| Audit | 結果 |
|---|---:|
| closed-bar assertion | 377,450 / 377,450 PASS |
| State v2 NOW join | 77,214 / 77,214 |
| future source timestamp violation | 0 |
| Higher-Low pivot timestamp assertions | 60,135 PASS / violation 0 |
| Missing signal values preserved | 1,777,206 |
| Oracle used by decision | false |
| Future Outcome used by decision | false |
| State v2 reference used by decision | false |
| Evaluator inputs parsed before decisions | false |
| Outcome filtering / pivot backdating | false / false |
| Provider requests / Protected data opened | 0 / 0 |
| Safety9 | 9/9 false |
| Overall | **PASS** |

## ✅ 10. Tests・Regression・Replay・CI

| Check | Result |
|---|---:|
| Python compile | PASS |
| Dedicated unit/integration tests | 14 / 14 PASS |
| Immediate baseline parity | PASS |
| 旧Signal-only baseline parity | PASS |
| Deterministic full replay | byte-identical PASS |
| Population preservation | 2,155 / 2,155 PASS |
| GitHub CI | `CI receiptをimplementation commit後に追記` |

## ⚠️ 11. v1の弱点と原因分離

| 原因層 | Evidence | 判定 |
|---|---|---|
| State prediction | UNKNOWN 53.09%。DEFINED同士agreementは91.49%だが、Entry時coverageが低い | 主因の一つ |
| Signal | Breakout/HL/Reclaimは平均的にSelectorより高く買い、Low側改善が弱い | 主因 |
| Timing | mean delay 9.125m、missed upside 0.662%、+3 Capture -14.06pp | 最大の実害 |
| UP routing | 218件をBUY NOWとし、旧Signal待ちよりCaptureを保持 | 正しく機能 |
| DOWN routing | MAEは改善したが、買値・MFE・Captureとのtrade-offが悪い | 不合格 |
| UNKNOWN routing | 1,144件中293 NO ENTRY。Fill損失106件のうち103件がここ | 最大のthroughput bottleneck |

## 🚦 12. 次段階判断

Entry v1には「State conditioningにより旧Signal-onlyを少し上回る」という研究価値は残るが、
Arkの正式Entryとして次段階へ残すには不十分。Immediateに対し価格優位がなく、+3/+5
Opportunityを12–14pp失うため、今すぐEXITへ進む状態ではない。

推奨は **Entry修正を1回だけ**。独立Recognition研究にはせず、次回もEntry pipeline内で、
既存causal primitiveによるUNKNOWN coverageの最小改善と、DOWN/NEUTRALでSignal成立時にも
current Stateの回復を要求するかを事前固定して一度だけ評価する。そこでImmediateとの
Capture差を解消できなければ、State-conditioned waitingを棄却し、Immediate Entryを
固定してEXITへ進む。

この報告でSTOPし、Entry v2、新EXIT、Allocation、Fresh/OOS/Prospective、main merge、
Paper/Live tradingには進まない。

