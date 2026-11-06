# Comprehensive LONG Entry Intelligence v3 — Causal Event Study

**COMPREHENSIVE_LONG_ENTRY_V3_DEVELOPMENT_LIMIT_REACHED**

TRAIN上の事前固定6 Event＋3 sequenceを測定。結果後の閾値・feature・sequence追加なし。これはEntry Timing全体の不可能性を示すものではない。

Protocol commit: `f66b4783f0507a2733d6ccdef90a209bb729fed0`。SHA256: `642e43b301b5d46535f7399e509e0923e3393584fa4bbafbe99852c6ee0975f8`。開始HEAD: `f935594fa2d6b714f25f045f5c86101054efcbb6`。

## Lineage / population / exposure

¥75 Selector、Frozen NEW Entry / Opportunity Generator、INITIAL/DIP identity、Candidate Aは不変。v1 KILL / v2 LIMIT Evidenceを保持。

| Partition | sessions | opportunities | v3 evaluated |
| --- | --- | --- | --- |
| TRAIN | 38 | 1760 | True |
| VALIDATION | 19 | 863 | False |
| DEVELOPMENT_TEST | 19 | 885 | False |

TRAIN complete common60: 633/1760。INITIAL/DIP emitted: {'DIP_REPRICE_OPPORTUNITY': 338, 'INITIAL_ENTRY_OPPORTUNITY': 1422}。

元データは76 Development sessionsのimmutable bundle。identity確認後にTRAINへfilterし、Validation/DEV TESTのv3 state/Event/outcomeは評価していない。過去に一般診断へ露出したDevelopmentでありFreshではない。

## Precommitted definitions

| Event | Exact definition |
| --- | --- |
| E1_PULLBACK | First completed post-opportunity CLOSE strictly below fixed opportunity reference OPEN. Zero is a structural sign, no magnitude threshold. |
| E2_STABILIZATION | After an earlier E1 bar: current LOW>=previous LOW, CLOSE>=previous CLOSE, and current range<=previous range. All comparisons use completed bars. |
| E3_RECLAIM | After an earlier E1 bar: current CLOSE>previous completed bar HIGH. |
| E4_MOMENTUM_TURN | After an earlier E1 bar and at least 3 completed post-opportunity bars: previous close-to-close change<=0 and current close-to-close change>0. |
| E5_FAILED_BREAKDOWN | After an earlier E1 bar: current LOW<previous LOW and current CLOSE>previous LOW. Only low vs terminal CLOSE is used, never HIGH-before-LOW ordering. |
| E6_CONTINUATION | At least 3 completed post-opportunity bars: two consecutive positive close changes, two consecutive higher LOWs, and current HIGH>previous HIGH. Does not require pullback. |
| S1_P_S_R | E1 -> E2 -> E3, strictly later completed-bar timestamps for every transition. |
| S2_P_F_R | E1 -> E5 -> E3, strictly later completed-bar timestamps for every transition. |
| S3_P_S_M | E1 -> E2 -> E4, strictly later completed-bar timestamps for every transition. |

数値の深さthreshold探索なし。ゼロ・前barとの順序・連続した符号という構造定義。全Eventは最初の認識のみ。sequenceは各stageを異なるcompleted barで満たす。最大30分・元segment内。

StateではOpportunity referenceからの下落、期間、range、wick、close位置、momentum変化等を連続量として保存。動的VWAP/出来高/相対強度/市場index pathはUNAVAILABLE。既存43特徴のanchor snapshotを更新値と偽らない。

## Event separation and KEEP/KILL

| Event | complete n | Event n | PB occurrence % | Failure occurrence % | gap pp | PB price improvement pp | PB strict30 median improvement pp | PB MFE ratio | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1_PULLBACK | 633 | 441 | 51.4563 | 95.8904 | -44.4341 | 0.8359 | 1.0039 | 1.1054 | KILL |
| E2_STABILIZATION | 633 | 333 | 38.8350 | 69.8630 | -31.0281 | 0.4276 | 1.1943 | 1.0169 | KILL |
| E3_RECLAIM | 633 | 202 | 37.8641 | 34.2466 | 3.6175 | -0.4051 | 0.8168 | 0.8865 | KILL |
| E4_MOMENTUM_TURN | 633 | 354 | 40.7767 | 77.3973 | -36.6206 | -0.2548 | 1.2385 | 0.8569 | KILL |
| E5_FAILED_BREAKDOWN | 633 | 194 | 25.2427 | 45.8904 | -20.6477 | -0.4102 | 0.5593 | 0.8302 | KILL |
| E6_CONTINUATION | 633 | 148 | 40.7767 | 12.3288 | 28.4479 | -2.1990 | -0.4060 | 0.5739 | KILL |
| S1_P_S_R | 633 | 107 | 25.2427 | 10.9589 | 14.2838 | -0.4073 | 1.3574 | 0.8982 | KILL |
| S2_P_F_R | 633 | 68 | 15.5340 | 11.6438 | 3.8901 | -1.7172 | 0.3275 | 0.6408 | KILL |
| S3_P_S_M | 633 | 136 | 17.4757 | 25.3425 | -7.8667 | -0.1320 | 1.3649 | 0.9715 | KILL |

PBはPULLBACK_THEN_WINNER＋DEEP_PULLBACK_THEN_WINNER。発生率はbaseline complete cohort全件分母、location/riskはentered pairs分母。両者を混同しない。発生率のWilson区間はJSONに保持し、相関したEpisodeを独立標本と主張しない。

KEEPにはPB location/strict30 MAE改善、MFE維持、entered-pair +3/+5維持、failureとの差、INITIAL/DIP、時系列、集中度の全事前条件を要求。KEEPでも全体Entry PASSではない。

| Event | Failed precommitted gates |
| --- | --- |
| E1_PULLBACK | failureSeparation, chronological, top3Exclusion |
| E2_STABILIZATION | failureSeparation, preserve3EnteredPairs, preserve5EnteredPairs, chronological, top3Exclusion |
| E3_RECLAIM | failureSeparation, priceMean, priceMedian, remainingMFE, preserve3EnteredPairs, preserve5EnteredPairs, INITIAL_DIP, chronological, top3Exclusion |
| E4_MOMENTUM_TURN | failureSeparation, priceMean, priceMedian, remainingMFE, preserve3EnteredPairs, preserve5EnteredPairs, INITIAL_DIP, chronological, top3Exclusion |
| E5_FAILED_BREAKDOWN | pbCapture, failureSeparation, priceMean, priceMedian, remainingMFE, preserve3EnteredPairs, preserve5EnteredPairs, INITIAL_DIP, chronological, top3Exclusion |
| E6_CONTINUATION | priceMean, priceMedian, strict30Median, strict30P05, remainingMFE, preserve3EnteredPairs, preserve5EnteredPairs, INITIAL_DIP, chronological, top3Exclusion |
| S1_P_S_R | pbCapture, priceMean, priceMedian, remainingMFE, preserve3EnteredPairs, preserve5EnteredPairs, INITIAL_DIP, chronological, concentration, top3Exclusion |
| S2_P_F_R | pbCapture, failureSeparation, priceMean, priceMedian, remainingMFE, preserve3EnteredPairs, preserve5EnteredPairs, pbEventN, INITIAL_DIP, chronological, top3Exclusion |
| S3_P_S_M | pbCapture, failureSeparation, priceMean, priceMedian, preserve3EnteredPairs, preserve5EnteredPairs, pbEventN, INITIAL_DIP, chronological, concentration, top3Exclusion |

## B0_IMMEDIATE and each diagnostic Event policy

### E1_PULLBACK

| Metric | B0 same entered pairs / full base as noted | Event |
| --- | --- | --- |
| Opportunity n | 1760 | 1760 |
| Reference ENTER (not real fills) | 1280 | 770 |
| Common complete | 633 | 633 |
| Complete ENTER | 633 | 441 |
| Entry coverage % | 100 | 69.6682 |
| Delay mean min | 0 | 9.4156 |
| Delay median min | 0 | 5.0000 |
| Paired mean Entry price | 1215.4478 | 1207.2075 |
| Mean price improvement pp | 0 | 0.8591 |
| Strict30 MAE mean | -2.3444 | -1.6576 |
| Strict30 MAE median | -1.8750 | -1.1611 |
| Strict30 MAE p10 | -4.5714 | -3.7288 |
| Strict30 MAE p05 | -6.1433 | -5.2227 |
| Strict30 worst MAE | -16.6134 | -8.5938 |
| Common remaining MFE mean | 1.5475 | 1.8840 |
| +1 preservation % | 100 | 45.5224 |
| +2 preservation % | 100 | 39.3701 |
| +3 preservation % | 100 | 33.1126 |
| +5 preservation % | 100 | 33.3333 |
| IMMEDIATE_WINNER entered & remaining+3 % | 100 | 3.3333 |
| FAST_WINNER entered & remaining+3 % | 100 | 16.4835 |
| PULLBACK_WINNER entered & remaining+3 % | 100 | 44.6602 |

| Path class | all n | complete n | ENTER complete | waited emitted | NO_EVENT | EXPIRED | UNKNOWN | missed +3 | missed +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHOP_THEN_WINNER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CONTINUED_FAILURE | 146 | 146 | 140 | 146 | 6 | 0 | 0 | 0 | 0 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 12 | 12 | 12 | 0 | 0 | 0 | 0 | 0 |
| IMMEDIATE_WINNER | 30 | 30 | 3 | 30 | 27 | 0 | 0 | 29 | 12 |
| INCONCLUSIVE | 1145 | 18 | 7 | 665 | 48 | 62 | 699 | 15 | 8 |
| OPPORTUNITY_EXPIRED | 336 | 336 | 238 | 336 | 98 | 0 | 0 | 0 | 0 |
| PULLBACK_THEN_WINNER | 91 | 91 | 41 | 91 | 50 | 0 | 0 | 57 | 20 |

| Pullback class | complete n | ENTER | price improvement pp | strict30 median improvement pp | strict30 p05 improvement pp | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- |
| PULLBACK_THEN_WINNER | 91 | 41 | 0.6440 | 0.7979 | 1.4286 | 1.0437 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 12 | 1.4917 | 2.2241 | 0.9129 | 1.2706 |

| Cohort | PB complete | PB ENTER | PB occurrence % | failure occurrence % | PB price pp | PB MAE median improvement pp | PB MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 25 | 12 | 48.0000 | 94.5946 | 0.7818 | 0.4211 | 1.0939 |
| INITIAL_ENTRY_OPPORTUNITY | 78 | 41 | 52.5641 | 96.3303 | 0.8518 | 1.0254 | 1.1089 |

| TRAIN block | PB complete | Event n in PB | gap pp | PB price pp | PB MAE median improvement pp | block gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 32 | 17 | -44.4360 | 0.7956 | 0.6088 | False |
| 2 | 19 | 11 | -36.9771 | 0.7883 | 0.5314 | False |
| 3 | 18 | 9 | -46.2963 | 0.7846 | 0.7882 | False |
| 4 | 34 | 16 | -47.8130 | 0.9404 | 1.1601 | False |

| MAE tail | B0 all | B0 entered pairs | Event entered pairs | better Entry reduction | not-entered baseline tail |
| --- | --- | --- | --- | --- | --- |
| 3 | 189 | 178 | 111 | 67 | 11 |
| 5 | 76 | 72 | 38 | 34 | 4 |
| 10 | 8 | 8 | 4 | 4 | 0 |

RISK_REDUCTION_BY_BETTER_ENTRYは同一Opportunityのbaseline tail−Event tail。非Entry側の件数はSKIPとみなした場合の見かけの減少に相当し、採用済みSKIP policyとは呼ばない。

Delay bins: {'0': 0, '10': 135, '15': 70, '20': 55, '25': 35, '30': 20, '5': 455}。Outcomes: {'COUNTERFACTUAL_ENTER': 770, 'EXPIRED_BOUNDARY': 62, 'NO_EVENT': 229, 'UNKNOWN_EXECUTION': 44, 'UNKNOWN_PREFIX': 175, 'UNKNOWN_REFERENCE': 480}。

No-event winners (+1/+2/+3/+5): {'1': 181, '2': 134, '3': 88, '5': 39}。Winner before event: {'1': 114, '2': 36, '3': 17, '5': 2}。

Evaluator-only IMMEDIATE_ENTRY_REQUIRED tag: 27。これは実行時のGuardではない。

Concentration: {'maxPullbackSessionShare': 0.1320754716981132, 'maxPullbackSymbolShare': 0.05660377358490566, 'pullbackEnteredSymbolHHI': 0.029547881808472762, 'pullbackEnteredUniqueSymbols': 40, 'symbolHHI': 0.002721461776859504, 'top10': [['25860', 18], ['48830', 17], ['190A0', 15], ['21560', 15], ['38030', 15], ['65740', 15], ['33500', 14], ['56160', 14], ['37790', 13], ['246A0', 12]], 'top3Train': ['25860', '48830', '190A0'], 'uniqueSymbols': 742}。Top3 exclusion failed gates: ['failureSeparation']。

### E2_STABILIZATION

| Metric | B0 same entered pairs / full base as noted | Event |
| --- | --- | --- |
| Opportunity n | 1760 | 1760 |
| Reference ENTER (not real fills) | 1280 | 546 |
| Common complete | 633 | 633 |
| Complete ENTER | 633 | 333 |
| Entry coverage % | 100 | 52.6066 |
| Delay mean min | 0 | 17.8388 |
| Delay median min | 0 | 15.0000 |
| Paired mean Entry price | 1193.1892 | 1188.4550 |
| Mean price improvement pp | 0 | 0.7012 |
| Strict30 MAE mean | -2.3145 | -1.6632 |
| Strict30 MAE median | -1.8651 | -1.1121 |
| Strict30 MAE p10 | -4.3363 | -3.4084 |
| Strict30 MAE p05 | -5.7741 | -4.4856 |
| Strict30 worst MAE | -16.6134 | -18.7273 |
| Common remaining MFE mean | 1.4657 | 1.5033 |
| +1 preservation % | 100 | 26.1194 |
| +2 preservation % | 100 | 23.2283 |
| +3 preservation % | 100 | 21.8543 |
| +5 preservation % | 100 | 15.0000 |
| IMMEDIATE_WINNER entered & remaining+3 % | 100 | 0.0000 |
| FAST_WINNER entered & remaining+3 % | 100 | 7.6923 |
| PULLBACK_WINNER entered & remaining+3 % | 100 | 31.0680 |

| Path class | all n | complete n | ENTER complete | waited emitted | NO_EVENT | EXPIRED | UNKNOWN | missed +3 | missed +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHOP_THEN_WINNER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CONTINUED_FAILURE | 146 | 146 | 102 | 146 | 44 | 0 | 0 | 0 | 0 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 12 | 11 | 12 | 1 | 0 | 0 | 2 | 1 |
| IMMEDIATE_WINNER | 30 | 30 | 1 | 30 | 29 | 0 | 0 | 30 | 13 |
| INCONCLUSIVE | 1145 | 18 | 4 | 665 | 82 | 99 | 747 | 17 | 9 |
| OPPORTUNITY_EXPIRED | 336 | 336 | 186 | 336 | 150 | 0 | 0 | 0 | 0 |
| PULLBACK_THEN_WINNER | 91 | 91 | 29 | 91 | 62 | 0 | 0 | 69 | 28 |

| Pullback class | complete n | ENTER | price improvement pp | strict30 median improvement pp | strict30 p05 improvement pp | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- |
| PULLBACK_THEN_WINNER | 91 | 29 | -0.0258 | 0.5481 | -0.9407 | 0.8631 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 11 | 1.6231 | 4.8084 | 4.8459 | 1.2857 |

| Cohort | PB complete | PB ENTER | PB occurrence % | failure occurrence % | PB price pp | PB MAE median improvement pp | PB MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 25 | 8 | 32.0000 | 62.1622 | 1.1796 | 1.3319 | 1.2393 |
| INITIAL_ENTRY_OPPORTUNITY | 78 | 32 | 41.0256 | 72.4771 | 0.2396 | 1.0831 | 0.9649 |

| TRAIN block | PB complete | Event n in PB | gap pp | PB price pp | PB MAE median improvement pp | block gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 32 | 16 | -23.1707 | 0.6843 | 1.3013 | False |
| 2 | 19 | 5 | -45.4791 | -1.1411 | 0.0098 | False |
| 3 | 18 | 5 | -35.1852 | -0.1097 | 0.4542 | False |
| 4 | 34 | 14 | -28.0543 | 0.8865 | 1.9690 | False |

| MAE tail | B0 all | B0 entered pairs | Event entered pairs | better Entry reduction | not-entered baseline tail |
| --- | --- | --- | --- | --- | --- |
| 3 | 189 | 129 | 67 | 62 | 60 |
| 5 | 76 | 49 | 21 | 28 | 27 |
| 10 | 8 | 8 | 4 | 4 | 0 |

RISK_REDUCTION_BY_BETTER_ENTRYは同一Opportunityのbaseline tail−Event tail。非Entry側の件数はSKIPとみなした場合の見かけの減少に相当し、採用済みSKIP policyとは呼ばない。

Delay bins: {'0': 0, '10': 155, '15': 131, '20': 110, '25': 95, '30': 55, '5': 0}。Outcomes: {'COUNTERFACTUAL_ENTER': 546, 'EXPIRED_BOUNDARY': 99, 'NO_EVENT': 368, 'UNKNOWN_EXECUTION': 30, 'UNKNOWN_PREFIX': 237, 'UNKNOWN_REFERENCE': 480}。

No-event winners (+1/+2/+3/+5): {'1': 241, '2': 165, '3': 106, '5': 46}。Winner before event: {'1': 98, '2': 31, '3': 13, '5': 3}。

Evaluator-only IMMEDIATE_ENTRY_REQUIRED tag: 29。これは実行時のGuardではない。

Concentration: {'maxPullbackSessionShare': 0.175, 'maxPullbackSymbolShare': 0.075, 'pullbackEnteredSymbolHHI': 0.035, 'pullbackEnteredUniqueSymbols': 33, 'symbolHHI': 0.002721461776859504, 'top10': [['25860', 18], ['48830', 17], ['190A0', 15], ['21560', 15], ['38030', 15], ['65740', 15], ['33500', 14], ['56160', 14], ['37790', 13], ['246A0', 12]], 'top3Train': ['25860', '48830', '190A0'], 'uniqueSymbols': 742}。Top3 exclusion failed gates: ['failureSeparation', 'preserve3EnteredPairs', 'preserve5EnteredPairs']。

### E3_RECLAIM

| Metric | B0 same entered pairs / full base as noted | Event |
| --- | --- | --- |
| Opportunity n | 1760 | 1760 |
| Reference ENTER (not real fills) | 1280 | 373 |
| Common complete | 633 | 633 |
| Complete ENTER | 633 | 202 |
| Entry coverage % | 100 | 31.9115 |
| Delay mean min | 0 | 19.4370 |
| Delay median min | 0 | 20.0000 |
| Paired mean Entry price | 1397.4480 | 1394.4777 |
| Mean price improvement pp | 0 | 0.1095 |
| Strict30 MAE mean | -2.2545 | -1.9062 |
| Strict30 MAE median | -1.7568 | -1.4815 |
| Strict30 MAE p10 | -4.2849 | -4.2865 |
| Strict30 MAE p05 | -5.6980 | -5.0616 |
| Strict30 worst MAE | -16.6134 | -12.1628 |
| Common remaining MFE mean | 1.9538 | 1.5679 |
| +1 preservation % | 100 | 19.1542 |
| +2 preservation % | 100 | 17.7165 |
| +3 preservation % | 100 | 19.8675 |
| +5 preservation % | 100 | 15.0000 |
| IMMEDIATE_WINNER entered & remaining+3 % | 100 | 3.3333 |
| FAST_WINNER entered & remaining+3 % | 100 | 6.5934 |
| PULLBACK_WINNER entered & remaining+3 % | 100 | 28.1553 |

| Path class | all n | complete n | ENTER complete | waited emitted | NO_EVENT | EXPIRED | UNKNOWN | missed +3 | missed +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHOP_THEN_WINNER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CONTINUED_FAILURE | 146 | 146 | 50 | 146 | 96 | 0 | 0 | 0 | 0 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 12 | 11 | 12 | 1 | 0 | 0 | 2 | 1 |
| IMMEDIATE_WINNER | 30 | 30 | 1 | 30 | 29 | 0 | 0 | 29 | 12 |
| INCONCLUSIVE | 1145 | 18 | 3 | 665 | 87 | 133 | 751 | 18 | 9 |
| OPPORTUNITY_EXPIRED | 336 | 336 | 109 | 336 | 227 | 0 | 0 | 0 | 0 |
| PULLBACK_THEN_WINNER | 91 | 91 | 28 | 91 | 63 | 0 | 0 | 72 | 29 |

| Pullback class | complete n | ENTER | price improvement pp | strict30 median improvement pp | strict30 p05 improvement pp | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- |
| PULLBACK_THEN_WINNER | 91 | 28 | -0.7186 | 0.6138 | -2.6538 | 0.7986 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 11 | 0.3930 | 3.4099 | 2.6710 | 1.0682 |

| Cohort | PB complete | PB ENTER | PB occurrence % | failure occurrence % | PB price pp | PB MAE median improvement pp | PB MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 25 | 9 | 36.0000 | 32.4324 | -0.1407 | 0.4306 | 0.9770 |
| INITIAL_ENTRY_OPPORTUNITY | 78 | 30 | 38.4615 | 34.8624 | -0.4843 | 1.0511 | 0.8579 |

| TRAIN block | PB complete | Event n in PB | gap pp | PB price pp | PB MAE median improvement pp | block gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 32 | 12 | 8.2317 | 0.2253 | 1.0286 | True |
| 2 | 19 | 9 | 11.4710 | -1.1685 | -0.0684 | False |
| 3 | 18 | 6 | -14.8148 | -1.3357 | -1.2731 | False |
| 4 | 34 | 12 | 7.0890 | 0.0026 | 1.3671 | True |

| MAE tail | B0 all | B0 entered pairs | Event entered pairs | better Entry reduction | not-entered baseline tail |
| --- | --- | --- | --- | --- | --- |
| 3 | 189 | 71 | 49 | 22 | 118 |
| 5 | 76 | 30 | 15 | 15 | 46 |
| 10 | 8 | 3 | 2 | 1 | 5 |

RISK_REDUCTION_BY_BETTER_ENTRYは同一Opportunityのbaseline tail−Event tail。非Entry側の件数はSKIPとみなした場合の見かけの減少に相当し、採用済みSKIP policyとは呼ばない。

Delay bins: {'0': 0, '10': 62, '15': 97, '20': 90, '25': 69, '30': 55, '5': 0}。Outcomes: {'COUNTERFACTUAL_ENTER': 373, 'EXPIRED_BOUNDARY': 133, 'NO_EVENT': 503, 'UNKNOWN_EXECUTION': 26, 'UNKNOWN_PREFIX': 245, 'UNKNOWN_REFERENCE': 480}。

No-event winners (+1/+2/+3/+5): {'1': 282, '2': 192, '3': 108, '5': 41}。Winner before event: {'1': 80, '2': 18, '3': 10, '5': 2}。

Evaluator-only IMMEDIATE_ENTRY_REQUIRED tag: 29。これは実行時のGuardではない。

Concentration: {'maxPullbackSessionShare': 0.1794871794871795, 'maxPullbackSymbolShare': 0.07692307692307693, 'pullbackEnteredSymbolHHI': 0.0440499671268902, 'pullbackEnteredUniqueSymbols': 27, 'symbolHHI': 0.002721461776859504, 'top10': [['25860', 18], ['48830', 17], ['190A0', 15], ['21560', 15], ['38030', 15], ['65740', 15], ['33500', 14], ['56160', 14], ['37790', 13], ['246A0', 12]], 'top3Train': ['25860', '48830', '190A0'], 'uniqueSymbols': 742}。Top3 exclusion failed gates: ['failureSeparation', 'preserve3EnteredPairs', 'preserve5EnteredPairs', 'priceMean', 'priceMedian']。

### E4_MOMENTUM_TURN

| Metric | B0 same entered pairs / full base as noted | Event |
| --- | --- | --- |
| Opportunity n | 1760 | 1760 |
| Reference ENTER (not real fills) | 1280 | 540 |
| Common complete | 633 | 633 |
| Complete ENTER | 633 | 354 |
| Entry coverage % | 100 | 55.9242 |
| Delay mean min | 0 | 21.3426 |
| Delay median min | 0 | 20.0000 |
| Paired mean Entry price | 1299.0523 | 1291.2627 |
| Mean price improvement pp | 0 | 0.7109 |
| Strict30 MAE mean | -2.3542 | -1.7485 |
| Strict30 MAE median | -1.8872 | -1.1682 |
| Strict30 MAE p10 | -4.3861 | -3.9452 |
| Strict30 MAE p05 | -6.1538 | -5.3970 |
| Strict30 worst MAE | -16.6134 | -10.5236 |
| Common remaining MFE mean | 1.5580 | 1.4852 |
| +1 preservation % | 100 | 30.8458 |
| +2 preservation % | 100 | 23.6220 |
| +3 preservation % | 100 | 20.5298 |
| +5 preservation % | 100 | 13.3333 |
| IMMEDIATE_WINNER entered & remaining+3 % | 100 | 3.3333 |
| FAST_WINNER entered & remaining+3 % | 100 | 13.1868 |
| PULLBACK_WINNER entered & remaining+3 % | 100 | 26.2136 |

| Path class | all n | complete n | ENTER complete | waited emitted | NO_EVENT | EXPIRED | UNKNOWN | missed +3 | missed +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHOP_THEN_WINNER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CONTINUED_FAILURE | 146 | 146 | 113 | 146 | 33 | 0 | 0 | 0 | 0 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 12 | 10 | 12 | 2 | 0 | 0 | 3 | 1 |
| IMMEDIATE_WINNER | 30 | 30 | 2 | 30 | 28 | 0 | 0 | 29 | 12 |
| INCONCLUSIVE | 1145 | 18 | 7 | 665 | 72 | 117 | 763 | 15 | 9 |
| OPPORTUNITY_EXPIRED | 336 | 336 | 190 | 336 | 146 | 0 | 0 | 0 | 0 |
| PULLBACK_THEN_WINNER | 91 | 91 | 32 | 91 | 59 | 0 | 0 | 73 | 30 |

| Pullback class | complete n | ENTER | price improvement pp | strict30 median improvement pp | strict30 p05 improvement pp | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- |
| PULLBACK_THEN_WINNER | 91 | 32 | -0.6679 | 0.5358 | -3.5507 | 0.7191 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 10 | 1.0670 | 4.1372 | 4.3422 | 1.1850 |

| Cohort | PB complete | PB ENTER | PB occurrence % | failure occurrence % | PB price pp | PB MAE median improvement pp | PB MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 25 | 10 | 40.0000 | 72.9730 | -0.5858 | 0.6315 | 0.8393 |
| INITIAL_ENTRY_OPPORTUNITY | 78 | 32 | 41.0256 | 78.8991 | -0.1514 | 1.2593 | 0.8628 |

| TRAIN block | PB complete | Event n in PB | gap pp | PB price pp | PB MAE median improvement pp | block gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 32 | 14 | -41.6159 | 0.3197 | 1.1988 | False |
| 2 | 19 | 9 | -29.5547 | -1.7462 | -0.5488 | False |
| 3 | 18 | 7 | -42.5926 | -0.8751 | -0.5187 | False |
| 4 | 34 | 12 | -31.3725 | 0.5552 | 1.5204 | False |

| MAE tail | B0 all | B0 entered pairs | Event entered pairs | better Entry reduction | not-entered baseline tail |
| --- | --- | --- | --- | --- | --- |
| 3 | 189 | 143 | 72 | 71 | 46 |
| 5 | 76 | 53 | 28 | 25 | 23 |
| 10 | 8 | 7 | 4 | 3 | 1 |

RISK_REDUCTION_BY_BETTER_ENTRYは同一Opportunityのbaseline tail−Event tail。非Entry側の件数はSKIPとみなした場合の見かけの減少に相当し、採用済みSKIP policyとは呼ばない。

Delay bins: {'0': 0, '10': 0, '15': 154, '20': 166, '25': 141, '30': 79, '5': 0}。Outcomes: {'COUNTERFACTUAL_ENTER': 540, 'EXPIRED_BOUNDARY': 117, 'NO_EVENT': 340, 'UNKNOWN_EXECUTION': 21, 'UNKNOWN_PREFIX': 262, 'UNKNOWN_REFERENCE': 480}。

No-event winners (+1/+2/+3/+5): {'1': 220, '2': 157, '3': 100, '5': 45}。Winner before event: {'1': 129, '2': 40, '3': 18, '5': 5}。

Evaluator-only IMMEDIATE_ENTRY_REQUIRED tag: 28。これは実行時のGuardではない。

Concentration: {'maxPullbackSessionShare': 0.14285714285714285, 'maxPullbackSymbolShare': 0.07142857142857142, 'pullbackEnteredSymbolHHI': 0.03741496598639455, 'pullbackEnteredUniqueSymbols': 32, 'symbolHHI': 0.002721461776859504, 'top10': [['25860', 18], ['48830', 17], ['190A0', 15], ['21560', 15], ['38030', 15], ['65740', 15], ['33500', 14], ['56160', 14], ['37790', 13], ['246A0', 12]], 'top3Train': ['25860', '48830', '190A0'], 'uniqueSymbols': 742}。Top3 exclusion failed gates: ['failureSeparation', 'preserve3EnteredPairs', 'preserve5EnteredPairs', 'priceMean', 'priceMedian', 'remainingMFE']。

### E5_FAILED_BREAKDOWN

| Metric | B0 same entered pairs / full base as noted | Event |
| --- | --- | --- |
| Opportunity n | 1760 | 1760 |
| Reference ENTER (not real fills) | 1280 | 279 |
| Common complete | 633 | 633 |
| Complete ENTER | 633 | 194 |
| Entry coverage % | 100 | 30.6477 |
| Delay mean min | 0 | 18.1183 |
| Delay median min | 0 | 15.0000 |
| Paired mean Entry price | 1372.3196 | 1360.7294 |
| Mean price improvement pp | 0 | 0.9312 |
| Strict30 MAE mean | -2.5749 | -1.5871 |
| Strict30 MAE median | -2.1236 | -1.0965 |
| Strict30 MAE p10 | -4.5587 | -3.2738 |
| Strict30 MAE p05 | -6.7878 | -4.2409 |
| Strict30 worst MAE | -16.6134 | -14.2035 |
| Common remaining MFE mean | 1.5822 | 1.7441 |
| +1 preservation % | 100 | 18.4080 |
| +2 preservation % | 100 | 14.9606 |
| +3 preservation % | 100 | 13.2450 |
| +5 preservation % | 100 | 8.3333 |
| IMMEDIATE_WINNER entered & remaining+3 % | 100 | 0.0000 |
| FAST_WINNER entered & remaining+3 % | 100 | 4.3956 |
| PULLBACK_WINNER entered & remaining+3 % | 100 | 18.4466 |

| Path class | all n | complete n | ENTER complete | waited emitted | NO_EVENT | EXPIRED | UNKNOWN | missed +3 | missed +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHOP_THEN_WINNER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CONTINUED_FAILURE | 146 | 146 | 67 | 146 | 79 | 0 | 0 | 0 | 0 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 12 | 4 | 12 | 8 | 0 | 0 | 8 | 3 |
| IMMEDIATE_WINNER | 30 | 30 | 2 | 30 | 28 | 0 | 0 | 30 | 13 |
| INCONCLUSIVE | 1145 | 18 | 1 | 665 | 135 | 160 | 764 | 17 | 9 |
| OPPORTUNITY_EXPIRED | 336 | 336 | 98 | 336 | 238 | 0 | 0 | 0 | 0 |
| PULLBACK_THEN_WINNER | 91 | 91 | 22 | 91 | 69 | 0 | 0 | 76 | 30 |

| Pullback class | complete n | ENTER | price improvement pp | strict30 median improvement pp | strict30 p05 improvement pp | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- |
| PULLBACK_THEN_WINNER | 91 | 22 | -0.5050 | 0.1653 | -0.6916 | 0.7718 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 4 | 0.1109 | 3.5871 | 6.3182 | 1.0117 |

| Cohort | PB complete | PB ENTER | PB occurrence % | failure occurrence % | PB price pp | PB MAE median improvement pp | PB MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 25 | 7 | 28.0000 | 40.5405 | -0.2455 | -0.1420 | 0.9506 |
| INITIAL_ENTRY_OPPORTUNITY | 78 | 19 | 24.3590 | 47.7064 | -0.4709 | 0.7423 | 0.7851 |

| TRAIN block | PB complete | Event n in PB | gap pp | PB price pp | PB MAE median improvement pp | block gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 32 | 10 | -27.2866 | 0.1365 | 0.6973 | False |
| 2 | 19 | 6 | 0.8097 | -1.6295 | -0.3925 | False |
| 3 | 18 | 2 | -33.3333 | -0.0160 | -0.0928 | False |
| 4 | 34 | 8 | -25.1885 | -0.2778 | 0.9178 | False |

| MAE tail | B0 all | B0 entered pairs | Event entered pairs | better Entry reduction | not-entered baseline tail |
| --- | --- | --- | --- | --- | --- |
| 3 | 189 | 84 | 40 | 44 | 105 |
| 5 | 76 | 31 | 15 | 16 | 45 |
| 10 | 8 | 6 | 3 | 3 | 2 |

RISK_REDUCTION_BY_BETTER_ENTRYは同一Opportunityのbaseline tail−Event tail。非Entry側の件数はSKIPとみなした場合の見かけの減少に相当し、採用済みSKIP policyとは呼ばない。

Delay bins: {'0': 0, '10': 78, '15': 69, '20': 46, '25': 52, '30': 34, '5': 0}。Outcomes: {'COUNTERFACTUAL_ENTER': 279, 'EXPIRED_BOUNDARY': 160, 'NO_EVENT': 557, 'UNKNOWN_EXECUTION': 9, 'UNKNOWN_PREFIX': 275, 'UNKNOWN_REFERENCE': 480}。

No-event winners (+1/+2/+3/+5): {'1': 312, '2': 199, '3': 122, '5': 51}。Winner before event: {'1': 55, '2': 18, '3': 10, '5': 3}。

Evaluator-only IMMEDIATE_ENTRY_REQUIRED tag: 28。これは実行時のGuardではない。

Concentration: {'maxPullbackSessionShare': 0.11538461538461539, 'maxPullbackSymbolShare': 0.07692307692307693, 'pullbackEnteredSymbolHHI': 0.05029585798816569, 'pullbackEnteredUniqueSymbols': 22, 'symbolHHI': 0.002721461776859504, 'top10': [['25860', 18], ['48830', 17], ['190A0', 15], ['21560', 15], ['38030', 15], ['65740', 15], ['33500', 14], ['56160', 14], ['37790', 13], ['246A0', 12]], 'top3Train': ['25860', '48830', '190A0'], 'uniqueSymbols': 742}。Top3 exclusion failed gates: ['failureSeparation', 'pbCapture', 'preserve3EnteredPairs', 'preserve5EnteredPairs', 'priceMean', 'priceMedian', 'remainingMFE']。

### E6_CONTINUATION

| Metric | B0 same entered pairs / full base as noted | Event |
| --- | --- | --- |
| Opportunity n | 1760 | 1760 |
| Reference ENTER (not real fills) | 1280 | 233 |
| Common complete | 633 | 633 |
| Complete ENTER | 633 | 148 |
| Entry coverage % | 100 | 23.3807 |
| Delay mean min | 0 | 20.4506 |
| Delay median min | 0 | 20.0000 |
| Paired mean Entry price | 1493.6216 | 1511.3615 |
| Mean price improvement pp | 0 | -1.5136 |
| Strict30 MAE mean | -1.5648 | -1.9041 |
| Strict30 MAE median | -0.9723 | -1.3393 |
| Strict30 MAE p10 | -3.6894 | -4.2672 |
| Strict30 MAE p05 | -5.0409 | -5.6053 |
| Strict30 worst MAE | -9.5149 | -13.0594 |
| Common remaining MFE mean | 3.6735 | 1.7443 |
| +1 preservation % | 100 | 17.6617 |
| +2 preservation % | 100 | 16.5354 |
| +3 preservation % | 100 | 18.5430 |
| +5 preservation % | 100 | 16.6667 |
| IMMEDIATE_WINNER entered & remaining+3 % | 100 | 10.0000 |
| FAST_WINNER entered & remaining+3 % | 100 | 15.3846 |
| PULLBACK_WINNER entered & remaining+3 % | 100 | 19.4175 |

| Path class | all n | complete n | ENTER complete | waited emitted | NO_EVENT | EXPIRED | UNKNOWN | missed +3 | missed +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHOP_THEN_WINNER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CONTINUED_FAILURE | 146 | 146 | 18 | 146 | 128 | 0 | 0 | 0 | 0 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 12 | 8 | 12 | 4 | 0 | 0 | 5 | 4 |
| IMMEDIATE_WINNER | 30 | 30 | 10 | 30 | 20 | 0 | 0 | 27 | 12 |
| INCONCLUSIVE | 1145 | 18 | 11 | 665 | 131 | 152 | 766 | 13 | 6 |
| OPPORTUNITY_EXPIRED | 336 | 336 | 67 | 336 | 269 | 0 | 0 | 0 | 0 |
| PULLBACK_THEN_WINNER | 91 | 91 | 34 | 91 | 57 | 0 | 0 | 78 | 28 |

| Pullback class | complete n | ENTER | price improvement pp | strict30 median improvement pp | strict30 p05 improvement pp | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- |
| PULLBACK_THEN_WINNER | 91 | 34 | -2.5598 | -0.1520 | -3.5327 | 0.4972 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 8 | -0.6655 | 3.4140 | 2.5493 | 0.8698 |

| Cohort | PB complete | PB ENTER | PB occurrence % | failure occurrence % | PB price pp | PB MAE median improvement pp | PB MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 25 | 10 | 40.0000 | 10.8108 | -1.3478 | -0.1003 | 0.7172 |
| INITIAL_ENTRY_OPPORTUNITY | 78 | 32 | 41.0256 | 12.8440 | -2.4649 | -0.4060 | 0.5373 |

| TRAIN block | PB complete | Event n in PB | gap pp | PB price pp | PB MAE median improvement pp | block gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 32 | 13 | 35.7470 | -1.5641 | 0.7041 | False |
| 2 | 19 | 9 | 24.2915 | -3.6163 | -1.3501 | False |
| 3 | 18 | 6 | 29.6296 | -2.5829 | 0.2003 | False |
| 4 | 34 | 14 | 25.7919 | -1.7127 | -0.7584 | False |

| MAE tail | B0 all | B0 entered pairs | Event entered pairs | better Entry reduction | not-entered baseline tail |
| --- | --- | --- | --- | --- | --- |
| 3 | 189 | 33 | 38 | -5 | 156 |
| 5 | 76 | 13 | 14 | -1 | 63 |
| 10 | 8 | 1 | 2 | -1 | 7 |

RISK_REDUCTION_BY_BETTER_ENTRYは同一Opportunityのbaseline tail−Event tail。非Entry側の件数はSKIPとみなした場合の見かけの減少に相当し、採用済みSKIP policyとは呼ばない。

Delay bins: {'0': 0, '10': 0, '15': 99, '20': 51, '25': 46, '30': 37, '5': 0}。Outcomes: {'COUNTERFACTUAL_ENTER': 233, 'EXPIRED_BOUNDARY': 152, 'NO_EVENT': 609, 'UNKNOWN_EXECUTION': 16, 'UNKNOWN_PREFIX': 270, 'UNKNOWN_REFERENCE': 480}。

No-event winners (+1/+2/+3/+5): {'1': 288, '2': 171, '3': 88, '5': 24}。Winner before event: {'1': 97, '2': 59, '3': 42, '5': 15}。

Evaluator-only IMMEDIATE_ENTRY_REQUIRED tag: 20。これは実行時のGuardではない。

Concentration: {'maxPullbackSessionShare': 0.11904761904761904, 'maxPullbackSymbolShare': 0.047619047619047616, 'pullbackEnteredSymbolHHI': 0.031746031746031744, 'pullbackEnteredUniqueSymbols': 35, 'symbolHHI': 0.002721461776859504, 'top10': [['25860', 18], ['48830', 17], ['190A0', 15], ['21560', 15], ['38030', 15], ['65740', 15], ['33500', 14], ['56160', 14], ['37790', 13], ['246A0', 12]], 'top3Train': ['25860', '48830', '190A0'], 'uniqueSymbols': 742}。Top3 exclusion failed gates: ['preserve3EnteredPairs', 'preserve5EnteredPairs', 'priceMean', 'priceMedian', 'remainingMFE', 'strict30Median']。

### S1_P_S_R

| Metric | B0 same entered pairs / full base as noted | Event |
| --- | --- | --- |
| Opportunity n | 1760 | 1760 |
| Reference ENTER (not real fills) | 1280 | 196 |
| Common complete | 633 | 633 |
| Complete ENTER | 633 | 107 |
| Entry coverage % | 100 | 16.9036 |
| Delay mean min | 0 | 22.6786 |
| Delay median min | 0 | 20.0000 |
| Paired mean Entry price | 1455.3785 | 1459.4206 |
| Mean price improvement pp | 0 | -0.1982 |
| Strict30 MAE mean | -1.8957 | -1.5220 |
| Strict30 MAE median | -1.5625 | -1.2579 |
| Strict30 MAE p10 | -3.5910 | -3.2012 |
| Strict30 MAE p05 | -5.1700 | -4.0066 |
| Strict30 worst MAE | -8.0986 | -6.0827 |
| Common remaining MFE mean | 2.0656 | 1.5256 |
| +1 preservation % | 100 | 10.1990 |
| +2 preservation % | 100 | 11.0236 |
| +3 preservation % | 100 | 13.9073 |
| +5 preservation % | 100 | 6.6667 |
| IMMEDIATE_WINNER entered & remaining+3 % | 100 | 0.0000 |
| FAST_WINNER entered & remaining+3 % | 100 | 4.3956 |
| PULLBACK_WINNER entered & remaining+3 % | 100 | 20.3883 |

| Path class | all n | complete n | ENTER complete | waited emitted | NO_EVENT | EXPIRED | UNKNOWN | missed +3 | missed +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHOP_THEN_WINNER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CONTINUED_FAILURE | 146 | 146 | 16 | 146 | 130 | 0 | 0 | 0 | 0 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 12 | 9 | 12 | 3 | 0 | 0 | 3 | 1 |
| IMMEDIATE_WINNER | 30 | 30 | 0 | 30 | 30 | 0 | 0 | 30 | 13 |
| INCONCLUSIVE | 1145 | 18 | 1 | 665 | 128 | 158 | 769 | 18 | 9 |
| OPPORTUNITY_EXPIRED | 336 | 336 | 64 | 336 | 272 | 0 | 0 | 0 | 0 |
| PULLBACK_THEN_WINNER | 91 | 91 | 17 | 91 | 74 | 0 | 0 | 79 | 33 |

| Pullback class | complete n | ENTER | price improvement pp | strict30 median improvement pp | strict30 p05 improvement pp | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- |
| PULLBACK_THEN_WINNER | 91 | 17 | -0.7825 | 0.8534 | -2.0694 | 0.7815 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 9 | 0.3013 | 3.4180 | 3.7503 | 1.0452 |

| Cohort | PB complete | PB ENTER | PB occurrence % | failure occurrence % | PB price pp | PB MAE median improvement pp | PB MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 25 | 6 | 24.0000 | 8.1081 | 0.4715 | 1.4309 | 1.1202 |
| INITIAL_ENTRY_OPPORTUNITY | 78 | 20 | 25.6410 | 11.9266 | -0.6710 | 1.1665 | 0.8437 |

| TRAIN block | PB complete | Event n in PB | gap pp | PB price pp | PB MAE median improvement pp | block gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 32 | 11 | 19.7409 | -0.0015 | 1.1235 | False |
| 2 | 19 | 3 | 0.4049 | -3.1986 | 1.0582 | False |
| 3 | 18 | 2 | 3.7037 | -0.6884 | -1.2067 | False |
| 4 | 34 | 10 | 24.2836 | 0.0398 | 1.0023 | True |

| MAE tail | B0 all | B0 entered pairs | Event entered pairs | better Entry reduction | not-entered baseline tail |
| --- | --- | --- | --- | --- | --- |
| 3 | 189 | 27 | 17 | 10 | 162 |
| 5 | 76 | 10 | 2 | 8 | 66 |
| 10 | 8 | 0 | 0 | 0 | 8 |

RISK_REDUCTION_BY_BETTER_ENTRYは同一Opportunityのbaseline tail−Event tail。非Entry側の件数はSKIPとみなした場合の見かけの減少に相当し、採用済みSKIP policyとは呼ばない。

Delay bins: {'0': 0, '10': 0, '15': 41, '20': 59, '25': 46, '30': 50, '5': 0}。Outcomes: {'COUNTERFACTUAL_ENTER': 196, 'EXPIRED_BOUNDARY': 158, 'NO_EVENT': 637, 'UNKNOWN_EXECUTION': 10, 'UNKNOWN_PREFIX': 279, 'UNKNOWN_REFERENCE': 480}。

No-event winners (+1/+2/+3/+5): {'1': 337, '2': 215, '3': 124, '5': 49}。Winner before event: {'1': 44, '2': 12, '3': 4, '5': 2}。

Evaluator-only IMMEDIATE_ENTRY_REQUIRED tag: 30。これは実行時のGuardではない。

Concentration: {'maxPullbackSessionShare': 0.2692307692307692, 'maxPullbackSymbolShare': 0.11538461538461539, 'pullbackEnteredSymbolHHI': 0.062130177514792904, 'pullbackEnteredUniqueSymbols': 19, 'symbolHHI': 0.002721461776859504, 'top10': [['25860', 18], ['48830', 17], ['190A0', 15], ['21560', 15], ['38030', 15], ['65740', 15], ['33500', 14], ['56160', 14], ['37790', 13], ['246A0', 12]], 'top3Train': ['25860', '48830', '190A0'], 'uniqueSymbols': 742}。Top3 exclusion failed gates: ['pbCapture', 'preserve3EnteredPairs', 'preserve5EnteredPairs', 'priceMean', 'priceMedian', 'remainingMFE']。

### S2_P_F_R

| Metric | B0 same entered pairs / full base as noted | Event |
| --- | --- | --- |
| Opportunity n | 1760 | 1760 |
| Reference ENTER (not real fills) | 1280 | 102 |
| Common complete | 633 | 633 |
| Complete ENTER | 633 | 68 |
| Entry coverage % | 100 | 10.7425 |
| Delay mean min | 0 | 22.5490 |
| Delay median min | 0 | 20.0000 |
| Paired mean Entry price | 1351.3971 | 1351.3529 |
| Mean price improvement pp | 0 | 0.0223 |
| Strict30 MAE mean | -2.5216 | -2.0218 |
| Strict30 MAE median | -1.9210 | -1.5696 |
| Strict30 MAE p10 | -4.2211 | -4.2736 |
| Strict30 MAE p05 | -6.7653 | -5.5489 |
| Strict30 worst MAE | -16.6134 | -12.1628 |
| Common remaining MFE mean | 2.1389 | 1.5590 |
| +1 preservation % | 100 | 7.2139 |
| +2 preservation % | 100 | 6.2992 |
| +3 preservation % | 100 | 4.6358 |
| +5 preservation % | 100 | 1.6667 |
| IMMEDIATE_WINNER entered & remaining+3 % | 100 | 0.0000 |
| FAST_WINNER entered & remaining+3 % | 100 | 0.0000 |
| PULLBACK_WINNER entered & remaining+3 % | 100 | 6.7961 |

| Path class | all n | complete n | ENTER complete | waited emitted | NO_EVENT | EXPIRED | UNKNOWN | missed +3 | missed +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHOP_THEN_WINNER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CONTINUED_FAILURE | 146 | 146 | 17 | 146 | 129 | 0 | 0 | 0 | 0 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 12 | 3 | 12 | 9 | 0 | 0 | 10 | 4 |
| IMMEDIATE_WINNER | 30 | 30 | 0 | 30 | 30 | 0 | 0 | 30 | 13 |
| INCONCLUSIVE | 1145 | 18 | 1 | 665 | 156 | 181 | 773 | 18 | 9 |
| OPPORTUNITY_EXPIRED | 336 | 336 | 34 | 336 | 302 | 0 | 0 | 0 | 0 |
| PULLBACK_THEN_WINNER | 91 | 91 | 13 | 91 | 78 | 0 | 0 | 86 | 33 |

| Pullback class | complete n | ENTER | price improvement pp | strict30 median improvement pp | strict30 p05 improvement pp | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- |
| PULLBACK_THEN_WINNER | 91 | 13 | -1.7679 | 0.0416 | -2.9372 | 0.5535 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 3 | -1.4974 | 4.0852 | 5.0695 | 0.8276 |

| Cohort | PB complete | PB ENTER | PB occurrence % | failure occurrence % | PB price pp | PB MAE median improvement pp | PB MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 25 | 5 | 20.0000 | 8.1081 | -2.5742 | -0.6486 | 0.5075 |
| INITIAL_ENTRY_OPPORTUNITY | 78 | 11 | 14.1026 | 12.8440 | -1.3276 | 0.4803 | 0.7057 |

| TRAIN block | PB complete | Event n in PB | gap pp | PB price pp | PB MAE median improvement pp | block gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 32 | 5 | 0.9909 | -0.0301 | 1.1644 | False |
| 2 | 19 | 5 | 16.0594 | -3.8374 | -2.7320 | False |
| 3 | 18 | 1 | -9.2593 | -0.3472 | 0.8130 | False |
| 4 | 34 | 5 | 7.0136 | -1.5580 | -0.6486 | False |

| MAE tail | B0 all | B0 entered pairs | Event entered pairs | better Entry reduction | not-entered baseline tail |
| --- | --- | --- | --- | --- | --- |
| 3 | 189 | 23 | 18 | 5 | 166 |
| 5 | 76 | 11 | 5 | 6 | 65 |
| 10 | 8 | 2 | 1 | 1 | 6 |

RISK_REDUCTION_BY_BETTER_ENTRYは同一Opportunityのbaseline tail−Event tail。非Entry側の件数はSKIPとみなした場合の見かけの減少に相当し、採用済みSKIP policyとは呼ばない。

Delay bins: {'0': 0, '10': 0, '15': 21, '20': 34, '25': 21, '30': 26, '5': 0}。Outcomes: {'COUNTERFACTUAL_ENTER': 102, 'EXPIRED_BOUNDARY': 181, 'NO_EVENT': 704, 'UNKNOWN_EXECUTION': 6, 'UNKNOWN_PREFIX': 287, 'UNKNOWN_REFERENCE': 480}。

No-event winners (+1/+2/+3/+5): {'1': 362, '2': 228, '3': 134, '5': 54}。Winner before event: {'1': 29, '2': 11, '3': 5, '5': 1}。

Evaluator-only IMMEDIATE_ENTRY_REQUIRED tag: 30。これは実行時のGuardではない。

Concentration: {'maxPullbackSessionShare': 0.1875, 'maxPullbackSymbolShare': 0.125, 'pullbackEnteredSymbolHHI': 0.0859375, 'pullbackEnteredUniqueSymbols': 13, 'symbolHHI': 0.002721461776859504, 'top10': [['25860', 18], ['48830', 17], ['190A0', 15], ['21560', 15], ['38030', 15], ['65740', 15], ['33500', 14], ['56160', 14], ['37790', 13], ['246A0', 12]], 'top3Train': ['25860', '48830', '190A0'], 'uniqueSymbols': 742}。Top3 exclusion failed gates: ['failureSeparation', 'pbCapture', 'preserve3EnteredPairs', 'preserve5EnteredPairs', 'priceMean', 'priceMedian', 'remainingMFE']。

### S3_P_S_M

| Metric | B0 same entered pairs / full base as noted | Event |
| --- | --- | --- |
| Opportunity n | 1760 | 1760 |
| Reference ENTER (not real fills) | 1280 | 209 |
| Common complete | 633 | 633 |
| Complete ENTER | 633 | 136 |
| Entry coverage % | 100 | 21.4850 |
| Delay mean min | 0 | 24.9282 |
| Delay median min | 0 | 25.0000 |
| Paired mean Entry price | 1106.3971 | 1104.1140 |
| Mean price improvement pp | 0 | 0.4399 |
| Strict30 MAE mean | -2.0354 | -1.5784 |
| Strict30 MAE median | -1.8465 | -1.1382 |
| Strict30 MAE p10 | -3.5023 | -3.4532 |
| Strict30 MAE p05 | -4.3185 | -4.2390 |
| Strict30 worst MAE | -7.6433 | -10.7034 |
| Common remaining MFE mean | 1.4477 | 1.3208 |
| +1 preservation % | 100 | 10.6965 |
| +2 preservation % | 100 | 10.6299 |
| +3 preservation % | 100 | 9.2715 |
| +5 preservation % | 100 | 6.6667 |
| IMMEDIATE_WINNER entered & remaining+3 % | 100 | 0.0000 |
| FAST_WINNER entered & remaining+3 % | 100 | 3.2967 |
| PULLBACK_WINNER entered & remaining+3 % | 100 | 12.6214 |

| Path class | all n | complete n | ENTER complete | waited emitted | NO_EVENT | EXPIRED | UNKNOWN | missed +3 | missed +5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHOP_THEN_WINNER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CONTINUED_FAILURE | 146 | 146 | 37 | 146 | 109 | 0 | 0 | 0 | 0 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 12 | 5 | 12 | 7 | 0 | 0 | 8 | 2 |
| IMMEDIATE_WINNER | 30 | 30 | 0 | 30 | 30 | 0 | 0 | 30 | 13 |
| INCONCLUSIVE | 1145 | 18 | 1 | 665 | 130 | 166 | 775 | 17 | 9 |
| OPPORTUNITY_EXPIRED | 336 | 336 | 80 | 336 | 256 | 0 | 0 | 0 | 0 |
| PULLBACK_THEN_WINNER | 91 | 91 | 13 | 91 | 78 | 0 | 0 | 82 | 32 |

| Pullback class | complete n | ENTER | price improvement pp | strict30 median improvement pp | strict30 p05 improvement pp | MFE ratio |
| --- | --- | --- | --- | --- | --- | --- |
| PULLBACK_THEN_WINNER | 91 | 13 | -0.3325 | 0.7751 | -1.0755 | 0.9148 |
| DEEP_PULLBACK_THEN_WINNER | 12 | 5 | 0.3891 | 2.7618 | 2.9180 | 1.0772 |

| Cohort | PB complete | PB ENTER | PB occurrence % | failure occurrence % | PB price pp | PB MAE median improvement pp | PB MFE ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DIP_REPRICE_OPPORTUNITY | 25 | 3 | 12.0000 | 18.9189 | 0.7161 | 1.2728 | 1.1639 |
| INITIAL_ENTRY_OPPORTUNITY | 78 | 15 | 19.2308 | 27.5229 | -0.3017 | 1.4571 | 0.9312 |

| TRAIN block | PB complete | Event n in PB | gap pp | PB price pp | PB MAE median improvement pp | block gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 32 | 10 | -2.8963 | 0.2628 | 0.9124 | False |
| 2 | 19 | 1 | -20.3779 | -1.1364 | 1.7109 | False |
| 3 | 18 | 2 | -7.4074 | -0.8281 | -1.1572 | False |
| 4 | 34 | 5 | -5.8069 | -0.4425 | 1.4571 | False |

| MAE tail | B0 all | B0 entered pairs | Event entered pairs | better Entry reduction | not-entered baseline tail |
| --- | --- | --- | --- | --- | --- |
| 3 | 189 | 47 | 21 | 26 | 142 |
| 5 | 76 | 12 | 7 | 5 | 64 |
| 10 | 8 | 1 | 1 | 0 | 7 |

RISK_REDUCTION_BY_BETTER_ENTRYは同一Opportunityのbaseline tail−Event tail。非Entry側の件数はSKIPとみなした場合の見かけの減少に相当し、採用済みSKIP policyとは呼ばない。

Delay bins: {'0': 0, '10': 0, '15': 11, '20': 57, '25': 65, '30': 76, '5': 0}。Outcomes: {'COUNTERFACTUAL_ENTER': 209, 'EXPIRED_BOUNDARY': 166, 'NO_EVENT': 610, 'UNKNOWN_EXECUTION': 9, 'UNKNOWN_PREFIX': 286, 'UNKNOWN_REFERENCE': 480}。

No-event winners (+1/+2/+3/+5): {'1': 332, '2': 216, '3': 132, '5': 54}。Winner before event: {'1': 47, '2': 9, '3': 1, '5': 0}。

Evaluator-only IMMEDIATE_ENTRY_REQUIRED tag: 30。これは実行時のGuardではない。

Concentration: {'maxPullbackSessionShare': 0.2777777777777778, 'maxPullbackSymbolShare': 0.1111111111111111, 'pullbackEnteredSymbolHHI': 0.07407407407407407, 'pullbackEnteredUniqueSymbols': 15, 'symbolHHI': 0.002721461776859504, 'top10': [['25860', 18], ['48830', 17], ['190A0', 15], ['21560', 15], ['38030', 15], ['65740', 15], ['33500', 14], ['56160', 14], ['37790', 13], ['246A0', 12]], 'top3Train': ['25860', '48830', '190A0'], 'uniqueSymbols': 742}。Top3 exclusion failed gates: ['failureSeparation', 'pbCapture', 'preserve3EnteredPairs', 'preserve5EnteredPairs', 'priceMean', 'priceMedian']。

## Architecture / Validation / economics / DEV TEST

KEEP mechanics: []。Selected mechanic: None。

KEEPがなければArchitecture/modelを作らずLIMIT。Validation・DEV TEST・Candidate A economic比較はいずれも未実行。未実行のmean/PF/p05/Win/HOLDを0やPASSとして表記しない。

## Integrity / limitations / STOP

Independent predicate/sequence implementation matched 1760 TRAIN episodes ×9 families. Original source pins 25 verified. Model fits 0。

StateとEventはPIT completed prefixのみ。Event後のnext OPENを実行参照とし、signal LOWやoracle bottomで約定しない。future MFE/MAE・path classは別Evaluator。same-bar HIGH/LOW順序UNKNOWN、missing/boundaryはfail-closed。terminal後resurrectionなし。

INITIAL/DIP・breadth1..5・朝/午後・TRAIN四分割・symbol HHI・top3除外・Event時点volatility別集計を保存。個別ルールやblacklistへの転用なし。

どのPIT情報が不足しているか、5m粒度そのものが限界か、出来高/板/市場contextを加えれば解決するかは今回比較していない。動的contextがUNAVAILABLEである事実と、その追加効果が未検証であることを分ける。新データ取得やCapital/EXITへの移行の優劣も本研究からは判定しない。

Exact HEAD・tests・regression・CI receiptは同一HEADのGitHub Actions artifactに保存。CI成功はEvent/Entry性能PASSを意味しない。Fresh/OOS・Capital/Portfolio・EXIT変更・main merge・実取引には進まない。全9 Safety=false。

**COMPREHENSIVE_LONG_ENTRY_V3_DEVELOPMENT_LIMIT_REACHED。Candidate Freezeなし。既存Frozen Opportunity Generator維持。Evidence固定してSTOP。**
