| Arm / Profile | 1日幾何平均 | 20日中央値 | 20日最大 | 200万円 hit N/rate |
|---|---:|---:|---:|---:|
| CORE_P5_MAX3 | +0.7765% | 1.208611x | 1.311044x | 0/19 / 0.00% |
| CORE_P5_MAX4 | +0.6800% | 1.164263x | 1.284560x | 0/19 / 0.00% |
| CORE_P5_MAX5 | +0.6795% | 1.164730x | 1.303621x | 0/19 / 0.00% |
| MOVE_P5_MAX3 | +0.0156% | 1.035625x | 1.141089x | 0/19 / 0.00% |
| MOVE_P5_MAX4 | +0.0574% | 1.017078x | 1.207707x | 0/19 / 0.00% |
| MOVE_P5_MAX5 | +0.0557% | 1.019482x | 1.208115x | 0/19 / 0.00% |
| MOVE_DUAL_MAX3 | +0.2718% | 1.051375x | 1.199756x | 0/19 / 0.00% |
| MOVE_DUAL_MAX4 | +0.1292% | 1.030560x | 1.163605x | 0/19 / 0.00% |
| MOVE_DUAL_MAX5 | +0.1452% | 1.032611x | 1.170293x | 0/19 / 0.00% |

**BEST V2: CORE_P5_MAX3**

1日幾何平均: **+0.7765%**

100万円 → 20日中央値: **¥1,208,611**

100万円 → 20日最大: **¥1,311,044**

2倍達成: **NO**。2倍hit rate: **0.00%**。

終了status: `CAPITAL_VNEXT_V2_DEV_IMPROVED_BUT_MISS`。JST: 2026-10-04T15:41:12.031652+09:00。

v1比: 1日幾何平均 +1.3402pp、rolling20中央値 +0.342201x。

| Metric | v1 best MAX4 | v2 best | delta |
|---|---:|---:|---:|
| daily geometric | -0.5637% | 0.7765% | +1.3402pp |
| rolling20 median | 0.866410x | 1.208611x | +0.342201x |
| rolling20 max | 1.070437x | 1.311044x | +0.240607x |
| 2x hit rate | 0.0000% | 0.0000% | +0.0000pp |
| utilization | 40.9497% | 49.4007% | +8.4510pp |
| BigWinner capture | 17.6471% | 24.7059% | +7.0588pp |
| Liquidity Winner reject | 65.2941% | 30.5882% | -34.7059pp |

指定58 Development sessions、最初20 warm-up、次38を5-session rolling-originで評価。全9 runsのvalid days=38,38,38,38,38,38,38,38,38、valid rolling windows=19,19,19,19,19,19,19,19,19、blocked=0,0,0,0,0,0,0,0,0。

rolling20は指定Developmentの20評価sessions。cohort外の2025-07-11/07-14は未評価で、0%へ補完していない。全ての連続TSE営業日や外部OOSの成績とは呼ばない。重複する19区間は独立標本ではない。

v1の正式negative Evidenceは変更0・再Replay0。v1→COREの差にはExtreme Veto・5% capacity・water-fillが同時に入るため、個々の寄与は分離していない。

| Profile | rolling20 N | min | mean | median | max | 2x N/rate | earliest2x | max amount |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| CORE_P5_MAX3 | 19 | 1.078578x | 1.194803x | 1.208611x | 1.311044x | 0 / 0.00% | NONE | ¥1,311,044 |
| CORE_P5_MAX4 | 19 | 1.016257x | 1.150008x | 1.164263x | 1.284560x | 0 / 0.00% | NONE | ¥1,284,560 |
| CORE_P5_MAX5 | 19 | 1.016326x | 1.153626x | 1.164730x | 1.303621x | 0 / 0.00% | NONE | ¥1,303,621 |
| MOVE_P5_MAX3 | 19 | 0.930731x | 1.035957x | 1.035625x | 1.141089x | 0 / 0.00% | NONE | ¥1,141,089 |
| MOVE_P5_MAX4 | 19 | 0.920457x | 1.041223x | 1.017078x | 1.207707x | 0 / 0.00% | NONE | ¥1,207,707 |
| MOVE_P5_MAX5 | 19 | 0.921205x | 1.041796x | 1.019482x | 1.208115x | 0 / 0.00% | NONE | ¥1,208,115 |
| MOVE_DUAL_MAX3 | 19 | 0.960187x | 1.082156x | 1.051375x | 1.199756x | 0 / 0.00% | NONE | ¥1,199,756 |
| MOVE_DUAL_MAX4 | 19 | 0.941792x | 1.050231x | 1.030560x | 1.163605x | 0 / 0.00% | NONE | ¥1,163,605 |
| MOVE_DUAL_MAX5 | 19 | 0.945207x | 1.054344x | 1.032611x | 1.170293x | 0 / 0.00% | NONE | ¥1,170,293 |

**BigWinner Preservation**

| Scope | BigWinner5 | Liquidity eligible | Extreme/UNKNOWN reject | reject rate | reject潜在 median / mean / max |
|---|---:|---:|---:|---:|---:|
| ALL58 | 244 | 178 | 66 | 27.05% | +8.67% / +12.20% / +43.36% |
| OOF38 | 170 | 118 | 52 | 30.59% | +8.50% / +12.88% / +43.36% |

| Profile | funded Winner5 / capture | extreme liquidity | score<1 | MAX | cash/lot | EOD cutoff | Winner10 diagnostic |
|---|---:|---:|---:|---:|---:|---:|---:|
| CORE_P5_MAX3 | 42 / 24.71% | 52 | 34 | 38 | 4 | 0 | 17 |
| CORE_P5_MAX4 | 54 / 31.76% | 52 | 34 | 20 | 10 | 0 | 23 |
| CORE_P5_MAX5 | 59 / 34.71% | 52 | 34 | 9 | 16 | 0 | 26 |
| MOVE_P5_MAX3 | 50 / 29.41% | 52 | 49 | 14 | 5 | 0 | 20 |
| MOVE_P5_MAX4 | 57 / 33.53% | 52 | 49 | 5 | 7 | 0 | 25 |
| MOVE_P5_MAX5 | 58 / 34.12% | 52 | 49 | 4 | 7 | 0 | 26 |
| MOVE_DUAL_MAX3 | 44 / 25.88% | 52 | 53 | 14 | 7 | 0 | 20 |
| MOVE_DUAL_MAX4 | 46 / 27.06% | 52 | 53 | 8 | 11 | 0 | 21 |
| MOVE_DUAL_MAX5 | 48 / 28.24% | 52 | 53 | 4 | 13 | 0 | 24 |

潜在値幅はstrictly-later/pre15:20 actual High/raw Entry比。約定可能な最大利益やrealized PnLではない。Liquidity v2の20%/5%/5% capは変更0。OOF reject52件はExtreme Veto51件とsupport UNKNOWN1件。

**Movement Hypothesis**

MOVEMENT_CAPACITY_SIGNAL: **WEAK**

| Feature | Winner5 N / mean / median | non-Winner5 N / mean / median | p25/p75 Winner | p25/p75 non | standardized difference | AUC |
|---|---:|---:|---:|---:|---:|---:|
| M1 prior5 median daily range% | 244 / 8.3405 / 6.1708 | 1355 / 5.4529 / 3.8591 | 3.0809/11.5969 | 2.1784/6.7896 | 0.4780 | 0.6358 |
| M2 prior20 median daily range% | 243 / 4.2290 / 3.3169 | 1355 / 3.8437 / 3.0296 | 2.1084/5.2083 | 2.0029/4.8394 | 0.1315 | 0.5352 |
| M3 prior20 daily range p75 | 243 / 7.1689 / 5.5572 | 1355 / 6.0738 / 4.5647 | 3.4749/9.0876 | 2.8338/7.6316 | 0.2269 | 0.5730 |
| M4 prior20 max daily range% | 243 / 21.3233 / 22.4615 | 1355 / 15.7253 / 12.5616 | 12.2556/29.2419 | 6.7338/22.4490 | 0.5165 | 0.6646 |
| M5 prior20 frequency range>=3% | 243 / 0.5503 / 0.5500 | 1355 / 0.5115 / 0.5000 | 0.3079/0.7895 | 0.2500/0.8000 | 0.1298 | 0.5369 |
| M6 prior20 frequency range>=5% | 243 / 0.3615 / 0.3000 | 1355 / 0.3030 / 0.2105 | 0.1500/0.5000 | 0.0526/0.4737 | 0.2209 | 0.5865 |
| M7 prior20 frequency range>=10% | 243 / 0.1770 / 0.1053 | 1355 / 0.1202 / 0.0500 | 0.0500/0.2500 | 0.0000/0.1579 | 0.3279 | 0.6325 |
| M8 median of prior5 session median absolute5m return% | 230 / 0.4444 / 0.4050 | 1289 / 0.3461 / 0.2924 | 0.2385/0.6248 | 0.1686/0.4503 | 0.3352 | 0.6096 |
| M9 median of prior20 session median absolute5m return% | 224 / 0.3175 / 0.3045 | 1271 / 0.2842 / 0.2724 | 0.1894/0.4246 | 0.1586/0.3859 | 0.1641 | 0.5527 |
| M10 pooled prior20 p90 absolute5m return% | 224 / 1.5801 / 1.4522 | 1271 / 1.2286 / 1.1040 | 1.0176/1.9516 | 0.7524/1.5442 | 0.4939 | 0.6495 |
| M11 prior20 median realized5m volatility% | 197 / 3.4951 / 2.8671 | 1164 / 2.8636 / 2.2376 | 1.7731/4.4881 | 1.3686/3.7114 | 0.2863 | 0.5992 |
| M12 prior20 median max30m range% | 243 / 2.9188 / 2.2620 | 1355 / 2.6340 / 2.0550 | 1.5494/3.5152 | 1.2736/3.3358 | 0.1364 | 0.5432 |
| M13 current range% on completed actual minute bars | 244 / 14.3467 / 11.7967 | 1356 / 9.6800 / 7.8914 | 8.3602/18.3929 | 5.2930/12.0078 | 0.6430 | 0.7025 |
| M14 current realized5m volatility% on completed5m bins | 239 / 7.7327 / 6.7099 | 1287 / 5.3563 / 4.3089 | 4.0774/10.7122 | 2.7511/6.7994 | 0.5514 | 0.6652 |
| M15 current range% / prior20 median same-clock range% | 238 / 14.9008 / 5.6260 | 1339 / 6.3909 / 3.3558 | 3.1597/11.9383 | 1.8671/6.5572 | 0.3019 | 0.6477 |
| M16 current actual Va pace / prior20 median same-clock Va pace | 243 / 186.0058 / 33.7067 | 1354 / 54.4980 / 7.3694 | 7.3614/148.1840 | 2.4506/31.2288 | 0.3686 | 0.6863 |

OOF P-AUC: CORE=0.653023、MOVE=0.709646、差=+0.056623。top20% enrichment: CORE=1.5558x、MOVE=2.0548x。

モデルはAnatomy前に固定した27 core numeric+M1–M16/I1–I3・7 categoricalのまま。UNKNOWN indicatorを残し、Anatomy後のfield追加/削除0。全featureのN/mean/median/p25/p75/標準化差/AUC/5 quantile bins、Winner10及びOOF38診断はMOVEMENT_ANATOMY.jsonに保存。

| MAX | ARM-A capture / daily geom / median20 | ARM-B capture / daily geom / median20 |
|---|---:|---:|
| 3 | 24.71% / +0.7765% / 1.208611x | 29.41% / +0.0156% / 1.035625x |
| 4 | 31.76% / +0.6800% / 1.164263x | 33.53% / +0.0574% / 1.017078x |
| 5 | 34.71% / +0.6795% / 1.164730x | 34.12% / +0.0557% / 1.019482x |

Movement追加はOOF potentialの判別と平均captureを改善したが、同じMAXのdaily/rolling20をCOREより下げた。事前のSUPPORTED条件を満たさず、WEAKで固定した。

**Realizability Head**

OOF Head R: known N=1016、positive rate=45.47%、AUC=0.511819。

| MAX / arm | Winner5 capture | realized positive rate | avg realized return | p05 / min return | daily geom | median20 / max20 |
|---|---:|---:|---:|---:|---:|---:|
| MAX3 / MOVE_P5 | 29.41% | 43.21% | +0.0208% | -5.98% / -15.46% | +0.0156% | 1.035625x / 1.141089x |
| MAX3 / MOVE_DUAL | 25.88% | 41.72% | +0.1498% | -5.00% / -15.46% | +0.2718% | 1.051375x / 1.199756x |
| MAX4 / MOVE_P5 | 33.53% | 43.55% | +0.0351% | -5.96% / -17.11% | +0.0574% | 1.017078x / 1.207707x |
| MAX4 / MOVE_DUAL | 27.06% | 41.76% | -0.0348% | -5.94% / -17.11% | +0.1292% | 1.030560x / 1.163605x |
| MAX5 / MOVE_P5 | 34.12% | 44.00% | -0.0418% | -6.43% / -17.11% | +0.0557% | 1.019482x / 1.208115x |
| MAX5 / MOVE_DUAL | 28.24% | 44.20% | +0.0766% | -5.89% / -17.11% | +0.1452% | 1.032611x / 1.170293x |

| MAX | BでfundしたWinnerをCで失ったN | Cで新たにfundしたWinner N | lossのうちC score<1 |
|---|---:|---:|---:|
| 3 | 12 | 6 | 8 |
| 4 | 13 | 2 | 8 |
| 5 | 13 | 3 | 8 |

Head R追加は各MAXのdaily geomとrolling20中央値をMOVE_P5比で改善したが、potential Winner5 captureを全MAXで減らした。MAX4/5ではrolling20最大も低下。単純なpositive rate/平均trade returnの改善とPortfolio改善は同義ではない。funded R unknownは全profile0、全候補のR unknown40件（cutoff22、valid EOD fill無し18）はUNKNOWNを維持し、runtime filterへ使っていない。

**Secondary Audit**

| Profile | daily arithmetic / median | Final Equity | total return | MaxDD | util mean / median | time>=80 / >=90 | cash min | max concurrent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CORE_P5_MAX3 | +0.8274% / +0.0671% | ¥1,341,668 | +34.17% | 10.83% | 49.40% / 58.51% | 0.00% / 0.00% | ¥195,683 | 3 |
| CORE_P5_MAX4 | +0.7270% / -0.0259% | ¥1,293,702 | +29.37% | 10.79% | 53.29% / 64.47% | 23.09% / 0.00% | ¥147,680 | 4 |
| CORE_P5_MAX5 | +0.7293% / +0.0224% | ¥1,293,505 | +29.35% | 10.77% | 55.43% / 66.45% | 26.80% / 1.48% | ¥95,210 | 5 |
| MOVE_P5_MAX3 | +0.0629% / -0.0940% | ¥1,005,964 | +0.60% | 12.40% | 42.69% / 44.59% | 0.00% / 0.00% | ¥191,802 | 3 |
| MOVE_P5_MAX4 | +0.1131% / -0.1138% | ¥1,022,046 | +2.20% | 15.30% | 44.01% / 44.90% | 7.97% / 0.00% | ¥140,578 | 4 |
| MOVE_P5_MAX5 | +0.1124% / -0.0381% | ¥1,021,392 | +2.14% | 15.78% | 45.12% / 46.21% | 13.13% / 0.01% | ¥91,634 | 5 |
| MOVE_DUAL_MAX3 | +0.3127% / -0.1555% | ¥1,108,631 | +10.86% | 10.83% | 37.15% / 39.69% | 0.00% / 0.00% | ¥195,936 | 3 |
| MOVE_DUAL_MAX4 | +0.1650% / -0.0947% | ¥1,050,298 | +5.03% | 12.55% | 39.03% / 42.83% | 5.55% / 0.00% | ¥146,279 | 4 |
| MOVE_DUAL_MAX5 | +0.1806% / -0.0947% | ¥1,056,697 | +5.67% | 12.19% | 39.96% / 42.93% | 6.61% / 0.00% | ¥103,330 | 5 |

| Profile | funded/rejected | Frozen EXIT | EOD regular/auction/unresolved | water-fill lots / funded positions | turnover | recycled cash used | idle cash |
|---|---:|---:|---:|---:|---:|---:|---:|
| CORE_P5_MAX3 | 164/875 | 79 | 77/8/0 | 57 / 10 | ¥89,264,307 | ¥7,829,498 | 50.60% |
| CORE_P5_MAX4 | 207/832 | 100 | 99/8/0 | 70 / 17 | ¥93,995,730 | ¥10,102,001 | 46.71% |
| CORE_P5_MAX5 | 230/809 | 114 | 106/10/0 | 94 / 21 | ¥97,990,329 | ¥11,623,756 | 44.57% |
| MOVE_P5_MAX3 | 162/877 | 95 | 62/5/0 | 14 / 4 | ¥80,471,977 | ¥7,343,359 | 57.31% |
| MOVE_P5_MAX4 | 186/853 | 110 | 71/5/0 | 18 / 7 | ¥83,908,768 | ¥8,818,061 | 55.99% |
| MOVE_P5_MAX5 | 200/839 | 117 | 78/5/0 | 26 / 12 | ¥85,816,468 | ¥9,562,369 | 54.88% |
| MOVE_DUAL_MAX3 | 151/888 | 85 | 61/5/0 | 31 / 5 | ¥69,338,828 | ¥4,680,844 | 62.85% |
| MOVE_DUAL_MAX4 | 170/869 | 94 | 71/5/0 | 43 / 5 | ¥71,203,457 | ¥5,063,298 | 60.97% |
| MOVE_DUAL_MAX5 | 181/858 | 100 | 76/5/0 | 44 / 6 | ¥72,805,053 | ¥5,677,908 | 60.04% |

**Limit-Up Cohort**

| Profile | confirmed/reaching | Frozen before EOD | 15:20 intent | regular/auction/unexecuted | realized return | Winner overlap | UNKNOWN funded |
|---|---:|---:|---:|---:|---:|---:|---:|
| CORE_P5_MAX3 | 0/0 | 0 | 0 | 0/0/0 | UNKNOWN | 0 | 164 |
| CORE_P5_MAX4 | 0/0 | 0 | 0 | 0/0/0 | UNKNOWN | 0 | 207 |
| CORE_P5_MAX5 | 0/0 | 0 | 0 | 0/0/0 | UNKNOWN | 0 | 230 |
| MOVE_P5_MAX3 | 0/0 | 0 | 0 | 0/0/0 | UNKNOWN | 0 | 162 |
| MOVE_P5_MAX4 | 0/0 | 0 | 0 | 0/0/0 | UNKNOWN | 0 | 186 |
| MOVE_P5_MAX5 | 0/0 | 0 | 0 | 0/0/0 | UNKNOWN | 0 | 200 |
| MOVE_DUAL_MAX3 | 0/0 | 0 | 0 | 0/0/0 | UNKNOWN | 0 | 151 |
| MOVE_DUAL_MAX4 | 0/0 | 0 | 0 | 0/0/0 | UNKNOWN | 0 | 170 |
| MOVE_DUAL_MAX5 | 0/0 | 0 | 0 | 0/0/0 | UNKNOWN | 0 | 181 |

authoritative price-limit/base/statusが既存sourceに無いため全funded positionはLIMIT_UP_UNKNOWN。confirmed0は実際のストップ高0を意味しない。UNKNOWNでも通常の15:20 SOR MARKET DAY intent→最初の15:20–15:25 actual trade→valid exact15:30 auction→fail-closedを維持した。未来Highによる認定0、Liquidity exception0。

Independent: **380,657 checks、mismatch 0**。Primary ranking/allocation/model/Movement実装をimportせず、Fractionで9 runsのcash/equity/BUY/SELL/marks/quantityを再計算。scalar score最大差=5.551e-16。canary **32/32 PASS**（要求30件を含む）。

共有provider aggregate/Frozen upstream/fitted coefficientsのI/O依存は残る。実装一致を独立外部source検証やproduction certificationとは呼ばない。actual source arrivalはUNKNOWNで、closed-minute bar_endという継承済みhistorical availability仮定を使用。

BUY raw×1.0005、SELL valid source×0.9995を各1回、commission0、旧roundtrip fee追加0、100-share lot、LONG cash-only。no-tradeではsame-session last actual markを保持し、SELL fill/cash releaseへ流用0。candidate/liquidity capsはBUY費用込みcash debitへ保守的に適用。

24 unique rolling fits、3 fixed arms×3 MAX=9測定runs。検証として同じ9 runsをdeterministic再実行し、別実装でも9 runsを照合した。追加model fit・profile refit・新arm・hyperparameter/feature/threshold sweep・result-based rescueはすべて0。v1及びFrozen Entry/EXIT変更0、Re-entry統合0、EXIT v4はRejected。

Source recoveryは既存79 Development datesのみ、新provider要求0・Protected body open0。Daily Va=NoneはUNKNOWNのまま扱い、価格/feature proxy作成0。初回materializationのnull parser停止はsource等値audit前段で修正し、attempt Evidenceをappend-only保存。policy/manifestは変更していない。

Safety全10項目false、orders0、main merge0、force push0、Claude0。North-Star未達を固定して終了し、このwork内で再調整や自動昇格を行わない。

全342 daily rowsと171 rolling-window rowsはDAILY_RETURN_SERIES.csv / ROLLING20_WINDOWS.csv。model hashes / source hashes / checkpoint actual receipts及びprivate replay記録を保持。
