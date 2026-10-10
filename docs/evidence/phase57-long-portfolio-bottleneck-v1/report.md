# Phase57 LONG Portfolio Bottleneck Diagnostic
Historical / Development / IN-SAMPLE / Outcome-exposed. NOT validated. Source head: 2c9d82b01032a1c49a1de589438e35a93b8a271f
No Selector, Entry, EXIT, sizing, threshold or allocation changes. All 277 identities retained. Common173 is a hindsight completeness-selected opportunity subset, of which Equal accepted166. These are observed-price reference replays, not executable-fill or full277 performance claims. Full277 equity remains unresolved. Future labels/extrema/removal sets below are evaluator-only.
## 1. Coverage

| Exclusive excluded reason | N |
| --- | --- |
| MISSING_BAR_BEFORE_LONG_EXIT | 65 |
| NO_REMAINING_REGULAR_BAR | 20 |
| LONG_EXIT_RESOLVED_OTHER_COMPARISON_ARM_CENSORED | 19 |

65 missing-path cases do not establish missing-data versus no-trade causality. 20 have no remaining regular bar. 19 already resolve the selected LONG exit but fail a different comparison arm: inherited four-arm common coverage is stricter than chosen-exit coverage. Unresolved LONG exits85; missing entry prices0. Overlapping late-session flags37; auction-window flags14, not proven auction-caused gaps.

| Entry time JST | Included | Excluded |
| --- | --- | --- |
| 09:30 | 62 | 10 |
| 10:00 | 31 | 13 |
| 10:30 | 15 | 9 |
| 11:00 | 10 | 7 |
| 11:30 | 15 | 10 |
| 13:00 | 16 | 7 |
| 13:30 | 11 | 7 |
| 14:00 | 10 | 4 |
| 14:30 | 3 | 9 |
| 15:00 | 0 | 28 |


| Coverage | N | Mean E[L] | Mean selector score | Mean rank | 30m label N | +1 hits | +2 hits | +3 hits | +5 hits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXCLUDED | 104 | 2.46 | 117.47 | 1.19 | 23 | 19 | 15 | 9 | 5 |
| INCLUDED | 173 | 2.43 | 115.73 | 1.23 | 158 | 137 | 117 | 86 | 51 |

Systematic entry-time bias is clear: all28 15:00 entries excluded; 14:30 only3/12 included. Outcome-bias direction is unknown: labels exist for158/173 versus23/104, so observable excluded outcomes cannot represent all104. diagnostic.json includes all277 rows, per-session/symbol/time/cohort cross-tabs and separate included/excluded feature distributions; no imputation.
## 2. Winner concentration and cash-ledger stress

| Sensitivity | Final JPY | Return % | DD % | PF | Avg JPY | Median JPY | Win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FULL | 1,230,530.70 | 23.05 | 20.17 | 1.28 | 1,388.74 | -185.57 | 45.18 |
| EXCLUDE_TOP1_TRADE | 1,133,503.35 | 13.35 | 20.17 | 1.16 | 809.11 | -184.00 | 44.85 |
| EXCLUDE_TOP1_SYMBOL | 921,445.63 | -7.86 | 25.27 | 0.88 | -549.33 | -159.75 | 47.55 |
| EXCLUDE_TOP3_TRADES | 1,053,943.17 | 5.39 | 20.28 | 1.07 | 330.94 | -169.60 | 44.79 |
| EXCLUDE_TOP3_SYMBOLS | 802,946.88 | -19.71 | 27.84 | 0.69 | -1,427.92 | -487.38 | 46.38 |
| WINSORIZED_POSITIVE_P95_ADDITIVE_ONLY | 1,183,310.62 | 18.33 | 20.29 | 1.22 | 1,104.28 | -185.57 | 45.18 |

Top profit symbol89180 contributes334,449.55 JPY over22 accepted trades (145.1% of net profit). Static subtraction leaves−103,918.85 JPY; cash-ledger replay excluding the whole symbol leaves−78,554.375 JPY because later sizing and acceptance change. Top trade is a DIFFERENT symbol90730: Dec30 10:00→11:00,300 shares, entry1101, exit1402, notional330300, PnL90134.85. Removing one trade therefore understates repeated-symbol dependency.
Removal sets are fixed once from baseline, not repeatedly optimized. They are hindsight stress tests, not tradable exclusion policies. Positive-PnL95% winsorization scales additive contribution curves, leaves losses unchanged, and is NOT a self-financing, lot-compliant replay.

| 89180 entry JST | Exit JST | Entry | Shares | Capital JPY | Exit price | Reason | PnL JPY | MFE % | MAE % | Bars | Rank | Selector score | E[L] | Cohort | Recovered |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-09-19T10:30:00+09:00 | 2024-09-19T11:30:00+09:00 | 7 | 48000 | 336,000.00 | 8.0 | FIXED12_CAP | 47,832.00 | 14.29 | 0.00 | 12 | 1 | 171.31 | 3.20 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-09-25T13:30:00+09:00 | 2024-09-25T14:30:00+09:00 | 7 | 50400 | 352,800.00 | 8.0 | FIXED12_CAP | 50,223.60 | 14.29 | 0.00 | 12 | 1 | 149.67 | 2.94 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-10-08T10:00:00+09:00 | 2024-10-08T11:00:00+09:00 | 7 | 52400 | 366,800.00 | 8.0 | FIXED12_CAP | 52,216.60 | 14.29 | 0.00 | 12 | 1 | 109.60 | 2.37 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-10-28T14:00:00+09:00 | 2024-10-28T15:00:00+09:00 | 7 | 52300 | 366,100.00 | 7.0 | FIXED12_CAP | -183.05 | 14.29 | 0.00 | 12 | 1 | 168.69 | 3.17 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-10-29T09:30:00+09:00 | 2024-10-29T10:30:00+09:00 | 7 | 52300 | 366,100.00 | 8.0 | FIXED12_CAP | 52,116.95 | 14.29 | 0.00 | 12 | 1 | 170.07 | 3.18 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-10-31T09:30:00+09:00 | 2024-10-31T10:30:00+09:00 | 7 | 52900 | 370,300.00 | 7.0 | FIXED12_CAP | -185.15 | 14.29 | 0.00 | 12 | 1 | 169.10 | 3.17 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-11-06T13:00:00+09:00 | 2024-11-06T14:00:00+09:00 | 7 | 51400 | 359,800.00 | 7.0 | FIXED12_CAP | -179.90 | 14.29 | 0.00 | 12 | 1 | 145.68 | 2.89 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-11-07T09:30:00+09:00 | 2024-11-07T10:30:00+09:00 | 7 | 51400 | 359,800.00 | 7.0 | FIXED12_CAP | -179.90 | 14.29 | 0.00 | 12 | 1 | 168.46 | 3.17 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-11-15T11:00:00+09:00 | 2024-11-15T13:00:00+09:00 | 8 | 42800 | 342,400.00 | 8.0 | FIXED12_CAP | -171.20 | 12.50 | 0.00 | 12 | 1 | 98.44 | 2.20 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-11-21T10:00:00+09:00 | 2024-11-21T11:00:00+09:00 | 8 | 44200 | 353,600.00 | 8.0 | FIXED12_CAP | -176.80 | 12.50 | 0.00 | 12 | 1 | 147.51 | 2.91 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-11-22T11:00:00+09:00 | 2024-11-22T13:00:00+09:00 | 8 | 43800 | 350,400.00 | 8.0 | FIXED12_CAP | -175.20 | 12.50 | 0.00 | 12 | 1 | 98.62 | 2.20 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-11-25T10:00:00+09:00 | 2024-11-25T11:00:00+09:00 | 8 | 43600 | 348,800.00 | 9.0 | FIXED12_CAP | 43,425.60 | 12.50 | 0.00 | 12 | 1 | 149.18 | 2.93 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-11-26T09:30:00+09:00 | 2024-11-26T10:30:00+09:00 | 8 | 47400 | 379,200.00 | 8.0 | FIXED12_CAP | -189.60 | 12.50 | 0.00 | 12 | 1 | 147.61 | 2.91 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-11-27T09:30:00+09:00 | 2024-11-27T10:30:00+09:00 | 8 | 47700 | 381,600.00 | 8.0 | FIXED12_CAP | -190.80 | 12.50 | 0.00 | 12 | 1 | 144.45 | 2.87 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-11-28T10:00:00+09:00 | 2024-11-28T11:00:00+09:00 | 8 | 47900 | 383,200.00 | 8.0 | FIXED12_CAP | -191.60 | 12.50 | 0.00 | 12 | 1 | 97.69 | 2.19 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-12-09T11:30:00+09:00 | 2024-12-09T13:30:00+09:00 | 8 | 47700 | 381,600.00 | 9.0 | FIXED12_CAP | 47,509.20 | 12.50 | 0.00 | 12 | 2 | 99.31 | 2.17 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-12-19T10:30:00+09:00 | 2024-12-19T11:30:00+09:00 | 8 | 51200 | 409,600.00 | 8.0 | FIXED12_CAP | -204.80 | 12.50 | 0.00 | 12 | 1 | 96.47 | 2.17 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-12-24T11:00:00+09:00 | 2024-12-24T13:00:00+09:00 | 8 | 46800 | 374,400.00 | 8.0 | FIXED12_CAP | -187.20 | 12.50 | 0.00 | 12 | 1 | 97.27 | 2.18 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-12-25T09:30:00+09:00 | 2024-12-25T10:30:00+09:00 | 8 | 46500 | 372,000.00 | 8.0 | FIXED12_CAP | -186.00 | 12.50 | 0.00 | 12 | 2 | 145.62 | 2.86 | A_FIRST_BAR_NON_ADVERSE | False |
| 2024-12-26T13:30:00+09:00 | 2024-12-26T14:30:00+09:00 | 8 | 44100 | 352,800.00 | 9.0 | FIXED12_CAP | 43,923.60 | 12.50 | 0.00 | 12 | 1 | 99.96 | 2.22 | A_FIRST_BAR_NON_ADVERSE | False |
| 2025-01-07T11:30:00+09:00 | 2025-01-07T13:30:00+09:00 | 8 | 49400 | 395,200.00 | 8.0 | FIXED12_CAP | -197.60 | 0.00 | -12.50 | 12 | 1 | 110.94 | 2.39 | B_ADVERSE_RECLAIM_BY_BAR5 | True |
| 2025-01-08T11:30:00+09:00 | 2025-01-08T13:30:00+09:00 | 8 | 49800 | 398,400.00 | 8.0 | FIXED12_CAP | -199.20 | 0.00 | -12.50 | 12 | 1 | 110.52 | 2.39 | A_FIRST_BAR_NON_ADVERSE | False |

Exact first-bar close, defensive/reclaim transitions and every continuation bar are retained in diagnostic.json. MFE/MAE in the table stop at actual exit; fixed-window extrema are separately retained.
## 3. Drawdown
Peak 2024-12-19T10:45:00+09:00 equity 1,281,228.85; trough 2024-12-26T09:55:00+09:00 equity 1,022,815.75; decline 258,413.10 JPY / 20.17%. Recovery: none within observed window.
Realized ledger change -207,213.10; unrealized change -51,200.00. The latter is loss of peak unrealized profit, not an assertion of a −51,200 open loss at trough. All equity points reconstruct from individual positions, max error 4.66e-10 JPY.

| Position | Realized change | Unrealized change | Total DD contribution |
| --- | --- | --- | --- |
| 2024-12-25|2024-12-25T09:30:00+09:00|57590 | -87,385.30 | 0.00 | -87,385.30 |
| 2024-12-19|2024-12-19T10:30:00+09:00|89180 | -102.40 | -51,200.00 | -51,302.40 |
| 2024-12-20|2024-12-20T09:30:00+09:00|57590 | -45,805.20 | 0.00 | -45,805.20 |
| 2024-12-20|2024-12-20T13:00:00+09:00|95620 | -41,174.80 | 0.00 | -41,174.80 |
| 2024-12-24|2024-12-24T10:30:00+09:00|87830 | -17,182.50 | 0.00 | -17,182.50 |
| 2024-12-24|2024-12-24T09:30:00+09:00|49350 | -9,644.75 | 0.00 | -9,644.75 |
| 2024-12-24|2024-12-24T11:00:00+09:00|31130 | -8,987.00 | 0.00 | -8,987.00 |
| 2024-12-26|2024-12-26T09:30:00+09:00|66960 | -4,153.20 | 0.00 | -4,153.20 |
| 2024-12-25|2024-12-25T11:00:00+09:00|31850 | -1,768.00 | 0.00 | -1,768.00 |
| 2024-12-23|2024-12-23T09:30:00+09:00|57590 | -190.80 | 0.00 | -190.80 |
| 2024-12-24|2024-12-24T11:00:00+09:00|89180 | -187.20 | 0.00 | -187.20 |
| 2024-12-25|2024-12-25T09:30:00+09:00|89180 | -186.00 | 0.00 | -186.00 |
| 2024-12-26|2024-12-26T09:30:00+09:00|57590 | -85.50 | 0.00 | -85.50 |
| 2024-12-23|2024-12-23T13:30:00+09:00|67210 | 2,909.35 | 0.00 | 2,909.35 |
| 2024-12-19|2024-12-19T13:00:00+09:00|73600 | 6,730.20 | 0.00 | 6,730.20 |

Largest loser57590 Dec25 lost87,385.30 JPY (33.82% of DD):17→13 within3 bars,21,800 shares,370,600 JPY notional. Max concurrent during DD 2; peak utilization 66.63%; sample-mean utilization 11.00% (not time-weighted). Consecutive losing exits 8; losing sessions during episode 2; full-window losing-session streak 4. All held IDs retained, including zero contribution.

| DD hypothesis | Evidence / limitation |
| --- | --- |
| A Single catastrophic loser | Material33.82%, insufficient to explain allDD |
| B Multiple correlated losers | Several losses observed, including repeated57590; correlation not established |
| C Excess sizing | Large notional amplifies loss; Rank adds30,464.60 JPY loss to worst trade; optimal size unknown |
| D High concurrency | At most2 in DD; concurrency limit not binding |
| E EXIT latency | Loss occurs within3 bars; no supported counterfactual safer fill/threshold |
| F Entry quality | Large loser E[L]=3.0767; predictive opportunity is not downside protection |
| G Market regime | INCONCLUSIVE: no aligned broad-market evidence |
| H Other | 51,200 JPY unrealized-profit reversal plus repeated realized losses |

## 4. Selector attribution

| Group | Opportunities | Accepted | Avg JPY | Avg unit % | PF | Win % | <=−10% N |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 137 | 131 | 1,814.89 | 0.56 | 1.35 | 44.27 | 4 |
| 2 | 32 | 31 | -125.98 | 0.00 | 0.97 | 48.39 | 0 |
| 3 | 4 | 4 | -828.70 | -0.13 | 0.84 | 50.00 | 0 |

Rank4/5:0 observations. Rank1>2>3 average JPY and unit return is descriptively monotonic, but rank3 has only4 observations; conditioned on Entry and included coverage, this cannot establish general ranking calibration.

| Group | Opportunities | Accepted | Avg JPY | Avg unit % | PF | Win % | <=−10% N |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | 44 | 41 | -1,297.70 | -0.33 | 0.69 | 43.90 | 0 |
| Q2 | 43 | 42 | 1,906.28 | 0.50 | 1.67 | 42.86 | 0 |
| Q3 | 43 | 43 | -1,290.97 | -0.33 | 0.78 | 44.19 | 1 |
| Q4 | 43 | 40 | 6,479.61 | 1.98 | 1.90 | 50.00 | 3 |

Selector-score quartile mean return is nonmonotonic. Quartile boundaries and all opportunity-tier results are in diagnostic.json. Opportunity tier is a future 30m high label, evaluator-only.

| Group | Opportunities | Accepted | Avg JPY | Avg unit % | PF | Win % | <=−10% N |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 21 | 21 | -14,514.98 | -4.18 | 0.00 | 4.76 | 2 |
| 1 | 20 | 18 | -8,987.43 | -2.51 | 0.05 | 22.22 | 1 |
| 2 | 31 | 30 | -5,467.69 | -1.50 | 0.08 | 23.33 | 0 |
| 3 | 35 | 34 | 3,096.45 | 0.82 | 2.08 | 70.59 | 1 |
| 5 | 51 | 49 | 13,801.98 | 4.09 | 18.85 | 63.27 | 0 |
| UNKNOWN | 15 | 14 | 5,683.81 | 1.56 | 2.60 | 57.14 | 0 |

## 5. Entry attribution

| Group | Opportunities | Accepted | Avg JPY | Avg unit % | PF | Win % | <=−10% N |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | 44 | 40 | -513.20 | -0.12 | 0.86 | 45.00 | 0 |
| Q2 | 43 | 43 | 919.70 | 0.22 | 1.26 | 39.53 | 0 |
| Q3 | 43 | 43 | -1,255.35 | -0.31 | 0.79 | 44.19 | 1 |
| Q4 | 43 | 40 | 6,637.30 | 2.03 | 1.94 | 52.50 | 3 |


| E[L] quartile | Mean MFE % | Mean MAE % | Mean Equal weight | Mean Rank weight |
| --- | --- | --- | --- | --- |
| Q1 | 4.13 | -2.79 | 0.86 | 0.83 |
| Q2 | 5.39 | -2.84 | 0.88 | 0.87 |
| Q3 | 3.95 | -4.48 | 0.80 | 0.81 |
| Q4 | 9.24 | -3.78 | 0.83 | 0.88 |

MSH E[L] estimates ordinal30m opportunity class, not expected executable net return or risk-adjusted sizing utility. Quartile means are nonmonotonic. Q4 has3/40 accepted losses<=−10%; Q1 has1/40 net winners>=5%. Stronger Q4 aggregate does not prove calibrated sizing. Extrema use complete available Fixed12 reference window, not information used at entry.
## 6. EXIT attribution

| Reason | N | PnL JPY | Avg JPY | Median JPY | PF | Median MFE capture | Median giveback pp | Mean pre-exit MAE % | Worst JPY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BAR5_NO_RECLAIM | 19 | -246,243.75 | -12,960.20 | -10,973.05 | 0.00 | -3.00 | 3.85 | -5.74 | -41,174.80 |
| CALENDAR_SESSION_CAP | 1 | 12,822.50 | 12,822.50 | 12,822.50 | INF | 1.00 | -0.00 | -0.99 | 12,822.50 |
| FIXED12_CAP | 48 | 404,886.75 | 8,435.14 | -176.00 | 3.15 | 0.10 | 3.21 | -2.44 | -73,784.00 |
| TWO_LOWER_COMPLETED_CLOSES | 98 | 59,065.20 | 602.71 | 726.35 | 1.15 | 0.10 | 3.87 | -2.38 | -87,385.30 |

LONG vs Fixed under Equal: +9,945.10 JPY (+0.99451 initial-capital percentage points); DD20.1692% vs21.3741%, improvement1.205pp. Same166 accepted identities.115 exits earlier,0 later; mean release lead23.55 clock minutes including lunch. Cash releases166 both; same-timestamp recycling5 vs16. MFE-capture denominator is available Fixed12-window high; negative capture permitted.

| Opportunity MFE | Arm | N | Positive net | Net reaches level |
| --- | --- | --- | --- | --- |
| 3 | LONG | 96 | 63 | 29 |
| 3 | FIXED | 96 | 63 | 30 |
| 5 | LONG | 61 | 41 | 18 |
| 5 | FIXED | 61 | 40 | 20 |

BAR5 failure group loss−246,243.75 does not imply dropping those trades would recover this amount: reason is known only after entry. EXIT provides modest portfolio improvement; no evidence here establishes EXIT as the dominant bottleneck.
## 7. Allocation attribution

| Rank minus Equal term | JPY |
| --- | --- |
| commonWinnerEffectJpy | 39,180.90 |
| commonLoserEffectJpy | -30,561.10 |
| commonQuantityEffectJpy | 8,619.80 |
| rankOnlyPnlJpy | -22,893.60 |
| equalOnlyPnlJpy | 843.50 |
| rankMinusEqualJpy | -15,117.30 |

Exact identity: +8,619.80 common sizing effect −22,893.60 Rank-only PnL −843.50 Equal-only PnL = −15,117.30. Common resizing is net positive; changed accepted set dominates aggregate underperformance. Rank-only304A0 Dec30 loses23,223 JPY (Equal below-lot), Rank-only50280 Nov27 gains329.40 (Equal cash-blocked); Equal-only36960 Dec30 gains843.50 (Rank below-lot).
Worst size effect:57590 Dec25 weight0.5→0.6667, shares21800→29400, loss grows30,464.60. Winner89180 Dec9 weight0.5→0.3333 reduces gain15,438. These are material but do not reverse the positive common-set aggregate. Scores, lot rounding, cash and compounding jointly change acceptance. Identical event ordering rules eliminate ordering-policy differences; concurrency-limit rejections0.

| Capital metric | Equal | Rank |
| --- | --- | --- |
| averageUtilization | 0.08 | 0.08 |
| peakUtilization | 0.97 | 1.00 |
| idleCashRatio | 0.92 | 0.92 |
| maxConcurrent | 3.00 | 4.00 |
| averageConcurrent | 0.26 | 0.26 |
| averageLockedPurchaseNotionalJpy | 92,011.36 | 93,997.97 |
| grossTurnoverJpy | 116,136,700.00 | 117,791,200.00 |
| grossTurnoverTimesInitial | 116.14 | 117.79 |
| cashReleaseCount | 166.00 | 167.00 |
| sameTimestampRecyclingEntries | 5.00 | 5.00 |
| feesJpy | 28,969.30 | 29,386.60 |
| tradingMinutes | 24,120.00 | 24,120.00 |

Equal accepted166/rejected7 (6 below-lot,1 cash); Rank167/rejected6 (all below-lot). Average utilization8.26% vs8.41%, idle cash91.74% vs91.59%; max concurrency3 vs4. Low utilization is observed, but increasing exposure is not justified by these concentrated, outcome-exposed results.
## 8. Bottleneck ranking and ONE next action

| Component | Judgment | Observed magnitude | Uncertainty | Next test |
| --- | --- | --- | --- | --- |
| Data Coverage | BOTTLENECK_HIGH | 104/277 excluded;85 LONG unresolved; all28 15:00 excluded; full277 equity unknown | Performance direction of missing paths unknown; close marks are not fill proof | A: reconcile existing raw bar provenance/no-trade/session boundary and executable timing; preserve every277 identity |
| Capital Allocation | BOTTLENECK_MEDIUM | Rank−Equal−15,117; worst size shift−30,465; accepted-set delta dominates | Sizing optimum and causal score calibration not established | After coverage repair, frozen paired sizing calibration audit |
| Entry | BOTTLENECK_MEDIUM | Q4 has3/40 deep losers; quartile means nonmonotonic | Opportunity classifier is not sizing utility; no fair alternative tested | After coverage repair, predeclared calibration/tail analysis |
| EXIT | BOTTLENECK_MEDIUM | +9,945 JPY vsFixed; DD improves1.205pp; BAR5 losses−246,244 | Reason-conditioned groups not causal intervention; no safe fill counterfactual | After coverage repair, validate frozen exit before considering v2 |
| Selector | INCONCLUSIVE | Ranks1>2>3 means monotonic; rank3 N4, rank4/5 N0; score quartiles not monotonic | Entry/coverage conditioning and symbol concentration prevent broad conclusion | After coverage repair, frozen full-event ranking attribution |

Choose A ONLY: Coverage / execution semantics. This is the largest evidence bottleneck, not a claim of largest guaranteed PnL uplift. First audit existing caches to distinguish legitimate no-trade, missing data and session-boundary behavior, and remove unnecessary four-arm comparison censoring from descriptive chosen-exit coverage. Do not silently expand performance sample, invent fills, release unresolved cash, or retune a component. Any new execution contract needs separate versioned identity and paired replay. Fresh0; no Validation consumption. Selector/Entry/EXIT/Allocation remain fixed.
## Verification and safety
All nine safety flags false; providerRequests0; Fresh0; OOS0; component modifications0; no main merge. Sources and frozen hashes checked before replay; per-position curve and allocation-difference accounting reconcile; deterministic stress replay and evidence hashes tested. Detailed per-entry and position ledgers accompany this report.
