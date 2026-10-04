| Profile | 1日幾何平均 | rolling20中央値 | rolling20最大 | 200万円hit N/rate |
|---|---:|---:|---:|---:|
| MAX3 | -0.5659% | 0.864119x | 1.070988x | 0/19 / 0.00% |
| MAX4 | -0.5637% | 0.866410x | 1.070437x | 0/19 / 0.00% |
| MAX5 | -0.5760% | 0.863524x | 1.069153x | 0/19 / 0.00% |

**BEST DEVELOPMENT PROFILE: MAX4**

100万円 → 20-session中央値: **¥866,410**

100万円 → 選定profileの20-session最大: **¥1,070,437**

**2倍達成: NO**。全profile中の最高金額は **¥1,070,988（MAX3）**。

終了status: `CAPITAL_VNEXT_DEV_NORTHSTAR_MISS`。作成JST: 2026-10-04T14:35:57.217682+09:00

指定58 Development sessionsの最初20 sessionsをwarm-up、次38 sessionsを5-session block rolling-originで評価。各profileに19のrolling20 windowsが成立し、blockedは0。
rolling20は指定されたDevelopmentの20評価sessions。cohort外の2025-07-11/07-14は未評価で、0%へ補完していない。全ての連続したTSE営業日に対する成績や外部検証成績とは呼ばない。

profile選定はprecommit通り、2x hit rate→rolling20中央値→1日幾何平均→MaxDD→保有上限の順。今回はhit rateが全て0なので、中央値が最も高いMAX4を選定。最高windowだけを使ってprofileを選び直していない。

| Profile | 1日算術平均 | 1日中央値 | rolling20最小 | rolling20平均 | Final Equity | Total Return | MaxDD |
|---|---:|---:|---:|---:|---:|---:|---:|
| MAX3 | -0.5389% | -0.2776% | 0.773538x | 0.916723x | ¥806,009 | -19.3991% | 26.74% |
| MAX4 | -0.5362% | -0.1057% | 0.774579x | 0.916969x | ¥806,688 | -19.3312% | 26.73% |
| MAX5 | -0.5481% | -0.1357% | 0.771986x | 0.914566x | ¥802,916 | -19.7084% | 26.99% |

| Profile | utilization平均 / 中央値 | time≥80% / ≥90% | idle cash平均 | funded / rejected | cash最小 | 最大同時保有 | execution unresolved |
|---|---:|---:|---:|---:|---:|---:|---:|
| MAX3 | 39.97% / 39.96% | 0.00% / 0.00% | 60.03% | 135 / 904 | ¥166,142 | 3 | 0 |
| MAX4 | 40.95% / 40.12% | 4.93% / 0.00% | 59.05% | 149 / 890 | ¥122,669 | 4 | 0 |
| MAX5 | 41.19% / 41.66% | 6.31% / 0.12% | 58.81% | 154 / 885 | ¥83,001 | 5 | 0 |

| Profile | turnover cash | closed/cash-release N | recycled cash used | Frozen EXIT | EOD regular | EOD exact auction |
|---|---:|---:|---:|---:|---:|---:|
| MAX3 | ¥57,782,783 | 135 | ¥3,731,753 | 70 | 64 | 1 |
| MAX4 | ¥60,423,782 | 149 | ¥4,412,910 | 78 | 70 | 1 |
| MAX5 | ¥60,969,083 | 154 | ¥4,667,276 | 80 | 73 | 1 |

utilizationは9:00–11:30/12:30–15:30のminute durationで集計。昼休みを除く。turnoverはeffective cash debit+credit、recycled cashは当sessionの開始cashを使い切った後のconfirmed releaseからBUYに使用した金額。

| BigWinner5 scope | total | Liquidity eligible | Liquidity rejected | reject rate | rejected潜在値幅中央値 / 最大 |
|---|---:|---:|---:|---:|---:|
| all58 | 244 | 89 | 155 | 63.52% | +8.5080% / +44.5545% |
| OOF38 | 170 | 59 | 111 | 65.29% | +8.6221% / +44.5545% |

| OOF rank | N | BigWinner5 N | Winner rate | enrichment vs OOF baseline |
|---|---:|---:|---:|---:|
| S | 153 | 36 | 23.53% | 1.4381x |
| A | 137 | 43 | 31.39% | 1.9183x |
| B | 172 | 32 | 18.60% | 1.1371x |
| C | 577 | 59 | 10.23% | 0.6249x |

| Profile | funded Winner5 | capture rate | missed MAX | missed cash/lot | missed Liquidity | missed C | funded Winner10 diagnostic |
|---|---:|---:|---:|---:|---:|---:|---:|
| CAPITAL_VNEXT_MAX3 | 29 | 17.06% | 7 | 7 | 111 | 16 | 12 |
| CAPITAL_VNEXT_MAX4 | 30 | 17.65% | 2 | 11 | 111 | 16 | 12 |
| CAPITAL_VNEXT_MAX5 | 30 | 17.65% | 2 | 11 | 111 | 16 | 12 |

上表の潜在値幅はEntry raw referenceに対するstrictly-later/pre15:20 actual High。実現利益や約定可能な最大利益ではない。Liquidity gateをこの結果で緩めていない。

| Profile | LIMIT_UP_CONFIRMED | funded reaching / Frozen early EXIT / EOD intent | regular / auction / unexecuted | realized return | Winner5 overlap | LIMIT_UP_UNKNOWN funded |
|---|---:|---:|---:|---:|---:|---:|
| CAPITAL_VNEXT_MAX3 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | UNKNOWN | 0 | 135 |
| CAPITAL_VNEXT_MAX4 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | UNKNOWN | 0 | 149 |
| CAPITAL_VNEXT_MAX5 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | UNKNOWN | 0 | 154 |

authoritative price-limit/base-priceとcausal exchange/provider statusが収録されていないため、limit-upは全てUNKNOWN。confirmed N=0は実際のストップ高N=0を意味しない。UNKNOWNは通常の15:20 SOR MARKET DAY SELL→最初の15:20–15:25 actual trade→exact15:30 auction→fail-closedという同一経路で処理。未来Highによるlimit-up認定やLiquidity免除は0。

Frozen FIRST ENTRY v2/EXIT v3のファイルは変更0。Re-entry統合0、EXIT v4はRejected。P1 scoreをprobabilityと呼び替えず、旧4 quality fieldsの代理値は作成0。今回のmanifestは実在する27 numeric/7 categorical fieldsで固定し、未復元の旧P0 matrix列は追加していない。

source recoveryは既存Development cacheだけ。初回exportが最終cohort sessionを含まなかった24件は最初のportfolio result前にappend-only supplementへ収録し、全1600件のcurrent-session sourceを確認。score/X/past Liquidityは変更0、supplement labelは8個のtraining prefix外、追加fit0。Protected7/11のbodyは開いていない。

8 fits、1モデル、3固定profiles。hyperparameter/feature/liquidity/rank threshold sweepは全て0。broker commission0、BUY raw×1.0005とSELL valid source×0.9995を各1回、旧round-trip fee追加0、100-share lot、cash<0/SHORT/margin/leverageは0。actual arrivalはUNKNOWNで、historical source availabilityは閉じたminuteのbar_endという継承済み仮定。markをSELL fillやcash releaseへ流用0。

IndependentはPrimary logicをimportせずFractionで3 profilesを再計算し、101,008 checksでmismatch0。scalar model score差の最大は1.665e-16。要求22件を含む23 canaries PASS。共有provider cache/Frozen upstream/fitted coefficientsのI/O依存は残るため、実装一致を外部市場source独立性やproduction certificationとは呼ばない。

Safety全10項目false、orders0、main merge0、force push0、Claude0。Development feasibility readoutを固定して終了。North Starに届くための再調整や自動昇格は行わない。

詳細: `NORTH_STAR_REPORT.json` / `BIG_WINNER_PRESERVATION.json` / `LIMIT_UP_REPORT.json` / `MAX3_4_5_REPLAY.json` / `INDEPENDENT_AUDIT.json` / `FOCUSED_TEST_RESULTS.json`。全38 daily seriesと19 windowsは以下のCSV及びReplay JSONに保持。
