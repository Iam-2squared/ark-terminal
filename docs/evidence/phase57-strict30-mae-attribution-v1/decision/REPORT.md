# Phase57 — Strict 30m MAE Tail Attribution Diagnostic

Date: 2026-09-18 JST。Historical Development / outcome-exposed。診断のみ。

**最終Attribution Verdict: INCONCLUSIVE**

事実としてRecoveryとFailureは混在する。特にFixed12まで観測できたdeep群はMIXED判定。ただし測定前に固定した主判定はstrict30であり、その判定規則ではINCONCLUSIVE。結果を見て主horizonや判定条件を変更しない。Entry・Selector・EXITのどれが主原因かの因果断定はできない。

## 1. 数値の出所を訂正

指定のmedian −1.53% / p05 −10.26% / worst −35.29%は、旧MSH Entry v1の277 ENTER中strict30を観測できた181件の値。現行Frozen NEW EntryのINITIAL/DIPとは別母集団・別参照価格。旧181件を正確に再現したうえで、現行3,284 opportunityを独立集計した。

| Panel | 全opportunity/ENTER | strict30 n | MAE median % | p05 % | worst % |
| --- | --- | --- | --- | --- | --- |
| CURRENT_DIP | 541 | 394 | -1.3004 | -5.4458 | -8.6528 |
| CURRENT_INITIAL | 2743 | 1303 | -1.3410 | -6.0611 | -35.2941 |
| CURRENT_OVERALL | 3284 | 1697 | -1.3158 | -5.7410 | -35.2941 |
| LEGACY_ENTER | 277 | 181 | -1.5337 | -10.2564 | -35.2941 |

開始GitHub HEAD `a6824fb56e688355235af5fade91472a2eb157a0`。測定前protocol commit `61bb2b61b7d4ed07ac2df75e9fc7e6ab56f9c533`。PR #587 Draft / unmerged。

Source identity: {"currentAnchorSHA256": "985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121", "legacyEnterSHA256": "72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236", "newEntryFreezeCommit": "6fabde7dfe208e19d5611e0a290b4df6724e562e", "quotedMaePopulation": "LEGACY_MSH_V1_277_ENTER_STRICT181", "selectorFreezeCommit": "565d74b3dea823581fdb32380113aac5913a248d", "selectorPayloadSHA": "3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59"}

76 Development sessions / 2024-09-17〜2025-01-09。CURRENT overallはopportunity加重。INITIALとDIPは同じanchorに属する場合があり、独立trade数・Portfolio収益ではない。

旧181と現行1,697の分布差をEntry改善効果とは呼ばない。元母集団、reference、coverageが違い、pairedな改善実験ではない。

## 2. Coverage / outcome semantics

CURRENT_DIP: `{"COMPLETE": 394, "LUNCH_OR_SESSION_BOUNDARY": 68, "MISSING_BAR": 47, "SESSION_END_OR_SHORT_PATH": 32}`

CURRENT_INITIAL: `{"COMPLETE": 1303, "EXPIRED_BOUNDARY": 353, "MISSING_BAR": 604, "UNKNOWN_REFERENCE_OPEN": 483}`

CURRENT_OVERALL: `{"COMPLETE": 1697, "EXPIRED_BOUNDARY": 353, "LUNCH_OR_SESSION_BOUNDARY": 68, "MISSING_BAR": 651, "SESSION_END_OR_SHORT_PATH": 32, "UNKNOWN_REFERENCE_OPEN": 483}`

LEGACY_ENTER: `{"COMPLETE": 181, "FROZEN_DECISION_CLOSE_REFERENCE": 20, "LUNCH_OR_SESSION_BOUNDARY": 25, "MISSING_BAR": 51}`

旧LEGACYのFROZEN_DECISION_CLOSE_REFERENCE 20件は保存future配列が空のsession-end群。旧coverageの51 provider gap / 25 lunch / 20 session endを保持。現行INITIALには保存Entry側のEXPIRED_BOUNDARYもある。unknownを損失ゼロ・安全・失敗にしない。

strict30=6本の連続5m完成足、30時計分、昼休み跨ぎなし。元minute観測が疎な足を事後除外せず、full-minute感度を別記する。Fixed12は保存済みcalendar capで昼休みを跨ぐことがある。session結果は全expected regular barが揃った場合のみ。最終auction補間なし。

Recoveryは将来HIGHのopportunity labelであり約定・実現利益ではない。先に上がって後に暴落した例を回復winnerへ数えない。HIGH/LOW同一足順序はUNKNOWN_INTRABAR_ORDER。終値はその足のLOWより後だが、保守的later-CLOSE reclaimとは別項目。

## 3. Deep tail分類とhorizon差

最初のLOW<=−dをstrict30内で固定し、その後の各horizonを追跡。RECOVERY_WINNER=後続足で+3到達。RECOVERY_BUT_NO_MAJOR_WIN=明確なCLOSE reclaimのみ。CONTINUED_FAILURE=回復なし、後続足あり、terminal<=−d。その他・順序不明はINCONCLUSIVE。Winner後に再度損失となる例はrecoveryとして残し、givebackとして別計数する。

| Panel | Tail | n | horizon | 完全観測n | Recovery winner | Reclaim only | Continued failure | Inconclusive（欠測含む） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CURRENT_DIP | <=-10 | 0 | FIXED12_WINDOW | 0 | 0 | 0 | 0 | 0 |
| CURRENT_DIP | <=-10 | 0 | SESSION | 0 | 0 | 0 | 0 | 0 |
| CURRENT_DIP | <=-10 | 0 | STRICT30 | 0 | 0 | 0 | 0 | 0 |
| CURRENT_DIP | <=-3 | 71 | FIXED12_WINDOW | 67 | 9 | 18 | 30 | 14 |
| CURRENT_DIP | <=-3 | 71 | SESSION | 27 | 11 | 6 | 10 | 44 |
| CURRENT_DIP | <=-3 | 71 | STRICT30 | 71 | 3 | 14 | 23 | 31 |
| CURRENT_DIP | <=-5 | 25 | FIXED12_WINDOW | 23 | 3 | 3 | 9 | 10 |
| CURRENT_DIP | <=-5 | 25 | SESSION | 10 | 5 | 1 | 4 | 15 |
| CURRENT_DIP | <=-5 | 25 | STRICT30 | 25 | 0 | 2 | 6 | 17 |
| CURRENT_INITIAL | <=-10 | 25 | FIXED12_WINDOW | 22 | 3 | 9 | 4 | 9 |
| CURRENT_INITIAL | <=-10 | 25 | SESSION | 4 | 1 | 2 | 0 | 22 |
| CURRENT_INITIAL | <=-10 | 25 | STRICT30 | 25 | 1 | 12 | 6 | 6 |
| CURRENT_INITIAL | <=-3 | 277 | FIXED12_WINDOW | 243 | 31 | 61 | 98 | 87 |
| CURRENT_INITIAL | <=-3 | 277 | SESSION | 70 | 15 | 17 | 32 | 213 |
| CURRENT_INITIAL | <=-3 | 277 | STRICT30 | 277 | 19 | 75 | 93 | 90 |
| CURRENT_INITIAL | <=-5 | 107 | FIXED12_WINDOW | 94 | 12 | 17 | 39 | 39 |
| CURRENT_INITIAL | <=-5 | 107 | SESSION | 25 | 5 | 4 | 11 | 87 |
| CURRENT_INITIAL | <=-5 | 107 | STRICT30 | 107 | 5 | 26 | 33 | 43 |
| CURRENT_OVERALL | <=-10 | 25 | FIXED12_WINDOW | 22 | 3 | 9 | 4 | 9 |
| CURRENT_OVERALL | <=-10 | 25 | SESSION | 4 | 1 | 2 | 0 | 22 |
| CURRENT_OVERALL | <=-10 | 25 | STRICT30 | 25 | 1 | 12 | 6 | 6 |
| CURRENT_OVERALL | <=-3 | 348 | FIXED12_WINDOW | 310 | 40 | 79 | 128 | 101 |
| CURRENT_OVERALL | <=-3 | 348 | SESSION | 97 | 26 | 23 | 42 | 257 |
| CURRENT_OVERALL | <=-3 | 348 | STRICT30 | 348 | 22 | 89 | 116 | 121 |
| CURRENT_OVERALL | <=-5 | 132 | FIXED12_WINDOW | 117 | 15 | 20 | 48 | 49 |
| CURRENT_OVERALL | <=-5 | 132 | SESSION | 35 | 10 | 5 | 15 | 102 |
| CURRENT_OVERALL | <=-5 | 132 | STRICT30 | 132 | 5 | 28 | 39 | 60 |
| LEGACY_ENTER | <=-10 | 10 | FIXED12_WINDOW | 10 | 2 | 1 | 4 | 3 |
| LEGACY_ENTER | <=-10 | 10 | SESSION | 1 | 0 | 0 | 0 | 10 |
| LEGACY_ENTER | <=-10 | 10 | STRICT30 | 10 | 1 | 1 | 2 | 6 |
| LEGACY_ENTER | <=-3 | 50 | FIXED12_WINDOW | 46 | 10 | 9 | 22 | 9 |
| LEGACY_ENTER | <=-3 | 50 | SESSION | 13 | 3 | 4 | 6 | 37 |
| LEGACY_ENTER | <=-3 | 50 | STRICT30 | 50 | 8 | 10 | 20 | 12 |
| LEGACY_ENTER | <=-5 | 24 | FIXED12_WINDOW | 23 | 5 | 1 | 13 | 5 |
| LEGACY_ENTER | <=-5 | 24 | SESSION | 4 | 1 | 0 | 2 | 21 |
| LEGACY_ENTER | <=-5 | 24 | STRICT30 | 24 | 3 | 3 | 10 | 8 |

主判定：−3%以下348件のstrict30分類は{'CONTINUED_FAILURE': 116, 'INCONCLUSIVE': 121, 'RECOVERY_BUT_NO_MAJOR_WIN': 89, 'RECOVERY_WINNER': 22}。INCONCLUSIVE 121/348=34.77%で、事前規則の1/3上限を超える。最終判定はINCONCLUSIVE。

Fixed12完全観測310件では{'CONTINUED_FAILURE': 128, 'INCONCLUSIVE': 63, 'RECOVERY_BUT_NO_MAJOR_WIN': 79, 'RECOVERY_WINNER': 40}。DEEP_MAE_MIXED_RECOVERY_AND_FAILURE。残り38件を失敗扱いしない。この混在はINITIAL/DIP双方、4時系列block、頻出3銘柄除外後にも観測される。

INCONCLUSIVEの内訳（追加の説明であり定義変更なし）：{"CURRENT": {"PARTIAL_RECOVERY_STILL_NEGATIVE_ABOVE_DEEP_THRESHOLD": 89, "LAST_BAR_BREACH_NO_LATER_OBSERVATION": 31, "TRIGGER_HIGH_LOW_ORDER_UNKNOWN": 1}, "LEGACY": {"PARTIAL_RECOVERY_STILL_NEGATIVE_ABOVE_DEEP_THRESHOLD": 8, "LAST_BAR_BREACH_NO_LATER_OBSERVATION": 3, "TRIGGER_HIGH_LOW_ORDER_UNKNOWN": 1}}

## 4. Deep tailの回復・EXIT勝率

下表は全deep nに対する「確認できた回復」の件数/率。最後の足で初めて逆行した等のunknownを成功にも失敗にも確定しない。観測可能分母での率とunknown数はsummary.jsonに別保存。EXIT Winは両policyを観測できたpaired分母。

| Panel | tail / n | horizon | 後+3 / 全deep | 後+5 / 全deep | later reclaim / 全deep | Fixed12 Win | A Win |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CURRENT_DIP | <=-10 / 0 | STRICT30 | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) |
| CURRENT_DIP | <=-10 / 0 | FIXED12_WINDOW | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) |
| CURRENT_DIP | <=-3 / 71 | STRICT30 | 3/71 (4.23%) | 1/71 (1.41%) | 17/71 (23.94%) | 14/67 (20.90%) | 14/67 (20.90%) |
| CURRENT_DIP | <=-3 / 71 | FIXED12_WINDOW | 9/71 (12.68%) | 4/71 (5.63%) | 27/71 (38.03%) | 14/67 (20.90%) | 14/67 (20.90%) |
| CURRENT_DIP | <=-5 / 25 | STRICT30 | 0/25 (0.00%) | 0/25 (0.00%) | 2/25 (8.00%) | 4/23 (17.39%) | 4/23 (17.39%) |
| CURRENT_DIP | <=-5 / 25 | FIXED12_WINDOW | 3/25 (12.00%) | 1/25 (4.00%) | 6/25 (24.00%) | 4/23 (17.39%) | 4/23 (17.39%) |
| CURRENT_INITIAL | <=-10 / 25 | STRICT30 | 1/25 (4.00%) | 1/25 (4.00%) | 13/25 (52.00%) | 3/22 (13.64%) | 2/22 (9.09%) |
| CURRENT_INITIAL | <=-10 / 25 | FIXED12_WINDOW | 3/25 (12.00%) | 3/25 (12.00%) | 12/25 (48.00%) | 3/22 (13.64%) | 2/22 (9.09%) |
| CURRENT_INITIAL | <=-3 / 277 | STRICT30 | 19/277 (6.86%) | 7/277 (2.53%) | 92/277 (33.21%) | 27/243 (11.11%) | 23/243 (9.47%) |
| CURRENT_INITIAL | <=-3 / 277 | FIXED12_WINDOW | 31/277 (11.19%) | 14/277 (5.05%) | 91/277 (32.85%) | 27/243 (11.11%) | 23/243 (9.47%) |
| CURRENT_INITIAL | <=-5 / 107 | STRICT30 | 5/107 (4.67%) | 5/107 (4.67%) | 30/107 (28.04%) | 10/94 (10.64%) | 10/94 (10.64%) |
| CURRENT_INITIAL | <=-5 / 107 | FIXED12_WINDOW | 12/107 (11.21%) | 8/107 (7.48%) | 28/107 (26.17%) | 10/94 (10.64%) | 10/94 (10.64%) |
| CURRENT_OVERALL | <=-10 / 25 | STRICT30 | 1/25 (4.00%) | 1/25 (4.00%) | 13/25 (52.00%) | 3/22 (13.64%) | 2/22 (9.09%) |
| CURRENT_OVERALL | <=-10 / 25 | FIXED12_WINDOW | 3/25 (12.00%) | 3/25 (12.00%) | 12/25 (48.00%) | 3/22 (13.64%) | 2/22 (9.09%) |
| CURRENT_OVERALL | <=-3 / 348 | STRICT30 | 22/348 (6.32%) | 8/348 (2.30%) | 109/348 (31.32%) | 41/310 (13.23%) | 37/310 (11.94%) |
| CURRENT_OVERALL | <=-3 / 348 | FIXED12_WINDOW | 40/348 (11.49%) | 18/348 (5.17%) | 118/348 (33.91%) | 41/310 (13.23%) | 37/310 (11.94%) |
| CURRENT_OVERALL | <=-5 / 132 | STRICT30 | 5/132 (3.79%) | 5/132 (3.79%) | 32/132 (24.24%) | 14/117 (11.97%) | 14/117 (11.97%) |
| CURRENT_OVERALL | <=-5 / 132 | FIXED12_WINDOW | 15/132 (11.36%) | 9/132 (6.82%) | 34/132 (25.76%) | 14/117 (11.97%) | 14/117 (11.97%) |
| LEGACY_ENTER | <=-10 / 10 | STRICT30 | 1/10 (10.00%) | 1/10 (10.00%) | 2/10 (20.00%) | 2/10 (20.00%) | 0/10 (0.00%) |
| LEGACY_ENTER | <=-10 / 10 | FIXED12_WINDOW | 2/10 (20.00%) | 1/10 (10.00%) | 3/10 (30.00%) | 2/10 (20.00%) | 0/10 (0.00%) |
| LEGACY_ENTER | <=-3 / 50 | STRICT30 | 8/50 (16.00%) | 3/50 (6.00%) | 17/50 (34.00%) | 7/46 (15.22%) | 5/46 (10.87%) |
| LEGACY_ENTER | <=-3 / 50 | FIXED12_WINDOW | 10/50 (20.00%) | 5/50 (10.00%) | 18/50 (36.00%) | 7/46 (15.22%) | 5/46 (10.87%) |
| LEGACY_ENTER | <=-5 / 24 | STRICT30 | 3/24 (12.50%) | 2/24 (8.33%) | 6/24 (25.00%) | 3/23 (13.04%) | 2/23 (8.70%) |
| LEGACY_ENTER | <=-5 / 24 | FIXED12_WINDOW | 5/24 (20.83%) | 3/24 (12.50%) | 6/24 (25.00%) | 3/23 (13.04%) | 2/23 (8.70%) |

## 5. MAE bucket別 opportunity / recovery / failure / EXIT

bucketは分布記述のみ。stopやfilterへの採用0。境界はprotocolどおり固定し、累積<=−3/5/10とは分母が違う。

### CURRENT_DIP

| MAE bucket | n | strict比 | 全opportunity比 | any +1 | any +2 | any +3 | any +5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | 152 | 38.58% | 28.10% | 121/152 (79.61%) | 73/152 (48.03%) | 45/152 (29.61%) | 15/152 (9.87%) |
| (-2,-1] | 120 | 30.46% | 22.18% | 66/120 (55.00%) | 27/120 (22.50%) | 15/120 (12.50%) | 6/120 (5.00%) |
| (-3,-2] | 51 | 12.94% | 9.43% | 27/51 (52.94%) | 17/51 (33.33%) | 9/51 (17.65%) | 4/51 (7.84%) |
| (-5,-3] | 46 | 11.68% | 8.50% | 19/46 (41.30%) | 7/46 (15.22%) | 6/46 (13.04%) | 2/46 (4.35%) |
| (-10,-5] | 25 | 6.35% | 4.62% | 11/25 (44.00%) | 6/25 (24.00%) | 1/25 (4.00%) | 0/25 (0.00%) |
| <=-10 | 0 | 0.00% | 0.00% | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) |

次は最初のglobal30m MAEより後の別足での回復。any-timeの上昇機会とは区別。MAE=0はEntryを基準とする。

| MAE bucket | after MAE +1 | +2 | +3 | +5 | later CLOSE reclaim |
| --- | --- | --- | --- | --- | --- |
| (-1,0] | 110/146 (75.34%); unknown 6 | 67/146 (45.89%); unknown 6 | 44/146 (30.14%); unknown 6 | 15/146 (10.27%); unknown 6 | 138/146 (94.52%); unknown 6 |
| (-2,-1] | 37/99 (37.37%); unknown 21 | 20/99 (20.20%); unknown 21 | 14/99 (14.14%); unknown 21 | 6/99 (6.06%); unknown 21 | 68/99 (68.69%); unknown 21 |
| (-3,-2] | 14/40 (35.00%); unknown 11 | 12/40 (30.00%); unknown 11 | 8/40 (20.00%); unknown 11 | 4/40 (10.00%); unknown 11 | 17/40 (42.50%); unknown 11 |
| (-5,-3] | 9/35 (25.71%); unknown 11 | 4/35 (11.43%); unknown 11 | 3/35 (8.57%); unknown 11 | 1/35 (2.86%); unknown 11 | 14/35 (40.00%); unknown 11 |
| (-10,-5] | 2/16 (12.50%); unknown 9 | 0/16 (0.00%); unknown 9 | 0/16 (0.00%); unknown 9 | 0/16 (0.00%); unknown 9 | 2/16 (12.50%); unknown 9 |
| <=-10 | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) |

| MAE bucket | reclaim中央値 Entry分 | +3到達上限中央値 Entry分 | +5上限中央値 | positive CLOSE | 追加下落>=2% | >=5% | session更に悪化 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | 10.0000 | 20.0000 | 20.0000 | 134/146 (91.78%); unknown 6 | 3/146 (2.05%); unknown 6 | 0/146 (0.00%); unknown 6 | 81/97 (83.51%); unknown 55 |
| (-2,-1] | 20.0000 | 15.0000 | 20.0000 | 53/99 (53.54%); unknown 21 | 4/99 (4.04%); unknown 21 | 1/99 (1.01%); unknown 21 | 77/88 (87.50%); unknown 32 |
| (-3,-2] | 15.0000 | 15.0000 | 20.0000 | 16/40 (40.00%); unknown 11 | 5/40 (12.50%); unknown 11 | 0/40 (0.00%); unknown 11 | 35/40 (87.50%); unknown 11 |
| (-5,-3] | 20.0000 | 30.0000 | 30.0000 | 11/35 (31.43%); unknown 11 | 2/35 (5.71%); unknown 11 | 0/35 (0.00%); unknown 11 | 30/36 (83.33%); unknown 10 |
| (-10,-5] | 30.0000 | N/A | N/A | 2/16 (12.50%); unknown 9 | 3/16 (18.75%); unknown 9 | 0/16 (0.00%); unknown 9 | 13/18 (72.22%); unknown 7 |
| <=-10 | N/A | N/A | N/A | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) | 0/0 (N/A) |

追加下落はadverse足のcompleted CLOSEを基準にした後続LOW。Entry基準MAEや既存DIP106/21タグとは別。

| MAE bucket | MAE median | MFE median | after MAE MFE median | giveback median pp | terminal30 mean % | session terminal mean / n |
| --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | -0.4043 | 1.9835 | 1.8491 | 0.8658 | 1.7649 | 0.3058 / 39 |
| (-2,-1] | -1.3573 | 1.0906 | 0.6009 | 1.3051 | -0.0175 | -0.4666 / 36 |
| (-3,-2] | -2.4336 | 1.1111 | 0.0899 | 2.2508 | -0.6819 | -3.2726 / 19 |
| (-5,-3] | -3.6876 | 0.8152 | 0.0000 | 2.9293 | -1.6188 | -2.3452 / 17 |
| (-10,-5] | -6.3063 | 0.6033 | 0.0000 | 5.4054 | -4.5164 | -4.5680 / 10 |
| <=-10 | N/A | N/A | N/A | N/A | N/A | N/A / 0 |

| MAE bucket | policy | paired n | mean % | median % | PF | p05 % | Win |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | fixed12 | 112 | 1.1052 | 0.4304 | 3.8478 | -2.2085 | 69/112 (61.61%) |
| (-1,0] | candidateA | 112 | 1.1902 | 0.6822 | 4.5802 | -1.9416 | 73/112 (65.18%) |
| (-2,-1] | fixed12 | 96 | -0.1249 | -0.4322 | 0.8413 | -3.2089 | 32/96 (33.33%) |
| (-2,-1] | candidateA | 96 | -0.2180 | -0.2389 | 0.6953 | -2.9661 | 38/96 (39.58%) |
| (-3,-2] | fixed12 | 49 | -0.4405 | -1.1611 | 0.6681 | -3.7089 | 13/49 (26.53%) |
| (-3,-2] | candidateA | 49 | -0.4064 | -0.9493 | 0.6878 | -3.7089 | 13/49 (26.53%) |
| (-5,-3] | fixed12 | 44 | -1.9219 | -2.7750 | 0.2721 | -5.8279 | 10/44 (22.73%) |
| (-5,-3] | candidateA | 44 | -1.6058 | -1.4306 | 0.2603 | -5.3248 | 10/44 (22.73%) |
| (-10,-5] | fixed12 | 23 | -3.9923 | -4.6892 | 0.0915 | -7.7070 | 4/23 (17.39%) |
| (-10,-5] | candidateA | 23 | -3.7031 | -4.4699 | 0.0980 | -7.7070 | 4/23 (17.39%) |
| <=-10 | fixed12 | 0 | N/A | N/A | N/A | N/A | 0/0 (N/A) |
| <=-10 | candidateA | 0 | N/A | N/A | N/A | N/A | 0/0 (N/A) |

### CURRENT_INITIAL

| MAE bucket | n | strict比 | 全opportunity比 | any +1 | any +2 | any +3 | any +5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | 539 | 41.37% | 19.65% | 425/539 (78.85%) | 292/539 (54.17%) | 191/539 (35.44%) | 90/539 (16.70%) |
| (-2,-1] | 300 | 23.02% | 10.94% | 149/300 (49.67%) | 76/300 (25.33%) | 44/300 (14.67%) | 19/300 (6.33%) |
| (-3,-2] | 187 | 14.35% | 6.82% | 83/187 (44.39%) | 56/187 (29.95%) | 27/187 (14.44%) | 7/187 (3.74%) |
| (-5,-3] | 170 | 13.05% | 6.20% | 63/170 (37.06%) | 33/170 (19.41%) | 19/170 (11.18%) | 3/170 (1.76%) |
| (-10,-5] | 82 | 6.29% | 2.99% | 27/82 (32.93%) | 16/82 (19.51%) | 10/82 (12.20%) | 4/82 (4.88%) |
| <=-10 | 25 | 1.92% | 0.91% | 7/25 (28.00%) | 4/25 (16.00%) | 2/25 (8.00%) | 2/25 (8.00%) |

次は最初のglobal30m MAEより後の別足での回復。any-timeの上昇機会とは区別。MAE=0はEntryを基準とする。

| MAE bucket | after MAE +1 | +2 | +3 | +5 | later CLOSE reclaim |
| --- | --- | --- | --- | --- | --- |
| (-1,0] | 385/511 (75.34%); unknown 28 | 273/511 (53.42%); unknown 28 | 185/511 (36.20%); unknown 28 | 89/511 (17.42%); unknown 28 | 494/511 (96.67%); unknown 28 |
| (-2,-1] | 110/266 (41.35%); unknown 34 | 58/266 (21.80%); unknown 34 | 37/266 (13.91%); unknown 34 | 17/266 (6.39%); unknown 34 | 189/266 (71.05%); unknown 34 |
| (-3,-2] | 52/161 (32.30%); unknown 26 | 40/161 (24.84%); unknown 26 | 20/161 (12.42%); unknown 26 | 7/161 (4.35%); unknown 26 | 89/161 (55.28%); unknown 26 |
| (-5,-3] | 30/133 (22.56%); unknown 37 | 18/133 (13.53%); unknown 37 | 14/133 (10.53%); unknown 37 | 2/133 (1.50%); unknown 37 | 61/133 (45.86%); unknown 37 |
| (-10,-5] | 8/67 (11.94%); unknown 15 | 5/67 (7.46%); unknown 15 | 4/67 (5.97%); unknown 15 | 4/67 (5.97%); unknown 15 | 17/67 (25.37%); unknown 15 |
| <=-10 | 2/21 (9.52%); unknown 4 | 1/21 (4.76%); unknown 4 | 1/21 (4.76%); unknown 4 | 1/21 (4.76%); unknown 4 | 13/21 (61.90%); unknown 4 |

| MAE bucket | reclaim中央値 Entry分 | +3到達上限中央値 Entry分 | +5上限中央値 | positive CLOSE | 追加下落>=2% | >=5% | session更に悪化 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | 10.0000 | 10.0000 | 10.0000 | 462/511 (90.41%); unknown 28 | 15/511 (2.94%); unknown 28 | 1/511 (0.20%); unknown 28 | 270/341 (79.18%); unknown 198 |
| (-2,-1] | 15.0000 | 20.0000 | 20.0000 | 149/266 (56.02%); unknown 34 | 5/266 (1.88%); unknown 34 | 0/266 (0.00%); unknown 34 | 182/212 (85.85%); unknown 88 |
| (-3,-2] | 15.0000 | 25.0000 | 20.0000 | 62/161 (38.51%); unknown 26 | 15/161 (9.32%); unknown 26 | 0/161 (0.00%); unknown 26 | 107/133 (80.45%); unknown 54 |
| (-5,-3] | 20.0000 | 25.0000 | 17.5000 | 28/133 (21.05%); unknown 37 | 14/133 (10.53%); unknown 37 | 0/133 (0.00%); unknown 37 | 93/113 (82.30%); unknown 57 |
| (-10,-5] | 20.0000 | 17.5000 | 17.5000 | 7/67 (10.45%); unknown 15 | 12/67 (17.91%); unknown 15 | 5/67 (7.46%); unknown 15 | 42/51 (82.35%); unknown 31 |
| <=-10 | 15.0000 | 30.0000 | 30.0000 | 2/21 (9.52%); unknown 4 | 7/21 (33.33%); unknown 4 | 5/21 (23.81%); unknown 4 | 8/12 (66.67%); unknown 13 |

追加下落はadverse足のcompleted CLOSEを基準にした後続LOW。Entry基準MAEや既存DIP106/21タグとは別。

| MAE bucket | MAE median | MFE median | after MAE MFE median | giveback median pp | terminal30 mean % | session terminal mean / n |
| --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | -0.3077 | 2.2222 | 2.1739 | 0.9957 | 1.5717 | 1.0509 / 135 |
| (-2,-1] | -1.5040 | 0.9901 | 0.6423 | 1.1924 | 0.2857 | -1.3051 / 86 |
| (-3,-2] | -2.3908 | 0.9009 | 0.0000 | 1.7699 | -0.3466 | -1.6108 / 72 |
| (-5,-3] | -3.7736 | 0.5467 | 0.0000 | 2.7564 | -1.6005 | -3.4738 / 45 |
| (-10,-5] | -5.9579 | 0.3573 | 0.0000 | 5.0000 | -3.6473 | -5.8543 / 21 |
| <=-10 | -12.5000 | 0.0000 | 0.0000 | 7.3794 | -6.3180 | -2.3163 / 4 |

| MAE bucket | policy | paired n | mean % | median % | PF | p05 % | Win |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | fixed12 | 424 | 1.3998 | 0.6576 | 5.6091 | -2.0089 | 275/424 (64.86%) |
| (-1,0] | candidateA | 424 | 1.4750 | 0.6333 | 7.0688 | -1.4993 | 278/424 (65.57%) |
| (-2,-1] | fixed12 | 235 | -0.1287 | -0.4114 | 0.8731 | -3.3532 | 94/235 (40.00%) |
| (-2,-1] | candidateA | 235 | -0.0845 | -0.3574 | 0.9087 | -3.1133 | 97/235 (41.28%) |
| (-3,-2] | fixed12 | 170 | -0.8655 | -0.9119 | 0.4238 | -5.6563 | 46/170 (27.06%) |
| (-3,-2] | candidateA | 170 | -0.7595 | -0.7374 | 0.4180 | -4.9160 | 48/170 (28.24%) |
| (-5,-3] | fixed12 | 149 | -2.1549 | -2.0500 | 0.0940 | -6.4210 | 17/149 (11.41%) |
| (-5,-3] | candidateA | 149 | -2.2247 | -2.0065 | 0.0611 | -6.2268 | 13/149 (8.72%) |
| (-10,-5] | fixed12 | 72 | -4.2048 | -4.8440 | 0.1138 | -9.0392 | 7/72 (9.72%) |
| (-10,-5] | candidateA | 72 | -3.7814 | -4.3089 | 0.1274 | -9.0342 | 8/72 (11.11%) |
| <=-10 | fixed12 | 22 | -6.5689 | -5.9841 | 0.1207 | -19.7643 | 3/22 (13.64%) |
| <=-10 | candidateA | 22 | -7.0394 | -5.8742 | 0.0414 | -19.7643 | 2/22 (9.09%) |

### CURRENT_OVERALL

| MAE bucket | n | strict比 | 全opportunity比 | any +1 | any +2 | any +3 | any +5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | 691 | 40.72% | 21.04% | 546/691 (79.02%) | 365/691 (52.82%) | 236/691 (34.15%) | 105/691 (15.20%) |
| (-2,-1] | 420 | 24.75% | 12.79% | 215/420 (51.19%) | 103/420 (24.52%) | 59/420 (14.05%) | 25/420 (5.95%) |
| (-3,-2] | 238 | 14.02% | 7.25% | 110/238 (46.22%) | 73/238 (30.67%) | 36/238 (15.13%) | 11/238 (4.62%) |
| (-5,-3] | 216 | 12.73% | 6.58% | 82/216 (37.96%) | 40/216 (18.52%) | 25/216 (11.57%) | 5/216 (2.31%) |
| (-10,-5] | 107 | 6.31% | 3.26% | 38/107 (35.51%) | 22/107 (20.56%) | 11/107 (10.28%) | 4/107 (3.74%) |
| <=-10 | 25 | 1.47% | 0.76% | 7/25 (28.00%) | 4/25 (16.00%) | 2/25 (8.00%) | 2/25 (8.00%) |

次は最初のglobal30m MAEより後の別足での回復。any-timeの上昇機会とは区別。MAE=0はEntryを基準とする。

| MAE bucket | after MAE +1 | +2 | +3 | +5 | later CLOSE reclaim |
| --- | --- | --- | --- | --- | --- |
| (-1,0] | 495/657 (75.34%); unknown 34 | 340/657 (51.75%); unknown 34 | 229/657 (34.86%); unknown 34 | 104/657 (15.83%); unknown 34 | 632/657 (96.19%); unknown 34 |
| (-2,-1] | 147/365 (40.27%); unknown 55 | 78/365 (21.37%); unknown 55 | 51/365 (13.97%); unknown 55 | 23/365 (6.30%); unknown 55 | 257/365 (70.41%); unknown 55 |
| (-3,-2] | 66/201 (32.84%); unknown 37 | 52/201 (25.87%); unknown 37 | 28/201 (13.93%); unknown 37 | 11/201 (5.47%); unknown 37 | 106/201 (52.74%); unknown 37 |
| (-5,-3] | 39/168 (23.21%); unknown 48 | 22/168 (13.10%); unknown 48 | 17/168 (10.12%); unknown 48 | 3/168 (1.79%); unknown 48 | 75/168 (44.64%); unknown 48 |
| (-10,-5] | 10/83 (12.05%); unknown 24 | 5/83 (6.02%); unknown 24 | 4/83 (4.82%); unknown 24 | 4/83 (4.82%); unknown 24 | 19/83 (22.89%); unknown 24 |
| <=-10 | 2/21 (9.52%); unknown 4 | 1/21 (4.76%); unknown 4 | 1/21 (4.76%); unknown 4 | 1/21 (4.76%); unknown 4 | 13/21 (61.90%); unknown 4 |

| MAE bucket | reclaim中央値 Entry分 | +3到達上限中央値 Entry分 | +5上限中央値 | positive CLOSE | 追加下落>=2% | >=5% | session更に悪化 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | 10.0000 | 10.0000 | 10.0000 | 596/657 (90.72%); unknown 34 | 18/657 (2.74%); unknown 34 | 1/657 (0.15%); unknown 34 | 351/438 (80.14%); unknown 253 |
| (-2,-1] | 20.0000 | 20.0000 | 20.0000 | 202/365 (55.34%); unknown 55 | 9/365 (2.47%); unknown 55 | 1/365 (0.27%); unknown 55 | 259/300 (86.33%); unknown 120 |
| (-3,-2] | 15.0000 | 22.5000 | 20.0000 | 78/201 (38.81%); unknown 37 | 20/201 (9.95%); unknown 37 | 0/201 (0.00%); unknown 37 | 142/173 (82.08%); unknown 65 |
| (-5,-3] | 20.0000 | 25.0000 | 20.0000 | 39/168 (23.21%); unknown 48 | 16/168 (9.52%); unknown 48 | 0/168 (0.00%); unknown 48 | 123/149 (82.55%); unknown 67 |
| (-10,-5] | 20.0000 | 17.5000 | 17.5000 | 9/83 (10.84%); unknown 24 | 15/83 (18.07%); unknown 24 | 5/83 (6.02%); unknown 24 | 55/69 (79.71%); unknown 38 |
| <=-10 | 15.0000 | 30.0000 | 30.0000 | 2/21 (9.52%); unknown 4 | 7/21 (33.33%); unknown 4 | 5/21 (23.81%); unknown 4 | 8/12 (66.67%); unknown 13 |

追加下落はadverse足のcompleted CLOSEを基準にした後続LOW。Entry基準MAEや既存DIP106/21タグとは別。

| MAE bucket | MAE median | MFE median | after MAE MFE median | giveback median pp | terminal30 mean % | session terminal mean / n |
| --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | -0.3352 | 2.1531 | 2.1191 | 0.9760 | 1.6142 | 0.8839 / 174 |
| (-2,-1] | -1.4534 | 1.0226 | 0.6231 | 1.2305 | 0.1990 | -1.0577 / 122 |
| (-3,-2] | -2.3966 | 0.9390 | 0.0000 | 1.9218 | -0.4184 | -1.9577 / 91 |
| (-5,-3] | -3.7536 | 0.6588 | 0.0000 | 2.7873 | -1.6044 | -3.1644 / 62 |
| (-10,-5] | -6.1433 | 0.4405 | 0.0000 | 5.1546 | -3.8503 | -5.4393 / 31 |
| <=-10 | -12.5000 | 0.0000 | 0.0000 | 7.3794 | -6.3180 | -2.3163 / 4 |

| MAE bucket | policy | paired n | mean % | median % | PF | p05 % | Win |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | fixed12 | 536 | 1.3382 | 0.6078 | 5.1646 | -2.0642 | 344/536 (64.18%) |
| (-1,0] | candidateA | 536 | 1.4155 | 0.6348 | 6.4083 | -1.5799 | 351/536 (65.49%) |
| (-2,-1] | fixed12 | 331 | -0.1276 | -0.4176 | 0.8655 | -3.2665 | 126/331 (38.07%) |
| (-2,-1] | candidateA | 331 | -0.1232 | -0.3333 | 0.8575 | -3.1199 | 135/331 (40.79%) |
| (-3,-2] | fixed12 | 219 | -0.7704 | -0.9371 | 0.4734 | -5.2954 | 59/219 (26.94%) |
| (-3,-2] | candidateA | 219 | -0.6805 | -0.7484 | 0.4782 | -4.5874 | 61/219 (27.85%) |
| (-5,-3] | fixed12 | 193 | -2.1018 | -2.1333 | 0.1380 | -6.3806 | 27/193 (13.99%) |
| (-5,-3] | candidateA | 193 | -2.0836 | -1.9019 | 0.1036 | -6.0376 | 23/193 (11.92%) |
| (-10,-5] | fixed12 | 95 | -4.1533 | -4.8003 | 0.1087 | -8.8933 | 11/95 (11.58%) |
| (-10,-5] | candidateA | 95 | -3.7624 | -4.3743 | 0.1205 | -8.8870 | 12/95 (12.63%) |
| <=-10 | fixed12 | 22 | -6.5689 | -5.9841 | 0.1207 | -19.7643 | 3/22 (13.64%) |
| <=-10 | candidateA | 22 | -7.0394 | -5.8742 | 0.0414 | -19.7643 | 2/22 (9.09%) |

### LEGACY_ENTER

| MAE bucket | n | strict比 | 全opportunity比 | any +1 | any +2 | any +3 | any +5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | 76 | 41.99% | 27.44% | 74/76 (97.37%) | 68/76 (89.47%) | 56/76 (73.68%) | 41/76 (53.95%) |
| (-2,-1] | 31 | 17.13% | 11.19% | 27/31 (87.10%) | 23/31 (74.19%) | 14/31 (45.16%) | 7/31 (22.58%) |
| (-3,-2] | 24 | 13.26% | 8.66% | 20/24 (83.33%) | 17/24 (70.83%) | 10/24 (41.67%) | 4/24 (16.67%) |
| (-5,-3] | 26 | 14.36% | 9.39% | 19/26 (73.08%) | 13/26 (50.00%) | 7/26 (26.92%) | 1/26 (3.85%) |
| (-10,-5] | 14 | 7.73% | 5.05% | 10/14 (71.43%) | 7/14 (50.00%) | 5/14 (35.71%) | 1/14 (7.14%) |
| <=-10 | 10 | 5.52% | 3.61% | 6/10 (60.00%) | 4/10 (40.00%) | 3/10 (30.00%) | 2/10 (20.00%) |

次は最初のglobal30m MAEより後の別足での回復。any-timeの上昇機会とは区別。MAE=0はEntryを基準とする。

| MAE bucket | after MAE +1 | +2 | +3 | +5 | later CLOSE reclaim |
| --- | --- | --- | --- | --- | --- |
| (-1,0] | 73/75 (97.33%); unknown 1 | 65/75 (86.67%); unknown 1 | 55/75 (73.33%); unknown 1 | 41/75 (54.67%); unknown 1 | 75/75 (100.00%); unknown 1 |
| (-2,-1] | 18/26 (69.23%); unknown 5 | 16/26 (61.54%); unknown 5 | 11/26 (42.31%); unknown 5 | 5/26 (19.23%); unknown 5 | 22/26 (84.62%); unknown 5 |
| (-3,-2] | 14/23 (60.87%); unknown 1 | 11/23 (47.83%); unknown 1 | 8/23 (34.78%); unknown 1 | 4/23 (17.39%); unknown 1 | 18/23 (78.26%); unknown 1 |
| (-5,-3] | 7/22 (31.82%); unknown 4 | 5/22 (22.73%); unknown 4 | 4/22 (18.18%); unknown 4 | 1/22 (4.55%); unknown 4 | 11/22 (50.00%); unknown 4 |
| (-10,-5] | 3/12 (25.00%); unknown 2 | 2/12 (16.67%); unknown 2 | 2/12 (16.67%); unknown 2 | 1/12 (8.33%); unknown 2 | 4/12 (33.33%); unknown 2 |
| <=-10 | 1/7 (14.29%); unknown 3 | 1/7 (14.29%); unknown 3 | 1/7 (14.29%); unknown 3 | 1/7 (14.29%); unknown 3 | 2/7 (28.57%); unknown 3 |

| MAE bucket | reclaim中央値 Entry分 | +3到達上限中央値 Entry分 | +5上限中央値 | positive CLOSE | 追加下落>=2% | >=5% | session更に悪化 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | 5.0000 | 5.0000 | 5.0000 | 74/75 (98.67%); unknown 1 | 4/75 (5.33%); unknown 1 | 0/75 (0.00%); unknown 1 | 30/39 (76.92%); unknown 37 |
| (-2,-1] | 12.5000 | 15.0000 | 15.0000 | 20/26 (76.92%); unknown 5 | 1/26 (3.85%); unknown 5 | 0/26 (0.00%); unknown 5 | 20/21 (95.24%); unknown 10 |
| (-3,-2] | 15.0000 | 20.0000 | 17.5000 | 14/23 (60.87%); unknown 1 | 4/23 (17.39%); unknown 1 | 0/23 (0.00%); unknown 1 | 16/19 (84.21%); unknown 5 |
| (-5,-3] | 20.0000 | 22.5000 | 20.0000 | 8/22 (36.36%); unknown 4 | 4/22 (18.18%); unknown 4 | 0/22 (0.00%); unknown 4 | 17/19 (89.47%); unknown 7 |
| (-10,-5] | 15.0000 | 22.5000 | 15.0000 | 3/12 (25.00%); unknown 2 | 3/12 (25.00%); unknown 2 | 2/12 (16.67%); unknown 2 | 6/7 (85.71%); unknown 7 |
| <=-10 | 25.0000 | 30.0000 | 30.0000 | 1/7 (14.29%); unknown 3 | 3/7 (42.86%); unknown 3 | 1/7 (14.29%); unknown 3 | 7/7 (100.00%); unknown 3 |

追加下落はadverse足のcompleted CLOSEを基準にした後続LOW。Entry基準MAEや既存DIP106/21タグとは別。

| MAE bucket | MAE median | MFE median | after MAE MFE median | giveback median pp | terminal30 mean % | session terminal mean / n |
| --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | 0.0000 | 5.5442 | 5.5556 | 1.8347 | 3.8930 | 5.4306 / 12 |
| (-2,-1] | -1.5762 | 2.7073 | 2.5341 | 1.6260 | 1.4622 | -0.6064 / 6 |
| (-3,-2] | -2.5724 | 2.5992 | 1.3889 | 2.0254 | 0.8454 | -1.2375 / 6 |
| (-5,-3] | -3.7274 | 1.9808 | 0.0000 | 3.5773 | -1.0646 | -4.0179 / 9 |
| (-10,-5] | -5.8525 | 1.9763 | 0.0000 | 5.5556 | -2.7736 | -3.8947 / 3 |
| <=-10 | -12.0869 | 1.2428 | 0.0000 | 10.1881 | -7.2126 | -9.8160 / 1 |

| MAE bucket | policy | paired n | mean % | median % | PF | p05 % | Win |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (-1,0] | fixed12 | 65 | 3.1665 | 0.9381 | 34.6717 | -0.6932 | 42/65 (64.62%) |
| (-1,0] | candidateA | 65 | 4.0213 | 0.8988 | 40.3018 | -0.7327 | 43/65 (66.15%) |
| (-2,-1] | fixed12 | 26 | 1.0586 | 0.0046 | 1.7112 | -4.9491 | 13/26 (50.00%) |
| (-2,-1] | candidateA | 26 | 1.5168 | 0.0799 | 2.9777 | -3.3001 | 13/26 (50.00%) |
| (-3,-2] | fixed12 | 21 | 0.2135 | 0.2749 | 1.2024 | -2.6306 | 12/21 (57.14%) |
| (-3,-2] | candidateA | 21 | 0.3424 | 0.2749 | 1.5627 | -2.1777 | 11/21 (52.38%) |
| (-5,-3] | fixed12 | 23 | -2.3175 | -1.9554 | 0.2029 | -6.6660 | 4/23 (17.39%) |
| (-5,-3] | candidateA | 23 | -2.4664 | -1.9554 | 0.0577 | -6.5446 | 3/23 (13.04%) |
| (-10,-5] | fixed12 | 13 | -3.3865 | -4.8974 | 0.2588 | -8.0476 | 1/13 (7.69%) |
| (-10,-5] | candidateA | 13 | -2.3130 | -3.7085 | 0.3507 | -7.7887 | 2/13 (15.38%) |
| <=-10 | fixed12 | 10 | -9.3305 | -10.5135 | 0.1070 | -25.2265 | 2/10 (20.00%) |
| <=-10 | candidateA | 10 | -9.9893 | -8.6617 | 0.0000 | -25.2265 | 0/10 (0.00%) |

## 6. INITIAL / DIP比較とEXIT母集団

| Panel | tail3 n/strict | tail5 | tail10 | EXIT paired n | Fixed mean / PF | A mean / PF |
| --- | --- | --- | --- | --- | --- | --- |
| CURRENT_DIP | 71/394 (18.02%) | 25/394 (6.35%) | 0/394 (0.00%) | 324 | -0.2660 / 0.7852 | -0.1956 / 0.8238 |
| CURRENT_INITIAL | 277/1303 (21.26%) | 107/1303 (8.21%) | 25/1303 (1.92%) | 1072 | -0.3286 / 0.7625 | -0.2632 / 0.7939 |
| CURRENT_OVERALL | 348/1697 (20.51%) | 132/1697 (7.78%) | 25/1697 (1.47%) | 1396 | -0.3141 / 0.7673 | -0.2475 / 0.8001 |
| LEGACY_ENTER | 50/181 (27.62%) | 24/181 (13.26%) | 10/181 (5.52%) | 158 | 0.2987 / 1.1585 | 0.7678 / 1.4936 |

今回のCURRENT EXIT paired n=1,396（INITIAL1,072 / DIP324）はstrict30との共通集合。前研究のA baseline1,469（DIP397）と同じ分母ではない。旧LEGACYのAはpolicyを変更せず旧referenceへ投影した診断値であり、Aの新しいFreeze・validation・採用結果ではない。

DIPのtail発生率が低いことだけでDIP Entryが因果的に優れるとは断定しない。source構成、参照位置、観測可能範囲が異なる。

## 7. MAE→MFE順序 / post-exit attribution

| Panel | MAE→MFE | MFE→MAE | same-bar unknown | MFEなし | 逆行なし |
| --- | --- | --- | --- | --- | --- |
| CURRENT_DIP | 174 | 155 | 11 | 27 | 27 |
| CURRENT_INITIAL | 450 | 422 | 61 | 184 | 186 |
| CURRENT_OVERALL | 624 | 577 | 72 | 211 | 213 |
| LEGACY_ENTER | 66 | 57 | 7 | 8 | 43 |

CURRENT_DIP <=−10: A退出との順序 `{}`

CURRENT_DIP <=−3: A退出との順序 `{"BREACH_AFTER_EXIT_OPEN": 3, "BREACH_BEFORE_EXIT": 64, "UNKNOWN_EXIT": 4}`

CURRENT_DIP <=−5: A退出との順序 `{"BREACH_AFTER_EXIT": 1, "BREACH_BEFORE_EXIT": 22, "UNKNOWN_EXIT": 2}`

CURRENT_INITIAL <=−10: A退出との順序 `{"BREACH_AFTER_EXIT": 1, "BREACH_AFTER_EXIT_OPEN": 1, "BREACH_BEFORE_EXIT": 20, "UNKNOWN_EXIT": 3}`

CURRENT_INITIAL <=−3: A退出との順序 `{"BREACH_AFTER_EXIT": 1, "BREACH_AFTER_EXIT_OPEN": 7, "BREACH_BEFORE_EXIT": 233, "BREACH_BEFORE_OR_AT_CLOSE_EXIT": 2, "UNKNOWN_EXIT": 34}`

CURRENT_INITIAL <=−5: A退出との順序 `{"BREACH_AFTER_EXIT_OPEN": 5, "BREACH_BEFORE_EXIT": 87, "BREACH_BEFORE_OR_AT_CLOSE_EXIT": 2, "UNKNOWN_EXIT": 13}`

CURRENT_OVERALL <=−10: A退出との順序 `{"BREACH_AFTER_EXIT": 1, "BREACH_AFTER_EXIT_OPEN": 1, "BREACH_BEFORE_EXIT": 20, "UNKNOWN_EXIT": 3}`

CURRENT_OVERALL <=−3: A退出との順序 `{"BREACH_AFTER_EXIT": 1, "BREACH_AFTER_EXIT_OPEN": 10, "BREACH_BEFORE_EXIT": 297, "BREACH_BEFORE_OR_AT_CLOSE_EXIT": 2, "UNKNOWN_EXIT": 38}`

CURRENT_OVERALL <=−5: A退出との順序 `{"BREACH_AFTER_EXIT": 1, "BREACH_AFTER_EXIT_OPEN": 5, "BREACH_BEFORE_EXIT": 109, "BREACH_BEFORE_OR_AT_CLOSE_EXIT": 2, "UNKNOWN_EXIT": 15}`

LEGACY_ENTER <=−10: A退出との順序 `{"BREACH_AFTER_EXIT": 1, "BREACH_AFTER_EXIT_OPEN": 1, "BREACH_BEFORE_EXIT": 8}`

LEGACY_ENTER <=−3: A退出との順序 `{"BREACH_AFTER_EXIT_OPEN": 4, "BREACH_BEFORE_EXIT": 42, "UNKNOWN_EXIT": 4}`

LEGACY_ENTER <=−5: A退出との順序 `{"BREACH_AFTER_EXIT_OPEN": 4, "BREACH_BEFORE_EXIT": 19, "UNKNOWN_EXIT": 1}`

A退出OPENより後のLOWはcounterfactual pathであり、A保有中MAEではない。Exit OPEN自身がthreshold以下なら退出時点までの逆行。global strict30 MAEとA held MAEをtrade ledgerで分離。

## 8. Worst −35.294118% path

Identity `2024-12-25|2024-12-25T09:30:00+09:00|57590` / INITIAL_ENTRY_OPPORTUNITY / Entry `2024-12-25T09:30:00+09:00` / reference 17.0円。旧181にも同じanchor・同じ17円referenceが存在する。

MAE: {"end": "2024-12-25T09:45:00+09:00", "entryMinutesInterval": [10, 15], "price": 11.0, "returnPct": -35.29411764705882, "slot": 3, "start": "2024-12-25T09:40:00+09:00"}。MFE: {"end": "2024-12-25T09:30:00+09:00", "entryMinutesInterval": [0, 0], "price": 17.0, "returnPct": 0.0, "slot": 0, "start": "2024-12-25T09:30:00+09:00"}

30m内+1/+2/+3/+5: {"1": false, "2": false, "3": false, "5": false}。strict30/Fixed12ともcompleted CLOSE reclaimなし、CONTINUED_FAILURE。

Fixed12 net -29.4618% / A net -29.4618%、FIXED12_FALLBACK。+3未到達のためAはarmしない。

| 5m開始 JST | OPEN円 | HIGH円 | LOW円 | CLOSE円 | observed minute n |
| --- | --- | --- | --- | --- | --- |
| 09:30 | 17.0000 | 17.0000 | 17.0000 | 17.0000 | 3 |
| 09:35 | 17.0000 | 17.0000 | 16.0000 | 16.0000 | 4 |
| 09:40 | 16.0000 | 17.0000 | 11.0000 | 13.0000 | 5 |
| 09:45 | 13.0000 | 15.0000 | 13.0000 | 15.0000 | 4 |
| 09:50 | 15.0000 | 15.0000 | 13.0000 | 14.0000 | 5 |
| 09:55 | 14.0000 | 14.0000 | 13.0000 | 13.0000 | 4 |
| 10:00 | 13.0000 | 13.0000 | 12.0000 | 13.0000 | 5 |
| 10:05 | 13.0000 | 13.0000 | 12.0000 | 13.0000 | 5 |
| 10:10 | 13.0000 | 13.0000 | 12.0000 | 13.0000 | 5 |
| 10:15 | 13.0000 | 13.0000 | 12.0000 | 12.0000 | 5 |
| 10:20 | 12.0000 | 13.0000 | 12.0000 | 13.0000 | 3 |
| 10:25 | 13.0000 | 13.0000 | 12.0000 | 12.0000 | 3 |

17円に対する1円差は5.88%。これは価格尺度の算術であり、tick size・spread・約定可能性の認証ではない。保存sessionの後半にもさらなる安値は観測されるが全expected barは揃わず、session終端損益はUNKNOWN。銘柄専用ruleは作成しない。

## 9. Selector opportunityとの接続・集中

| Panel | score AUC: higher→deep | deep n | nondeep n | <=−10 symbol counts |
| --- | --- | --- | --- | --- |
| CURRENT_DIP | 0.5938 | 71 | 323 | {} |
| CURRENT_INITIAL | 0.6193 | 277 | 1026 | {"44160": 1, "47840": 1, "49350": 1, "57590": 7, "65520": 1, "65740": 1, "70690": 1, "81070": 1, "89180": 10, "95620": 1} |
| CURRENT_OVERALL | 0.6132 | 348 | 1349 | {"44160": 1, "47840": 1, "49350": 1, "57590": 7, "65520": 1, "65740": 1, "70690": 1, "81070": 1, "89180": 10, "95620": 1} |
| LEGACY_ENTER | 0.5050 | 50 | 131 | {"190A0": 1, "49350": 1, "57590": 5, "70690": 1, "81070": 1, "95620": 1} |

scoreは損失確率ではない。現行では深い逆行群のscoreが低いとは言えず、粗いupside opportunityとpath riskが共存する。ただし高scoreだからSelectorが正しかった、とも断定しない。厳密な逆行後recoveryとterminal outcomeを併記する必要がある。

現行<=−10は25件でINITIALのみ。うち89180が10件、57590が7件。集中を記録するが銘柄除外ルールにはしない。selector未来MFE/opportunityはevaluatorOnlyとして分離し、decision特徴へは使わない。

| Panel / group | deep3 n | Fixed12 complete n | recovery winner | continued failure | score AUC |
| --- | --- | --- | --- | --- | --- |
| CURRENT_DIP / block1 | 23 | 21 | 3 | 10 | 0.4581 |
| CURRENT_DIP / block2 | 14 | 14 | 1 | 5 | 0.6972 |
| CURRENT_DIP / block3 | 14 | 13 | 1 | 6 | 0.5988 |
| CURRENT_DIP / block4 | 20 | 19 | 4 | 9 | 0.6506 |
| CURRENT_DIP / excludeFrequencyTop3 | 70 | 66 | 9 | 29 | 0.5861 |
| CURRENT_DIP / fullUnderlyingMinutes | 44 | 44 | 8 | 22 | 0.6274 |
| CURRENT_INITIAL / block1 | 61 | 55 | 3 | 27 | 0.6163 |
| CURRENT_INITIAL / block2 | 66 | 60 | 10 | 19 | 0.6587 |
| CURRENT_INITIAL / block3 | 79 | 70 | 6 | 29 | 0.5751 |
| CURRENT_INITIAL / block4 | 71 | 58 | 12 | 23 | 0.6207 |
| CURRENT_INITIAL / excludeFrequencyTop3 | 242 | 219 | 30 | 98 | 0.6253 |
| CURRENT_INITIAL / fullUnderlyingMinutes | 138 | 132 | 21 | 61 | 0.5611 |
| CURRENT_OVERALL / block1 | 84 | 76 | 6 | 37 | 0.5797 |
| CURRENT_OVERALL / block2 | 80 | 74 | 11 | 24 | 0.6659 |
| CURRENT_OVERALL / block3 | 93 | 83 | 7 | 35 | 0.5728 |
| CURRENT_OVERALL / block4 | 91 | 77 | 16 | 32 | 0.6292 |
| CURRENT_OVERALL / excludeFrequencyTop3 | 313 | 286 | 39 | 128 | 0.6175 |
| CURRENT_OVERALL / fullUnderlyingMinutes | 182 | 176 | 29 | 83 | 0.5773 |
| LEGACY_ENTER / block1 | 9 | 9 | 1 | 4 | 0.4248 |
| LEGACY_ENTER / block2 | 12 | 11 | 3 | 6 | 0.4359 |
| LEGACY_ENTER / block3 | 12 | 11 | 0 | 7 | 0.5483 |
| LEGACY_ENTER / block4 | 17 | 15 | 6 | 5 | 0.5712 |
| LEGACY_ENTER / excludeFrequencyTop3 | 40 | 37 | 7 | 20 | 0.5304 |
| LEGACY_ENTER / fullUnderlyingMinutes | 29 | 28 | 8 | 12 | 0.4947 |

rank1〜5の全分布、scoreのbucket別分布、session/symbol concentrationはsummary.json。Outcomeに合わせたrank cutoff・symbol exclusion・time ruleなし。

## 10. Verification / stop

Source/PIT/prefix audit: {"currentSavedStrict30Matches": 1697, "legacyAUnchangedPolicyProjections": 173, "legacySavedStrict30Matches": 181, "savedCurrentPairedExitMatches": 1469, "selectorPITIdentityChecks": 3561, "strict30FutureSuffixChecks": 1878}

18 attribution unit tests: bucket境界、same-bar順序、上昇先行、回復後giveback、missing/lunch、post-exit LOW、future suffix、固定分類gate、上書き拒否。同じ診断を新directoryへ再生成しbyte一致を確認する。GitHub CIとexact code HEADは別receiptへ追記。

Candidate A / Frozen Entry / Selector / 既存Evidence変更0。全9Safety flags false。Fresh/OOS未開封、新provider0、1m0、fit0、Capital/Portfolio0、main merge0。

判断できたこと：deep MAEを一律Entry failure扱いして除外する根拠はない。回復機会を保持する必要がある一方、worstのような実損失もある。Fixed12 follow-upでは両方が確認できる。今回だけではEntry前に識別できるか、Selector/HOLD/EXITのどこが主原因かは確定しない。

**診断完了でSTOP。改善案の実装・threshold変更・Fresh/OOS開封は行わない。**
