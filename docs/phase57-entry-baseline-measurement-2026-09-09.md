# Frozen Hybrid v1 × existing P21: 17-session diagnostic

The real-input gates and measurement policy were committed as `5460582fdf17648ea457f8ad952c6a35eb73ccff` before baseline future labels. The earlier NO-GO audit remains immutable and is superseded by the new real-input evidence directory.

## Source admission

All 17 precommitted sessions, 2026-08-13 through 2026-09-04, have hash-verified normalized market shards. The 3,709-symbol prior universe has 3,647–3,677 available symbols per session. All 7,410 compressed provider/normalized receipt files were hash checked. The raw archive contains 2,512,365 bars; 35,094 provider endpoint records at 11:30 or 15:30 are excluded to match unchanged Hybrid regular open-stamped intervals. 2,477,271 regular bars remain. No timestamp is shifted and absent intervals are not filled.

The fixed schedule is 66 decision points/session (1,122 total); 1,108 meet the precommitted market-coverage minimum. Fourteen points are explicitly blocked, not treated as empty selection successes. Missing versus no-trade cannot be inferred from this provider archive. Exact grid availability governs every outcome horizon independently.

Classification is `HISTORICAL_RECONSTRUCTION_LATER_FETCHED`, development diagnostic only. It is neither Actual Durable, formal OOS nor prospective. The prior June 30 universe misses some later IPOs and cannot establish full historical JPX coverage. Existing #572 evidence verifies provider bar-start sequence parity on 41 Golden prefixes, but not full OHLCV equality. Quote revision and corporate-action basis remain source limitations. This replay performs no adjustment or cross-session price feature transformation and opens no daily archive. Logical completed-bar PIT is distinct from proving historical provider vintage; no such vintage claim is made.

## P21 and adapter

Canonical snapshot SHA256 is `10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a`; exact prior pack SHA256 is `0d110f22bc664da3d7b3615e4bee765eb642631cda1146f38a1b50bfbdcd9b67`. The pack was independently regenerated from canonical bytes and compared deeply. It contains five symbols × 38 dates, June 18–August 12. These 190 symbol-session records are unrelated to the 190 protected Reserve sessions.

Prior-only rows cover horizons 1/3/6/12/24. The real adapter gate compares identical direct and mapped current inputs and independently refitted existing P21 outputs. The original model/config/horizon/feature/threshold choices and training/signal minima are unchanged. The legacy P21 feature-cutoff key remains the last bar-open timestamp, while actual outer availability is bar-open + five minutes. Both cutoffs are recorded.

The measurement runner reuses only the identical constant prior bundle after every prior outcome is known. It uses the already established #572 artifact-hash reconstruction and verifies exact refit parity in the first and last baseline sessions. It also caches native Intl formatter instances with identical constructor arguments; full unchanged Hybrid output is compared with the native uncached runtime before use. Selector and P21 source files are not edited.

## Measurement contract

All Hybrid selections are retained. Event-level signals and the first ENTER per symbol-session are separate populations. There are no fills, position management, EXIT simulations or portfolio returns. A later repeated ENTER is not a second independent opportunity.

Features are frozen for all sessions before the separate label phase. Hypothetical LONG and SHORT labels require exact same-session +1/+3/+6/+12 grids. Scheduled lunch may be crossed; overnight substitution is forbidden. Gross > 0 is HIT; zero is NEUTRAL in the observed denominator; missing labels are excluded with counts. Net labels subtract the frozen five-basis-point round-trip contract once. Horizons are separate diagnostics and must not be summed as trades.

Time/rank/delay buckets are fixed by policy. MFE/MAE timing means the close of the first extremum bar, not a known intrabar execution time. The VWAP diagnostic is an observed typical-price × volume proxy, not exchange turnover VWAP. Pre-entry move references the first observed regular bar open; incomplete early history is disclosed. WAIT comparisons pair the first ABSTAIN with first later ENTER, with different forward windows, and cannot establish a causal benefit of waiting.

Session ICC/effective N are approximate unequal-cluster diagnostics, not a validation/OOS claim. Regime is unclassified because no existing definition with admitted PIT inputs was established; no new regime thresholds or protected inputs are used.

## Protection and scope

Protected 190 newly opened = 0; protected new outcome viewed = 0. Original cross-research UNKNOWN statuses remain. #572, main, Frozen Hybrid, P21, EXIT and Capital Allocation remain unchanged. All nine safety flags are false. No new Entry model, retuning, allocation or promotion is performed. Subsequent model research requires a separate dataset allocation and readiness decision.

## Measured result (development diagnostic only)

All 17 sessions are now `BASELINE_DIAGNOSTIC_USED`. Selection events: 4542; unique symbols: 307; symbol-sessions: 720; repeated selections: 3822 (84.15%). ENTER: 194; ABSTAIN: 4348; P21 event BLOCKED: 0. Event coverage: 4.27%. LONG/SHORT: 112/82.

First ENTER opportunities: 79 (43 LONG / 36 SHORT), covering 10.97% of selected symbol-sessions. Repeated same-direction signals: 102 (52.58% of ENTER signals). Fourteen market-wide points were blocked before selection; this is separate from zero blocked P21 events.

### eventLevel

| Direction | Horizon | Observed / censored | Gross hit | Net positive | Gross mean / median bps | Net mean / median bps | MFE mean / median bps | MAE mean / median bps | MFE/MAE | Time MFE / MAE min |
|---|---|---|---|---|---|---|---|---|---|---|
| ALL | +1 | 154 / 40 | 46.10% | 46.10% | 167.37 / 0.00 | 162.37 / -5.00 | 346.41 / 177.52 | 96.32 / 27.68 | 3.60 | 4.45 / 2.63 |
| ALL | +3 | 120 / 74 | 51.67% | 50.83% | 117.06 / 25.82 | 112.06 / 20.82 | 399.11 / 284.01 | 186.20 / 65.96 | 2.14 | 10.08 / 7.54 |
| ALL | +6 | 95 / 99 | 60.00% | 58.95% | 108.35 / 67.05 | 103.35 / 62.05 | 418.93 / 322.58 | 265.57 / 147.44 | 1.58 | 17.53 / 15.21 |
| ALL | +12 | 73 / 121 | 56.16% | 56.16% | 106.13 / 56.99 | 101.13 / 51.99 | 478.46 / 385.89 | 334.59 / 210.08 | 1.43 | 34.45 / 26.30 |
| LONG | +1 | 84 / 28 | 47.62% | 47.62% | 212.47 / 0.00 | 207.47 / -5.00 | 349.02 / 125.82 | 97.58 / 25.62 | 3.58 | 3.93 / 2.62 |
| LONG | +3 | 65 / 47 | 47.69% | 46.15% | 124.44 / 0.00 | 119.44 / -5.00 | 390.92 / 222.22 | 190.59 / 76.14 | 2.05 | 10.08 / 7.69 |
| LONG | +6 | 51 / 61 | 56.86% | 54.90% | 44.13 / 26.04 | 39.13 / 21.04 | 399.69 / 298.51 | 300.34 / 153.85 | 1.33 | 16.76 / 15.98 |
| LONG | +12 | 44 / 68 | 52.27% | 52.27% | 66.94 / 53.34 | 61.94 / 48.34 | 407.73 / 302.63 | 377.49 / 219.35 | 1.08 | 30.80 / 26.02 |
| SHORT | +1 | 70 / 12 | 44.29% | 44.29% | 113.26 / 0.00 | 108.26 / -5.00 | 343.27 / 224.32 | 94.81 / 36.86 | 3.62 | 5.07 / 2.64 |
| SHORT | +3 | 55 / 27 | 56.36% | 56.36% | 108.34 / 65.61 | 103.34 / 60.61 | 408.79 / 312.50 | 181.01 / 61.20 | 2.26 | 10.09 / 7.36 |
| SHORT | +6 | 44 / 38 | 63.64% | 63.64% | 182.79 / 163.59 | 177.79 / 158.59 | 441.23 / 343.36 | 225.26 / 131.68 | 1.96 | 18.41 / 14.32 |
| SHORT | +12 | 29 / 53 | 62.07% | 62.07% | 165.60 / 179.95 | 160.60 / 174.95 | 585.78 / 630.25 | 269.50 / 193.55 | 2.17 | 40.00 / 26.72 |

### statefulOpportunityLevel

| Direction | Horizon | Observed / censored | Gross hit | Net positive | Gross mean / median bps | Net mean / median bps | MFE mean / median bps | MAE mean / median bps | MFE/MAE | Time MFE / MAE min |
|---|---|---|---|---|---|---|---|---|---|---|
| ALL | +1 | 66 / 13 | 42.42% | 42.42% | 34.25 / 0.00 | 29.25 / -5.00 | 217.69 / 145.31 | 135.24 / 61.27 | 1.61 | 4.02 / 3.64 |
| ALL | +3 | 58 / 21 | 55.17% | 53.45% | 42.19 / 41.73 | 37.19 / 36.73 | 304.16 / 235.94 | 220.49 / 114.76 | 1.38 | 8.79 / 7.67 |
| ALL | +6 | 52 / 27 | 57.69% | 55.77% | 39.79 / 24.30 | 34.79 / 19.30 | 352.77 / 268.10 | 297.68 / 170.05 | 1.19 | 17.02 / 15.96 |
| ALL | +12 | 46 / 33 | 54.35% | 54.35% | 53.11 / 55.38 | 48.11 / 50.38 | 436.62 / 332.89 | 372.74 / 241.31 | 1.17 | 34.13 / 29.35 |
| LONG | +1 | 35 / 8 | 40.00% | 40.00% | 20.14 / 0.00 | 15.14 / -5.00 | 181.03 / 80.70 | 158.05 / 86.96 | 1.15 | 3.86 / 3.57 |
| LONG | +3 | 31 / 12 | 45.16% | 41.94% | -4.00 / 0.00 | -9.00 / -5.00 | 258.47 / 161.29 | 254.24 / 165.29 | 1.02 | 8.71 / 7.26 |
| LONG | +6 | 28 / 15 | 50.00% | 46.43% | -70.20 / 2.15 | -75.20 / -2.85 | 295.91 / 202.65 | 361.22 / 254.67 | 0.82 | 14.82 / 17.68 |
| LONG | +12 | 26 / 17 | 46.15% | 46.15% | -12.76 / -38.66 | -17.76 / -43.66 | 348.78 / 252.37 | 441.62 / 301.96 | 0.79 | 28.27 / 30.00 |
| SHORT | +1 | 31 / 5 | 45.16% | 45.16% | 50.17 / 0.00 | 45.17 / -5.00 | 259.09 / 189.78 | 109.47 / 56.50 | 2.37 | 4.19 / 3.71 |
| SHORT | +3 | 27 / 9 | 66.67% | 66.67% | 95.22 / 71.43 | 90.22 / 66.43 | 356.63 / 254.24 | 181.75 / 70.96 | 1.96 | 8.89 / 8.15 |
| SHORT | +6 | 24 / 12 | 66.67% | 66.67% | 168.11 / 135.95 | 163.11 / 130.95 | 419.11 / 315.89 | 223.55 / 133.89 | 1.87 | 19.58 / 13.96 |
| SHORT | +12 | 20 / 16 | 65.00% | 65.00% | 138.73 / 200.13 | 133.73 / 195.13 | 550.82 / 561.31 | 283.19 / 201.82 | 1.95 | 41.75 / 28.50 |

### Timing and continuation

First-selection → first ENTER delay: mean 34.81 minutes, median 0; LONG mean 47.79 / median 5, SHORT mean 19.31 / median 0. This is first-entry delay, not a simulated holding duration.

First ENTER +1: 28 HIT / 14 NEUTRAL / 24 MISS out of 66 observed labels; 13 are censored. Within the first future bar, any adverse excursion occurs in 48/66 (72.73%); this is not tick-level order-of-moves evidence.

First ENTER +6: MFE > 0 in 51/52 (98.08%), but positive terminal directional return in 30/52 (57.69%) and net-positive in 29/52 (55.77%). An excursion is not captured profit. First ENTER LONG +6 has 28 observed cases and mean gross -70.20 bps; SHORT has 24 and +168.11 bps. These are small descriptive samples, not evidence for retuning a side.

PIT timing fields show a contrarian pattern among ENTER events: LONG median observed intraday range position is 0 and SHORT is 1; LONG median last-bar momentum is -744.93 bps and SHORT +476.19 bps. This differs from assuming P21 follows Hybrid continuation. Pre-entry move is the signed market move from first observed bar, not an Entry-direction-normalized return. All underlying per-event values are retained.

### Precommitted breakdowns

#### timeOfDay

| Bucket | Selected | ENTER | Coverage | +6 observed / missing | +6 hit | +6 net positive |
|---|---|---|---|---|---|---|
| MORNING_EARLY | 785 | 18 | 2.29% | 17 / 1 | 47.06% | 41.18% |
| MORNING_LATE | 1474 | 38 | 2.58% | 25 / 13 | 52.00% | 52.00% |
| AFTERNOON_EARLY | 911 | 60 | 6.59% | 28 / 32 | 64.29% | 64.29% |
| AFTERNOON_LATE | 1372 | 78 | 5.69% | 25 / 53 | 72.00% | 72.00% |

#### rank

| Bucket | Selected | ENTER | Coverage | +6 observed / missing | +6 hit | +6 net positive |
|---|---|---|---|---|---|---|
| 1 | 63 | 6 | 9.52% | 3 / 3 | 66.67% | 66.67% |
| 2-3 | 274 | 16 | 5.84% | 9 / 7 | 88.89% | 88.89% |
| 7+ | 3688 | 129 | 3.50% | 61 / 68 | 60.66% | 59.02% |
| 4-6 | 517 | 43 | 8.32% | 22 / 21 | 45.45% | 45.45% |

#### delay

| Bucket | Selected | ENTER | Coverage | +6 observed / missing | +6 hit | +6 net positive |
|---|---|---|---|---|---|---|
| 0 | 121 | 121 | 100.00% | 48 / 73 | 62.50% | 62.50% |
| NO_ENTRY | 4348 | 0 | 0.00% | 0 / 0 | N/A | N/A |
| 31+ | 29 | 29 | 100.00% | 17 / 12 | 58.82% | 58.82% |
| 11-30 | 21 | 21 | 100.00% | 12 / 9 | 41.67% | 41.67% |
| 1-10 | 23 | 23 | 100.00% | 18 / 5 | 66.67% | 61.11% |

#### selectionRepetition

| Bucket | Selected | ENTER | Coverage | +6 observed / missing | +6 hit | +6 net positive |
|---|---|---|---|---|---|---|
| FIRST | 720 | 44 | 6.11% | 26 / 18 | 65.38% | 65.38% |
| REPEATED | 3822 | 150 | 3.92% | 69 / 81 | 57.97% | 56.52% |

Rank is the original frozen Hybrid rank, not a new rank within the selected subset. Small observed buckets cannot support performance claims. Complete +1/+3/+6/+12 and censoring breakdowns are in metrics.json.gz.

### WAIT paired diagnostic

| Horizon | Pairs | Mean / median return difference bps | Improved rate |
|---|---|---|---|
| +1 | 31 | 45.49 / -15.58 | 41.94% |
| +3 | 27 | 87.53 / 66.86 | 62.96% |
| +6 | 26 | 177.04 / 176.12 | 65.38% |
| +12 | 24 | 182.70 / 210.77 | 66.67% |

WAIT pairing changes the forecast origin and conditions on a subsequent ENTER. It does not establish that waiting causes improvement and is not a WAIT policy.

### Session dependence and completeness

| Horizon | All-selection labels / missing | ENTER event ICC / effective n | First ENTER ICC / effective n |
|---|---|---|---|
| +1 | 4313 / 229 | 0.03 / 123.22 | 0.08 / 51.35 |
| +3 | 4078 / 464 | 0.09 / 69.45 | 0.15 / 39.13 |
| +6 | 3757 / 785 | 0.01 / 89.60 | -0.12 / 52.00 |
| +12 | 3293 / 1249 | -0.07 / 73.00 | -0.09 / 46.00 |

Event-level +3 mean gross is positive in 12/17 sessions and negative in 5/17; it is not uniformly stable. Regime diversity is UNKNOWN/unclassified, not 17 NORMAL_VOL. First-entry +3 effective n is approximately 39.13, not 4,542.

### Evaluation and next step

The baseline measurement is complete for this admitted development reconstruction. The most visible limitations are sparse P21 coverage, frequent immediate adverse excursions in first-entry opportunities, a weak first-entry LONG result in longer observed horizons, heavy censoring and substantial dependence. Provider-vintage/corporate-action uncertainty further limits external validity. No calibrated probability or general performance claim is made.

New Entry fitting remains NO-GO in this task: no separate approved development/validation/untouched OOS allocation or regime/readiness evidence has been established. The next highest-value step is to design that separate dataset with explicit access ledger, using these frozen diagnostics to define research questions without repeatedly optimizing these 17 sessions. Protected 190 remains excluded.

Release manifest SHA256: `2632d8c680ea7e388a736385936d7a3ed8b43e3e3a82f3194f26635bd78c9fa6`. The release contains immutable input/Gate references, feature freezes, event and stateful ledgers, both-direction labels, complete metrics, independent arithmetic verification and allocation status.

Local offline tests: 81 passed. All first/last-session real P21 parity checks passed. Logical completed-prefix/prior/feature-label violations = 0; duplicate events = 0. Historical provider-vintage PIT is unverified and is not included in that zero. Main remains `899d16b808dba0d5b2003228a5f46332b3a3ce09`; PR #579 remains Draft.
