# Capital v3 MAX3 Top-3 Quality Result

## A. Main vs Control

| Metric | Control Liquidity OFF | QUALITY_V3 | Delta |
|---|---:|---:|---:|
| daily geom | +1.0960% | +0.6352% | -0.4608pp |
| rolling20 median | 1.141916x | 1.075604x | -0.066312x |
| rolling20 maximum | 1.308664x | 1.204569x | -0.104094x |
| Final Equity | ¥1,513,160 | ¥1,272,017 | ¥-241,143 |
| 2x hit | 0/19 (0.0000%) | 0/19 (0.0000%) | +0.0000pp |
| MaxDD | 12.3006% | 10.8495% | -1.4512pp |
| utilization mean | 53.0040% | 41.4272% | -11.5768pp |
| PF1 >=+1% rate | 32.3353% | 30.9859% | -1.3494pp |
| loser <=0% rate | 53.2934% | 53.5211% | +0.2277pp |
| tail <=-1% rate | 34.7305% | 35.2113% | +0.4807pp |
| U3 capture | 73/297 (24.5791%) | 58/297 (19.5286%) | -5.0505pp |
| Medium3–<5 capture | 28/127 (22.0472%) | 23/127 (18.1102%) | -3.9370pp |
| U5 capture | 45/170 (26.4706%) | 35/170 (20.5882%) | -5.8824pp |
| U10 capture | 26/67 (38.8060%) | 22/67 (32.8358%) | -5.9701pp |
| <2% contamination | 41.9162% | 50.0000% | +8.0838pp |
| <3% contamination | 56.2874% | 59.1549% | +2.8675pp |

200万円到達: **NO**
Selection Status: **TOP3_SELECTION_WORSE**
Economic Status: **CAPITAL_QUALITY_V3_WORSE**

1日幾何平均: **+0.6352%**。100万円 → 20日中央値: **¥1,075,604**、20日最大: **¥1,204,569**。38 sessions、valid rolling20=19、blocked=0、最初の2x区間なし。

Q1–Q8: Q1=FAIL, Q2=FAIL, Q3=FAIL, Q4=FAIL, Q5=FAIL, Q6=FAIL, Q7=FAIL, Q8=FAIL。PF1 gap_to_100pct: **69.0141%**。

### Realized selection quality

| Metric | Control | MAIN |
|---|---:|---:|
| funded N | 167 | 142 |
| realized mean | +0.9717% | +0.6375% |
| realized median | -0.1000% | -0.1000% |
| >0 rate | 46.7066% | 46.4789% |
| <=-3% rate | 13.1737% | 14.7887% |
| worst return | -17.5170% | -17.5170% |
| p05 return | -5.2648% | -5.2647% |

MAIN realized resolved 142/142; >=+1% 44, >0 66, <=0 76, <=-1% 50, <=-3% 21。候補teacherの実現欠損23件は0%補完しない。

## B. Entry→High bucket → realized result

| Entry→High | funded N / bucket N | funded rate | realized mean | median | PF1 rate | loser rate |
|---|---:|---:|---:|---:|---:|---:|
| <1% | 39/410 | 9.5122% | -1.9281% | -1.9672% | 2.5641% | 84.6154% |
| 1-<2% | 32/197 | 16.2437% | -0.3124% | -0.1649% | 21.8750% | 59.3750% |
| 2-<3% | 13/135 | 9.6296% | -2.0303% | +0.0975% | 15.3846% | 46.1538% |
| 3-<4% | 14/73 | 19.1781% | -0.3614% | +1.0387% | 50.0000% | 42.8571% |
| 4-<5% | 9/54 | 16.6667% | -0.1046% | +0.4720% | 44.4444% | 33.3333% |
| 5-<10% | 13/103 | 12.6214% | +2.7635% | +2.7749% | 69.2308% | 7.6923% |
| >=10% | 22/67 | 32.8358% | +7.8267% | +4.4699% | 63.6364% | 36.3636% |

Bucketはstrictly-later/pre15:20 actual High。評価専用であり、runtimeへの入力0。

## C. Rank Cutoff independent diagnostics

| Metric | MAIN | S_ONLY | A_PLUS | B_PLUS |
|---|---:|---:|---:|---:|
| funded N | 142 | 18 | 84 | 138 |
| avg funded/session | 3.7368 | 0.4737 | 2.2105 | 3.6316 |
| daily geom | +0.6352% | -0.0691% | +0.3984% | +0.6488% |
| rolling20 median | 1.075604x | 1.018806x | 1.074887x | 1.073066x |
| rolling20 max | 1.204569x | 1.035408x | 1.220331x | 1.204466x |
| Final Equity | ¥1,272,017 | ¥974,079 | ¥1,163,111 | ¥1,278,596 |
| MaxDD | 10.8495% | 7.3157% | 10.8495% | 10.8495% |
| utilization | 41.4272% | 4.6528% | 26.2536% | 40.7746% |
| EXIT>=+1% rate | 30.9859% | 33.3333% | 36.9048% | 31.8841% |
| EXIT<=0% rate | 53.5211% | 61.1111% | 48.8095% | 51.4493% |
| EXIT<=-1% rate | 35.2113% | 44.4444% | 35.7143% | 35.5072% |
| 2x hit | 0/19 (0%) | 0/19 (0%) | 0/19 (0%) | 0/19 (0%) |
| U3 capture | 19.5286% | 2.3569% | 15.1515% | 19.1919% |
| Medium3–<5 capture | 18.1102% | 1.5748% | 15.7480% | 18.1102% |
| U5 capture | 20.5882% | 2.9412% | 14.7059% | 20.0000% |
| U10 capture | 32.8358% | 7.4627% | 22.3881% | 31.3433% |
| <2% funded rate | 50.0000% | 61.1111% | 41.6667% | 48.5507% |
| <3% funded rate | 59.1549% | 61.1111% | 46.4286% | 58.6957% |

各診断のrank identity violation=0、backfill violation=0、MAX3 violation=0。3診断は独立Evidenceのみ。同cycleで正式採用するprofileの変更0。

## D. Missed Winner / Selected Loser

| Same-entry batch diagnostic | N |
|---|---:|
| MAX3 binding entry batch | 89 |
| selected loser while missed PF1 (batches/pairs) | 1/1 |
| selected <3 while missed U5 (batches/pairs) | 1/1 |
| selected lower realized while better missed (batches/pairs) | 5/5 |
| missed U5 due MAX3 | 20 |
| missed U10 due MAX3 | 7 |

Regretは事前固定した同時刻Entry batch内FUNDED対MAX rejectの比較。既存held positionも枠を占めるが、将来結果による差替え/EXIT上書きは行わない。未来teacherは診断専用。

| Missed cohort | quality gate | MAX3 | cash/lot |
|---|---:|---:|---:|
| U3 | 195 | 33 | 11 |
| Medium | 83 | 13 | 8 |
| U5 | 112 | 20 | 3 |
| U10 | 38 | 7 | 0 |

全候補reasons: {"CAPITAL_EOD_ENTRY_CUTOFF": 11, "CASH_OR_LOT_CONSTRAINED": 32, "FUNDED": 142, "MAX_POSITION_CAP": 93, "QUALITY_GATE_REJECT": 761}。U5 gate拒否112件の失敗条件: L3=63 / LF1=71 / LSAFE=80 (重複あり)。Liquidity理由の拒否0。

## E. Thin Liquidity

| Historical liquidity status | MAIN funded N | PF1 | loser | tail<=-1 | U3/U5/U10 | mean | median |
|---|---:|---:|---:|---:|---:|---:|---:|
| LIQUIDITY_ELIGIBLE | 107 | 32 (29.9065%) | 58 (54.2056%) | 36 (33.6449%) | 42/22/12 | +0.4752% | -0.1000% |
| EXTREME_ILLIQUIDITY_REJECT | 35 | 12 (34.2857%) | 18 (51.4286%) | 14 (40.0000%) | 16/13/10 | +1.1336% | -0.0336% |
| LIQUIDITY_UNKNOWN | 0 | 0 (—) | 0 (—) | 0 (—) | 0/0/0 | — | — |

| Thin subset | Control | MAIN |
|---|---:|---:|
| funded N | 36 | 35 |
| PF1 rate | 36.1111% | 34.2857% |
| loser rate | 52.7778% | 51.4286% |
| tail<=-1 rate | 38.8889% | 40.0000% |
| U5 N | 11 | 13 |
| U10 N | 8 | 10 |
| mean realized | +0.9717% | +1.1336% |
| median realized | -0.1647% | -0.0336% |
| worst | -17.5170% | -17.5170% |
| p05 | -9.4737% | -6.5102% |
| no-trade MTM5m events | 433 | 526 |
| EOD regular | 20 | 19 |
| EOD auction | 5 | 6 |
| EOD unexecuted | 0 | 0 |
| actual PnL | ¥196,299 | ¥114,243 |

旧Liquidity reject52 Winner: admission eligible **20/52**、funded U5 **13**、U10 **10**、実現mean **+6.2099%** / median **+3.5906%**、actual PnL **¥218,441**。Controlは11 U5 / 8 U10。

薄いWinnerのcaptureは増えたが、thin全体のPF1率とtail率は改善していない。数量・他候補・cash recycling・compoundingが同時に変わるため、cohort PnLをPortfolio deltaの独立因果分解と呼ばない。Liquidity Hard Gate/capはOFFのまま。

## F. Integrity

| Head | OOF N | ROC AUC | Brier | top20% enrichment |
|---|---:|---:|---:|---:|
| H5 | 1039 | 0.656590 | 0.136187 | 1.616092x |
| H3 | 1039 | 0.651034 | 0.196754 | 1.530513x |
| HF1 | 1016 | 0.522519 | 0.207582 | 1.084292x |
| HL0 | 1016 | 0.502645 | 0.263080 | 1.105755x |

Head別positive base、decile observed rate、block AUC/base rateはHEAD_QUALITY_DIAGNOSTICS.jsonへ保存。HF1/HL0の識別力はこのOOFでは弱く、今回のgate/Qは選択品質改善に結び付かなかった。Head削除・重み変更0。

- New fits **24** (H3/HF1/HL0各8)、H5 new fits **0**。H5 byte reuse hash `a34f2c4a090a589d4e80858b65f01f3dc95a7849a57aece7e815213d20429731`。
- CORE manifest exact identity、Movement追加0。Primary Main1 + diagnostic3、Control replay0、MAX4/5 replay0、result retune0。
- Canary **46/46 PASS**。Independent **333,419 checks / mismatch0**。Primary logic imports0。
- Protected/Holdout/Fresh/Validation/OOS/Prospective開封0、新provider0、Frozen Entry/EXIT変更0。
- orders0、main merge0、force push0。Safety10 flagsは全false、productionReady=false。

Historical actual tradeはexecution reference。provider到着時刻はUNKNOWNで、Controlと同じcompleted-minute availability仮定を維持。Liquidity cap OFFのquantityに対するhistorical executable depthは保証していない。Development feasibility/negative Evidenceで終了。

### Daily / rolling20 / capital secondary

| Metric | MAIN |
|---|---:|
| daily arithmetic mean | +0.6887% |
| daily median | -0.0090% |
| rolling20 min | 1.022340x |
| rolling20 mean | 1.087698x |
| median utilization | 50.6813% |
| time >=80% utilization | 0.0000% |
| minimum cash | ¥219,299 |
| turnover cash | ¥70,366,246 |
| recycled cash used | ¥3,767,136 |
| avg funded trades/session | 3.736842105263158 |

Sessions with max concurrent0/1/2/3: {"0": 1, "1": 2, "2": 3, "3": 32}。MAX3は最大同時保有数であり資金3等分ではない。

Paired daily delta: positive 15、negative 22、equal 1。mean -0.5093%、median -0.1951%、max gain +3.3518%、max deterioration -6.0373%。

Limit-up causal authority confirmed0、funded142はUNKNOWN。UNKNOWNを理由に停止せず、通常EOD routeを維持。全4profile EOD unexecuted0。

Repo Iam-2squared/ark-terminal / branch capital-state9-vnext-20261004 / instruction basis eaea4b7b1541ccf5285748a75986f8ef6e7fc5ef。

**STOP: Main・3診断・監査・Report完了後に設定変更/診断採用を行わず、次cycleの判断をユーザーへ返す。**
