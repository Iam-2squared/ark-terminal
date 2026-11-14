# EXIT v3 Official Freeze → Persistent Re-entry v1 FINAL

| Original FIRST Entry→High | Watch N | realized / unresolved | V3 FIRST-only mean / median % | Re-entry込み simple mean / median % | Δmean / Δmedian pp | 平均trades/watch |
| --- | --- | --- | --- | --- | --- | --- |
| <1% | 619 | 601 / 18 | -1.4642 / -0.9089 | -1.6065 / -0.9919 | -0.1422 / -0.0831 | 1.2036 |
| 1–<2% | 297 | 290 / 7 | -0.4493 / -0.0597 | -0.5160 / -0.0188 | -0.0668 / +0.0409 | 1.2997 |
| 2–<3% | 213 | 209 / 4 | +0.2919 / +0.7687 | +0.1118 / +0.7478 | -0.1801 / -0.0210 | 1.2629 |
| 3–<4% | 130 | 128 / 2 | +0.6592 / +1.5220 | +0.4399 / +1.5918 | -0.2192 / +0.0698 | 1.3462 |
| 4–<5% | 83 | 80 / 3 | +0.7567 / +1.4078 | +0.4826 / +1.5844 | -0.2741 / +0.1766 | 1.4217 |
| >=5% | 253 | 253 / 0 | +3.9283 / +3.1755 | +4.5737 / +3.5915 | +0.6453 / +0.4160 | 1.9368 |
| UNKNOWN | 5 | 0 / 5 | UNKNOWN / UNKNOWN | UNKNOWN / UNKNOWN | UNKNOWN / UNKNOWN | 1.0000 |

数値はmean / median、return単位は%。Δはpp。比較母集団は全tradeがrealizedの共通watch。今回はV3の既知returnと同じ1,561 watchで、追加未解決0。Original bucketは最初のFrozen Entry→strictly-later observed Highから一度だけ固定。future bucketはdecision input=0。

Status: **PERSISTENT_REENTRY_V1_EVIDENCE_READY**。EXIT v3はOFFICIAL FREEZE済み。Re-entryはEvidence完成まででSTOPし、正式Re-entry Freeze・Capitalへ自動進行しない。

Frozen FIRST ENTRY後の主構造HOLDをbyte-identicalなV3で維持し、flat時だけ保存済みP1_Q70を監視した。FIRST-only baselineは再Replay・性能再計算0。V4 EXIT-Dは不使用。

## Multi-leg recoveryとsecondary compounding

| Group | watch / common N | simple mean / median % | same-watch compounded mean / median % | Re-entry watches | 追加trades | 追加return合計 pp |
| --- | --- | --- | --- | --- | --- | --- |
| 2–<3% | 213 / 209 | +0.1118 / +0.7478 | +0.1129 / +0.7478 | 40 | 56 | -37.6318 |
| 3–<4% | 130 / 128 | +0.4399 / +1.5918 | +0.4347 / +1.5871 | 32 | 45 | -28.0599 |
| 4–<5% | 83 / 80 | +0.4826 / +1.5844 | +0.4804 / +1.5844 | 27 | 35 | -21.9307 |
| 2–<5% combined | 426 / 417 | +0.2837 / +1.1053 | +0.2822 / +1.1070 | 99 | 136 | -87.6223 |
| >=5% | 253 / 253 | +4.5737 / +3.5915 | +4.5693 / +3.5755 | 135 | 237 | +163.2640 |
| ALL_1600 | 1600 / 1561 | +0.1027 / -0.1000 | +0.1024 / -0.1561 | 380 | 588 | -29.2092 |

>=5%のFIRST EXIT後Re-entry率は135/253=53.36%。追加237 trade平均+0.6889%、中央値−0.1000%、追加simple returnの合計+163.2640pp。2–<5%は99/417=23.74%、追加136 trade平均−0.6443%、中央値−0.2679%、合計−87.6223pp。pp合計は各watch/tradeの単純加算で、資金・portfolio利益ではない。same-watch compoundingも理論値で、同時刻の他銘柄とのcash競合・sizeを含まない。

## Re-entry activity

0 Re-entry1,220 watch、>=1は380、>=2は145、>=3は44。588 fills /591 intents。総2,188 trades、完成2,149 round trips、Frozen FIRST unresolved39。新しいunresolved0。任意回数cap・cooldownは0。

対象はFrozen1,600 watchの58 sessions。sessionあたりRe-entry fills平均10.1379、中央値10、0 Re-entry session0。これは他のSelector日・NO_FIRST_ENTRY watchを含む144日全体の集計ではない。

EXIT fill→reset mean8.54 /median1分、reset→fresh cross14.59 /5分、EXIT fill→new BUY intent25.31 /11分、EXIT fill→new BUY fill25.14 /11分。lunchをactive timeから除外。regular close後のEntry decision0。

| Previous EXIT | flat episodes | reset | fresh cross | Re-entry filled | rate % |
| --- | --- | --- | --- | --- | --- |
| UP_STRUCTURE_REVERSED | 456 | 443 | 358 | 356 | 78.07 |
| UP_STRUCTURE_RETIRED_BY_RANGE | 259 | 257 | 176 | 176 | 67.95 |
| LOCAL_UP_STRUCTURE_GUARD_BROKEN | 73 | 73 | 57 | 56 | 76.71 |
| SESSION_CLOSE | 1361 | 0 | 0 | 0 | 0.00 |
| UNRESOLVED | 0 | 0 | 0 | 0 | UNKNOWN |

## Trade indexとcost

| Trade | N / sell-filled | return mean / median % | positive rate % | holding mean / median active min | EXIT A / B / C / close / unresolved |
| --- | --- | --- | --- | --- | --- |
| #1 FIRST | 1600 / 1561 | +0.1214 / -0.1000 | 45.48 | 124.97 / 114 | 294 / 155 / 43 / 1069 / 39 |
| #2 first REENTRY | 380 / 380 | -0.0501 / -0.1945 | 41.32 | 75.18 / 56.5 | 113 / 68 / 17 / 182 / 0 |
| #3 second REENTRY | 145 / 145 | -0.0250 / -0.1000 | 44.83 | 56.53 / 36 | 37 / 24 / 10 / 74 / 0 |
| #4+ | 63 / 63 | -0.1042 / -0.0427 | 47.62 | 46.21 / 31 | 12 / 12 / 3 / 36 / 0 |

追加588 tradeの336件=57.14%がreturn<=0。holding<=1/3/5 active minは12/29/49件、EXIT→Re-entry<=1/3/5 active minは0/93/164件。診断のみでcooldown/capへ変換していない。

買い+5bps・売り−5bps・commission0を各追加round tripに含めた。追加trade raw return mean/median +0.0503 /0.0000%、adjusted −0.0497 /−0.1000%。exact sourceに基づくdrag mean0.1000pp、sum58.8002pp。FIRST Entry costの二重計上0。全2,149 completed round tripsのdrag sum215.1679pp。bps/pp合計はcost exposure診断で、position sizingを持たない。

## Integrityと時刻順序

独立監査はprimary engine/evaluatorをimportせず、配列上のreset/cross探索、Fractionによるstructural arithmetic、別V3 phase/pivot ledger、別canonical fillを使った。1,138,726 checks。mismatch=0 /future leakage=0 /position overlap=0 /same-bar sell-buy=0 /future bucket decision reads=0。

初回audit checkerは、closed-bar fresh cross時刻tの直後にnext raw Open tでBUY fillした482件を「既にopen中のdecision」と誤判定した。全件でclosed source start=t−1、旧SELL fill<t、新positionはdecision確定後にfillしていた。auditのevent順序のみ修正し、6境界テストPASSと全件再監査を行った。初回結果・correction receiptは保存。R0 decisionコード、contract、trade ledger、primary Replay回数はいずれも無変更。

historical actual_known_atはUNKNOWN。bar_end availabilityは研究上の仮定で、実際の過去到着時刻を検証したとは主張しない。original raw remaining pathが完全なのは55/1,600、>=5%群7/253。bucket/Highは保存済みobserved Highに基づく同一coverageの比較で、missingを補完しない。

PULLBACK /RISE_STOP /local DOWN /dwell単独SELL0、fixed stop/profit/trailing0。V3 A/B/Cは構造条件とwhole-byte code hash一致。PRE/quality/reset、SELL fill、dated calendar変更0。新model/teacher/score計算/threshold-feature search、provider/new market data、State9/Path reconstruction、V4 replay、Capital/Portfolio/orders/main mergeは全て0。LONG-only /cash-equity-only、全10 safety flags=false、productionReady=false。

## 必須18回答

| # | 確認 | 回答 |
| --- | --- | --- |
| 1 | EXIT v3はOFFICIAL FREEZEされたか | はい。F0 receiptとactual result GETで固定。EntryFrozen=true / ExitFrozen=true。 |
| 2 | V4 EXIT-Dを混ぜていないか | 不使用0。V4_NOT_BETTER_KEEP_V3とV4 FINAL HEADをpin。Recovery Floorも不採用。 |
| 3 | FIRST ENTRY v2 / EXIT v3変更0か | 1,600件のFrozen FIRST fillとV3 saved outcomeをexact reuse。A/B/C/PRE/quality/clock/fillのwhole-file hash一致、変更0。 |
| 4 | Re-entryはFrozen P1_Q70 fresh crossだけか | はい。SELL fill後の最初のscore<Q70でreset、その後previous eligible score<Q70→current>=Q70のみ。新fit・score計算・threshold/feature変更0。 |
| 5 | total Re-entry fills | 588。intent591、NO_REENTRY_NO_NEXT_REGULAR_OPEN3。追加588 tradeすべてSELL filled。 |
| 6 | watchあたりtrade回数分布 | 1回1,220 /2回235 /3回101 /4回28 /5回13 /6回3。平均1.3675、中央値1。最大Re-entry5回。 |
| 7 | exclusive bucket別 FIRST-only→simple mean/median | 上のPrimary table。UNKNOWN5はreturn UNKNOWN、39 unresolvedを0補完しない。 |
| 8 | 2–5%帯 | 426 watch /417 complete。0.4938 /1.0893%→0.2837 /1.1053%。mean −0.2101pp、median +0.0159pp。各exclusive meanは全て低下。 |
| 9 | >=5%帯 | 253 watch全件complete。3.9283 /3.1755%→4.5737 /3.5915%。mean +0.6453pp、median +0.4160pp。135 watch、237追加trade。 |
| 10 | same-watch compounded | >=5%4.5693 /3.5755%、2–<5%0.2822 /1.1070%、全体0.1024 /−0.1561%。Capital/Portfolio returnではない。 |
| 11 | Trade #2/#3/#4+の質 | mean −0.0501 /−0.0250 /−0.1042%。positive rate41.32 /44.83 /47.62%。全追加trade平均はcost後−0.0497%。 |
| 12 | EXIT→Re-entry時間 | fill→reset中央値1分、reset→cross5分、fill→新intent11分、fill→新BUY fill11分。すべてactive minutes。 |
| 13 | churn/costで利益を失っていないか | 失っている。追加trade cost前mean +0.0503%、cost後−0.0497%。588 round tripsのdrag合計58.8002pp、net追加return合計−29.2092pp。全体simple meanは0.1214%→0.1027%。 |
| 14 | same-bar SELL/BUY / overlap | ともに0。旧positionはSELL fillまでopen、closed-bar cross→その直後のnext raw Openというevent順序を監査。 |
| 15 | future Entry→High bucket decision read | 0。決定用signal projectionにbucket/economicsを含めず、bucketは決定seal後に保存済みV3からjoin。 |
| 16 | audit mismatch / leakage | 0 /0。1,138,726 checks、全1,600 watch・2,188 trade・588追加V3 lifecycle。actual_known_at=UNKNOWN、bar_end availabilityは仮定。 |
| 17 | Capital / Portfolio | 0。position size、cash constraint、他銘柄間資金競合は未実装。orders/main merge0、全10 safety flags=false。 |
| 18 | 人間判断用Evidenceが揃ったか | はい。結果は大Winner改善・2–5%mean悪化・cost後追加trade平均負という混在。Re-entryを自動Freeze/採用せず、人間判断へ。Capitalへ進まずSTOP。 |

## 保存・STOP

actual saved_at_jst: 2026-10-03T23:13:32.126118+09:00。actual basis_head: `28b73476c322c66e659bd018ec17d4bbbf6cdcdc`。

4 checkpoint: F0_EXIT_V3_OFFICIAL_FREEZE /R0_REENTRY_CONTRACT_PRECOMMIT /R1_REPLAY_AND_EVALUATION /FINAL_AUDIT_AND_EVIDENCE。各commit後actual GETでresult HEADを確認。FINALは自分自身の未来SHAを記載せず、commit後のactual GETを別receiptへ保存する。force push/main merge0。

決定的再現用trade/flat/decision ledgerはprivate packageへ保存。public contract・source・tables・auditはこのresearch directory。原本のP1 score/grid/State9 full traceは既存Frozen private bundleをhash dependencyとして参照し、再構築・複製しない。

このWorkの結果から全面採用の自動判定は置かない。>=5%の後続leg回収改善と、小〜中幅群の平均悪化・cost負担の両方が確認できるEvidenceが揃った。Re-entry Freezeまたは最小修正は人間判断。ここでSTOP。
