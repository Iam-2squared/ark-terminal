# Phase57 Capital × EXIT integrated recycling — controlling handoff

Saved JST: 2026-09-27T19:24:59.480287+09:00. Basis research HEAD: `98b162565ad19b0b66b5a9c128ffa0963436a37a`. Draft PR #587 remains open.

**EXPERIMENTAL DEVELOPMENT INTEGRATED REPLAY.** Capital v3-B and R50-A remain formally unselected; no Final EXIT, live, paper or production authority. Frozen Entry Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d` remains unchanged.

## Exact evidence chain

- Performance-blind integration precommit `f0de21a1` / SHA256 `93d9ddb8e45a473947430fb67f013e56f28d079614625f534ef769c3434990f9`: fixed 24 session window, three comparison methods, MAX3, 100 shares, one-shot Entry, EXIT→Entry ordering, buckets and null valuation.
- Implementation/required zero-performance CI: `0efa0e1b`, run `36311671022` SUCCESS, artifact `10928807601`; 62 focused and inherited tests passed; saved CI v3-B score coverage IM 819/R1 795; 0 fits and 0 funded performance at that gate.
- First finite launch `1ac33b3a`, run `36311796946` failed at shallow `HEAD^` preflight before tests/replay. Pre-replay recovery `7abf361f` and append-only recovery launch `98b16256` changed only checkout depth and marker identification.
- Completed finite Action `36312012367` SUCCESS, exact tested SHA `98b162565ad19b0b66b5a9c128ffa0963436a37a`, artifact `10929214125`, ZIP SHA256 `949b4a3bcddf41ad15051c30924fcdc3c8b1b5c187c0505d464804ef0335f356`; six arms, zero model fits.
- Independent local audit PASS: all six replay ledger bytes match Action, both v3-B terminal arms match previously archived Capital v3 CI ledgers exactly; R50 fill/cost, cash/slot/lot, exclusive misses, EOD null and recycling witnesses checked. Result ZIP and manifest are saved under `RESULT/`.

## Funded capital and High-Upside comparison

| Entry | Rank × EXIT | Funded / exits | ≥5 funded / observed available | ≥5 rate / reach | ≥7.5 / ≥10 funded | CAPACITY_FULL misses | Final equity / return | EOD valid / 24 |
|---|---|---:|---:|---:|---:|---:|---|---:|
| IM | v3-B × terminal | 72 / 72 | 27 / 158 | +37.500% / +17.089% | 15 / 15 | 128 | ¥942,937 / -5.706% | 24 / 24 |
| IM | v3-B × R50-A | 79 / 79 | 27 / 158 | +34.177% / +17.089% | 15 / 15 | 123 | ¥887,131 / -11.287% | 24 / 24 |
| IM | causal rank × R50-A | 79 / 79 | 27 / 158 | +34.177% / +17.089% | 16 / 15 | 123 | ¥862,378 / -13.762% | 24 / 24 |
| R1 | v3-B × terminal | 30 / 29 | 11 / 143 | +36.667% / +7.692% | 8 / 7 | 36 | null / null | 9 / 24 |
| R1 | v3-B × R50-A | 32 / 31 | 12 / 143 | +37.500% / +8.392% | 9 / 8 | 35 | null / null | 9 / 24 |
| R1 | causal rank × R50-A | 32 / 31 | 10 / 143 | +31.250% / +6.993% | 8 / 7 | 35 | null / null | 9 / 24 |

Observed High is known for every funded position. The previous v3 training-label convention excludes one R1 negative observation with a missing terminal auction: `2025-08-04|36700|602`, observed upside +0.317%. Its terminal proceeds and subsequent equity remain unresolved, while its observed upside belongs to the 0–1% bucket. The append-only `EVALUATOR_DENOMINATOR_RECONCILIATION.json` gives both denominators; R1 primary funded ≥5 rate is 12/32 = 37.500%, not the inherited training-label 12/31 = 38.710%.

## Full funded upside distribution (v3-B × R50-A)

Strictly later same-session observed best High relative to Frozen Entry effective price. Half-open ranges; `UNKNOWN/CENSORED` retained. Net refers only to confirmed exits; capital is funded notional.

| Arm | Bucket | N | Funded % | Upside mean / median | Realized net mean / median | Net evaluable | Allocated capital | Capital % |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| IM | <0% | 9 | +11.392% | -0.294% / -0.093% | -5.983% / -4.469% | 9 | ¥2,624,312 | +11.943% |
| IM | 0–1% | 11 | +13.924% | +0.697% / +0.873% | -3.578% / -2.377% | 11 | ¥3,007,703 | +13.687% |
| IM | 1–2% | 8 | +10.127% | +1.282% / +1.189% | -4.812% / -1.906% | 8 | ¥2,237,318 | +10.181% |
| IM | 2–3% | 7 | +8.861% | +2.325% / +2.217% | -0.860% / +1.014% | 7 | ¥1,840,920 | +8.378% |
| IM | 3–4% | 6 | +7.595% | +3.320% / +3.333% | -1.750% / -0.681% | 6 | ¥1,635,818 | +7.444% |
| IM | 4–5% | 11 | +13.924% | +4.395% / +4.375% | -0.728% / -0.195% | 11 | ¥3,222,310 | +14.664% |
| IM | 5–7.5% | 12 | +15.190% | +6.207% / +5.885% | +1.682% / +1.501% | 12 | ¥3,382,390 | +15.392% |
| IM | 7.5–10% | 0 | +0.000% | null / null | null / null | 0 | ¥0 | +0.000% |
| IM | >=10% | 15 | +18.987% | +18.771% / +14.875% | +7.468% / +3.647% | 15 | ¥4,023,711 | +18.311% |
| IM | UNKNOWN/CENSORED | 0 | +0.000% | null / null | null / null | 0 | ¥0 | +0.000% |
| R1 | <0% | 3 | +9.375% | -0.304% / -0.380% | -5.082% / -4.718% | 3 | ¥868,834 | +9.424% |
| R1 | 0–1% | 3 | +9.375% | +0.592% / +0.627% | -8.883% / -8.883% | 2 | ¥767,283 | +8.323% |
| R1 | 1–2% | 3 | +9.375% | +1.533% / +1.413% | -2.670% / -2.179% | 3 | ¥847,323 | +9.191% |
| R1 | 2–3% | 5 | +15.625% | +2.315% / +2.208% | +1.379% / +1.706% | 5 | ¥1,584,692 | +17.190% |
| R1 | 3–4% | 3 | +9.375% | +3.594% / +3.525% | +0.538% / +1.200% | 3 | ¥855,027 | +9.275% |
| R1 | 4–5% | 3 | +9.375% | +4.313% / +4.240% | -1.393% / -3.643% | 3 | ¥906,953 | +9.838% |
| R1 | 5–7.5% | 3 | +9.375% | +6.375% / +6.520% | +2.602% / +2.857% | 3 | ¥874,237 | +9.483% |
| R1 | 7.5–10% | 1 | +3.125% | +8.308% / +8.308% | +1.435% / +1.435% | 1 | ¥234,517 | +2.544% |
| R1 | >=10% | 8 | +25.000% | +20.229% / +19.818% | +9.517% / +7.096% | 8 | ¥2,280,039 | +24.732% |
| R1 | UNKNOWN/CENSORED | 0 | +0.000% | null / null | null / null | 0 | ¥0 | +0.000% |

Summary of the requested cuts: IM <1% = 20/79 (25.316%), 3–4% = 6/79 (7.595%), 4–5% = 11/79 (13.924%), ≥5% = 27/79 (34.177%). R1 <1% = 6/32 (18.750%), 3–4% = 3/32 (9.375%), 4–5% = 3/32 (9.375%), ≥5% = 12/32 (37.500%). `<1%` includes the negative bucket.

## Recycling, capacity and premature exit trade-off

| Measure | IM | R1 |
|---|---:|---:|
| Terminal → R50-A funded entries | 72 → 79 | 30 → 32 |
| New funded identities absent from terminal | 8 | 2 |
| Directly after an earlier same-day model EXIT | 7 | 2 |
| Net entry count gain (lost terminal identities accounted) | 7 | 2 |
| Recycling-funded ≥5 / ≥7.5 / ≥10 | 0 / 0 / 0 | 1 / 1 / 1 |
| Confirmed early model EXITs / freed slots | 7 | 2 |
| Net confirmed cash released ahead of terminal, summed | ¥1,975,414 | ¥656,077 |
| Average minutes earlier than auction | 305.6 | 291.5 |
| Realized PnL from newly funded identities, closed only | -¥134,200 | ¥44,894 |
| Own early EXIT PnL difference vs same-quantity terminal | ¥73,000 | ¥20,400 |
| CAPACITY_FULL ≥5 misses: terminal → R50-A | 128 → 123 | 36 → 35 |
| Confirmed realized PnL difference vs terminal | -¥55,806 | ¥64,421 |

IM has 8 incremental identities but only 7 after a same-day early EXIT. The eighth entered before that day’s model EXIT and reflects earlier portfolio balance/path differences. One terminal-funded IM identity disappears, so net entries gain is 7. The shared preceding-release witness is a chronology check, not a unique per-exit causal effect estimate. R1 has 2 incremental identities, both after same-day release.

Post-EXIT observed best High is evaluator-only, never a sell fill. Across actually funded early model exits, the mean additional High above the exit price is IM 3.746% and R1 3.163%; a non-executable same-quantity peak-minus-exit proxy sums to ¥76,700 IM and ¥20,400 R1. Against the actually observed terminal auction rather than a peak oracle, those early R50-A exits improved same-quantity realized PnL by ¥73,000 IM and ¥20,400 R1. Reinvestment identities generated ¥−134,200 IM and ¥44,894 R1 in confirmed realized PnL. The IM full-period portfolio change is ¥−55,806 versus terminal; residual differences arise from changed sizing, an identity displaced from the control, and the changed path. R1 realized closed-trade difference is ¥64,421; it is not a 24-day equity gain.

## Turnover, valuation, daily return

| Measure | IM v3-B × R50-A | R1 v3-B × R50-A |
|---|---:|---:|
| Funded entries | 79 | 32 |
| Confirmed exits | 79 | 31 |
| Entries/day mean | 3.292 | 1.333 |
| Entries/day median | 3.000 | 0.000 |
| Entries/day max | 4 | 4 |
| Exits/day mean | 3.292 | 1.292 |
| Holding wall minutes mean | 326.633 | 321.161 |
| Holding wall minutes median | 360.000 | 340.000 |
| Average concurrent positions | 2.708 | 1.652 |
| Time at MAX3 / active minutes | +89.667% | +34.641% |
| Time-weighted utilization / valid as-of minutes | +76.844% | +70.331% |
| Utilization coverage of active minutes | +99.731% | +41.436% |
| Time ≥80% utilization / valid minutes | +58.285% | +66.399% |
| Cash turnover (buy notional + confirmed sell cash) | ¥43,836,095 | ¥18,396,793 |
| Slot turnover/day mean | 1.097 | 0.444 |

IM bought 4 positions on 7 of 24 days, and R1 on 2 days, while concurrency never exceeded 3. Thus MAX3 is a simultaneous-holding bound, not a three-purchases-per-day limit. Trading-active time weighting excludes lunch and includes only the scheduled continuous-minute grid; utilization null time is omitted from its mean, with coverage shown above.

| Portfolio and EOD measure | IM v3-B × R50-A | R1 v3-B × R50-A |
|---|---:|---:|
| Initial equity | ¥1,000,000 | ¥1,000,000 |
| Final equity | ¥887,131 | null |
| 24-session portfolio return | -11.287% | null |
| Realized PnL (closed trades only) | -¥112,869 | ¥149,574 |
| Unrealized PnL at last timestamp | ¥0 | null |
| Full intraday MaxDD | null | null |
| Certified EOD MaxDD, valid prefix only if censored | -16.118% | -4.016% |
| Profit factor, closed trades | 0.814 | 1.790 |
| Win rate, closed trades | +44.304% | +54.839% |
| Priced event coverage | +99.554% | +40.133% |
| Certified EOD sessions | 24 | 9 |
| Null EOD sessions | 0 | 15 |
| Arithmetic mean daily return, full 24 | -0.394% | null |
| Median daily return, full 24 | -1.230% | null |
| Geometric daily return, full 24 | -0.498% | null |
| Positive-day rate, full 24 | +37.500% | null |
| Best/worst day, full 24 | +12.453% / -8.316% | null |
| Cumulative return, full 24 | -11.287% | null |

Period: 2025-07-22 to 2025-08-25, 35 calendar days, 24 scheduled trading sessions. Funded sessions: IM 24, R1 10. IM has 24 certified flat EOD values and 24 contiguous initial-to-EOD daily returns; geometric daily = (¥887,131.009125 / ¥1,000,000)^(1/24) − 1 = −0.498%. R1 has 9 valid and 15 null EOD sessions after the unresolved 2025-08-04 terminal auction for `2025-08-04|36700|602`. Its full 24-session Final Equity, Portfolio Return, geometric/arithmetic daily average and full MaxDD are null. An independently valid first-nine-session diagnostic ending 2025-08-01 is R1 +13.432% versus IM −5.088% over the same first nine dates; this does not identify the full period arm ordering.

IM EOD-only MaxDD is −16.118% over 24 certified EODs; full intraday MaxDD remains null because within-session mark gaps are explicit. R1 EOD-only −4.016% describes its 9-session certified prefix, not a 24-session MaxDD. Marks are never fills; no auction substitution, interpolation, unknown terminal price, or cross-session corporate-action mark is used.


Closed-trade downside and concentration diagnostics: IM R50-A net trade p05/p10/worst = −10.845% / −8.950% / −18.042%; R1 = −10.399% / −5.855% / −11.911%. The exact average winning and losing JPY trade, top symbol/session funded shares, cash turnover and daily distinct positions are in `RESULT/report.json`.

## Exclusive ≥5 miss reasons

| Reason | IM terminal | IM R50-A | R1 terminal | R1 R50-A |
|---|---:|---:|---:|---:|
| CAPACITY_FULL | 128 | 123 | 36 | 35 |
| INSUFFICIENT_CASH | 0 | 1 | 0 | 0 |
| LOT_INFEASIBLE | 0 | 0 | 1 | 1 |
| RANK_LOSS | 2 | 6 | 0 | 0 |
| ENTRY_NOT_ELIGIBLE | 0 | 0 | 0 | 0 |
| UNRESOLVED_CASH_LOCK | 0 | 0 | 95 | 95 |
| OTHER_CAUSAL | 1 | 1 | 0 | 0 |

Each missed observed ≥5% Entry receives exactly one causal reason; rank and EXIT never inspect that future label.

## Attribution and limitations

- IM ≥5 misses stay 131, while CAPACITY_FULL falls 128→123 (5); other causal reject reasons offset the same count. R1 ≥5 misses fall 132→131, CAPACITY_FULL 36→35 (1); 95 R1 misses remain UNRESOLVED_CASH_LOCK. Exact exclusive reasons are in `RESULT/report.json`.
- IM rank-controlled R50-A v3-B versus existing causal rank both fund 79 and 27 ≥5 winners; v3-B final equity ¥887,131 versus causal ¥862,378. R1 v3-B R50-A funds 12 ≥5 vs causal rank 10, but all full-period equity variants remain null. No rank or EXIT SELECT follows from this Development comparison.
- R50-A remains formal R50 NO_SELECTION_STOP (median Capture <50%); Capital v3-B remains Capital v3 NO_SELECTION_STOP (0/2 PASS). The earlier v3 CI/local floating prediction-byte discrepancy remains unresolved; this run pins saved CI `scores.json` byte SHA256 `b6ed8340536b4c89fd562873bc95e028efd7bfd9130e7c92a3ede52b3b0d3645`, with zero refits.
- Data: 2,155 previously outcome-exposed Development opportunities. Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective / Protected new opens 0; provider acquisitions 0. Past R49/v0 allowlist-external decode remains disclosed; this run read source paths allowlist-first. Safety9 all false. No main merge, force push, paper, live, production, broker/Excel/RSS write, transmission or automatic promotion.

## Restore and next action

`RESULT/phase57-integrated-result.zip` retains six JSON gzip cash ledgers, six CSV and JSON equity curves with nulls, three PNG comparisons, Action report and hashes. `RESULT/independent-audit.json` records six exact-byte reproduction checks. `EVALUATOR_DENOMINATOR_RECONCILIATION.json` records observed-high rates separately from the inherited training-label censor. The ZIP, saved R50-A source, frozen CI scores, Entry/R1 inputs, raw path, implementation and precommit are on the branch. Re-run source audit with `python -m scripts.phase57_capital_exit_integrated_audit --result EXTRACTED_RESULT_DIR --out AUDIT.json`.

Controlling disposition: keep this as an experimental negative/qualified diagnosis. IM recycler rotates slots but yields no additional ≥5 winners and lowers complete 24-session equity; R1 adds one ≥5 winner, while unresolved auction prevents complete equity comparison. Preserve formal NO_SELECTION and solve genuine auction/mark continuity and prediction reproducibility under a new performance-blind contract before any Final EXIT or Capital promotion.
