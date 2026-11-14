# Entry v2 — fixed-population comparison and coverage review

Primary fixed by selection dates: **RIDGE_FULL_QUALITY_1m**. ENTRY_DEVELOPMENT_INCONCLUSIVE.

All methods retain the same 2,155 evaluation Opportunities. No refit, inference, policy change or evaluation-based model selection occurs in this review. B2 preserves v1 timing/fill mechanics and is historical context; B0 is the fair mechanics-matched timing baseline.

## Data funnel

| Item | Count |
|---|---:|
| inputSessions | 144 |
| candidateSessions | 142 |
| evaluationManifestSessions | 59 |
| evaluationCandidateSessions | 58 |
| opportunitiesAll | 5375 |
| evaluationOpportunities | 2155 |
| patternRows | 160608 |
| v1EmptyAll | 600 |
| v2EmptyAll | 90 |
| evaluation1130 | 201 |
| evaluation1130EmptyV2 | 0 |
| frozenSelectorEvents | 7100 |

## Main methods

| Entry | BUY | No entry | +1 Capture | +2 Capture | +3 Capture | +4 Capture | +5 Capture | Median delay | Price improvement vs Selector |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B0_RETRY_1m | 1963 | 192 | 85.23 | 85.58 | 85.28 | 86.76 | 87.50 | 0.00 | -0.05 |
| B1_WAIT5_1m | 1899 | 256 | 75.20 | 75.24 | 73.19 | 74.82 | 75.98 | 5.00 | -0.15 |
| B1_WAIT15_1m | 1807 | 348 | 66.84 | 65.94 | 62.94 | 65.26 | 65.69 | 15.00 | -0.18 |
| B2_E5_V1_PRESERVED | 1645 | 510 | 72.66 | 73.15 | 71.75 | 76.10 | 74.51 | 0.00 | -0.05 |
| RIDGE_FULL_QUALITY_1m | 1020 | 1135 | 42.45 | 41.46 | 40.74 | 41.91 | 41.91 | 1.00 | -0.05 |

Capture uses the original fixed Selector session-end winner denominator; no-entry and unknown outcomes are not successes. Delay is session-active minutes. Price improvement is relative to the Selector reference, not automatically model alpha.

## 30 active-minute path / return / Hit

| Entry | BUY | Complete | Censored | Unavailable | MFE med | MAE med | MAE p5 | MaxDD med | MaxDD p5 | Net mean | Net med | Positive % | +1 Hit | +2 Hit | +3 Hit | +4 Hit | +5 Hit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0_RETRY_1m | 1963 | 1365 | 150 | 448 | 1.09 | -1.23 | -5.95 | -2.13 | -7.61 | -0.06 | -0.10 | 44.69 | 46.92 | 25.42 | 14.26 | 8.30 | 5.50 |
| B0_RETRY_5m | 1802 | 1350 | 132 | 320 | 1.11 | -1.20 | -6.09 | -2.12 | -7.63 | -0.07 | -0.10 | 46.07 | 48.95 | 26.25 | 14.48 | 8.55 | 5.66 |
| B1_WAIT10_1m | 1857 | 1337 | 144 | 376 | 0.95 | -1.14 | -5.19 | -1.99 | -6.82 | -0.03 | -0.10 | 44.50 | 43.67 | 23.21 | 13.73 | 8.78 | 5.98 |
| B1_WAIT10_5m | 1685 | 1320 | 121 | 244 | 0.94 | -1.14 | -5.31 | -2.02 | -7.04 | -0.01 | -0.10 | 44.47 | 45.22 | 24.39 | 14.30 | 9.14 | 6.29 |
| B1_WAIT15_1m | 1807 | 1327 | 137 | 343 | 0.91 | -1.12 | -5.06 | -1.96 | -6.67 | 0.03 | -0.10 | 42.88 | 41.89 | 22.91 | 14.00 | 8.63 | 5.98 |
| B1_WAIT15_5m | 1624 | 1291 | 112 | 221 | 0.92 | -1.08 | -5.14 | -2.01 | -6.72 | 0.05 | -0.10 | 43.07 | 43.41 | 24.20 | 14.90 | 9.36 | 6.47 |
| B1_WAIT30_1m | 1062 | 890 | 92 | 80 | 0.85 | -1.09 | -5.30 | -1.96 | -6.60 | -0.13 | -0.10 | 41.91 | 42.84 | 22.22 | 14.69 | 9.42 | 6.31 |
| B1_WAIT30_5m | 1062 | 890 | 92 | 80 | 0.85 | -1.09 | -5.30 | -1.96 | -6.60 | -0.13 | -0.10 | 41.91 | 42.84 | 22.22 | 14.69 | 9.42 | 6.31 |
| B1_WAIT5_1m | 1899 | 1343 | 143 | 413 | 1.00 | -1.18 | -5.61 | -2.04 | -7.13 | -0.05 | -0.10 | 43.04 | 44.81 | 23.38 | 14.43 | 8.37 | 5.63 |
| B1_WAIT5_5m | 1728 | 1337 | 123 | 268 | 1.01 | -1.17 | -5.69 | -2.06 | -7.14 | -0.03 | -0.10 | 43.83 | 47.22 | 24.88 | 15.39 | 8.91 | 5.96 |
| B2_E5_V1_PRESERVED | 1645 | 1243 | 132 | 270 | 1.10 | -1.21 | -6.16 | -2.14 | -7.59 | -0.07 | -0.10 | 44.57 | 48.81 | 26.14 | 14.41 | 8.51 | 5.17 |
| RIDGE_FULL_QUALITY_1m | 1020 | 695 | 88 | 237 | 1.12 | -1.11 | -5.86 | -2.01 | -7.36 | 0.02 | -0.10 | 47.34 | 47.25 | 25.39 | 14.51 | 8.92 | 6.18 |
| RIDGE_FULL_QUALITY_5m | 784 | 571 | 66 | 147 | 1.11 | -1.11 | -6.16 | -2.02 | -7.44 | 0.04 | -0.10 | 47.11 | 48.47 | 26.28 | 14.80 | 9.06 | 6.25 |
| RIDGE_FULL_STOP_1m | 435 | 242 | 59 | 134 | 0.92 | -0.89 | -4.17 | -1.63 | -6.46 | 0.37 | 0.05 | 50.83 | 40.69 | 21.15 | 12.41 | 8.97 | 6.44 |
| RIDGE_FULL_STOP_5m | 266 | 166 | 30 | 70 | 0.98 | -0.83 | -4.43 | -1.63 | -6.12 | 0.53 | 0.09 | 53.01 | 42.11 | 22.56 | 15.04 | 10.15 | 6.02 |
| RIDGE_NO_PREVIOUS_STOP_1m | 298 | 161 | 36 | 101 | 0.59 | -0.73 | -3.54 | -1.21 | -4.83 | 0.16 | -0.10 | 45.96 | 34.90 | 11.74 | 5.70 | 3.36 | 2.01 |
| RIDGE_NO_RECENT_STOP_1m | 361 | 201 | 42 | 118 | 0.80 | -0.79 | -4.01 | -1.51 | -6.67 | 0.42 | -0.10 | 46.27 | 39.61 | 19.11 | 12.74 | 9.42 | 6.65 |
| RIDGE_NO_SEQUENCE_STOP_1m | 415 | 227 | 47 | 141 | 1.01 | -0.84 | -4.48 | -1.63 | -6.29 | 0.50 | 0.01 | 50.22 | 42.17 | 21.93 | 12.77 | 8.92 | 5.78 |
| TREE_FULL_QUALITY_1m | 108 | 76 | 6 | 26 | 2.37 | -2.19 | -8.11 | -3.79 | -9.58 | 0.62 | 0.51 | 56.58 | 65.74 | 48.15 | 30.56 | 25.93 | 20.37 |
| TREE_FULL_QUALITY_5m | 84 | 64 | 4 | 16 | 2.29 | -2.16 | -8.80 | -3.79 | -9.79 | 0.53 | 0.16 | 53.12 | 66.67 | 52.38 | 29.76 | 26.19 | 23.81 |
| TREE_FULL_STOP_1m | 12 | 8 | 1 | 3 | 2.84 | -1.94 | -7.07 | -3.43 | -7.82 | 1.24 | 0.86 | 75.00 | 83.33 | 58.33 | 41.67 | 25.00 | 8.33 |
| TREE_FULL_STOP_5m | 7 | 6 | 1 | 0 | 3.79 | -0.95 | -7.61 | -3.43 | -8.40 | 1.50 | 1.23 | 66.67 | 85.71 | 57.14 | 57.14 | 42.86 | 14.29 |

Path and returns condition on complete observed source-slot coverage. Hit denominator is all BUY; rates are observed lower bounds, with unknown counts and upper bounds in review.json. A missing source minute is not certified as no trade. MaxDD is the confirmed chronological OHLC bound; intra-bar ordering remains unknown.

## 60 active-minute path / return / Hit

| Entry | BUY | Complete | Censored | Unavailable | MFE med | MAE med | MAE p5 | MaxDD med | MaxDD p5 | Net mean | Net med | Positive % | +1 Hit | +2 Hit | +3 Hit | +4 Hit | +5 Hit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0_RETRY_1m | 1963 | 1117 | 308 | 538 | 1.60 | -1.66 | -7.55 | -3.09 | -9.77 | -0.08 | -0.10 | 44.49 | 57.31 | 34.64 | 21.85 | 14.42 | 10.04 |
| B0_RETRY_5m | 1802 | 1117 | 277 | 408 | 1.60 | -1.67 | -7.80 | -3.08 | -9.83 | -0.10 | -0.10 | 45.57 | 59.43 | 36.07 | 22.42 | 15.04 | 10.27 |
| B1_WAIT10_1m | 1857 | 1099 | 290 | 468 | 1.35 | -1.59 | -7.35 | -2.89 | -9.52 | -0.14 | -0.21 | 43.31 | 53.26 | 31.66 | 21.11 | 14.16 | 9.59 |
| B1_WAIT10_5m | 1685 | 1099 | 253 | 333 | 1.35 | -1.57 | -7.57 | -2.92 | -9.58 | -0.15 | -0.21 | 42.95 | 54.90 | 32.82 | 21.96 | 14.78 | 10.27 |
| B1_WAIT15_1m | 1807 | 1090 | 278 | 439 | 1.40 | -1.49 | -6.87 | -2.82 | -9.57 | -0.09 | -0.10 | 44.13 | 51.80 | 31.88 | 20.86 | 13.95 | 9.63 |
| B1_WAIT15_5m | 1624 | 1083 | 244 | 297 | 1.36 | -1.48 | -6.87 | -2.84 | -9.60 | -0.11 | -0.10 | 44.14 | 53.63 | 33.19 | 21.92 | 14.96 | 10.65 |
| B1_WAIT30_1m | 1062 | 754 | 186 | 122 | 1.23 | -1.54 | -6.68 | -2.74 | -8.82 | -0.22 | -0.18 | 42.84 | 53.67 | 31.07 | 21.19 | 15.35 | 10.45 |
| B1_WAIT30_5m | 1062 | 754 | 186 | 122 | 1.23 | -1.54 | -6.68 | -2.74 | -8.82 | -0.22 | -0.18 | 42.84 | 53.67 | 31.07 | 21.19 | 15.35 | 10.45 |
| B1_WAIT5_1m | 1899 | 1099 | 292 | 508 | 1.53 | -1.64 | -7.47 | -2.96 | -9.64 | -0.15 | -0.10 | 44.13 | 55.03 | 32.70 | 21.75 | 14.48 | 9.90 |
| B1_WAIT5_5m | 1728 | 1109 | 258 | 361 | 1.51 | -1.62 | -7.52 | -2.94 | -9.79 | -0.14 | -0.10 | 44.18 | 57.00 | 34.32 | 23.21 | 15.10 | 10.42 |
| B2_E5_V1_PRESERVED | 1645 | 1018 | 275 | 352 | 1.59 | -1.66 | -7.79 | -3.06 | -9.76 | -0.12 | -0.11 | 45.09 | 59.15 | 36.05 | 22.37 | 15.38 | 10.03 |
| RIDGE_FULL_QUALITY_1m | 1020 | 554 | 172 | 294 | 1.54 | -1.51 | -7.58 | -2.83 | -9.53 | -0.03 | -0.10 | 46.57 | 57.16 | 34.41 | 22.16 | 13.92 | 10.39 |
| RIDGE_FULL_QUALITY_5m | 784 | 458 | 128 | 198 | 1.51 | -1.50 | -7.68 | -2.77 | -10.09 | -0.04 | -0.10 | 47.82 | 58.67 | 35.46 | 22.32 | 14.29 | 10.20 |
| RIDGE_FULL_STOP_1m | 435 | 178 | 104 | 153 | 1.51 | -1.30 | -6.26 | -2.41 | -9.15 | 0.70 | 0.15 | 53.37 | 50.34 | 29.43 | 18.62 | 13.10 | 8.74 |
| RIDGE_FULL_STOP_5m | 266 | 132 | 55 | 79 | 1.48 | -1.03 | -5.26 | -2.20 | -8.93 | 0.64 | 0.26 | 56.82 | 52.63 | 31.95 | 22.93 | 15.41 | 10.15 |
| RIDGE_NO_PREVIOUS_STOP_1m | 298 | 105 | 69 | 124 | 1.12 | -1.01 | -4.23 | -1.77 | -5.43 | 0.40 | 0.06 | 51.43 | 44.63 | 18.79 | 10.07 | 5.37 | 3.36 |
| RIDGE_NO_RECENT_STOP_1m | 361 | 145 | 78 | 138 | 1.22 | -1.17 | -5.43 | -2.30 | -8.30 | 0.61 | -0.10 | 47.59 | 47.37 | 25.48 | 19.11 | 14.13 | 9.70 |
| RIDGE_NO_SEQUENCE_STOP_1m | 415 | 160 | 94 | 161 | 1.55 | -1.23 | -6.50 | -2.58 | -9.36 | 0.75 | -0.10 | 48.12 | 48.19 | 29.16 | 18.55 | 13.73 | 8.92 |
| TREE_FULL_QUALITY_1m | 108 | 64 | 14 | 30 | 2.78 | -2.62 | -14.12 | -5.04 | -18.58 | 0.22 | -0.25 | 48.44 | 72.22 | 52.78 | 36.11 | 32.41 | 25.00 |
| TREE_FULL_QUALITY_5m | 84 | 55 | 9 | 20 | 2.67 | -2.65 | -15.23 | -4.71 | -18.89 | 0.25 | -0.40 | 47.27 | 75.00 | 57.14 | 35.71 | 33.33 | 28.57 |
| TREE_FULL_STOP_1m | 12 | 5 | 1 | 6 | 3.41 | -1.14 | -5.93 | -4.05 | -6.51 | -0.53 | 0.33 | 60.00 | 83.33 | 58.33 | 50.00 | 33.33 | 8.33 |
| TREE_FULL_STOP_5m | 7 | 4 | 1 | 2 | 2.21 | -1.12 | -6.12 | -4.09 | -6.64 | -1.01 | -0.15 | 50.00 | 85.71 | 57.14 | 57.14 | 42.86 | 28.57 |

Path and returns condition on complete observed source-slot coverage. Hit denominator is all BUY; rates are observed lower bounds, with unknown counts and upper bounds in review.json. A missing source minute is not certified as no trade. MaxDD is the confirmed chronological OHLC bound; intra-bar ordering remains unknown.

## Availability by AM/PM elapsed minutes

Each row is an evaluation decision opportunity before model actions. Window warmup masks are shown separately from finite observed summaries: a partial observed local window is usable information, not a certified full window.

| Phase / age | N | Quote true % | Local15 finite % | Local30 finite % | Local60 finite % | Full15 age % | Full30 age % | Full60 age % | Previous sequence finite % | Swing finite % | VWAP finite % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AM/30-59 | 8700 | 96.57 | 99.26 | 99.99 | 100.00 | 100.00 | 100.00 | 0.00 | 100.00 | 80.80 | 100.00 |
| AM/60+ | 22609 | 87.36 | 95.54 | 99.63 | 100.00 | 100.00 | 100.00 | 100.00 | 100.00 | 90.70 | 100.00 |
| PM/00-14 | 2814 | 82.41 | 93.46 | 93.46 | 93.46 | 0.00 | 0.00 | 0.00 | 100.00 | 80.10 | 100.00 |
| PM/15-29 | 3015 | 76.58 | 87.23 | 97.65 | 97.65 | 100.00 | 0.00 | 0.00 | 100.00 | 80.43 | 100.00 |
| PM/30-59 | 6711 | 91.43 | 97.63 | 99.72 | 99.94 | 100.00 | 100.00 | 0.00 | 100.00 | 93.55 | 100.00 |
| PM/60+ | 21463 | 80.99 | 92.95 | 99.45 | 100.00 | 100.00 | 100.00 | 100.00 | 100.00 | 84.35 | 100.00 |

## Interpretation boundaries

- Metrics use active-minute horizons; do not silently compare them with v1 wall-clock 30m/60m values. The original v1 report is preserved.
- The continuation target is realized-best future quality supervision, an optimistic proxy; this is not a solved Bellman optimal stopping policy.
- The recorded timeToRecovery is first observed high reaching Entry price, which can be zero in the entry minute. It is not post-drawdown recovery duration.
- Lower MAE among fewer entrants does not by itself establish Entry value. Read fixed-denominator Capture, BUY throughput, unknown outcomes and session stability together.
- Feature availability and attribution are descriptive. Partial bars, fixed projection, and inherited upstream metadata limit claims about chart understanding and independent prospective PIT.
- Common Holdout244 and other sealed partitions remain outside this study. No Entry promotion, EXIT development, allocation change or trading is performed.

