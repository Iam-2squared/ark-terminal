# One-bar wait counterfactual diagnosis only

Verdict: **WAIT_VALUE_NOT_SUPPORTED**

Candidate SHA: f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a; threshold: strictly >0.60; analysis code commit: 552b7d6b499a425635bc3e2313bf0704e0965bde.

## Fixed semantics

- price: Close of the exact next regular completed 5-minute bar after the frozen decision. The bar starts at decision T (or 12:30 JST when T is 11:30); its close is available at bar.availableAt and is reference-only, not an executable fill.
- eligibility: Fail closed when that exact next regular bar is absent or crosses the JST session boundary. No next-day carry and no substitution with a later observed bar.
- sameAbsoluteEndpoint: Uses the original baseline +3/+6 endpoint and excludes the one waited bar from excursion measurement.
- samePostEntryHorizon: Starts after the counterfactual reference becomes available and uses the same exact-grid +3/+6 bar count, with lunch normalization and fail-closed missing bars.
- cost: Same 5 bps round-trip cost deducted once from every completed counterfactual horizon.
- chasedAfterWait: Direction-adjusted entry price improvement is negative; no magnitude threshold.

The counterfactual is applied mechanically to every eligible frozen ENTER. It never chooses ENTER/SKIP/WAIT MORE from the waited bar and does not represent an implemented Timing Challenger.

## Independent replication

| Metric | Development | Holdout29 | Direction consistent? |
|---|---:|---:|:---:|
| Baseline ENTER | 95.00 | 99.00 | — |
| Eligible / unavailable | 92/3 | 98/1 | — |
| Entry improvement mean bps | -94.70 | -35.59 | Yes |
| Entry improvement median bps | -51.25 | -38.63 | Yes |
| Price improved | 32.61% | 35.71% | — |
| Chased after wait | 56.52% | 51.02% | Yes |
| Baseline +3 positive | 57.14% | 58.51% | — |
| Wait same endpoint +3 positive | 50.00% | 50.00% | — |
| Wait post-entry +3 positive | 51.90% | 51.09% | — |
| Baseline +3 mean net | 120.87 | 101.00 | — |
| Baseline +3 median net | 62.19 | 104.60 | — |
| Wait same endpoint +3 mean net | 39.69 | 58.43 | — |
| Wait same endpoint +3 median net | -0.46 | -0.82 | — |
| Wait post-entry +3 mean net | 61.56 | 95.99 | — |
| Wait post-entry +3 median net | 22.70 | 12.54 | — |
| Same endpoint +3 net difference | -81.18 | -42.57 | Yes |
| Post-entry +3 net difference | -96.35 | -18.74 | Yes |
| Same endpoint +3 MAE reduction | -10.61 | 65.33 | No |
| Post-entry +3 MAE reduction | -44.12 | 23.80 | No |
| Same endpoint +3 MFE lost | 142.34 | 117.51 | Yes |
| Post-entry +3 MFE lost | 119.90 | 56.06 | Yes |
| Baseline +6 positive | 63.16% | 63.22% | — |
| Wait same endpoint +6 positive | 47.37% | 63.22% | — |
| Wait post-entry +6 positive | 48.65% | 68.24% | — |
| Baseline +6 mean net | 166.78 | 186.57 | — |
| Baseline +6 median net | 140.58 | 147.28 | — |
| Wait same endpoint +6 mean net | 59.91 | 136.46 | — |
| Wait same endpoint +6 median net | -5.00 | 85.09 | — |
| Wait post-entry +6 mean net | 22.78 | 174.34 | — |
| Wait post-entry +6 median net | -5.00 | 175.18 | — |
| Same endpoint +6 net difference | -106.88 | -50.11 | Yes |
| Post-entry +6 net difference | -138.07 | -24.57 | Yes |
| Same endpoint +6 MAE reduction | -37.81 | 40.70 | No |
| Post-entry +6 MAE reduction | -92.27 | 27.08 | No |
| Same endpoint +6 MFE lost | 140.61 | 72.69 | Yes |
| Post-entry +6 MFE lost | 128.43 | 39.46 | Yes |

Positive entry improvement means LONG bought lower or SHORT sold higher. Positive MAE reduction means lower adverse excursion; positive MFE lost means favorable excursion was sacrificed. Baseline denominators retain all valid original outcomes; WAIT denominators and missing counts are explicit in JSON.

## Price distribution and persistence

### Development

Entry improvement: n=92, mean=-94.70, median=-51.25, P25=-193.53, P75=83.45, P90=252.32 bps. Improved/worsened/unchanged=30/52/10. Counterfactual unavailable=3.

Chased deterioration: n=52, mean=289.95, median=162.61, P75=430.34, P90=682.69 bps.

| Hybrid at counterfactual time | Improved | Worsened | Unchanged |
|---|---:|---:|---:|
| STILL_SELECTED | 27 | 34 | 8 |
| DROPPED | 3 | 18 | 2 |
| NOT_OBSERVABLE | 0 | 0 | 0 |

### Holdout29

Entry improvement: n=98, mean=-35.59, median=-38.63, P25=-188.33, P75=125.97, P90=341.75 bps. Improved/worsened/unchanged=35/50/13. Counterfactual unavailable=1.

Chased deterioration: n=50, mean=302.56, median=187.97, P75=375.91, P90=677.03 bps.

| Hybrid at counterfactual time | Improved | Worsened | Unchanged |
|---|---:|---:|---:|
| STILL_SELECTED | 32 | 33 | 13 |
| DROPPED | 3 | 17 | 0 |
| NOT_OBSERVABLE | 0 | 0 | 0 |

## Path type and side diagnostics

### Development

| Group | N | Entry improvement mean | Same +3 net diff | Post +3 net diff | Same +6 net diff | Post +6 net diff |
|---|---:|---:|---:|---:|---:|---:|
| SHORT | 86 | -69.74 | -53.21 | -68.61 | -78.41 | -114.69 |
| LONG (exploratory) | 9 | -356.81 | -388.90 | -381.70 | -387.43 | -361.78 |
| TYPE_A | 44 | -90.48 | -83.78 | -56.93 | -88.86 | -132.57 |
| TYPE_B | 6 | 256.14 | 253.18 | 358.28 | 247.41 | 370.03 |
| TYPE_C | 9 | 223.59 | 227.39 | 230.14 | 229.72 | 142.08 |
| TYPE_D | 16 | -449.26 | -450.95 | -420.94 | -447.99 | -475.95 |
| TYPE_E | 7 | -154.28 | -154.93 | -422.40 | -161.42 | -150.50 |
| TYPE_UNKNOWN | 13 | -1.21 | 210.98 | 39.68 | UNKNOWN | UNKNOWN |

### Holdout29

| Group | N | Entry improvement mean | Same +3 net diff | Post +3 net diff | Same +6 net diff | Post +6 net diff |
|---|---:|---:|---:|---:|---:|---:|
| SHORT | 85 | -2.28 | 2.09 | 15.41 | -15.23 | 11.07 |
| LONG (exploratory) | 14 | -235.48 | -320.82 | -226.26 | -268.10 | -264.32 |
| TYPE_A | 50 | -3.24 | -6.43 | 12.31 | -4.38 | 9.94 |
| TYPE_B | 6 | 198.08 | 200.34 | 592.31 | 192.29 | 196.66 |
| TYPE_C | 9 | 425.16 | 423.93 | 446.02 | 423.28 | 414.74 |
| TYPE_D | 17 | -449.71 | -435.70 | -372.13 | -442.11 | -524.01 |
| TYPE_E | 7 | -210.18 | -210.18 | -238.93 | -228.17 | 188.68 |
| TYPE_UNKNOWN | 10 | 86.16 | 36.21 | -636.16 | UNKNOWN | UNKNOWN |

LONG remains exploratory: Development n=9 and Holdout29 n=14. No side-specific rule follows from these diagnostics.

## Verdict and governance

Evidence for WAIT: Holdout29 shows lower mean MAE after waiting under both endpoint conventions; its post-entry +6 positive rate increases despite lower mean net return.

Evidence against WAIT: Both independent periods have negative mean and median entry-price improvement, more worsened than improved entries, lower mean net return at +3 and +6 under both endpoint conventions, and positive MFE loss.

Remaining uncertainty: Reference closes are not executable fills; small LONG samples; exact counterfactual is one fixed bar only; missing exact-grid horizons are fail-closed; Development uses OOF models while Holdout uses the final model.

Pooled194 was DESCRIPTIVE_ONLY; price, net-return and MFE-loss directions replicate; no fitting or rule selection. Independent groups remain primary.

PIT/duplicate/state issues: 0/0/0. Candidate changed=false; threshold changed=false; Timing Challenger=NOT_STARTED. Fresh Validation/Fresh OOS/Protected103 new access=0/0/0. Safety flags are all false.