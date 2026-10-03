# Ark Terminal — State9 Structural EXIT v4 Recovery-Failure

Status: **V4_NOT_BETTER_KEEP_V3**。V3無変更fallback保持。Evidence完成後STOP。

| Observed Entry→High exclusive | watches | V3/V4 filled | unresolved | V3 return mean / median % | V4 return mean / median % | Δmean pp | Δmedian pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2–<3% | 213 | 209 / 209 | 4 / 4 | +0.2919 / +0.7687 | +0.3015 / +0.7478 | +0.0097 | -0.0210 |
| 3–<4% | 130 | 128 / 128 | 2 / 2 | +0.6592 / +1.5220 | +0.6438 / +1.2999 | -0.0154 | -0.2221 |
| 4–<5% | 83 | 80 / 80 | 3 / 3 | +0.7567 / +1.4078 | +0.9440 / +1.6909 | +0.1873 | +0.2831 |
| 2–<5%_COMBINED | 426 | 417 / 417 | 9 / 9 | +0.4938 / +1.0893 | +0.5298 / +1.0483 | +0.0360 | -0.0410 |
| >=5%_PROTECTION | 253 | 253 / 253 | 0 / 0 | +3.9283 / +3.1755 | +3.9351 / +3.1297 | +0.0067 | -0.0457 |

returnは同一watch_keyの共通sell-filled母集団。2–<5 combinedは417件、>=5は253件。Δmean/medianは群統計の差であり、各Entry paired delta中央値とは区別する。UNKNOWN5件、全体unresolved39件を0補完しない。

## 判定と意味

2–<5 combined平均は+0.4938%→+0.5298%だが、中央値は+1.0893%→+1.0483%。既定の中央値厳密改善条件を満たさずV4不採用。3–<4%群も平均・中央値が低下。4–<5%群は改善したが、同Work内でDをそのbucket専用に変更することはしない。>=5%平均は微増、中央値は低下し、holding中央値85→68 active minutes。V3をFreeze候補として保持する。

| fixed conservative condition | result |
| --- | --- |
| combined_mean_strictly_greater | PASS |
| combined_median_strictly_greater | FAIL |
| three_exclusive_means_nonworse | FAIL |
| at_least_two_exclusive_means_strictly_greater | PASS |
| GE5_mean_nonworse | PASS |
| GE5_median_nonworse | FAIL |
| audit_zero | PASS |

2–<5%群D41件中、paired return増加20、減少19、同値2。群全417件のdelta同値は378件。最大1件の正寄与は10.6845pp、net平均改善の約71.1%を占める。最大正寄与1件除外でも平均deltaは+0.0104pp残るが、primary中央値改善と3–<4%改善は成立しない。少数case依存の新しい数値FAIL閾値は作らず、既定中央値Gateで結論を確定した。

## >=5% protection

| >=5% quality | V3 mean / median | V4 mean / median | paired Δ mean / median | common N |
| --- | --- | --- | --- | --- |
| return % | +3.9283 / +3.1755 | +3.9351 / +3.1297 | +0.0067 / +0.0000 | 253 |
| MFE Realization % | +30.5096 / +32.8053 | +31.7333 / +34.6925 | +1.2237 / +0.0000 | 253 |
| pre-sell observed giveback pp | +3.7011 / +2.3641 | +3.4989 / +2.3697 | -0.2023 / +0.0000 | 250 |
| full observed window Peak Giveback pp | +7.2208 / +5.1502 | +7.2140 / +5.0843 | -0.0067 / +0.0000 | 253 |
| later missed upside % | +7.3948 / +5.3158 | +7.3858 / +5.2250 | +0.1320 / +0.0000 | 163 |
| holding active minutes | +113.1660 / +85.0000 | +107.3676 / +68.0000 | -5.7984 / +0.0000 | 253 |

EXIT-before-final-observed-High率: V3 46.2451%→V4 49.4071%。D46件。later missedの母数は163→171件、真正paired共通163件の平均deltaは+0.1320pp。増加を単独FAILにはしていない。

>=5% D46件: return平均/中央値 +3.4770 / +2.9736→+3.5140 / +2.9799%。paired return delta +0.0370 / +0.1386pp。pre-sell giveback paired -1.0993 / -0.4652pp（46件）。later missed paired +0.5662 / -0.1450pp（共通38件、raw observed母数38→46）。D後later Highと時刻、missed upside、advanceを個別EXIT_D_ROWSに保存。

## EXIT-D診断と機構

Floor成立414 position（25.875%）、creation537、tighten180、reset263、never1186。全127 Dはmain context UPのまま。intent advance平均47.7323／中央値14分、sell advance平均47.6535／中央値13分。holding中央値の89→40分という群差を、paired advance中央値と混同しない。negative→positive17、positive→negative10。

D群return平均/中央値 +0.7338 / +0.1151→+0.9918 / +0.4923%。真正paired delta +0.2580 / +0.0000pp。pre-sell givebackは共通126件で-0.8100 / -0.3665pp。later missedは共通89件で+0.3862 / +0.0000pp。売る前に返した幅と売った後の上伸を別に保存している。

| exclusive | D N | paired return Δ mean / median pp | pre-sell giveback Δ pp / N | later missed upside Δ pp / N |
| --- | --- | --- | --- | --- |
| <1% | 26 | +0.4083 / +0.0332 | -0.3669 / +0.0000 / 25 | +0.0086 / +0.0000 / 18 |
| 1–<2% | 14 | +0.3866 / -0.0262 | -0.4542 / +0.0262 / 14 | +0.7330 / +0.0523 / 7 |
| 2–<3% | 14 | +0.1441 / +0.2851 | -0.7225 / -0.4522 / 14 | +0.0869 / +0.2131 / 8 |
| 3–<4% | 15 | -0.1313 / -0.1010 | -0.4922 / +0.0000 / 15 | +0.4706 / +0.1873 / 8 |
| 4–<5% | 12 | +1.2486 / +0.6915 | -1.5386 / -0.8896 / 12 | +0.3111 / +0.5090 / 10 |
| >=5% | 46 | +0.0370 / +0.1386 | -1.0993 / -0.4652 / 46 | +0.5662 / -0.1450 / 38 |
| UNKNOWN | 0 | — / — | — / — / 0 | — / — / 0 |

| V3 would exit via | D N | V3 return mean / median % | V4 return mean / median % | paired return Δ pp | intent / sell advance median active min |
| --- | --- | --- | --- | --- | --- |
| A: main reversal | 47 | -0.3672 / -0.3973 | +0.9360 / +0.7824 | +1.3032 / +0.5709 | 5 / 6 |
| B: RANGE retirement | 34 | +2.8221 / +1.9026 | +1.8597 / +1.3960 | -0.9624 / -0.4914 | 9.0 / 9.0 |
| C: mature Guard break | 8 | +0.4444 / -0.3086 | +0.2769 / -0.4179 | -0.1675 / -0.0051 | 5.5 / 5.5 |
| SESSION_CLOSE | 38 | +0.2882 / -0.3478 | +0.4348 / +0.0207 | +0.1466 / -0.0781 | 86.5 / 85.0 |

主改善対象のV3 EXIT-A 79件のうち16件をDが先行。この固定79件のreturn平均/中央値は-0.2269 / -0.1000→+0.0553 / +0.0791%。ただしcombined primary中央値は低下したため、この部分改善だけで採用しない。

floor-to-main distance at activation平均/中央値 +11.3515 / +7.2010U（717 updates）。break ageはcreationから平均4.5512／中央値3 bars、last updateから平均2.5512／中央値2 bars。break Primary/contextはPULLBACK/UP 127件。これは観測結果であり、PULLBACK文字列のSELL ruleではない。前3 distinct Primary、pivot exact fields、floor effective timestamps/resetと全updateを各position metadataに保存。

## EXIT理由別

| V4 exit reason | N | return mean / median % | MFE realization % | pre-sell giveback pp | holding active min | later missed upside % |
| --- | --- | --- | --- | --- | --- | --- |
| A: main reversal | 247 | +0.2863 / -0.3535 | -188.6048 / -8.6762 | +2.6279 / +1.8356 | +55.1498 / +39.0000 | +4.0095 / +1.6760 |
| B: RANGE retirement | 121 | +0.1062 / +0.0483 | -105.8556 / +10.6458 | +1.9783 / +1.1391 | +58.8926 / +40.0000 | +2.8607 / +1.3007 |
| C: mature Guard break | 35 | +1.6505 / +0.2718 | -56.2486 / +11.0458 | +3.1878 / +2.4537 | +59.9143 / +31.0000 | +2.9892 / +1.9927 |
| D: recovery failure | 127 | +0.9918 / +0.4923 | -74.8187 / +9.6994 | +2.5461 / +1.9635 | +62.0787 / +40.0000 | +3.1086 / +1.7750 |
| SESSION_CLOSE | 1031 | -0.0437 / -0.1000 | -166.4143 / +8.8786 | +1.9759 / +1.2633 | +153.5344 / +164.0000 | — / — |
| UNRESOLVED | 39 | — / — | — / — | — / — | — / — | — / — |

各metricの有効NはJSON/CSVに明示。N不一致は補完しない。理由×exclusiveの全内訳と各metricはV4_EXIT_REASON_EXCLUSIVEにも保存。

| V4 reason | exclusive bucket watches |
| --- | --- |
| A: main reversal | 1–<2%: 39; 2–<3%: 27; 3–<4%: 21; 4–<5%: 15; <1%: 66; >=5%: 79 |
| B: RANGE retirement | 1–<2%: 27; 2–<3%: 14; 3–<4%: 6; 4–<5%: 5; <1%: 36; >=5%: 33 |
| C: mature Guard break | 1–<2%: 6; 2–<3%: 3; 3–<4%: 2; 4–<5%: 3; <1%: 7; >=5%: 14 |
| D: recovery failure | 1–<2%: 14; 2–<3%: 14; 3–<4%: 15; 4–<5%: 12; <1%: 26; >=5%: 46 |
| SESSION_CLOSE | 1–<2%: 204; 2–<3%: 151; 3–<4%: 84; 4–<5%: 45; <1%: 466; >=5%: 81 |
| UNRESOLVED | 1–<2%: 7; 2–<3%: 4; 3–<4%: 2; 4–<5%: 3; <1%: 18; UNKNOWN: 5 |

## 全Entry economics

| all1600 metric | V3 | V4 |
| --- | --- | --- |
| return mean / median % | +0.1214 / -0.1000 | +0.1424 / -0.1000 |
| filled / unresolved | 1561 / 39 | 1561 / 39 |
| positive rate % | +45.4837 | +45.9321 |
| negative N / mean / median % | 851 / -1.9589 / -1.1084 | 844 / -1.9110 / -1.0605 |
| worst return % | -27.1000 | -27.1000 |
| <-1% / <-2% N | 455 / 262 | 438 / 250 |
| holding active min mean / median | +124.9680 / +114.0000 | +121.0910 / +109.0000 |

pre-sell giveback共通1538件paired mean delta -0.0664pp。later missed共通487件paired mean delta +0.0706pp。全体平均の改善はprimary combined中央値Gateを代替しない。<-1%/<-2%やworst returnは診断のみで、新stop ruleに変換していない。

## 原本・因果・独立性

開始actual GET V3 FINAL: c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad。Full traceはV3がhash-pinする原本V2 FULL_TRACE 1,600件／523,200 scheduled endpointsとFrozen Path。再構築0。V3 ZIPはFull traceを複製せず原本依存を明示しているため、両方の既存原本をexact reuseした。

原本hash: V2 ZIP `31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89`、V3 ZIP `16cb53e6c986963f5a103e56c9f3fafad142548d7d9fd3286bb9e8c92e5a04b3`。Frozen Entry `e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb`。contract `bda3fa62e10675e7c30d2e693861176b0af84fa802e32800a61b3d840aaf1fe2`。48 public、1,605 V3 private、1,606原本依存成分をhash照合。6 semantic authority pinも一致。原本からの補正・再構築・Entry→High再計算は行っていない。

One primary V4 ReplayをRUN_ONCE receiptで固定。新規V4 decision196,552 rows、Full traceから読むprefix含むcutoff447,533箇所。独立監査はboolean phase latch／全segment pivot ledger／floor ledger／独立fill・calendar・Fraction economicsで全1,600件を検算し、1,206,668 checks、mismatch0、future causal leakage0、lineage mismatch0。primary decision/evaluator imports0。別実装監査であり外部reviewerではない。共通依存は保存済み入力、Python standard runtime/Fraction、I/O/hashのみ。

Decision arithmeticはoriginal numeric stringのFractionで厳密、許容epsilonなし。economicsのfloat表現差のみabs1e-10/rel1e-12で検算。全717 floor updateのkind L/DC、confirmation cutoff、context UP、mainより上、monotonic、次足有効を確認。127 Dのexact break、A/B/C優先、same-segment、V3より早いfirst intent、fill5bpsを確認。D以外1,473件はV3 intent/fill/outcome完全一致。

historical actual_known_atはUNKNOWN。因果PASSは保存時のbar_end availability仮定内であり、実市場到着時刻の証明ではない。Entry→Highはstrictly-later observed Highで、full remaining source completeは55/1600（>=5群7/253）。欠測区間を含む完全な日中最高値と過大表示しない。observed High UNKNOWN5件、unresolved39件を保持。

## 必須20回答

| No. | 必須回答 | 結果 |
| --- | --- | --- |
| 1 | V3 Full traceを再構築せずexact reuseしたか | はい。V3がpinする原本V2 FULL_TRACE 1,600ファイルとFrozen Pathをそのまま読み、原本1,606成分・V3 1,605成分hash一致。新規出力はV4 position metadataでありState9/Path再構築ではない。 |
| 2 | State9/Path変更0か | 0。RC2/profile/source snapshot/M0/State Path Contract/PATH_FROZENの6pin一致。Frozen尺度1U/4U/0.5U/0.5U変更0。 |
| 3 | Recovery Floor成立position N | 414。creation537、tighten180、reset263、never1186。 |
| 4 | EXIT-D N | 127。全127件でmain context=UPかつ有効floor>main protected、Close<=floor−0.5U。 |
| 5 | DはV3 EXIT-Aを何件preemptしたか | 47件。2–<5%の既存EXIT-A79件では16件。 |
| 6 | 2–<3% V3→V4 mean/median | +0.2919 / +0.7687 → +0.3015 / +0.7478%。共通filled209。 |
| 7 | 3–<4% V3→V4 mean/median | +0.6592 / +1.5220 → +0.6438 / +1.2999%。共通filled128。 |
| 8 | 4–<5% V3→V4 mean/median | +0.7567 / +1.4078 → +0.9440 / +1.6909%。共通filled80。 |
| 9 | 2–<5% combined V3→V4 mean/median | +0.4938 / +1.0893 → +0.5298 / +1.0483%。426 watches／共通filled417／unresolved9。>=5%を混ぜていない。 |
| 10 | >=5% V3→V4 mean/median | +3.9283 / +3.1755 → +3.9351 / +3.1297%。共通253。平均微増、中央値低下。 |
| 11 | >=5%でD発火Nとpaired return | 46件。群return +3.4770 / +2.9736 → +3.5140 / +2.9799%。真正paired return Δ +0.0370 / +0.1386pp（group median差とは異なる）。 |
| 12 | D群pre-sell givebackの変化 | 共通126件のpaired Δ -0.8100 / -0.3665pp。V3 observed N127、V4 N126を0補完していない。 |
| 13 | D群later missed upsideの変化 | 共通89件のpaired Δ +0.3862 / +0.0000pp。V3 observed N89→V4 N127。異なる母数のraw平均を改善と解釈しない。単独FAILにしていない。 |
| 14 | PULLBACK/RISE_STOP単独SELL=0か | 両方0。local DOWN、dwell/time、stop count単独も0。Dは全件PULLBACKで観測されたが、文字列はtrigger条件に含まれない。 |
| 15 | fixed stop/profit/trailing=0か | 全0。Hard1、固定損失/利益%、giveback%、固定trailing、State sequence rule、モデル/teacher/OOF/score/rank/searchも0。 |
| 16 | mismatch=0 / future leakage=0か | 両0。全1,600件、1,206,668 checks。historical actual_known_at=UNKNOWN、bar_end availability仮定の範囲での因果監査。 |
| 17 | selection status | V4_NOT_BETTER_KEEP_V3。combined中央値が厳密改善しないため固定Gateで否決。3–<4%平均、>=5%中央値も悪化。later missed upsideでは否決していない。 |
| 18 | V4不成立時V3を無変更fallbackとして保持したか | はい。V3 FINAL c7a5e5c25eb19cbd58b45c3e4ffff977f4648fadを保持。A/B/C/PRE/quality/fill/calendarのwhole bytes一致。D以外1,473件のintent/fill/outcome完全一致。V3 branch変更0。 |
| 19 | Re-entry/Capital=0か | 両0。Portfolio、Protected/Fresh/Validation/OOS/Prospective、orders/main mergeも0。 |
| 20 | 次はEXIT Freezeへ進める状態か | 人間がV3をEXIT Freeze候補として判断できるEvidenceは揃った。V4採用条件は未達。今回を最後の限定EXIT改善Workとして終了し、正式EXIT Freezeは実行していない。 |

## 保存・予算・終了

S0 actual HEAD d4d96dedcdb35f65615994dd8a259a0a51a3ed49でcontractとGateをReplay前に固定。S1 actual HEAD d423f77bb67a586f1dd2a02858adfabad5af787cをcommit後GET確認。FINAL basis_headはS1、結果HEADはcommit後actual GETで確認する（未来SHAを記載しない）。checkpointは指定3点のみ。

new policy1／Recovery Floor variant1／primary V4 Replay1。model/teacher/OOF/probability/score/rank/search/provider/new market data/Entry replay/State9・Path再構築または変更/V3 Replay/old EXIT Replay/Hard1/fixed stop/fixed trailing/Protected/Fresh/Validation/OOS/Prospective/Re-entry/Capital/Portfolio/orders/main merge/force pushは全0。結果を見たcontract/D条件/Gate修正0、追加candidate0。

全10 safety flags=false。LONG-only／cash-equity-only／productionReady=false。正式EXIT Freezeを実行していない。次の最小修正を同Work内で作らない。V3を無変更fallbackおよび人間のFreeze判断候補として保持し、V4_NOT_BETTER_KEEP_V3でSTOP。
