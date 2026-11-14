# Phase57 Guard-first EXIT — Development Phase 0 最終報告

作成：2026-09-29 JST。対象：`Iam-2squared/ark-terminal` の Draft PR #587、`research/phase57-long-only-cash-equity`。今回のOutcomeは、結果閲覧前に保存した `CYCLE_PRECOMMIT.json`（SHA-256 `1b7bc9d41333958e3bb1cc5845d044427f107ebf6824f6a8975ab37eaa58293d`）に従う。

## 🧭 Current Status

**`GUARD_FEASIBILITY_UNMEASURABLE / NO_SELECTION / selected=null / productionReady=false`**。

| 固定境界 | 内容 |
|---|---|
| Selector / Entry | Frozen / IMMEDIATE と ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF |
| Entry Dual Freeze | `4878a1cc53430e816261dea0fb16aeb53b3c238d` |
| Capital / Control EXIT | Saved Capital v3 B / R50_A_LIFECYCLE |
| 資本・数量 | ¥1,000,000、100株単位、MAX3、現物LONGのみ |
| Source | 既存Development R45・R54・R34、全ZIPとraw pathのpin一致 |
| 実施量 | 新規estimator fit 0、Integrated Replay 0、新規候補0 |

R54の訂正済みcycleはClosed、WPSDは既存Phase 0 NO-GOのまま。どちらの負の結果も今回のGuard評価へ再選抜していない。各Entry armは代替世界なので、合算した件数を独立した取引実績と呼ばない。

## 🔬 Phase 0A — Coverage / power

既存の `postEntryUpsidePct` は同一sessionのEntry後Highから作ったevaluator-only教師であり、R50_Aの早期Control EXIT後を含み得る。Entry時点では未知で、runtime特徴量には入れない。今回の1,614件ではラベル欠測は0。

| Entry arm | 全Entry | ≥1% | ≥2% | ≥3% | ≥5% | ≥10% |
|---|---:|---:|---:|---:|---:|---:|
| IM | 819 | 540 | 395 | 283 | 158 | 66 |
| R1 | 795 | 505 | 364 | 262 | 143 | 60 |
| Combined（代替armの行数） | 1,614 | 1,045 | 759 | 545 | 301 | 126 |

| Potential head | 陽性 | 陰性 | 陽性session | 事前固定AUC=.60検出Power | Power Gate |
|---|---:|---:|---:|---:|---|
| ≥5% | 301 | 1,313 | 24 | 99.6% | PASS |
| ≥10% | 126 | 1,488 | 23 | 95.4% | PASS |

Powerは実特徴量を使わない、固定seed 570928系の1,000反復・各199回session bootstrapシミュレーション。これは予測skillの実測ではない。

Control保有区間内のHigh到達は、欠測を跨がずに順序を証明できる場合だけ `REACHED`。+5%はIM 48、R1 48、+10%はIM 18、R1 14。最終High教師の≥5%=301、≥10%=126と同じ意味ではない。途中の1分barが欠けた区間を勝手に到達済み・未到達へ補完していない。

## 📈 Phase 0B — Milestone / giveback

同一bar内の上限touchとfloor割れは `AMBIGUOUS_SAME_BAR` としてUNKNOWN。以下は全1,614 Entryに対するControl保有区間の遷移。後続のmilestone到達に失敗したことと、順序を観測できないことは別の分類。

| 遷移 | Upper first | Floor first | Same-bar曖昧 | Missing / prior missing | Control terminal first |
|---|---:|---:|---:|---:|---:|
| +1→+2、floor 0 | 114 | 103 | 205 | 1,078 | 114 |
| +2→+3、floor +1 | 82 | 47 | 134 | 1,199 | 152 |
| +3→+5、floor +2 | 28 | 49 | 96 | 1,262 | 179 |
| +5→+10、floor +3 | 14 | 43 | 19 | 1,311 | 227 |

上表の行ごとの計は1,614。+10到達後floor +5の保護は別診断で、次の+15 milestoneを仮定していない。Givebackは候補exitではなく、**完全観測されたControl保有prefix** のhighと最終closeとの差である。≥5% Winnerの完全prefixはIM 26/158、R1 30/143。≥10%はIM 8/66、R1 10/60。少数の既知例の中央値を全WinnerのGivebackだと扱わない。

| Control-prefix Winner bucket | IM既知N | IM中央値pp | R1既知N | R1中央値pp |
|---|---:|---:|---:|---:|
| 5–10% | 18/92 | 3.79 | 20/83 | 4.92 |
| ≥10% | 8/66 | 7.61 | 10/60 | 7.61 |

## 🚧 Guard Feasibility — **UNMEASURABLE**

PrecommitはWinnerが目標milestoneへ届く前の各prior floor遷移をexactに判定できるEntry coverageを80%以上、既知20件以上、8session以上と固定した。≥5 Winnerは+1→+2→+3→+5、≥10 Winnerはさらに+5→+10を対象とする。

| Winner cohort | 全件 | exact既知 | coverage | 必要coverage | floor先行（既知内） | session平均（既知内） | 2 checkpoint未回復（floor先行内） |
|---|---:|---:|---:|---:|---:|---:|---:|
| ≥5% | 301 | 57 | 18.9% | 80% | 49/57 = 86.0% | 92.3% | 14/49 |
| ≥10% | 126 | 30 | 23.8% | 80% | 30/30 = 100% | 100% | 10/30 |

既知部分のfloor先行率は高いが、unknown・same-bar・Control終了例を含む全Winnerの過半にその率を外挿できない。**確定した停止理由はcoverage Gate不達**。floor/ladder/確認回数を変えず、Guard候補の実装とReplayを行わない。

## 🔮 Entry Potential — Power PASS、skill未測定

| Head | N+ | Sessions+ | AUC | 95% CI | PR-AUC | Brier vs Base | LogLoss vs Base | Status |
|---|---:|---:|---|---|---|---|---|---|
| ≥5% | 301 | 24 | 未測定 | 未測定 | 未測定 | 未測定 | 未測定 | `POTENTIAL_FEATURE_SCHEMA_AMBIGUOUS` |
| ≥10% | 126 | 23 | 未測定 | 未測定 | 未測定 | 未測定 | 未測定 | 同上 |

R1の凍結済みEntry artifactには566列の名前と149,900行のrow metadataはあるが、manifest記載の`features.npy`は公開ZIPに含まれない。IMの凍結Entryレコードにもそれと同一のEntry時点feature arrayはない。Selectorのscore/rankは因果的な縮約情報だが、その2列だけをPotential用schemaと選ぶことは新しい特徴量設計になる。R45 EXIT checkpoint featuresはEntry後。結果閲覧後にこれらから都合の良いschemaを選ばず、**fit 0、OOF予測0**で閉じた。PotentialにHOLD・SELL・Guard・Capital authorityはない。

## 🧠 Survival — Coverage NO-GO

| Arm | ALERT | exact t+30 | Positive | Negative | UNKNOWN |
|---|---:|---:|---:|---:|---:|
| IM | 844 | 469 | 184 | 285 | 375 |
| R1 | 802 | 422 | 186 | 236 | 380 |
| Combined | 1,646 | 891（54.1%） | 370 | 521 | 755 |

要件70%を下回り、Survival fitは0。欠測は時間依存で、EARLY 108/375、MID 268/614、LATE 379/657。UNKNOWNを0/1へ置換せず、30分以外のheadも追加していない。

## 🏆 Winner Preservation / 🛡 Profit Preservation / 📉 Loser Non-Degradation

Guard candidateがGate前に存在しないため、Layer AのIM/R1 ≥5/≥10 exact Net/PnL、milestone retention、候補giveback、<1/1–3/3–5 Loser非悪化は**いずれも未実行**。Control-prefixの記述値を候補のPASSへ転用しない。

## 🌐 All-entry / 💴 Capital / 📊 Portfolio / 🧪 Stress

| 対象 | 今回の状態 |
|---|---|
| all-entry standalone | Phase 0のIM819/R1 795診断のみ。候補100株EXITは未実行 |
| fixed Capital integrated Replay / 0.20pp stress | 0/22 invocations / 未実行 |
| replacement・utilization・cash lock | 新候補について未測定 |
| 24-session Final Equity / MaxDD / daily | 新候補について未測定 |
| R54の既知mark/auction blocker | `2025-07-23|62650|883`、`2025-08-04|36700|602`。今回の新規測定結果ではない |

## 🔁 Reproducibility / 🔒 Safety

独立スクリプトは元のraw pathから8,070件のmilestone reach、8,070件の遷移、1,646 ALERTと30分教師の陽性370／陰性521／UNKNOWN755を再計算して一致。保存済みR45・R54・R34 ZIPとraw pathのSHA pinが一致。Phase 0 focused unit testは5/5 PASS。GitHub専用再生成CIの結果は別receiptで記録する。

| 指標 | 今回 |
|---|---:|
| 新規estimator fits / integrated Replay | 0 / 0 |
| 新規provider request / Protected・Fresh・Validation・OOS開封 | 0 / 0 |
| Orders / main merge | 0 / 0 |

Safety9（execution、broker、Excel order、RSS order、live、paper、promotion、production、transmission）はすべてfalse。

## 🎯 Month 2x / ✅ Final

¥1,000,000→約¥2,000,000／24sessionと日次幾何約+2.93%はNorth Starとして保持する。新候補のcertified equityがないので、到達・不足額・日次gapはいずれも **ARK_MONTH_2X_UNMEASURABLE**。

`selected=null / productionReady=false`。次のEXIT研究は、今回のfloorやPower結果を見て追加閾値を選ぶ継続runではなく、欠測と保有区間のfirst-passage可観測性を解決できる新しい事前固定architecture cycleが必要。Protected/Fresh/OOSを開けない。

## 🖼 Figures

1. [Entry→milestone reach](figures/01_entry_to_milestone_reach.png)
2. [最終High bucket](figures/02_milestone_bucket_counts.png)
3. [floor first / upper first / unknown](figures/03_first_passage_status.png)
4. [≥5 WinnerのControl-prefix giveback](figures/04_winner_ge5_control_prefix_giveback.png)
5. [≥10 WinnerのControl-prefix giveback](figures/05_winner_ge10_control_prefix_giveback.png)
6. [floor breach後のrecovery curve](figures/06_breach_recovery_curve.png)

Guard exit event-time、Potential reliability 2図、equity curveは該当候補fit/Replayが停止されたため作れない。空欄や仮値の図は作らない。
