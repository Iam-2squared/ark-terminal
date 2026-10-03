# Phase57 — ¥75 Minimum Tradable Price Policy Impact

2026-09-18 JST / Development only / human-defined Safety Policy / outcome-exposed。

75円以下を選定対象から除外する事前固定policy。予測最適化のthresholdではない。価格境界・score・モデル・Entry・EXIT変更なし。FREEZE判定とexact HEAD/CIは別freeze manifest/receiptに固定する。

Policy `LONG_ONLY_MIN_DECISION_PRICE_75_JPY_V1`。Digest `b991d0ececd4719318d8bd60bc98fa03e782cd56bef9af4bddce5c3294c26120`。測定前commit `dd93029c7e1b68ba8f0d030740c055ea81ef0fc1`。

Parent Selector commit `565d74b3dea823581fdb32380113aac5913a248d`、payload `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59`、model `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb`。

## 1. Policy / causal semantics

Decision Price <=75 JPY → INELIGIBLE_MIN_PRICE、>75 → price gate上eligible。missing / nonnumeric / nonfinite / bool / nonpositiveはBLOCKED。親のPIT freshness（age 0〜5分）を通過後、Gateを適用してscore降順・symbol昇順の既存Top5を構成する。Entry価格による除外ではない。75円超でも他の親eligibility条件を満たさなければ選定されない。

Decision Priceは親のlatest causally available accepted market CLOSE。価格のavailableAtはdecision timestamp−保存age。future High/Low/Close・MAE・outcomeをGateへ渡さない。保存minute cacheは既存5m adapterの不変再構成にのみ使用し、新しい1m研究・provider取得・fitは行っていない。

## 2. Basic impact

| 項目 | 値 |
| --- | --- |
| affectedTimestamps | 617 |
| decisionTimestamps | 760 |
| excludedCandidates | 18790 |
| excludedOldTop5 | 1107 |
| excludedPrices | {"max": 75.0, "mean": 43.728419372, "min": 3.0, "missing": 0, "n": 18790, "p1": 8.0, "p10": 20.0, "p25": 29.0, "p5": 18.0, "p50": 44.0, "p75": 60.0, "p90": 71.0, "p95": 73.0, "p99": 75.0} |
| excludedUniqueSymbols | 58 |
| newEligibleCandidates | 1736930 |
| newSelected | 3800 |
| newTop5ShortfallTimestamps | 0 |
| oldEligibleCandidates | 1755720 |
| oldSelected | 3800 |
| preEligibilityCandidates | 2758341 |
| removedTop5Prices | {"max": 75.0, "mean": 25.5230352304, "min": 3.0, "missing": 0, "n": 1107, "p1": 7.0, "p10": 8.0, "p25": 19.0, "p5": 7.0, "p50": 22.0, "p75": 30.0, "p90": 44.0, "p95": 50.7, "p99": 69.94} |
| replacements | 1107 |
| sessions | 76 |

候補数はsymbol×decision timestamp件数。unique symbolsとは別。760 timestampsを完全pairedで比較し、replacementは元eligible universe内のrankとGate後rankをidentity ledgerへ保存。

## 3. Opportunity trade-off

| HIGH | arm | hits | Precision % | mean hits/5 | P>=1 % | Recall % | recall lift | precision lift | universe opportunities | all-selected LB % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| +1 | old | 2895 | 76.3852 | 3.8092 | 98.5526 | 0.8994 | 4.1544 | 4.1580 | 321894 | 76.1842 |
| +1 | new | 2600 | 68.6741 | 3.4211 | 96.7105 | 0.8357 | 3.8191 | 3.8265 | 311101 | 68.4211 |
| +2 | old | 2323 | 61.2929 | 3.0566 | 97.2368 | 2.3228 | 10.7584 | 10.7388 | 100010 | 61.1316 |
| +2 | new | 1792 | 47.3323 | 2.3579 | 90.0000 | 1.9399 | 8.8908 | 8.8822 | 92375 | 47.1579 |
| +3 | old | 1791 | 47.2559 | 2.3566 | 92.5000 | 3.9808 | 18.4382 | 18.4044 | 44991 | 47.1316 |
| +3 | new | 1167 | 30.8241 | 1.5355 | 78.4211 | 2.9063 | 13.3203 | 13.3069 | 40154 | 30.7105 |
| +5 | old | 947 | 24.9868 | 1.2461 | 72.5000 | 6.1378 | 28.4103 | 28.3768 | 15429 | 24.9211 |
| +5 | new | 537 | 14.1838 | 0.7066 | 49.6053 | 3.9494 | 18.0845 | 18.0828 | 13597 | 14.1316 |

Precisionは親evaluatorと同じHigh観測可能選定分母。all-selected lower boundも併記。Recallとrandom liftは各armのeligible universeに対して計算するので、共通旧universe分母のRecallも次に示す。future欠測による選定差し替えはない。

| HIGH | 旧Top5除外winner | replacement winner | selected hit純増減 | 旧universe共通分母 new Recall % |
| --- | --- | --- | --- | --- |
| 1 | 975 | 680 | -295 | 0.8077 |
| 2 | 944 | 413 | -531 | 1.7918 |
| 3 | 852 | 228 | -624 | 2.5939 |
| 5 | 501 | 91 | -410 | 3.4805 |

| HIGH | 全除外candidate hits | evaluable | n |
| --- | --- | --- | --- |
| 1 | 10793 | 18760 | 18790 |
| 2 | 7635 | 18760 | 18790 |
| 3 | 4837 | 18760 | 18790 |
| 5 | 1832 | 18760 | 18790 |

75円以下にwinnerが存在してもPolicyを変更しない。精度改善があっても75円が最適だったとは解釈しない。High touchは約定保証ではない。

| CLOSE | arm | Precision % | Recall % | P>=1 % |
| --- | --- | --- | --- | --- |
| 1 | old | 71.8158 | 0.9304 | 98.5526 |
| 1 | new | 63.3947 | 0.8504 | 96.8421 |
| 2 | old | 57.0000 | 2.4378 | 96.3158 |
| 2 | new | 42.2105 | 1.9610 | 88.2895 |
| 3 | old | 43.5789 | 4.2404 | 90.9211 |
| 3 | new | 26.9211 | 2.9539 | 73.8158 |
| 5 | old | 22.9474 | 6.8189 | 70.0000 |
| 5 | new | 11.9474 | 4.0758 | 43.6842 |

## 4. Frozen Entry downstream / population identity

Gate後の完全なnew selection streamに対して、同一銘柄・sessionの最初の選定をanchorとする親規則を再適用。共通anchorは保存済みdecisionを再利用し、新anchorのみexact Frozen Entry kernel/replayを使用。first selectionが移動する場合を含め、旧母集団の単純filterとは区別する。

| arm | cohort | opportunities | reference eligible | strict30 n |
| --- | --- | --- | --- | --- |
| old | ALL | 3284 | 2448 | 1697 |
| old | DIP_REPRICE_OPPORTUNITY | 541 | 541 | 394 |
| old | INITIAL_ENTRY_OPPORTUNITY | 2743 | 1907 | 1303 |
| new | ALL | 3508 | 2640 | 1872 |
| new | DIP_REPRICE_OPPORTUNITY | 667 | 667 | 468 |
| new | INITIAL_ENTRY_OPPORTUNITY | 2841 | 1973 | 1404 |
| retained | ALL | 2484 | 1944 | 1442 |
| retained | DIP_REPRICE_OPPORTUNITY | 513 | 513 | 377 |
| retained | INITIAL_ENTRY_OPPORTUNITY | 1971 | 1431 | 1065 |
| removed | ALL | 800 | 504 | 255 |
| removed | DIP_REPRICE_OPPORTUNITY | 28 | 28 | 17 |
| removed | INITIAL_ENTRY_OPPORTUNITY | 772 | 476 | 238 |
| added | ALL | 1024 | 696 | 430 |
| added | DIP_REPRICE_OPPORTUNITY | 154 | 154 | 91 |
| added | INITIAL_ENTRY_OPPORTUNITY | 870 | 542 | 339 |

| arm | Decision Price<=75 opportunities | Entry reference<=75 opportunities |
| --- | --- | --- |
| new | 0 | 0 |
| old | 708 | 427 |

Policy対象はSelector Decision Price。選定後の値動きでEntry参照価格が75円以下になる場合はあり得るため、上表で別監査する。Entryへ追加Gateは導入しない。

actual ENTER/fillはNOT_MODELED。Entry opportunity、reference eligibility、Capital Allocationによる資金配分・実約定を混同しない。

| arm | cohort | +1 strict30 % | +2 % | +3 % | +5 % |
| --- | --- | --- | --- | --- | --- |
| old | ALL | 58.8097 | 35.7690 | 21.7443 | 8.9570 |
| old | DIP_REPRICE_OPPORTUNITY | 61.9289 | 32.9949 | 19.2893 | 6.8528 |
| old | INITIAL_ENTRY_OPPORTUNITY | 57.8665 | 36.6078 | 22.4866 | 9.5932 |
| new | ALL | 56.4637 | 30.5556 | 16.8803 | 6.4637 |
| new | DIP_REPRICE_OPPORTUNITY | 58.7607 | 29.4872 | 16.8803 | 5.9829 |
| new | INITIAL_ENTRY_OPPORTUNITY | 55.6980 | 30.9117 | 16.8803 | 6.6239 |

| horizon | level | 旧winner identity retained | 旧winner n | preservation % |
| --- | --- | --- | --- | --- |
| sessionHigh | 1 | 1426 | 1745 | 81.7192 |
| sessionHigh | 2 | 1043 | 1320 | 79.0152 |
| sessionHigh | 3 | 725 | 950 | 76.3158 |
| sessionHigh | 5 | 367 | 484 | 75.8264 |
| strict30 | 1 | 852 | 998 | 85.3707 |
| strict30 | 2 | 489 | 607 | 80.5601 |
| strict30 | 3 | 284 | 369 | 76.9648 |
| strict30 | 5 | 111 | 152 | 73.0263 |

| cohort | level strict30 | 旧winner retained | 旧winner n | preservation % |
| --- | --- | --- | --- | --- |
| INITIAL_ENTRY_OPPORTUNITY | 1 | 619 | 754 | 82.0955 |
| INITIAL_ENTRY_OPPORTUNITY | 2 | 367 | 477 | 76.9392 |
| INITIAL_ENTRY_OPPORTUNITY | 3 | 212 | 293 | 72.3549 |
| INITIAL_ENTRY_OPPORTUNITY | 5 | 85 | 125 | 68.0000 |
| DIP_REPRICE_OPPORTUNITY | 1 | 233 | 244 | 95.4918 |
| DIP_REPRICE_OPPORTUNITY | 2 | 122 | 130 | 93.8462 |
| DIP_REPRICE_OPPORTUNITY | 3 | 72 | 76 | 94.7368 |
| DIP_REPRICE_OPPORTUNITY | 5 | 26 | 27 | 96.2963 |

sessionHighのprecision・coverageはdownstream-summary.json。観測された後続Highに基づく機会であり、全session pathが揃うという意味ではない。strict30は前MAE診断と同じ6本連続完成5m、昼休み跨ぎなし。

## 5. MAE secondary diagnostic

| arm | cohort | n | MAE median % | p05 % | worst % | <=-3 | <=-5 | <=-10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| old | ALL | 1697 | -1.3158 | -5.7410 | -35.2941 | 348 | 132 | 25 |
| old | DIP_REPRICE_OPPORTUNITY | 394 | -1.3004 | -5.4458 | -8.6528 | 71 | 25 | 0 |
| old | INITIAL_ENTRY_OPPORTUNITY | 1303 | -1.3410 | -6.0611 | -35.2941 | 277 | 107 | 25 |
| new | ALL | 1872 | -1.1439 | -5.3489 | -29.6703 | 314 | 110 | 9 |
| new | DIP_REPRICE_OPPORTUNITY | 468 | -1.2041 | -5.4613 | -8.6528 | 83 | 29 | 0 |
| new | INITIAL_ENTRY_OPPORTUNITY | 1404 | -1.1242 | -5.2617 | -29.6703 | 231 | 81 | 9 |
| retained | ALL | 1442 | -1.2914 | -5.5367 | -29.6703 | 271 | 98 | 8 |
| retained | DIP_REPRICE_OPPORTUNITY | 377 | -1.2987 | -5.5088 | -8.6528 | 70 | 25 | 0 |
| retained | INITIAL_ENTRY_OPPORTUNITY | 1065 | -1.2876 | -5.5362 | -29.6703 | 201 | 73 | 8 |
| removed | ALL | 255 | -1.6393 | -11.1111 | -35.2941 | 77 | 34 | 17 |
| removed | DIP_REPRICE_OPPORTUNITY | 17 | -1.3378 | -2.6297 | -3.8462 | 1 | 0 | 0 |
| removed | INITIAL_ENTRY_OPPORTUNITY | 238 | -1.6711 | -11.3194 | -35.2941 | 76 | 34 | 17 |
| added | ALL | 430 | -0.8253 | -3.7591 | -11.1570 | 43 | 12 | 1 |
| added | DIP_REPRICE_OPPORTUNITY | 91 | -0.7921 | -4.3264 | -8.5106 | 13 | 4 | 0 |
| added | INITIAL_ENTRY_OPPORTUNITY | 339 | -0.8278 | -3.5467 | -11.1570 | 30 | 8 | 1 |

旧worst `2024-12-25|2024-12-25T09:30:00+09:00|57590`: Selector Decision Price 17.0円 / Entry 17.0円 / strict30 MAE -35.2941%。Selector段階の除外=True。旧Fixed12/A net −29.4618%は前Evidenceを保持し、今回EXIT再測定はしていない。

旧<=−10% 25件のうち、Decision Price Gate対象 17件、同一Entry opportunity非保持 17件。new全体の残存tailはreplacement・anchor移動も含む上表のnew値。

| symbol | 旧deep10 n | Gate対象 | 同一opportunity retained |
| --- | --- | --- | --- |
| 44160 | 1 | 0 | 1 |
| 47840 | 1 | 0 | 1 |
| 49350 | 1 | 0 | 1 |
| 57590 | 7 | 6 | 1 |
| 65520 | 1 | 0 | 1 |
| 65740 | 1 | 0 | 1 |
| 70690 | 1 | 0 | 1 |
| 81070 | 1 | 1 | 0 |
| 89180 | 10 | 10 | 0 |
| 95620 | 1 | 0 | 1 |

| arm | cohort | deep10 n | deep10 symbol HHI | deep10 symbols |
| --- | --- | --- | --- | --- |
| old | ALL | 25 | 0.2512 | {"44160": 1, "47840": 1, "49350": 1, "57590": 7, "65520": 1, "65740": 1, "70690": 1, "81070": 1, "89180": 10, "95620": 1} |
| old | DIP_REPRICE_OPPORTUNITY | 0 | N/A | {} |
| old | INITIAL_ENTRY_OPPORTUNITY | 25 | 0.2512 | {"44160": 1, "47840": 1, "49350": 1, "57590": 7, "65520": 1, "65740": 1, "70690": 1, "81070": 1, "89180": 10, "95620": 1} |
| new | ALL | 9 | 0.1111 | {"44160": 1, "47770": 1, "47840": 1, "49350": 1, "57590": 1, "65520": 1, "65740": 1, "70690": 1, "95620": 1} |
| new | DIP_REPRICE_OPPORTUNITY | 0 | N/A | {} |
| new | INITIAL_ENTRY_OPPORTUNITY | 9 | 0.1111 | {"44160": 1, "47770": 1, "47840": 1, "49350": 1, "57590": 1, "65520": 1, "65740": 1, "70690": 1, "95620": 1} |

MAE分布変化は上流eligibilityによる母集団変更の記述。EXIT問題の解決、実現利益改善、未知データの再現性を示すものではない。

## 6. Chronological / concentration

| block | arm | +3 Precision % | +5 Precision % | +3 P>=1 % | +5 P>=1 % |
| --- | --- | --- | --- | --- | --- |
| 1 | old | 43.1579 | 20.3158 | 90.0000 | 66.8421 |
| 1 | new | 28.0000 | 12.1053 | 74.2105 | 44.7368 |
| 2 | old | 42.2996 | 19.8312 | 88.9474 | 63.6842 |
| 2 | new | 29.4615 | 12.1436 | 77.8947 | 46.3158 |
| 3 | old | 50.3165 | 28.9030 | 94.7368 | 77.3684 |
| 3 | new | 31.9958 | 16.5787 | 77.3684 | 54.2105 |
| 4 | old | 53.2839 | 30.9322 | 96.3158 | 82.1053 |
| 4 | new | 33.8641 | 15.9236 | 84.2105 | 53.1579 |

| selection | n | symbol unique | symbol HHI | session HHI | top symbols |
| --- | --- | --- | --- | --- | --- |
| new | 3800 | 1085 | 0.0025 | 0.0132 | [["25860", 32], ["31850", 32], ["56160", 32], ["21560", 30], ["38070", 30], ["36240", 29], ["38030", 28], ["45760", 28], ["48830", 28], ["52470", 28]] |
| newExTop3 | 3800 | 1085 | 0.0025 | 0.0132 | [["25860", 32], ["31850", 32], ["56160", 32], ["21560", 30], ["38070", 30], ["36240", 29], ["38030", 28], ["45760", 28], ["48830", 28], ["52470", 28]] |
| old | 3800 | 934 | 0.0070 | 0.0132 | [["89180", 125], ["67400", 116], ["21340", 115], ["99730", 105], ["69930", 67], ["57590", 63], ["45640", 60], ["57210", 57], ["81070", 57], ["17570", 49]] |
| oldExTop3 | 3444 | 931 | 0.0050 | 0.0132 | [["99730", 105], ["69930", 67], ["57590", 63], ["45640", 60], ["57210", 57], ["81070", 57], ["17570", 49], ["88360", 46], ["14910", 29], ["21560", 27]] |

頻出除外は旧Selectorの固定top3 ["89180", "67400", "21340"] を両armに同じように適用した診断のみ。新たなblacklistは作成しない。

| block | arm | cohort | strict30 n | p05 | worst | <=-10 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | new | ALL | 442 | -5.7372 | -16.6134 | 2 |
| 1 | new | DIP_REPRICE_OPPORTUNITY | 107 | -6.0339 | -8.6528 | 0 |
| 1 | new | INITIAL_ENTRY_OPPORTUNITY | 335 | -5.2602 | -16.6134 | 2 |
| 1 | old | ALL | 405 | -6.5390 | -16.6134 | 6 |
| 1 | old | DIP_REPRICE_OPPORTUNITY | 94 | -6.3401 | -8.6528 | 0 |
| 1 | old | INITIAL_ENTRY_OPPORTUNITY | 311 | -6.5260 | -16.6134 | 6 |
| 2 | new | ALL | 477 | -4.5808 | -9.5149 | 0 |
| 2 | new | DIP_REPRICE_OPPORTUNITY | 122 | -3.9211 | -6.7227 | 0 |
| 2 | new | INITIAL_ENTRY_OPPORTUNITY | 355 | -4.8184 | -9.5149 | 0 |
| 2 | old | ALL | 443 | -4.9995 | -12.5000 | 4 |
| 2 | old | DIP_REPRICE_OPPORTUNITY | 106 | -3.9053 | -6.1433 | 0 |
| 2 | old | INITIAL_ENTRY_OPPORTUNITY | 337 | -5.4296 | -12.5000 | 4 |
| 3 | new | ALL | 475 | -5.2326 | -29.6703 | 2 |
| 3 | new | DIP_REPRICE_OPPORTUNITY | 113 | -5.1107 | -7.7093 | 0 |
| 3 | new | INITIAL_ENTRY_OPPORTUNITY | 362 | -5.1646 | -29.6703 | 2 |
| 3 | old | ALL | 426 | -5.6960 | -29.6703 | 7 |
| 3 | old | DIP_REPRICE_OPPORTUNITY | 95 | -5.0174 | -7.7093 | 0 |
| 3 | old | INITIAL_ENTRY_OPPORTUNITY | 331 | -5.9011 | -29.6703 | 7 |
| 4 | new | ALL | 478 | -5.4706 | -12.9291 | 5 |
| 4 | new | DIP_REPRICE_OPPORTUNITY | 126 | -5.1386 | -8.5337 | 0 |
| 4 | new | INITIAL_ENTRY_OPPORTUNITY | 352 | -5.4766 | -12.9291 | 5 |
| 4 | old | ALL | 423 | -6.2571 | -35.2941 | 8 |
| 4 | old | DIP_REPRICE_OPPORTUNITY | 99 | -5.1193 | -8.5337 | 0 |
| 4 | old | INITIAL_ENTRY_OPPORTUNITY | 324 | -6.7230 | -35.2941 | 8 |

76 session別の全opportunity統計、INITIAL/DIP別集中、固定top3除外後MAEはJSON原本に保存。

## 7. Integrity / STOP

Selector audit: {"causalAgeBounds": true, "eligiblePriceMin": 76.0, "excludedPlusAddedCountBalance": true, "lowPriceSelected": 0, "maxScoreTransportDifference": 2.842170943040401e-14, "missingFailOpen": false, "oldMetricsParity": true, "oldSelectedParity": 3800, "outputOnlyLabels": true, "price75Selected": 0, "reverseInputSelectionParity": true, "runtimeWrapperParity": true, "scoreTransportComparisonOnlyTolerance": 1e-12, "scoreTransportDifferences": 486, "scoresUnchanged": true, "sourcePinsUnchanged": true}

Entry audit: {"newAnchorReplay": 870, "oldStrict30Parity": 1697, "retainedDecisionsReused": 1971}

測定時のold Top5 3,800 identity/price/rank完全一致・scoreのCSV表現差監査、旧opportunity集計一致、旧strict30 1,697件一致を必須assertionで確認。runtime Gateと全候補measurementのTop5一致、入力逆順でも同一selectionを確認。

全9Safety flags false。Fresh/OOS未開封。旧Selector・Entry・Candidate A・旧Evidenceは不変。専用CIでは新measurement 7ファイルのbyte一致を確認し、artifact内容を確認後にFreeze判定する。既存Candidate C KILL gateはそのまま保持。

本policyのimpact audit完了でSTOP。Entry/EXIT研究、Fresh/OOS、Capital、Portfolio、main merge、実行機能へ進まない。
