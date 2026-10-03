# Ark Terminal — State9 Structural EXIT v3 Local Guard

**STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_READY — Evidence完成、ここでSTOP。**

## Primary — Frozen exclusive Entry→High

| Entry→High exclusive | N | 約定 / unresolved（両v同数） | v2 return % 平均 / 中央値 | v3 return % 平均 / 中央値 | Δmean pp | Δmedian pp |
| --- | --- | --- | --- | --- | --- | --- |
| <1% | 619 | 601 / 18 | -1.4692 / -0.9121 | -1.4642 / -0.9089 | 0.0049 | 0.0033 |
| 1–<2% | 297 | 290 / 7 | -0.5129 / -0.1000 | -0.4493 / -0.0597 | 0.0637 | 0.0402 |
| 2–<3% | 213 | 209 / 4 | 0.2702 / 0.7687 | 0.2919 / 0.7687 | 0.0217 | 0.0000 |
| 3–<4% | 130 | 128 / 2 | 0.5604 / 1.4003 | 0.6592 / 1.5220 | 0.0988 | 0.1217 |
| 4–<5% | 83 | 80 / 3 | 0.7628 / 1.4078 | 0.7567 / 1.4078 | -0.0061 | 0.0000 |
| >=5% | 253 | 253 / 0 | 3.9014 / 3.2909 | 3.9283 / 3.1755 | 0.0270 | -0.1155 |
| UNKNOWN | 5 | 0 / 5 | — / — | — / — | — | — |

PrimaryのΔmean/Δmedianは **v3群平均/中央値−v2群平均/中央値**。Entryごとのpaired差分の中央値とは異なる。全paired Δとmetric-specific Nは[EXCLUSIVE_ENTRY_HIGH_PRIMARY.json](EXCLUSIVE_ENTRY_HIGH_PRIMARY.json) / [CSV](EXCLUSIVE_ENTRY_HIGH_PRIMARY.csv)に保存。Unknown5件を含むbucket合計1,600で、Entryやopportunityを再選別していない。

3–<4%群は平均+0.0988pp、中央値+0.1217pp改善した。ただし変わったのはC2件で、そのpaired return改善平均は+6.3213pp。群全体への一般化を証明した結果ではない。4–<5%群は平均−0.0061pp、中央値変化0で、C3件のpaired return平均は−0.1639pp。狙った3–5%群の改善は一様ではなかった。

≥5%全253件は平均return3.9014→3.9283%で微増、中央値3.2909→3.1755%で低下。holding中央値87→85 active minutes、MFE Realization中央値33.3483→32.8053%。平均を保ちつつ中央値と取り逃しに悪化があり、v2 HOLD能力を全面維持したとは判定しない。自動PASS thresholdは置かず、v2維持 / v3採用 / 次の最小修正は人間判断へ渡す。

Document: `WORK_STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_FASTTRACK_20261003`。作成: 2026-10-03T20:22:56.227245+09:00。開始actual GETはv2 FINAL `823fe3a7203e58fbc20fa73acab1d77e1da62c8e` と一致。Frozen Entry1,600変更0、v2 Full trace/Path exact reuse。v3 position Replayのみ1回、v2 Replay / Entry refit / State9・Path reconstructionは0。

## ≥5% Winner protection — 全253件

| metric | v2 N | v2 平均 / 中央値 | v3 N | v3 平均 / 中央値 | 共通N | paired Δ 平均 / 中央値 |
| --- | --- | --- | --- | --- | --- | --- |
| realized return % | 253 | 3.9014 / 3.2909 | 253 | 3.9283 / 3.1755 | 253 | 0.0270 / 0.0000 |
| MFE Realization % | 253 | 30.1795 / 33.3483 | 253 | 30.5096 / 32.8053 | 253 | 0.3300 / 0.0000 |
| pre-sell observed peak giveback pp | 250 | 3.8026 / 2.3193 | 250 | 3.7011 / 2.3641 | 250 | -0.1014 / 0.0000 |
| full-session observed Peak Giveback pp | 253 | 7.2477 / 5.2862 | 253 | 7.2208 / 5.1502 | 253 | -0.0270 / 0.0000 |
| later missed upside % | 161 | 7.3082 / 5.2670 | 163 | 7.3948 / 5.3158 | 161 | 0.1466 / 0.0000 |
| holding active minutes | 253 | 115.2530 / 87.0000 | 253 | 113.1660 / 85.0000 | 253 | -2.0870 / 0.0000 |
| EXIT→later High active minutes | 161 | 61.8261 / 35.0000 | 163 | 62.1963 / 35.0000 | 161 | 0.6894 / 0.0000 |

| 指標 | v2 | v3 |
| --- | --- | --- |
| sell-filled / unresolved | 253 / 0 | 253 / 0 |
| EXIT-before-final-observed-High rate % | 44.2688 | 46.2451 |
| EXIT-C N | — | 17 |

≥5%群のpre-sell givebackは平均3.8026→3.7011pp（平均改善、中央値は2.3193→2.3641pp）。Full-session Givebackは平均7.2477→7.2208pp。later missed upsideは観測Nが161→163へ増えるため、単純群平均の+0.0865ppと共通161 Entryのpaired平均+0.1466ppを区別する。EXIT-before-final-High率は44.2688→46.2451%へ増えた。

## EXIT-C専用 — 43件

| metric | v2 N | v2 平均 / 中央値 | v3 N | v3 平均 / 中央値 | 共通N | paired Δ 平均 / 中央値 |
| --- | --- | --- | --- | --- | --- | --- |
| realized return % | 43 | 0.3812 / -0.6951 | 43 | 1.4261 / 0.1151 | 43 | 1.0449 / 0.7971 |
| MFE Realization % | 41 | -157.6714 / -25.9237 | 41 | -97.2824 / 9.9293 | 41 | 60.3890 / 23.9011 |
| pre-sell observed peak giveback pp | 43 | 4.6730 / 3.6422 | 43 | 3.0609 / 2.4187 | 43 | -1.6120 / -0.9726 |
| full-session observed Peak Giveback pp | 43 | 5.2908 / 4.0313 | 43 | 4.2458 / 3.2193 | 43 | -1.0449 / -0.7971 |
| later missed upside % | 29 | 3.0767 / 1.5659 | 43 | 2.9391 / 1.9927 | 29 | 0.5878 / 0.0000 |
| holding active minutes | 43 | 122.0233 / 99.0000 | 43 | 65.5814 / 42.0000 | 43 | -56.4419 / -26.0000 |
| EXIT→later High active minutes | 29 | 45.9310 / 27.0000 | 43 | 43.5349 / 20.0000 | 29 | 4.7241 / 3.0000 |

| 指標 | N | 平均 / 中央値 |
| --- | --- | --- |
| v2 intent/planned closeより早い active minutes | 43 | 56.4651 / 26.0000 |
| v2 sell fillより早い active minutes | 43 | 56.4419 / 26.0000 |
| paired return Δ pp | 43 | 1.0449 / 0.7971 |
| paired pre-sell giveback Δ pp | 43 | -1.6120 / -0.9726 |
| paired later missed upside Δ pp | 29 | 0.5878 / 0.0000 |

| v2保存済みならintent理由 | C N |
| --- | --- |
| SESSION_CLOSE | 14 |
| UP_STRUCTURE_RETIRED_BY_RANGE | 8 |
| UP_STRUCTURE_REVERSED | 21 |

C43件はmain context=UPのまま、effective guard>main protected、Close<=guard−0.5Uを満たした。break時Primaryは43件ともPULLBACKだが、Primary文字列をSELL条件には使っていない。1,557件のnon-Cではv2保存済みintent・fillと全件同一。Cはv2より早いintentを持つが、Cが必ず利益を保証するわけではない。C群v3 return中央値は+0.1151%、negative19件。

C群のpre-sell giveback paired平均−1.6120ppは「売るまでに返した利益」の減少。一方、later High共通観測29件のmissed upside paired平均は+0.5878pp。単純later-missed群平均3.0767→2.9391%だけを見ると改善に見えるが、分母は29→43件で異なる。売却後に伸びた幅を減ったgivebackへ混ぜていない。

| exclusive bucket | C N | paired return Δ pp 平均 / 中央値 | pre-sell giveback paired Δmean pp | missed upside 共通N | missed upside paired Δmean pp |
| --- | --- | --- | --- | --- | --- |
| <1% | 11 | 0.2692 / 0.3226 | -0.2815 | 9 | 0.0176 |
| 1–<2% | 6 | 3.0772 / 2.0059 | -3.0772 | 1 | -0.9725 |
| 2–<3% | 4 | 1.1326 / 1.0890 | -1.1326 | 2 | -0.1521 |
| 3–<4% | 2 | 6.3213 / 6.3213 | -6.3213 | 1 | -6.9882 |
| 4–<5% | 3 | -0.1639 / -0.6581 | -1.7409 | 1 | 1.5528 |
| >=5% | 17 | 0.4016 / 0.0000 | -1.4919 | 15 | 1.5733 |
| UNKNOWN | 0 | — / — | — | 0 | — |

## ≥5% WinnerのEXIT-C subgroup — 17件

| metric | v2 N | v2 平均 / 中央値 | v3 N | v3 平均 / 中央値 | 共通N | paired Δ 平均 / 中央値 |
| --- | --- | --- | --- | --- | --- | --- |
| realized return % | 17 | 5.1314 / 4.9934 | 17 | 5.5330 / 4.2781 | 17 | 0.4016 / 0.0000 |
| MFE Realization % | 17 | 33.8127 / 48.5421 | 17 | 38.7246 / 51.1838 | 17 | 4.9119 / 0.0000 |
| pre-sell observed peak giveback pp | 17 | 5.2683 / 4.2312 | 17 | 3.7764 / 3.2087 | 17 | -1.4919 / -0.9726 |
| full-session observed Peak Giveback pp | 17 | 6.6705 / 5.8805 | 17 | 6.2690 / 4.2609 | 17 | -0.4016 / 0.0000 |
| later missed upside % | 15 | 4.1994 / 2.2562 | 17 | 5.3950 / 3.6002 | 15 | 1.5733 / 0.4751 |
| holding active minutes | 17 | 99.5882 / 88.0000 | 17 | 68.5294 / 42.0000 | 17 | -31.0588 / -14.0000 |
| EXIT→later High active minutes | 15 | 49.8667 / 24.0000 | 17 | 54.8235 / 20.0000 | 15 | 7.4000 / 3.0000 |

| 指標 | v2 | v3 / paired |
| --- | --- | --- |
| return group中央値 % | 4.9934 | 4.2781 |
| paired return Δ mean / median pp | — | 0.4016 / 0.0000 |
| intent advance active minutes 平均 / 中央値 | — | 31.0000 / 14.0000 |
| EXIT-before-final-High rate % | 41.1765 | 70.5882 |

この17件のreturn平均5.1314→5.5330%、中央値4.9934→4.2781%。paired return平均+0.4016pp / 中央値0で、群中央値差−0.7153ppとは別の値。pre-sell giveback paired平均−1.4919ppに対して、later High共通15件のmissed upside paired平均+1.5733pp。C後later Highの価格・時刻・active minutesはprivate `EXIT_C_ROWS.jsonl.gz` の全17個別行に保存。

## Local Guard mechanics

| Mechanic | N |
| --- | --- |
| Entry後local pivot observed | 20126 |
| 既知prefix local pivot | 35976 |
| LHL eligible unique suffix | 1249 |
| higher-low unique suffix | 777 |
| guard creation events | 291 |
| guard tighten events | 78 |
| unique positions with guard | 245 |
| guard never established | 1355 |
| guard reset with level | 163 |
| guard break | 43 |

| metric | N | 平均 / 中央値 |
| --- | --- | --- |
| guard−main distance at activation U | 369 | 7.1389 / 3.8297 |
| guard age since creation at break bars | 43 | 7.0000 / 5.0000 |
| guard age since last update at break bars | 43 | 3.9535 / 3.0000 |

| break preceding3 distinct Primary | N |
| --- | --- |
| DROP>RISE>PULLBACK | 1 |
| PULLBACK>DROP_STOP>PULLBACK | 1 |
| PULLBACK>RISE>PULLBACK | 26 |
| PULLBACK>SHARP_RISE>PULLBACK | 2 |
| RANGE>RISE>PULLBACK | 1 |
| RANGE>SHARP_RISE>PULLBACK | 1 |
| REBOUND>RISE>PULLBACK | 1 |
| RISE>SHARP_RISE>PULLBACK | 7 |
| SHARP_RISE>RISE>PULLBACK | 3 |

Guard成立245 position（15.3125%）、C43 position（2.6875%）。Guard未成立1,355件。LHL eligibleはsame-segment・previous-bar suffixのunique組、higher-low適格組を別count。creation291はreset/re-arm後の再成立を含み、unique positions245と異なる。現在足のconfirmationは判定後にappendし、guardはt+1有効。guardを下げず、gap/reset/null時に持ち越さない。既知same-segmentのEntry/arm前pivotはinput-historyとして利用し、Entry時guardはunset。同時A/Bがあればv2理由を優先し、予定closing clockと同足のCへ付け替えない。

## All-entry economics

| metric | v2 N | v2 平均 / 中央値 | v3 N | v3 平均 / 中央値 | 共通N | paired Δ 平均 / 中央値 |
| --- | --- | --- | --- | --- | --- | --- |
| realized return % | 1561 | 0.0926 / -0.1000 | 1561 | 0.1214 / -0.1000 | 1561 | 0.0288 / 0.0000 |
| MFE Realization % | 1394 | -158.6462 / 1.8525 | 1394 | -156.8700 / 3.2811 | 1394 | 1.7761 / 0.0000 |
| pre-sell observed peak giveback pp | 1539 | 2.2650 / 1.4033 | 1539 | 2.2200 / 1.3966 | 1539 | -0.0450 / 0.0000 |
| full-session observed Peak Giveback pp | 1561 | 2.9416 / 1.6701 | 1561 | 2.9128 / 1.6545 | 1561 | -0.0288 / 0.0000 |
| later missed upside % | 473 | 3.5116 / 1.5659 | 487 | 3.4870 / 1.6012 | 473 | 0.0360 / 0.0000 |
| holding active minutes | 1561 | 126.5227 / 114.0000 | 1561 | 124.9680 / 114.0000 | 1561 | -1.5548 / 0.0000 |
| EXIT→later High active minutes | 473 | 44.5962 / 22.0000 | 487 | 44.4230 / 21.0000 | 473 | 0.2896 / 0.0000 |

| 指標 | v2 | v3 |
| --- | --- | --- |
| Entry / filled / unresolved | 1600 / 1561 / 39 | 1600 / 1561 / 39 |
| positive rate % | 45.0993 | 45.4837 |
| negative N | 857 | 851 |
| negative return mean / median % | -1.9955 / -1.1290 | -1.9589 / -1.1084 |
| worst return % | -27.1000 | -27.1000 |
| <−1% N / <−2% N (診断のみ) | 467 / 267 | 455 / 262 |

v3 reasons: EXIT-A294、EXIT-B155、EXIT-C43、SESSION_CLOSE1069、UNRESOLVED39。Entry +5bps二重計上0、sell adverse5bps、commission0。Closing source欠落39件は既存のままUNRESOLVED、last-observed Close補完0。Entry→arm timestampは全1,600件でv2と一致し、PREで新しいSELLやEntry再filterを追加していない。

## Exact reuse / audit / limitations

v2 saved ZIP SHA: `31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89`。1,606 components、Full trace1,600本 / 523,200 scheduled endpoints、Frozen Entry原本gzip、v2 saved outcomes全てhash一致。6 Frozen pins一致、v2 base lifecycle byte SHA=`6cf642d3d8d7b00422245d1308d3b07cbf507b7fbd9859e61aba596c0b5bcdb5`。State9/Path semantic変更0、Full reconstruction0、v2 Replay0、Frozen Entry opportunity evaluator rerun0。

別logic全件監査: **1,210,542 checks、mismatch=0、future causal leakage=0、lineage mismatch=0**。Primaryのguard/base/fill/evaluatorをimportせず、Boolean latch、segment内pivot ledger、Fraction arithmetic、calendar/fill/economicsを別実装。共通依存は保存済みimmutable trace/raw/opportunity、Python runtime、I/O/hashのみ。外部reviewer監査を称していない。Historical actual_known_atはUNKNOWN、因果検算はv2と同じbar_end availability仮定内に限る。

| Audit No. | 要求 | 結果 |
| --- | --- | --- |
| 1 | Frozen Entry identity | PASS |
| 2 | v2 Full trace exact hash reuse | PASS |
| 3 | no State9/Path reconstruction | PASS |
| 4 | local pivot exact source bytes/fields | PASS |
| 5 | pivot confirmed_at causality | PASS |
| 6 | L0/H0/L1 ordering | PASS |
| 7 | same segment | PASS |
| 8 | confirmed_at<t | PASS |
| 9 | higher-low condition | PASS |
| 10 | H0+delta progress | PASS |
| 11 | guard effective next bar | PASS |
| 12 | guard monotonicity | PASS |
| 13 | no cross-segment carry | PASS |
| 14 | EXIT-C exact break arithmetic | PASS |
| 15 | EXIT-C requires context still UP | PASS |
| 16 | A/B/C precedence | PASS |
| 17 | first valid intent only | PASS |
| 18 | canonical next-open sell5bps | PASS |
| 19 | v2 saved-result join identity | PASS |
| 20 | exclusive High denominators | PASS |
| 21 | paired return delta | PASS |
| 22 | giveback/missed upside | PASS |
| 23 | post-exit decision0 | PASS |
| 24 | model/teacher/search0 | PASS |
| 25 | Re-entry/Capital0 | PASS |

Full-session source completenessはv2からread-onlyで引き継ぎ、complete55/1600、observed High既知1595、UNKNOWN5。≥5%群のcompleteは7/253。observed Highに到達したWinnerであり、欠測部分を含むcomplete-session opportunityへ読み替えない。未観測later Highのnullは0に変えず、missed upsideのpaired共通Nを必ず併記した。

初回public source保存で末尾空行を落としたローカルcopyを、取得済みGitの完全なtext bytesから修正し、19 public source/result filesをmanifest hashへ一致させてからS0を固定した。Frozen objects自体の変更0。監査table selectorのSESSION_CLOSE intent=None参照を修正し、全件監査を完了した。S0 contract/decision codeは結果後も変更0、primary Replay再実行0、追加candidate0。[AUDIT_VALIDATOR_CORRECTION.json](AUDIT_VALIDATOR_CORRECTION.json)参照。

## 必須17回答 / STOP

| No. | 必須回答 | 結果 |
| --- | --- | --- |
| 1 | v2 Full trace再構築なしexact reuse | はい。Full trace1,600本のexact hash照合。State9/Path reconstruction0。 |
| 2 | State9/Path semantics変更 | 0。Frozen6 pins、main A/B/PRE/quality byte identity。 |
| 3 | LOCAL_GUARD成立 | 245 unique positions、creation291、tighten78。 |
| 4 | EXIT-C発火 | 43件。全件context=UP、exact guard break。 |
| 5 | v2より中央値何分早い | intent・fillとも26 active minutes（N43）。>=5 C群は14分（N17）。 |
| 6 | exclusive各bucket v2→v3 return差 | Primary表に全6群+UNKNOWNを保存。Δmean pp: +0.0049,+0.0637,+0.0217,+0.0988,−0.0061,+0.0270。 |
| 7 | 3–<4%改善 | 平均+0.0988pp、群中央値+0.1217pp。C2件の効果。 |
| 8 | 4–<5%改善 | 平均−0.0061pp、中央値変化0。C3件の平均delta−0.1639pp。 |
| 9 | >=5% return維持/改善か | 平均3.9014→3.9283%は微増、中央値3.2909→3.1755%は低下。holding87→85分。全面維持とは判定しない。 |
| 10 | >=5% C件数・paired損益 | 17件。return5.1314/4.9934→5.5330/4.2781%、pairedΔmean+0.4016pp / median0。 |
| 11 | pre-sell giveback変化 | 全体paired平均−0.0450pp、C43件−1.6120pp、>=5 C17件−1.4919pp。 |
| 12 | later missed upside変化 | 共通knownで全体+0.0360pp（N473）、C+0.5878pp（N29）、>=5 C+1.5733pp（N15）。 |
| 13 | PULLBACK/RISE_STOP単独SELL | 0。C全件の独立structural条件を検算。State文字列/stop count/dwell単独も0。 |
| 14 | fixed% stop/profit/trailing | 全て0。唯一bufferはFrozen0.5Uで、variants0。 |
| 15 | audit mismatch / future leakage | 0 / 0。historical actual_known_at UNKNOWN、bar_end仮定内。 |
| 16 | Re-entry/Capital | 0。Portfolio/orders/main mergeも0。 |
| 17 | 人間判断用Evidence | 全10 Completion Gateまで完成。三checkpointのFINALでSTOP。正式採用Freezeへ進まない。 |

New EXIT policies=1、local guard variants=1。それ以外のfit/teacher/score/rank/OOF/search/provider/new market data/Entry replay/refit/State/Path reconstruction/v2 Replay/old EXIT Replay/Hard1/fixed stop/trailing/Protected/Fresh/Validation/OOS/Prospective/Re-entry/Capital/Portfolio/orders/main merge/force pushは0。全10 safety flags=false、LONG-only / cash-equity-only、productionReady=false。

Git checkpointsはV3_S0_START_AND_CONTRACT、V3_S1_REPLAY_AND_EVALUATION、V3_FINAL_AUDIT_AND_EVIDENCEのみ。保存はactual saved_at_jst / actual basis_headを記録し、commit後actual GETでresult HEADを確認。未来SHAを埋め込まない。個別Evidenceは[PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json](PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json)、保存成功は[PRIVATE_EVIDENCE_SAVE_RECEIPT.json](PRIVATE_EVIDENCE_SAVE_RECEIPT.json)。**ここでSTOP。**
