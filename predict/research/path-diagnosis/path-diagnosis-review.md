# Path diagnosis only

Verdict: TIMING_HYPOTHESIS_MIXED. No candidate change; no Timing Challenger.

Candidate SHA: f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a. Threshold strictly >0.60 (not >=). Analysis code commit: 8a20218fc239478133a93e737e2de6673971d879.

## Semantics

- entry: Last completed bar close; reference only, not executable fill. Price equality checked for every entry.
- horizon: h regular 5m bars starting at decision T; lunch skipped, same JST session, no next-day fill. Thus not always h*5 elapsed minutes.
- return: LONG=(close/reference-1)*10000; SHORT=negative LONG; net=gross-5bps once per horizon.
- adverse: First postdecision bar low<reference LONG or high>reference SHORT; no minimum depth.
- chronology: First bar attaining global MAE6 versus first bar attaining global MFE6; tied bar UNKNOWN; not ordering of every excursion.
- recovery: First observed completed-bar close at or beyond gross reference after first adverse bar; bounds only, not first touch. +3/+6 positive uses net>0.
- types: A/B/C use observed close recovery by3/by6 after immediate adverse; D/E use net6 sign without immediate adverse. Unknown horizons remain unknown.
- persistence: Next stored complete Hybrid decision. Hybrid has no direction; persistence cannot be classified same/opposite direction.

All194 reference prices equal the last completed close; reference-age-at-availability0min. This is not an executable quote/fill. Any adverse excursion counts, with no depth cutoff. First adverse is localized to a bar, not a precise time. Same signal-bar adverse is not measured; BAR1 is the first future bar. Recovery is observed close recovery, not exact first touch. Neither guarantees net positive at horizon.

## Replication

| Metric | Development | Holdout29 | Difference H-D |
|---|---:|---:|---:|
| ENTER | 95.00 | 99.00 | 4.00 |
| Immediate adverse % | 71.74 | 71.43 | -0.31 |
| First adverse BAR_1 | 66.00 | 70.00 | 4.00 |
| First adverse BAR_2 | 2.00 | 3.00 | 1.00 |
| First adverse BAR_3 | 4.00 | 0.00 | -4.00 |
| First adverse BAR_4 | 0.00 | 1.00 | 1.00 |
| First adverse BAR_5 | 1.00 | 1.00 | 0.00 |
| First adverse BAR_6 | 0.00 | 0.00 | 0.00 |
| First adverse NEVER_WITHIN6 | 17.00 | 19.00 | 2.00 |
| First adverse UNKNOWN | 5.00 | 5.00 | 0.00 |
| MAE_BEFORE_MFE | 34.00 | 36.00 | 2.00 |
| MFE_BEFORE_MAE | 20.00 | 23.00 | 3.00 |
| UNKNOWN_INTRABAR_ORDER | 3.00 | 5.00 | 2.00 |
| UNAVAILABLE_OR_NEITHER | 38.00 | 35.00 | -3.00 |
| mae3 mean bps | 251.14 | 281.55 | 30.41 |
| mae3 median bps | 169.13 | 176.07 | 6.93 |
| mae3 p25 bps | 21.82 | 28.97 | 7.15 |
| mae3 p75 bps | 364.56 | 399.56 | 35.00 |
| mae3 p90 bps | 657.40 | 797.84 | 140.45 |
| mfe3 mean bps | 390.57 | 379.46 | -11.10 |
| mfe3 median bps | 295.05 | 295.38 | 0.33 |
| mfe3 p25 bps | 158.27 | 143.78 | -14.48 |
| mfe3 p75 bps | 508.93 | 500.00 | -8.93 |
| mfe3 p90 bps | 967.52 | 932.65 | -34.86 |
| mae6 mean bps | 267.11 | 332.66 | 65.55 |
| mae6 median bps | 119.60 | 225.67 | 106.07 |
| mae6 p25 bps | 14.89 | 51.31 | 36.43 |
| mae6 p75 bps | 452.31 | 483.42 | 31.11 |
| mae6 p90 bps | 802.06 | 846.88 | 44.81 |
| mfe6 mean bps | 473.55 | 473.10 | -0.45 |
| mfe6 median bps | 440.09 | 398.77 | -41.32 |
| mfe6 p25 bps | 214.17 | 213.96 | -0.21 |
| mfe6 p75 bps | 621.54 | 616.07 | -5.47 |
| mfe6 p90 bps | 1041.40 | 1007.08 | -34.32 |
| remainingFavorable mean bps | 65.88 | 89.52 | 23.63 |
| remainingFavorable median bps | 0.00 | 0.00 | 0.00 |
| remainingFavorable p25 bps | 0.00 | 0.00 | 0.00 |
| remainingFavorable p75 bps | 88.60 | 102.13 | 13.54 |
| remainingFavorable p90 bps | 185.28 | 283.30 | 98.01 |
| Observed recovery by1 % of known immediate-adverse | 54.55 | 50.00 | -4.55 |
| Observed recovery by2 % of known immediate-adverse | 68.75 | 66.18 | -2.57 |
| Observed recovery by3 % of known immediate-adverse | 68.75 | 73.53 | 4.78 |
| Observed recovery by6 % of known immediate-adverse | 85.00 | 86.15 | 1.15 |
| Immediate adverse -> net positive3 % | 46.67 | 52.94 | 6.27 |
| Immediate adverse -> net positive6 % | 60.38 | 60.32 | -0.06 |
| Net3->net6 A_NEG_POS | 7.00 | 10.00 | 3.00 |
| Net3->net6 B_POS_POS | 41.00 | 45.00 | 4.00 |
| Net3->net6 C_POS_NEG | 6.00 | 8.00 | 2.00 |
| Net3->net6 D_NEG_NEG | 22.00 | 24.00 | 2.00 |
| Net3->net6 MISSING | 19.00 | 12.00 | -7.00 |
| Next Hybrid selected | 72.00 | 78.00 | 6.00 |
| TYPE_A | 44.00 | 50.00 | 6.00 |
| TYPE_B | 6.00 | 6.00 | 0.00 |
| TYPE_C | 9.00 | 9.00 | 0.00 |
| TYPE_D | 16.00 | 17.00 | 1.00 |
| TYPE_E | 7.00 | 7.00 | 0.00 |
| TYPE_UNKNOWN | 13.00 | 10.00 | -3.00 |

Transition A:7/76=9.21% vs10/87=11.49% among paired labels (7/95 and10/99 among all entries). All counts and missing denominators are preserved in JSON. MFE6-MFE3 median0 in both groups: later favorable extension is not universal.

## Separate groups and sessions

### Development

| Side | N | Immediate adverse | Adverse -> net6 positive |
|---|---:|---|---|
| ALL | 95 | 66/92 | 32/53 |
| SHORT | 86 | 62/84 | 31/50 |
| LONG | 9 | 4/8 | 1/3 |

LONG exploratory only:9 and14 entries; no reliable side-specific policy conclusion.

| Session | ENTER | Adverse/valid1 | Recovered by3 | Recovered by6 | Mean MAE6 | Mean MFE6 |
|---|---:|---|---|---|---:|---:|
| 2025-11-19 | 3 | 3/3 | 2/2 | 2/2 | 169.49 | 338.98 |
| 2025-11-20 | 0 | 0/0 | 0/0 | 0/0 | UNKNOWN | UNKNOWN |
| 2025-11-25 | 3 | 3/3 | 3/3 | 3/3 | 160.07 | 501.80 |
| 2025-11-26 | 2 | 1/2 | 1/1 | 1/1 | UNKNOWN | UNKNOWN |
| 2025-11-27 | 6 | 4/6 | 2/4 | 2/3 | 243.14 | 419.03 |
| 2025-11-28 | 3 | 2/3 | 1/2 | 2/2 | 357.72 | 722.26 |
| 2025-12-01 | 2 | 1/2 | 0/1 | 0/1 | 576.31 | 158.09 |
| 2025-12-03 | 2 | 2/2 | 1/2 | 1/2 | 634.37 | 318.86 |
| 2025-12-04 | 5 | 4/5 | 1/4 | 3/4 | 208.59 | 487.21 |
| 2025-12-05 | 2 | 1/2 | 0/1 | 1/1 | 565.37 | 70.67 |
| 2025-12-08 | 4 | 3/4 | 3/3 | 3/3 | 87.15 | 424.67 |
| 2025-12-09 | 2 | 2/2 | 1/2 | 1/2 | 937.23 | 246.37 |
| 2025-12-10 | 4 | 3/4 | 2/2 | 3/3 | 79.15 | 714.62 |
| 2025-12-11 | 3 | 3/3 | 1/3 | 1/2 | 862.94 | 50.76 |
| 2025-12-15 | 3 | 2/3 | 1/2 | 1/1 | 60.67 | 937.43 |
| 2025-12-16 | 4 | 4/4 | 4/4 | 4/4 | 262.65 | 494.11 |
| 2025-12-17 | 4 | 4/4 | 3/4 | 3/3 | 120.39 | 617.02 |
| 2025-12-18 | 7 | 4/7 | 4/4 | 4/4 | 175.94 | 401.87 |
| 2025-12-19 | 3 | 2/3 | 2/2 | 2/2 | 47.85 | 709.58 |
| 2025-12-22 | 4 | 3/3 | 1/3 | 2/3 | 580.66 | 468.28 |
| 2025-12-23 | 3 | 2/3 | 2/2 | 2/2 | 554.12 | 495.07 |
| 2025-12-25 | 2 | 1/2 | 1/1 | 1/1 | 32.79 | 785.06 |
| 2025-12-26 | 5 | 2/5 | 2/2 | 2/2 | 204.86 | 460.79 |
| 2025-12-29 | 5 | 2/4 | 2/2 | 2/2 | 114.44 | 431.75 |
| 2025-12-30 | 4 | 3/3 | 2/3 | 3/3 | 292.53 | 508.57 |
| 2026-01-05 | 4 | 2/4 | 0/2 | 0/2 | 310.52 | 247.35 |
| 2026-01-06 | 3 | 2/3 | 1/2 | 1/1 | 146.30 | 396.76 |
| 2026-01-07 | 3 | 1/3 | 1/1 | 1/1 | 105.82 | 518.52 |
### Holdout29

| Side | N | Immediate adverse | Adverse -> net6 positive |
|---|---:|---|---|
| ALL | 99 | 70/98 | 38/63 |
| SHORT | 85 | 62/84 | 34/56 |
| LONG | 14 | 8/14 | 4/7 |

LONG exploratory only:9 and14 entries; no reliable side-specific policy conclusion.

| Session | ENTER | Adverse/valid1 | Recovered by3 | Recovered by6 | Mean MAE6 | Mean MFE6 |
|---|---:|---|---|---|---:|---:|
| 2025-08-27 | 5 | 2/5 | 2/2 | 2/2 | 142.84 | 740.10 |
| 2025-08-28 | 9 | 5/9 | 2/5 | 3/5 | 343.05 | 265.73 |
| 2025-08-29 | 4 | 3/4 | 2/3 | 2/2 | 482.61 | 221.54 |
| 2025-09-01 | 3 | 3/3 | 1/3 | 2/3 | 1366.18 | 461.87 |
| 2025-09-02 | 4 | 2/4 | 2/2 | 2/2 | 95.94 | 916.30 |
| 2025-09-03 | 3 | 2/3 | 1/1 | 1/1 | 262.67 | 701.70 |
| 2025-09-04 | 4 | 2/4 | 2/2 | 2/2 | 323.00 | 589.82 |
| 2025-09-05 | 3 | 3/3 | 2/3 | 2/3 | 457.83 | 244.39 |
| 2025-09-08 | 5 | 4/5 | 4/4 | 4/4 | 197.59 | 558.42 |
| 2025-09-09 | 3 | 2/3 | 1/2 | 2/2 | 569.19 | 386.51 |
| 2025-09-10 | 5 | 5/5 | 4/5 | 5/5 | 371.63 | 431.71 |
| 2025-09-11 | 4 | 2/4 | 2/2 | 2/2 | 111.66 | 773.62 |
| 2025-09-12 | 4 | 2/4 | 2/2 | 2/2 | 75.14 | 223.54 |
| 2025-09-16 | 7 | 6/7 | 5/6 | 5/5 | 324.89 | 497.89 |
| 2025-09-17 | 2 | 2/2 | 1/2 | 1/2 | 373.32 | 177.87 |
| 2025-09-18 | 2 | 1/2 | 1/1 | 1/1 | 75.47 | 726.42 |
| 2025-09-19 | 0 | 0/0 | 0/0 | 0/0 | UNKNOWN | UNKNOWN |
| 2025-09-22 | 2 | 1/2 | 1/1 | 1/1 | 562.22 | 281.11 |
| 2025-09-24 | 2 | 1/2 | 1/1 | 1/1 | 0.00 | 671.64 |
| 2025-09-25 | 4 | 4/4 | 3/3 | 3/3 | 256.68 | 321.53 |
| 2025-09-26 | 2 | 1/2 | 0/1 | 1/1 | 199.12 | 604.09 |
| 2025-09-29 | 3 | 2/2 | 1/2 | 2/2 | 345.86 | 603.38 |
| 2025-09-30 | 4 | 3/4 | 3/3 | 3/3 | 302.81 | 382.74 |
| 2025-10-01 | 4 | 3/4 | 2/3 | 2/3 | 466.17 | 349.08 |
| 2025-10-02 | 5 | 4/5 | 2/4 | 2/4 | 423.65 | 180.46 |
| 2025-10-03 | 2 | 1/2 | 1/1 | 1/1 | 16.72 | 1412.23 |
| 2025-10-06 | 1 | 1/1 | 0/1 | 0/1 | 166.18 | 21.68 |
| 2025-10-07 | 2 | 2/2 | 1/2 | 1/1 | 102.04 | 476.19 |
| 2025-10-08 | 1 | 1/1 | 1/1 | 1/1 | 375.10 | 87.79 |

## Interpretation and limits

FOR: first-bar adverse concentration replicates; observed recovery by6 is51/60 and56/65; adverse-to-net6-positive32/53 and38/63; MAE-before-MFE34 and36 exceeds opposite20 and23; next selected72/95 and78/99.

AGAINST/uncertainty: many reverse-order or unavailable paths; same-bar extrema order unknown3/5; recovery-to-reference is weaker than sustained net-positive; no executable price/spread/queue evidence or counterfactual wait comparison. Hybrid has no direction, so same/opposite directional persistence is not identifiable. Holdout is earlier historical diagnostic with prior Selector exposure, not prospective or formal OOS. Dev uses OOF fold models while Holdout uses the final58-session model. No pooled analysis, timing search, normalization revision or rule fitting.

PIT: source feature/bar fingerprints verified; original runtime PIT/state0 inherited, not a fresh full-source independent audit.194 unique first entries and reference parity checked. Fresh Validation/OOS/Protected103 new access0; safety allfalse. Next: review diagnostic limitations and only with a separate instruction consider a hypothesis contract; no timing implementation in this task.
