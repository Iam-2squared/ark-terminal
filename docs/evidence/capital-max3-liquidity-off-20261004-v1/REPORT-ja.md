# MAX3 Liquidity OFF Result

| Metric | Control | Liquidity OFF | Delta |
|---|---:|---:|---:|
| daily_geometric | 0.7765% | 1.0960% | +0.3195pp |
| rolling20_median | 1.208611x | 1.141916x | -0.066695x |
| rolling20_maximum | 1.311044x | 1.308664x | -0.002380x |
| 2x_hit_rate | 0.0000% | 0.0000% | +0.0000pp |
| final_equity_jpy | ¥1,341,668 | ¥1,513,160 | +171,492円 |
| MaxDD | 10.8301% | 12.3006% | +1.4705pp |
| utilization | 49.4007% | 53.0040% | +3.6033pp |
| BigWinner5_capture | 24.7059% | 26.4706% | +1.7647pp |
| liquidity_Winner_reject | 30.5882% | 0.0000% | -30.5882pp |

1日幾何平均: **+1.0960%**

100万円 → 20日中央値: **¥1,141,916**

100万円 → 20日最大: **¥1,308,664**

200万円到達: **NO**。hit 0/19。

BigWinner5 capture: **45/170 = 26.4706%**

旧Liquidity reject52件: score eligible **27件**、実際に回収したWinner **11件**。

薄商い新規funded（historical veto/unknown）**36件**、平均実現return **+0.9717%**。

EOD unexecuted: **0**。判断: **MIXED**。

終了status: `CAPITAL_MAX3_LIQUIDITY_OFF_MIXED` / `NORTH_STAR_HIT=False`。JST: 2026-10-04T17:12:25.649979+09:00。

指定38 sessionsのpaired比較。rolling20は指定Development評価sessionsであり、連続する全TSE営業日とは呼ばない。cohort外2025-07-11/07-14を開封・0%補完していない。19区間は重複する。

| OFF measurement | value |
|---|---:|
| valid days / blocked | 38 / 0 |
| daily arithmetic mean / median | +1.1980% / +0.2860% |
| rolling20 valid N | 19 |
| rolling20 min / mean / median / max | 1.050792x / 1.167457x / 1.141916x / 1.308664x |
| 2x N / rate / earliest | 0 / 0.0000% / None |
| max20 window | {'amount_from_1m': 1308663.6299732034, 'end_session': '2025-07-31', 'growth_multiple': 1.3086636299732035, 'hit': False, 'start_session': '2025-07-01'} |

| paired daily delta | value |
|---|---:|
| valid_paired_day_N | 38 |
| positive_day_N | 13 |
| negative_day_N | 24 |
| equal_day_N | 1 |
| median_delta | -0.0435pp |
| mean_delta | +0.3706pp |
| maximum_gain | +17.5380pp |
| maximum_deterioration | -7.7781pp |

Liquidity理由のcandidate/lot-cap rejectは0。score>=1 threshold、candidate equity caps、dynamic target utilization、water-fill、100-share lot、MAX3、MTM/EXIT/EOD/accountingは固定。

| Winner preservation | Control | OFF |
|---|---:|---:|
| Winner5 funded/capture | 42 / 24.7059% | 45 / 26.4706% |
| Winner10 funded | 17 | 26 |
| Liquidity Winner reject | 52 | 0 |
| score<1 missed | 34 | 59 |
| MAX missed | 38 | 59 |
| cash/lot missed | 4 | 7 |
| Entry cutoff missed | 0 | 0 |

新規funded Winner5は15件、Control funded Winner5のdropは12件。回収11件をそのままnet capture改善とはしない。

| old Liquidity-rejected Winner52 cohort | N | score eligible | funded Winner5 | funded Winner10 | realized mean | realized median | actual PnL |
|---|---:|---:|---:|---:|---:|---:|---:|
| TOTAL | 52 | 27 | 11 | 8 | +7.2885% | +5.3740% | ¥318,081 |
| EXTREME_ILLIQUIDITY_REJECT | 51 | 26 | 11 | 8 | +7.2885% | +5.3740% | ¥318,081 |
| LIQUIDITY_ELIGIBLE | 0 | 0 | 0 | 0 | UNAVAILABLE | UNAVAILABLE | ¥0 |
| LIQUIDITY_UNKNOWN | 1 | 1 | 0 | 0 | UNAVAILABLE | UNAVAILABLE | ¥0 |

未回収52 cohortのreasons: {'BELOW_CAPITAL_BASELINE': 25, 'CASH_OR_LOT_CONSTRAINED': 1, 'MAX_POSITION_CAP': 15}。潜在Winnerラベルはevaluation専用。

| newly-funded cohort | N | mean | median | positive rate | Winner5/10 | worst / p05 | Frozen / EOD regular / auction / unexecuted | no-trade5m | min historical coverage | prior median Va min / p25 / median / p75 / max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL newly funded | 45 | +1.3432% | -0.1000% | 48.8889% | 15/11 | -17.5170% / -8.9048% | 16 / 23 / 6 / 0 | 492 | 3.0769% | ¥452,150 / ¥1,440,200 / ¥2,919,100 / ¥6,856,600 / ¥3,855,628,700 |
| Historical veto/unknown | 36 | +0.9717% | -0.1647% | 47.2222% | 11/8 | -17.5170% / -9.4737% | 11 / 20 / 5 / 0 | 433 | 3.0769% | ¥452,150 / ¥1,212,788 / ¥2,465,650 / ¥3,777,350 / ¥10,659,250 |
| EXTREME_ILLIQUIDITY_REJECT | 36 | +0.9717% | -0.1647% | 47.2222% | 11/8 | -17.5170% / -9.4737% | 11 / 20 / 5 / 0 | 433 | 3.0769% | ¥452,150 / ¥1,212,788 / ¥2,465,650 / ¥3,777,350 / ¥10,659,250 |
| LIQUIDITY_ELIGIBLE | 9 | +2.8293% | +0.1992% | 55.5556% | 4/3 | -4.5639% / -3.1740% | 5 / 3 / 1 / 0 | 59 | 23.0769% | ¥6,856,600 / ¥18,027,000 / ¥22,773,800 / ¥246,606,750 / ¥3,855,628,700 |
| LIQUIDITY_UNKNOWN | 0 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0/0 | UNAVAILABLE / UNAVAILABLE | 0 / 0 / 0 / 0 | 0 | UNAVAILABLE | UNAVAILABLE / UNAVAILABLE / UNAVAILABLE / UNAVAILABLE / UNAVAILABLE |

funded entry identity: {'OFF': 167, 'control': 164, 'dropped': 42, 'new': 45, 'shared': 122}。ALL newly fundedのうちhistorical liquidity eligibleも含まれるため、薄商いsubsetを別表にした。

no-trade MTMはEntry後の完了5m windowにactual printがなく、Positionが残る場合のvaluation保持回数。fill/cash releaseではない。cohortごとのminute snapshotとsource lineageはprivate ledgerへ保存。

独立監査: 81,977項目、mismatch=0。canary 24/24 PASS。score hash `a34f2c4a090a589d4e80858b65f01f3dc95a7849a57aece7e815213d20429731`。新fit0、model/feature追加0、Control replay0、MAX4/MAX5 replay0、provider requests0、retune0。

Frozen Entry/EXITおよび旧v1/v2 Evidenceは変更0。新MAX3 policyは`docs/policies/CAPITAL_MAX_CONCURRENT_3_RESEARCH_POLICY_V1.md`。MAX3は最大同時保有3銘柄で、3等分ではない。

独立実装はPrimary ranking/allocation/replayをimportしない。固定score/models・Frozen upstream・保存source IOは共有しており、外部市場sourceによる独立検証ではない。actual-arrival metadataはUNKNOWNで、v2のcompleted-minute availability仮定を維持。limit-up authorityもUNKNOWNのまま通常EOD routeを使用。

Liquidity capを外した数量について、historical printのprice/time Evidenceは市場depthや実数量の約定保証を示さない。Development counterfactualであり、production安全性や外部OOSを示さない。

New/dropped/shared cohorts separate outcomes, but concurrent selection, changed quantities and compounding interact; cohort PnL is not a causal decomposition of the paired portfolio delta.

Safety全false。orders=0、main merge=0、force push=0。このsingle resultを固定してSTOP。Liquidity threshold/capを同cycle内で作り直さない。
