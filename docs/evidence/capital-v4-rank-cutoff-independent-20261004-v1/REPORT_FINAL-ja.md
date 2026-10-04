# v4 Independent Rank-Cutoff Result

38 OOF Development sessions / 19 rolling20 windows。MAX3 ONLY / new fit=0。正式Capitalの選定・promotionは行わない。

| Metric | v4 Main/B_PLUS | S_ONLY | A_PLUS |
| --- | --- | --- | --- |
| funded N | 172 | 41 | 132 |
| avg funded/session | 4.5263 | 1.0789 | 3.4737 |
| daily geometric | 0.9526% | -0.2905% | 0.8769% |
| rolling20 median | 1.14584896x | 0.95660196x | 1.14348991x |
| rolling20 max | 1.28138096x | 1.02709288x | 1.27578953x |
| Final Equity | ¥1,433,740.25 | ¥895,356.10 | ¥1,393,406.80 |
| 2x hit | 0/19 (NO) | 0/19 (NO) | 0/19 (NO) |
| MaxDD | 11.5772% | 17.8438% | 9.8453% |
| utilization mean | 49.1563% | 11.6391% | 38.3660% |
| PF1 >=+1% rate | 30.2326% | 29.2683% | 31.0606% |
| Loser <=0% rate | 54.0698% | 63.4146% | 56.0606% |
| Tail <=-1% rate | 34.3023% | 36.5854% | 35.6061% |
| U3 capture | 73/297 = 24.5791% | 22/297 = 7.4074% | 70/297 = 23.5690% |
| U3 precision | 42.4419% | 53.6585% | 53.0303% |
| Medium capture | 31/127 = 24.4094% | 10/127 = 7.8740% | 24/127 = 18.8976% |
| Medium precision | 18.0233% | 24.3902% | 18.1818% |
| U5 capture | 42/170 = 24.7059% | 12/170 = 7.0588% | 46/170 = 27.0588% |
| U5 precision | 24.4186% | 29.2683% | 34.8485% |
| U10 capture | 23/67 = 34.3284% | 6/67 = 8.9552% | 24/67 = 35.8209% |
| U10 precision | 13.3721% | 14.6341% | 18.1818% |
| <2 contamination | 44.7674% | 39.0244% | 38.6364% |
| <3 contamination | 57.5581% | 46.3415% | 46.9697% |

Captureは全Winnerを分母、Precisionは各profileのfunded Nを分母とする。B_PLUSは保存済みv4 Mainと全ledger・保存済み指標が完全一致。Final Equityの丸め前値は¥1,433,740.25。

## A. Rank Quality Monotonicity

Candidate: `RANK_QUALITY_MONOTONIC_PARTIAL` / v4 Main funded: `RANK_QUALITY_MONOTONIC_PARTIAL`。

判定をprecommit: U5/U10 precision S>A>B、<2/Loser S<A<Bの4条件（隣接2組とも厳密）。全4=STRONG、一部=PARTIAL、0=NOT_MONOTONIC。空rankは条件PASSにしない。Candidate全1039件には15:20以降11件を含むがfundingは禁止。

Candidateのrealized品質はFrozen Entry→EXIT teacher（unresolved除外）。Fundedのrealized品質は各profileの実際のEXIT/EOD ledger。

### Candidate

| Metric | S | A | B |
| --- | --- | --- | --- |
| N | 43 | 154 | 297 |
| resolved | 43 | 154 | 295 |
| unresolved | 0 | 0 | 2 |
| U2 | 58.1395% | 55.8442% | 49.4949% |
| U3 | 51.1628% | 44.8052% | 31.9865% |
| Medium | 23.2558% | 14.2857% | 13.8047% |
| U5 | 27.9070% | 30.5195% | 18.1818% |
| U10 | 13.9535% | 14.9351% | 6.0606% |
| <1 | 18.6047% | 24.0260% | 30.6397% |
| <2 | 41.8605% | 44.1558% | 50.5051% |
| <3 | 48.8372% | 55.1948% | 68.0135% |
| realized mean | -0.7962% | 0.9356% | -0.1944% |
| median | -0.2047% | -0.3552% | -0.1000% |
| >=+1 | 30.2326% | 30.5195% | 25.7627% |
| >0 | 37.2093% | 43.5065% | 46.1017% |
| =0 | 0.0000% | 0.0000% | 0.0000% |
| <=0 | 62.7907% | 56.4935% | 53.8983% |
| <=-1 | 37.2093% | 35.7143% | 31.1864% |
| <=-3 | 18.6047% | 13.6364% | 12.5424% |

### S_ONLY_MAX3 funded

| Metric | S | A | B |
| --- | --- | --- | --- |
| N | 41 | 0 | 0 |
| resolved | 41 | 0 | 0 |
| unresolved | 0 | 0 | 0 |
| U2 | 60.9756% | — | — |
| U3 | 53.6585% | — | — |
| Medium | 24.3902% | — | — |
| U5 | 29.2683% | — | — |
| U10 | 14.6341% | — | — |
| <1 | 19.5122% | — | — |
| <2 | 39.0244% | — | — |
| <3 | 46.3415% | — | — |
| realized mean | -0.7809% | — | — |
| median | -0.2047% | — | — |
| >=+1 | 29.2683% | — | — |
| >0 | 36.5854% | — | — |
| =0 | 0.0000% | — | — |
| <=0 | 63.4146% | — | — |
| <=-1 | 36.5854% | — | — |
| <=-3 | 17.0732% | — | — |

### A_PLUS_MAX3 funded

| Metric | S | A | B |
| --- | --- | --- | --- |
| N | 30 | 102 | 0 |
| resolved | 30 | 102 | 0 |
| unresolved | 0 | 0 | 0 |
| U2 | 66.6667% | 59.8039% | — |
| U3 | 63.3333% | 50.0000% | — |
| Medium | 26.6667% | 15.6863% | — |
| U5 | 36.6667% | 34.3137% | — |
| U10 | 20.0000% | 17.6471% | — |
| <1 | 10.0000% | 19.6078% | — |
| <2 | 33.3333% | 40.1961% | — |
| <3 | 36.6667% | 50.0000% | — |
| realized mean | -0.1423% | 1.4596% | — |
| median | -0.1000% | -0.3153% | — |
| >=+1 | 33.3333% | 30.3922% | — |
| >0 | 43.3333% | 44.1176% | — |
| =0 | 0.0000% | 0.0000% | — |
| <=0 | 56.6667% | 55.8824% | — |
| <=-1 | 26.6667% | 38.2353% | — |
| <=-3 | 10.0000% | 11.7647% | — |

### B_PLUS_MAX3 funded

| Metric | S | A | B |
| --- | --- | --- | --- |
| N | 18 | 68 | 86 |
| resolved | 18 | 68 | 86 |
| unresolved | 0 | 0 | 0 |
| U2 | 72.2222% | 55.8824% | 51.1628% |
| U3 | 72.2222% | 47.0588% | 32.5581% |
| Medium | 38.8889% | 14.7059% | 16.2791% |
| U5 | 33.3333% | 32.3529% | 16.2791% |
| U10 | 16.6667% | 22.0588% | 5.8140% |
| <1 | 11.1111% | 20.5882% | 25.5814% |
| <2 | 27.7778% | 44.1176% | 48.8372% |
| <3 | 27.7778% | 52.9412% | 67.4419% |
| realized mean | 0.3883% | 2.5260% | -0.6161% |
| median | 0.0753% | -0.0314% | -0.1000% |
| >=+1 | 38.8889% | 36.7647% | 23.2558% |
| >0 | 50.0000% | 50.0000% | 41.8605% |
| =0 | 0.0000% | 0.0000% | 0.0000% |
| <=0 | 50.0000% | 50.0000% | 58.1395% |
| <=-1 | 27.7778% | 33.8235% | 36.0465% |
| <=-3 | 5.5556% | 8.8235% | 17.4419% |

Candidateでは<2 contaminationのみ単調。U5/U10はA>S>B、LoserはSが最も高く、期待された全品質単調性は成立しない。Main fundedではU5と<2は単調だが、U10はA>S>B、LoserはS=A<B（厳密なS<Aではない）。Main-funded Sは18件であり、S_ONLYの41件とは選択集合が異なる。

## B. Capture vs Precision

上のPrimary Tableが全4cohortのcapture/precisionを明示。A_PLUSはU5 46/170、U10 24/67でB_PLUSの42/170、23/67を上回る一方、Mediumは24/127でB_PLUS31/127を下回る。S_ONLYはU5 12/170、U10 6/67に留まり、coverageの低下は大きい。Profileごとにheld slots・cash・ロットが変わるためfunded集合は単純包含ではない。

## C. Entry→High Buckets

### S_ONLY_MAX3

| Potential | funded N | composition | realized mean | median | >=+1 | Loser <=0 | Tail <=-1 | actual PnL JPY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1-<2 | 8 | 19.5122% | -2.3322% | -0.3973% | 0.0000% | 87.5000% | 25.0000% | -77,303.80 |
| 2-<3 | 3 | 7.3171% | -0.1108% | 0.6449% | 33.3333% | 33.3333% | 33.3333% | -81.00 |
| 3-<4 | 7 | 17.0732% | -1.4714% | 1.9223% | 57.1429% | 42.8571% | 28.5714% | -37,799.95 |
| 4-<5 | 3 | 7.3171% | -0.1368% | -1.9549% | 33.3333% | 66.6667% | 66.6667% | -8.65 |
| 5-<10 | 6 | 14.6341% | 0.1027% | 0.0753% | 33.3333% | 50.0000% | 16.6667% | 1,237.25 |
| <1 | 8 | 19.5122% | -3.2115% | -1.8312% | 0.0000% | 100.0000% | 62.5000% | -72,442.80 |
| >=10 | 6 | 14.6341% | 3.7932% | 3.9580% | 66.6667% | 33.3333% | 33.3333% | 81,755.05 |

### A_PLUS_MAX3

| Potential | funded N | composition | realized mean | median | >=+1 | Loser <=0 | Tail <=-1 | actual PnL JPY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1-<2 | 28 | 21.2121% | -1.5439% | -0.9989% | 7.1429% | 78.5714% | 50.0000% | -167,397.40 |
| 2-<3 | 11 | 8.3333% | -0.4351% | 0.1776% | 18.1818% | 45.4545% | 27.2727% | -7,948.15 |
| 3-<4 | 17 | 12.8788% | 0.3300% | 1.6885% | 58.8235% | 35.2941% | 17.6471% | 10,187.45 |
| 4-<5 | 7 | 5.3030% | -0.4263% | -0.9793% | 28.5714% | 57.1429% | 42.8571% | -10,215.05 |
| 5-<10 | 22 | 16.6667% | 1.5025% | 0.5058% | 45.4545% | 36.3636% | 13.6364% | 81,658.90 |
| <1 | 23 | 17.4242% | -1.9903% | -2.0672% | 0.0000% | 91.3043% | 65.2174% | -135,413.45 |
| >=10 | 24 | 18.1818% | 8.4466% | 5.3751% | 62.5000% | 33.3333% | 25.0000% | 622,534.50 |

### B_PLUS_MAX3

| Potential | funded N | composition | realized mean | median | >=+1 | Loser <=0 | Tail <=-1 | actual PnL JPY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1-<2 | 39 | 22.6744% | -0.7326% | -0.5343% | 7.6923% | 76.9231% | 35.8974% | -72,166.70 |
| 2-<3 | 22 | 12.7907% | -1.0283% | 0.2909% | 27.2727% | 40.9091% | 27.2727% | -53,520.55 |
| 3-<4 | 18 | 10.4651% | 0.4339% | 1.6643% | 55.5556% | 27.7778% | 5.5556% | -315.15 |
| 4-<5 | 13 | 7.5581% | 0.1947% | 0.8337% | 38.4615% | 23.0769% | 23.0769% | 8,570.60 |
| 5-<10 | 19 | 11.0465% | 1.9390% | 1.9786% | 68.4211% | 21.0526% | 15.7895% | 80,292.05 |
| <1 | 38 | 22.0930% | -2.3387% | -1.9900% | 0.0000% | 92.1053% | 65.7895% | -225,918.05 |
| >=10 | 23 | 13.3721% | 9.5070% | 10.0503% | 65.2174% | 30.4348% | 30.4348% | 696,798.05 |

## D. Empty Slot / Opportunity Cost

Regular minute-samples:540<=minute<690 または750<=minute<930、各snapshotはSELL/Entry処理後。各38 sessions ×330=12,540 samples。unused sessionは「1 sample以上で保有<3」なので全profile38件。Peak<3のsession数とは異なる。

| Metric | B_PLUS_MAX3 | S_ONLY_MAX3 | A_PLUS_MAX3 |
| --- | --- | --- | --- |
| rank_cutoff_reject_N | 0 | 451 | 297 |
| sessions_with_unused_MAX3_slot | 38 | 38 | 38 |
| minute positions=0 | 1781 | 9203 | 2927 |
| minute positions=1 | 802 | 2883 | 2876 |
| minute positions=2 | 2496 | 393 | 3865 |
| minute positions=3 | 7461 | 61 | 2872 |

### U5

| Opportunity | B_PLUS_MAX3 | S_ONLY_MAX3 | A_PLUS_MAX3 |
| --- | --- | --- | --- |
| later_arrived_slot_free_N | 70 | 169 | 123 |
| later_arrived_slot_occupied_N | 100 | 1 | 47 |
| missed_cutoff_N | 0 | 101 | 54 |
| missed_MAX3_N | 66 | 0 | 11 |
| HELD_SLOT_BLOCKED_WINNER_N | 66 | 0 | 11 |

### U10

| Opportunity | B_PLUS_MAX3 | S_ONLY_MAX3 | A_PLUS_MAX3 |
| --- | --- | --- | --- |
| later_arrived_slot_free_N | 34 | 67 | 52 |
| later_arrived_slot_occupied_N | 33 | 0 | 15 |
| missed_cutoff_N | 0 | 41 | 18 |
| missed_MAX3_N | 21 | 0 | 5 |
| HELD_SLOT_BLOCKED_WINNER_N | 21 | 0 | 5 |

Winner arrivalは15:20前Entryのbatch直前（due SELL後、BUY前）。初回batchも含む。occupied=既存3保有、free=0–2保有。HELD_SLOT_BLOCKEDはcapacity rejectかつbatch内先頭3 eligible以内で既存保有あり。Heldを外した仮想selection可能性のみで、約定可能性やreplacementを主張しない。未来結果をBUY/position replacementへ戻していない。

### S_ONLY_MAX3 reject reasons

| Reason | N |
| --- | --- |
| CAPITAL_EOD_ENTRY_CUTOFF | 11 |
| CASH_OR_LOT_CONSTRAINED | 1 |
| FUNDED | 41 |
| MAX_POSITION_CAP | 1 |
| RANK_CUTOFF_S_ONLY | 451 |
| UPWARD_BELOW_BASELINE | 534 |

U5 missed: {"RANK_CUTOFF_S_ONLY": 101, "UPWARD_BELOW_BASELINE": 57} / U10 missed: {"RANK_CUTOFF_S_ONLY": 41, "UPWARD_BELOW_BASELINE": 20}

### A_PLUS_MAX3 reject reasons

| Reason | N |
| --- | --- |
| CAPITAL_EOD_ENTRY_CUTOFF | 11 |
| CASH_OR_LOT_CONSTRAINED | 9 |
| FUNDED | 132 |
| MAX_POSITION_CAP | 56 |
| RANK_CUTOFF_A_PLUS | 297 |
| UPWARD_BELOW_BASELINE | 534 |

U5 missed: {"CASH_OR_LOT_CONSTRAINED": 2, "MAX_POSITION_CAP": 11, "RANK_CUTOFF_A_PLUS": 54, "UPWARD_BELOW_BASELINE": 57} / U10 missed: {"MAX_POSITION_CAP": 5, "RANK_CUTOFF_A_PLUS": 18, "UPWARD_BELOW_BASELINE": 20}

### B_PLUS_MAX3 reject reasons

| Reason | N |
| --- | --- |
| CAPITAL_EOD_ENTRY_CUTOFF | 11 |
| CASH_OR_LOT_CONSTRAINED | 31 |
| FUNDED | 172 |
| MAX_POSITION_CAP | 291 |
| UPWARD_BELOW_BASELINE | 534 |

U5 missed: {"CASH_OR_LOT_CONSTRAINED": 5, "MAX_POSITION_CAP": 66, "UPWARD_BELOW_BASELINE": 57} / U10 missed: {"CASH_OR_LOT_CONSTRAINED": 3, "MAX_POSITION_CAP": 21, "UPWARD_BELOW_BASELINE": 20}

## E. Economic / Capital

各profile dailyとrolling20の全データは `DAILY.csv` / `ROLLING20.csv`、minute asset curveはPrivate ZIPの各`*_CURVE.jsonl.gz`。

| Metric | B_PLUS_MAX3 | S_ONLY_MAX3 | A_PLUS_MAX3 |
| --- | --- | --- | --- |
| arithmetic_mean_daily_return | 1.0224% | -0.2818% | 0.9457% |
| median_daily_return | 0.1930% | 0.0000% | 0.2256% |
| utilization_median | 58.6366% | 0.0000% | 37.4593% |
| time_utilization_ge80 | 0.0000% | 0.0000% | 0.0000% |
| time_utilization_ge90 | 0.0000% | 0.0000% | 0.0000% |
| cash_minimum | 214,408.85 | 220,241.25 | 221,811.10 |
| turnover_cash_jpy | 89,919,260.65 | 28,487,845.20 | 79,986,183.30 |
| capital_recycling_used_jpy | 7,020,365.35 | 680,968.20 | 5,187,344.10 |
| maximum_20_session_amount | 1,281,380.96 | 1,027,092.88 | 1,275,789.53 |
| daily_sign_counts | {'negative': 17, 'positive': 20, 'zero': 1} | {'negative': 12, 'positive': 9, 'zero': 17} | {'negative': 14, 'positive': 23, 'zero': 1} |
| session_max_concurrent_counts | {'0': 1, '1': 0, '2': 0, '3': 37} | {'0': 17, '1': 12, '2': 7, '3': 2} | {'0': 1, '1': 3, '2': 7, '3': 27} |
| rolling20_minimum | 1.08669814x | 0.90607215x | 1.06139662x |
| rolling20_arithmetic_mean | 1.16573674x | 0.96551955x | 1.15209673x |

全profile rolling20 valid19 / 2x0 / earliest2xなし。¥1m→20日中央値: S_ONLY_MAX3 ¥956,601.96、A_PLUS_MAX3 ¥1,143,489.91、B_PLUS_MAX3 ¥1,145,848.96。

### Thin Liquidity (diagnostic-only)

Hard Reject0 / position-size cap0 / eligibility・score・quantityへのLiquidity使用0。

### S_ONLY_MAX3

| Historical status | funded N | U5 composition | U10 composition | PF1 | Loser | actual PnL |
| --- | --- | --- | --- | --- | --- | --- |
| EXTREME_ILLIQUIDITY_REJECT | 7 | 42.8571% | 28.5714% | 14.2857% | 85.7143% | -62,102.10 |
| LIQUIDITY_ELIGIBLE | 34 | 26.4706% | 11.7647% | 32.3529% | 58.8235% | -42,541.80 |
| LIQUIDITY_UNKNOWN | 0 | — | — | — | — | 0.00 |

### A_PLUS_MAX3

| Historical status | funded N | U5 composition | U10 composition | PF1 | Loser | actual PnL |
| --- | --- | --- | --- | --- | --- | --- |
| EXTREME_ILLIQUIDITY_REJECT | 22 | 59.0909% | 40.9091% | 54.5455% | 45.4545% | 247,407.45 |
| LIQUIDITY_ELIGIBLE | 110 | 30.0000% | 13.6364% | 26.3636% | 58.1818% | 145,999.35 |
| LIQUIDITY_UNKNOWN | 0 | — | — | — | — | 0.00 |

### B_PLUS_MAX3

| Historical status | funded N | U5 composition | U10 composition | PF1 | Loser | actual PnL |
| --- | --- | --- | --- | --- | --- | --- |
| EXTREME_ILLIQUIDITY_REJECT | 38 | 26.3158% | 21.0526% | 28.9474% | 52.6316% | 132,861.40 |
| LIQUIDITY_ELIGIBLE | 134 | 23.8806% | 11.1940% | 30.5970% | 54.4776% | 300,878.85 |
| LIQUIDITY_UNKNOWN | 0 | — | — | — | — | 0.00 |

## F. Identity / Integrity

B_PLUS identity PASS / independent mismatch0 (196,874 checks) / opportunity追加5 checks mismatch0 / canary51 PASS、fail0。

Primary3 replay + Independent Fraction3 replay + deterministic canary3 replay + same-Entry causal mutation2 mini replay。同じ診断profileのresult-based rerun/retuneは0。v4 Main・Control・MAX4/MAX5 replay0。新fit0。Frozen score/ML/rank/H2/H3/H5/Entry/EXIT/accounting変更0。

Future EXITの変更は現在Entryのdecision不変を検証。実際のfuture SELL時刻・価格を変更すると後続Entryのcash/slotsは合法的に変わるため、全session decision不変とは主張しない。MTMはfillでもcash releaseでもなく、全cash変化を実BUY/SELL ledgerで検証。

PrecommitされたPrimary/Independent/analysis/canary codeはhash不変。後追加のopportunity補助コードv1には構文上の空白欠落があり実行前に失敗。append-onlyでv1を保持し、audit_opportunity_v2.pyを追加して同じ独立ledgerを監査、追加replay0/mismatch0。売買・モデル・threshold・結果の変更0。

Frozen sources: `SOURCE_HASHES.json`。Model/score identity: `V4_IDENTITY_FREEZE.json`。Code pin/config: `CODE_PRECOMMIT.json` / `DIAGNOSTIC_CONFIG.json`。Actual GitHub receipts: `receipts/`、最終HEAD/treeは `CHECKPOINT_INDEX.json` にpostcommit GETで追記。

Safety全false: {"automaticPromotionAllowed": false, "brokerWriteAllowed": false, "excelOrderWriteAllowed": false, "executionAllowed": false, "liveTradingAllowed": false, "paperTradingAllowed": false, "productionReady": false, "productionUpdateAllowed": false, "rssOrderFunctionAllowed": false, "transmitted": false}。orders0/main merge0/force push0/new provider0/Claude0/retune0/promotion0。

`ITERATIVE_DEVELOPMENT_EVIDENCE`。58 supplied Development sessionsは既に複数cycleの判断に使用されており、反復によるoverfit riskがある。fresh/OOS成績ではない。Protected/Holdout/Fresh/Validation/OOS/Prospective開封0。productionReady=false。

## Conclusions / STOP

S_ONLYは少数化しUpward precisionはB_PLUSより高いが、最高品質とは言えない。Loser63.4146%、日次幾何−0.2905%、Final¥895,356.10。

A_PLUSはBig/Megaのcaptureとprecision、低upside contaminationでB_PLUSより良い。一方Medium coverage低下、Loser56.0606%・Tail35.6061%はB_PLUSより悪く、日次幾何+0.8769%・Final¥1,393,406.80も下回る。上方向の品質改善がLoser抑制へ一貫して波及した証拠はない。

B_PLUSはv4 Mainを完全再現。S>A>Bの全品質単調性は不成立（PARTIAL）。3軸QUALITY/COVERAGE/CAPITALにtradeoffがあり、正式winnerや次のCapitalは選ばない。

結果を固定しSTOP。threshold/rank/ML/model/Movement/Liquidity/MAX/Entry/EXIT変更0。次の判断はユーザーへ返す。
