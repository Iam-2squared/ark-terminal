# Ark Terminal — State9 Structural EXIT v2

**STATE9_STRUCTURAL_EXIT_V2_EVIDENCE_READY — Evidence完成、ここでSTOP。**

Document: `WORK_STATE9_STRUCTURAL_EXIT_V2_20261003`。作成: 2026-10-03T18:41:04.508352+09:00。Frozen FIRST ENTRY v2 P1_Q70の1,600 Entryを変更0でReplayした。新EXIT policyは1本、State9/Path/profile/M0変更0、teacher/model/score/rank/searchは0。研究contractを結果前に固定したが、EXIT正式採用のFreezeは行っていない。

全1,600件中、sell-filled 1,561件、UNRESOLVED 39件。独立実装による3,712,630 checksはmismatch=0、future causal leakage=0。Leakage判定はFrozen Entryと同じavailability=bar_end仮定内の検算で、historical actual_known_atはUNKNOWN。

## ≥3% Winner — 独立詳細表

| 指標 | metric N | 平均 / 中央値（または件数） |
| --- | --- | --- |
| denominator / sell-filled / unresolved | 466 | 461 / 5 |
| realized return % | 461 | 2.429 / 2.148 |
| observed Entry→High % | 466 | 7.823 / 5.264 |
| MFE Realization % | 461 | 23.900 / 34.320 |
| Peak Giveback pp | 461 | 5.435 / 3.579 |
| later missed upside % | 228 | 5.858 / 3.636 |
| EXIT before final observed High % | 461 | 30.803 |
| EXIT→later High active minutes | 228 | 56.149 / 31.500 |
| holding active minutes | 461 | 125.080 / 111.000 |

## ≥5% Winner — 独立詳細表

| 指標 | metric N | 平均 / 中央値（または件数） |
| --- | --- | --- |
| denominator / sell-filled / unresolved | 253 | 253 / 0 |
| realized return % | 253 | 3.901 / 3.291 |
| observed Entry→High % | 253 | 11.149 / 8.200 |
| MFE Realization % | 253 | 30.180 / 33.348 |
| Peak Giveback pp | 253 | 7.248 / 5.286 |
| later missed upside % | 161 | 7.308 / 5.267 |
| EXIT before final observed High % | 253 | 44.269 |
| EXIT→later High active minutes | 161 | 61.826 / 35.000 |
| holding active minutes | 253 | 115.253 / 87.000 |

WinnerはFrozen Entry fill後のstrictly-later **observed High**で定義。≥3%と≥5%は累積bucket。元Workの「=3 / =5」はこの≥3 / ≥5として集計した。MFE Realizationは各positionの比率の平均であり、平均return÷平均MFEではない。Peak GivebackはEntry基準のpercentage points（pp）。later missed upsideはsell価格基準、EXIT後のstrictly-later Highが保存されているpositionのみ。未観測を0に置換しない。

## Lifecycle coverage

| Lifecycle | N |
| --- | --- |
| Entry時点UP context | 94 |
| Entry後初回UP context | 980 |
| UP structure armed total | 1074 |
| never armed | 526 |
| EXIT-A UP_STRUCTURE_REVERSED | 315 |
| EXIT-B UP_STRUCTURE_RETIRED_BY_RANGE | 163 |
| observation suspended position | 810 |
| SESSION_CLOSE理由 | 1083 |
| UNRESOLVED | 39 |

| 時間 / count | N | 平均 / 中央値 または総数 |
| --- | --- | --- |
| Entry→初回arm active minutes | 1074 | 29.336 / 16.000 |
| 初回arm→EXIT intent/planned deadline active minutes | 1074 | 92.993 / 63.000 |
| holding active minutes | 1561 | 126.523 / 114.000 |
| suspension events | — | 2206 |
| re-arm events | — | 1736 |
| protected level tighten | — | 237 |
| PULLBACK distinct runs | — | 2216 |
| RISE_STOP distinct runs | — | 231 |

Countersは全て排他的ではない。94+980=1,074、1,074+526=1,600。観測suspensionはarmed群に重複する。構造EXIT 478件中473件はnext eligible regular raw Open、5件はregular Open sourceが無く予定closing sourceで約定した。理由はEXIT-Aのまま保持。Closing fill source総数は1,088件、SESSION_CLOSE理由は1,083件。39件はexact terminal closing sourceも無くUNRESOLVED、returnを0で補完していない。

PREでは当時のDOWN/RANGE/null/時間/損失でSELLせず、最初のvalid UPまで待った。ACTIVEでは同一segmentのUP→DOWN、または独立RANGE/BALANCED/context NONEだけでEXIT。null・gap・resetではsuspendし、新segmentのDOWNへ旧UPから接続しない。PULLBACK単独SELL=0、RISE_STOP単独SELL=0、protected tighten単独SELL=0。

## All-entry economics

| 指標 | N | 値（平均 / 中央値） |
| --- | --- | --- |
| realized return % | 1561 | 0.093 / -0.100 |
| positive rate | 1561 | 45.099%（positive N=704） |
| negative return % | 857 | -1.995 / -1.129 |
| worst return % | 1561 | -27.100 |
| return <−1% / <−2% | diagnostic only | 467 / 267 |
| observed Entry→High % | 1595 | 2.997 / 1.549 |
| MFE Realization % | 1394 | -158.646 / 1.853 |
| Peak Giveback pp | 1561 | 2.942 / 1.670 |
| later missed upside % | 473 | 3.512 / 1.566 |

Entry +5bpsはFrozen fillに含まれ、二重計上0。Sell adverse5bps、commission0。全体MFE Realizationの負の平均は、小さいpositive MFEを分母にするpositionの影響を受ける。値のclipは行っていない。主要判断用に≥3/≥5 Winnerを独立表示した。Return tailは診断のみで、fixed stopや追加SELL ruleへ変換していない。

## Cumulative / exclusive Winner

| observed High bucket | denominator | filled / unresolved | return % 平均 / 中央値 | MFE realization % 平均 / 中央値 |
| --- | --- | --- | --- | --- |
| >=1% | 976 | 960 / 16 | 1.070 / 0.878 | 1.568 / 27.965 |
| >=2% | 679 | 670 / 9 | 1.756 / 1.408 | 19.463 / 33.501 |
| >=3% | 466 | 461 / 5 | 2.429 / 2.148 | 23.900 / 34.320 |
| >=4% | 336 | 333 / 3 | 3.147 / 2.600 | 26.994 / 32.773 |
| >=5% | 253 | 253 / 0 | 3.901 / 3.291 | 30.180 / 33.348 |

| observed High bucket | denominator | filled / unresolved | return % 平均 / 中央値 | MFE realization % 平均 / 中央値 |
| --- | --- | --- | --- | --- |
| <1% | 619 | 601 / 18 | -1.469 / -0.912 | -513.037 / -137.544 |
| 1–<2% | 297 | 290 / 7 | -0.513 / -0.100 | -39.775 / -5.497 |
| 2–<3% | 213 | 209 / 4 | 0.270 / 0.769 | 9.674 / 30.782 |
| 3–<4% | 130 | 128 / 2 | 0.560 / 1.400 | 15.853 / 40.738 |
| 4–<5% | 83 | 80 / 3 | 0.763 / 1.408 | 16.918 / 32.028 |
| >=5% | 253 | 253 / 0 | 3.901 / 3.291 | 30.180 / 33.348 |
| UNKNOWN_HIGH | 5 | 0 / 5 | — / — | — / — |

排他bucket合計1,600、UNKNOWN_HIGH 5件を含む。各bucketのHigh、Giveback、missed upside、EXIT-before-High、EXIT→later High、holdingの平均/中央値と個別metric Nは[WINNER_CUMULATIVE.csv](WINNER_CUMULATIVE.csv) / [WINNER_EXCLUSIVE.csv](WINNER_EXCLUSIVE.csv)に保存。

## Armed / never armed

| Group | N | filled / unresolved | return % 平均 / 中央値 | ≥3 / ≥5 N | SESSION_CLOSE理由 N |
| --- | --- | --- | --- | --- | --- |
| armed | 1074 | 1065 / 9 | 0.249 / -0.100 | 394 / 224 | 587 |
| never_armed | 526 | 496 / 30 | -0.242 / -0.241 | 72 / 29 | 496 |

| never-armed source / lifecycle provenance | N |
| --- | --- |
| M0_CONNECTED_BUT_NO_OBSERVED_UP | 366 |
| M0_PREVIOUS_SOURCE_U_UNAVAILABLE | 159 |
| PREVIOUS_PRICE_BASIS_NOT_CONTINUOUS | 1 |

armed群の平均returnは+0.249%、never-armed群は−0.242%。これは観測されたgroup差であり、Entry再filterや因果効果の証明には使わない。never-armedにも≥3 Winner 72件、≥5 Winner 29件があり、UP contextが立たないcoverage制約は全体平均に埋めていない。全件にPREの新SELL ruleを追加していない。

| Entry formal Primary / context | N | armed N / 率% | Entry→arm分 平均 / 中央値 | return % 平均 / 中央値 | observed High % 平均 / 中央値 |
| --- | --- | --- | --- | --- | --- |
| DROP / -1 | 208 | 187 / 89.904 | 28.326 / 19.000 | 0.093 / -0.100 | 3.958 / 2.279 |
| DROP / 0 | 59 | 48 / 81.356 | 26.042 / 19.000 | -0.602 / -0.453 | 2.735 / 1.453 |
| DROP_STOP / -1 | 1 | 1 / 100.000 | 24.000 / 24.000 | 1.698 / 1.698 | 4.061 / 4.061 |
| DROP_STOP / 0 | 1 | 1 / 100.000 | 73.000 / 73.000 | -3.353 / -3.353 | 0.229 / 0.229 |
| PULLBACK / 1 | 59 | 59 / 100.000 | 0.000 / 0.000 | -0.315 / -0.261 | 3.077 / 1.867 |
| RANGE / 0 | 45 | 38 / 84.444 | 48.079 / 25.500 | -1.430 / -0.444 | 3.354 / 1.562 |
| REBOUND / -1 | 50 | 47 / 94.000 | 25.383 / 18.000 | -0.024 / -0.164 | 3.441 / 1.725 |
| RISE / 0 | 42 | 37 / 88.095 | 18.919 / 8.000 | -0.068 / -0.100 | 2.153 / 1.433 |
| RISE / 1 | 33 | 33 / 100.000 | 0.000 / 0.000 | -0.222 / -0.205 | 3.476 / 2.072 |
| RISE_STOP / -1 | 2 | 1 / 50.000 | 55.000 / 55.000 | 1.283 / 1.283 | 1.750 / 1.750 |
| RISE_STOP / 1 | 1 | 1 / 100.000 | 0.000 / 0.000 | -3.127 / -3.127 | 0.960 / 0.960 |
| SHARP_DROP / -1 | 56 | 46 / 82.143 | 27.739 / 23.000 | -0.635 / -0.683 | 3.557 / 2.074 |
| SHARP_RISE / 1 | 1 | 1 / 100.000 | 0.000 / 0.000 | -1.221 / -1.221 | 0.449 / 0.449 |
| None / 0 | 396 | 316 / 79.798 | 29.123 / 13.000 | 0.052 / -0.100 | 2.898 / 1.493 |
| None / None | 646 | 258 / 39.938 | 41.120 / 23.000 | 0.449 / -0.100 | 2.699 / 1.262 |

contextのFrozen値は+1=UP、−1=DOWN、0=NONE。Noneはunavailableで、独立RANGEのNONEとは区別する。

## EXIT理由別の値幅

| 理由 | N | return % 平均 / 中央値 | MFE realization % 平均 / 中央値 | Peak Giveback pp 平均 / 中央値 | later missed upside % 平均 / 中央値 | ≥3 / ≥5 N |
| --- | --- | --- | --- | --- | --- | --- |
| UP_STRUCTURE_REVERSED | 315 | 0.236 / -0.354 | -163.025 / -8.211 | 5.086 / 3.264 | 3.781 / 1.676 | 156 / 107 |
| UP_STRUCTURE_RETIRED_BY_RANGE | 163 | 0.889 / 0.284 | -97.850 / 17.979 | 4.069 / 2.504 | 2.998 / 1.347 | 73 / 55 |
| SESSION_CLOSE | 1083 | -0.069 / -0.100 | -167.045 / 6.140 | 2.148 / 1.281 | — / — | 232 / 91 |
| UNRESOLVED | 39 | — / — | — / — | — / — | — / — | 5 / 0 |

UP→DOWN群はfull-session観測Highから平均5.086ppを失い、later observed Highがある310件ではmissed upside平均3.781%。Range retirement群はGiveback平均4.069pp、later observed Highがある163件ではmissed upside平均2.998%。SESSION_CLOSE群は平均return−0.069%、Giveback平均2.148pp。これらは同じpolicy内の理由分解で、別EXIT controlとの比較ではない。

全session High基準のGivebackは、保有中に経験したpeakのgivebackとEXIT後missed upsideを含み得る。≥5 Winnerではfull-session Giveback平均7.248ppに対し、sellより前のobserved peak基準は平均3.803pp（N=250）。同群の44.269%がfinal observed Highより前に売却され、later High observed 161件のmissed upside平均7.308%だった。構造反転時に既に失った幅と、EXIT後に再上昇した幅を分けて次の人間判断へ渡せる。この結果から3つ目のtriggerやRe-entryを同Work内に追加していない。

exit直前3 distinct PrimaryとPath run sequence、exit時context/protected/balance/dwellはprivate Replay/economics各行に保存。理由別sequence件数は[EXIT_REASON_DECOMPOSITION.json](EXIT_REASON_DECOMPOSITION.json)。protected_before/buffer0.5/Close/effective timestampのA315件検算、独立balance windowのB163件検算は[INDEPENDENT_AUDIT.json](INDEPENDENT_AUDIT.json)を参照。

## Full trace / integrity / coverage

Full trace 523,200 scheduled endpoints、67,283,725 bytes、1,600 gzip。全formal responseとFrozen Path endpoint/eventsを保存。observed slots159,020、formal null slots364,180。saved overlap157,133件（unavailable overlap10,561件を含む）は全数一致、candidate vs独立Frozen RC2全523,200 slots一致。80/120座標確認83,189 price checks。

原raw/M0 sourceは保存済みsourceのみ。160 watchesはM0 previous source/price-basis unavailableのため正式unavailable・observed=falseを保存し、DOWN transitionに偽装しなかった。観測High既知1,595件、High未知5件。元Frozen Entryのremaining_source_complete=trueは55件のみ。≥3 Winnerのcomplete sourceは14/466、≥5は7/253。observed Winnerは到達が確認された群だが、complete-session opportunityと同じではない。部分経路の<1%群も完全なnon-winnerとは認定しない。

最初のtrace生成中に73本のgzip containerが不完全/空で保存された。Replay前に検出し、Frozen sourceから最初に記録されたSHAと完全一致するbytesへ73本すべてを復元。1,600本のstream/footer/row count/SHAを確認してから最終Replay・auditを実行した。Semantic mismatchではなく保存containerの不備で、復元前の不完全bytesをEvidenceとして使用していない。[TRACE_CONTAINER_RECOVERY_RECEIPT.json](TRACE_CONTAINER_RECOVERY_RECEIPT.json)に経緯を残した。

結果前に固定したcontract/lifecycle/Frozen sourceのSHAは変更0。summaryのUNRESOLVED key serializingと監査validatorのFrozen Pivot.extremum_tフィールド参照の誤記を修正した。policy・semantic・市場値変更0。[IMPLEMENTATION_IO_CORRECTIONS.json](IMPLEMENTATION_IO_CORRECTIONS.json)に前後SHAを保存。

| Frozen object | SHA256 |
| --- | --- |
| M0.md | 08cad3ca8316ccab644872e3d843e2d491ac6a953a03193d5c391be3bcf73bb3 |
| PATH_FROZEN.py | ad59222fcc0f9dfed4698efb49a87d66ea4e01b90562cdcaa8b9bc028ffffbf8 |
| RC2_CONTRACT.txt | 45859122a62ccdc946b31bb5709f3fc080ea4a4f935958afd8f1ca895f75b6ff |
| STATE_PATH_CONTRACT_V1.md | fc3808cb7d3d161e85527d7ebf97f902df7f0c3463457beddf1a25d053cee268 |
| profile.json | 77ee61ba1808a2c17614439fe7d14212a53cbfa7358c032ce16989eeb5248922 |
| source_snapshot.json | 08e1a20a4d022a1429b74387169dd8729a2eaeb4dc0008f3af2b52ec0e661c23 |

Frozen Entry HEAD: `4a2d6f35946b16820a13449a9288a6685a5c283c`、exact records gzip SHA: `e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb`。開始時actual GET HEAD: `9bbbe99aad255534d084d86aa6b4a94106e7c151`。

## Independent Audit

| 項目 | 検算結果 |
| --- | --- |
| Frozen Entry identity | PASS |
| RC2/profile/M0/Path hashes | PASS |
| full State9 trace reconstruction | PASS |
| saved overlap parity | PASS |
| causal cutoff | PASS |
| segment continuity | PASS |
| observed/null distinction | PASS |
| UP arm timestamp | PASS |
| PULLBACK単独SELL=0 | PASS |
| RISE_STOP単独SELL=0 | PASS |
| protected tighten単独SELL=0 | PASS |
| UP→DOWN structural protection | PASS |
| independent Range retirement | PASS |
| gap/reset跨ぎtransition=0 | PASS |
| first valid EXIT trigger | PASS |
| next-open sell5bps | PASS |
| exact session-close source / explicit unresolved | PASS |
| post-exit decision=0 | PASS |
| MFE / Giveback / later missed upside | PASS |
| Winner denominators | PASS |
| model/teacher/audit fit=0 | PASS |
| hard stop/trailing=0 | PASS |
| old EXIT access/replay/comparison=0 | PASS |
| Re-entry/Capital=0 | PASS |

全1,600 Entryを別実装のBoolean latch scan、独立calendar/fill、Decimal/Fraction economicsで検算。lifecycle/replay/evaluateを監査decisionへimportしていない。Frozen RC2 independent kernelとPath event ordering/run/dwellも全件検算。mismatch=0、future causal leakage=0、audit fit=0。共有依存はimmutable raw/source、Frozen schema、Python runtime、settingsのI/O/hashのみ。これは別実装監査であり、外部reviewerによる監査を称していない。禁止作業の検証は実装ASTと作業ledgerで、brokerage等の外部access-log認証は行っていない。

## 必須17回答 / STOP

| No. | 必須回答 | 結果 |
| --- | --- | --- |
| 1 | Frozen Entry 1,600を変更0で使用したか | はい。exact original gzip、watch key集合、fill時刻・価格を全件照合。 |
| 2 | Full RC2 State9 / Path traceを使ったか | はい。523,200 scheduled endpoints、全responseとPath eventsを保存。 |
| 3 | State9 / Path semantic変更0か | 0。6 pinsとFrozen source hash一致。 |
| 4 | model / teacher / score / thresholdは0か | 全て0。OOF/probability/rank/search/audit fitも0。 |
| 5 | armed / never-armed N | 1,074 / 526。 |
| 6 | Entry→arm時間 | active minutes平均29.336 / 中央値16、N=1,074。 |
| 7 | EXIT-A / B / session-close N | 315 / 163 / 1,083（理由）。closing fill source1,088、UNRESOLVED39。 |
| 8 | PULLBACK / RISE_STOP単独SELL | 両方0。protected tighten単独も0。 |
| 9 | overall realized mean / median | +0.092601% / −0.099950%、filled N=1,561。 |
| 10 | ≥3 Winner return / MFE Realization | return2.429064% / 2.148440%、実現率23.900405% / 34.319603%。N466、filled461。 |
| 11 | ≥5 Winner return / MFE Realization | return3.901357% / 3.290913%、実現率30.179517% / 33.348326%。N253。 |
| 12 | ≥5 Giveback / missed upside | Giveback7.247741 / 5.286239pp（N253）、missed7.308232% / 5.267002%（later observed N161）。 |
| 13 | armed vs never差 | return平均+0.248618% vs −0.242395%。neverのsource/未成立を別集計。 |
| 14 | exit理由別の値幅損失 | A Giveback平均5.086pp、B4.069pp、session close2.148pp。pre-sell peakとpost-exit upsideも保存。 |
| 15 | independent mismatch / future leakage | 0 / 0。historical actual_known_at UNKNOWN、bar_end availability仮定内。 |
| 16 | old EXIT / Hard1 / Re-entry / Capital実行 | 一度も実行していない。旧EXITのread/replay/comparisonも0。 |
| 17 | 人間判断用Evidenceが揃ったか | はい。全11 Completion Gateを満たしFINAL checkpointでSTOP。39 unresolvedとsource coverageを明示。 |

新EXIT policies=1、それ以外のbudgetは全0。LONG-only / cash-equity-only。全10 safety flags=false。v1は失敗Evidenceとして継承し非採用のまま閉じた。正式EXIT Freeze、追加EXIT、Protected/Fresh/Validation/OOS/Prospective、Re-entry、Capital、Portfolio、orders、main mergeへ自動進行しない。次判断は人間に委ねる。

Four checkpoints: S0_START_AND_IDENTITY、S1_CONTRACT_AND_TRACE_READY、S2_REPLAY_COMPLETE、FINAL_AUDIT_AND_EVIDENCE。各commit後のactual GETでresult HEADを確認。このreportはFINAL保存直前のactual basis HEADを記録し、未来SHAを埋め込まない。[S2_HEAD_GET_RECEIPT.json](S2_HEAD_GET_RECEIPT.json) / [CHECKPOINTS](CHECKPOINTS/)を参照。
