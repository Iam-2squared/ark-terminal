# Phase57 Selector V1/V2/V3 historical pilot result — 2026-09-05

## Result status

The requested historical selection-outcome measurement completed successfully. This is a `REDUCED_UNIVERSE_PIPELINE_PILOT` and a `SURVIVORSHIP_LIMITED_RECONSTRUCTION`; it is not JPX-wide performance and it is not an exact TradingView realtime replay.

No selector winner is declared. Frozen V3.0 was not changed, Untouched OOS was not opened, and no result was promoted to Lane Y.

## Evidence boundary

| Item | Value |
| --- | --- |
| Dataset ID | `PHASE57_SELECTOR_YAHOO_5M_24626FD37F8633F4` |
| Requested sample | 200 symbols, deterministic SHA-256 sample |
| Successfully reconstructed | 199 symbols |
| Provider failure | `2877.T`: Yahoo returned no valid 5m data for the requested range |
| Eligible sessions | 59, from 2026-06-12 through 2026-09-04 |
| Complete market-state records | 459,521 |
| Development | 28 sessions, 2026-06-12 through 2026-07-22 |
| Purge | 2026-07-23 |
| Validation | 10 sessions, 2026-07-24 through 2026-08-06 |
| Purge | 2026-08-07 |
| Untouched OOS | 19 sessions, 2026-08-10 through 2026-09-04; sealed |
| Selection outcome rows exposed | 122,705, Development and Validation only |
| V3 threshold | 0.70, selected on Validation from the frozen grid |
| Primary horizon | 6 bars / 30 minutes |
| Cost-adjusted utility | TwoSidedOpportunity minus the frozen 10 bps cost; this is not PnL |

The ten-session Validation set was used to select the frozen-grid V3 threshold. Its metrics therefore are not Untouched OOS estimates.

## Primary Validation comparison: every selector's actual output

| Metric | V1 | V2 | V3 |
| --- | ---: | ---: | ---: |
| Target-ready selections | 16,003 | 13,063 | 2,654 |
| Mean selected per timestamp | 36.70 | 29.98 | 6.08 |
| Absolute session-open-to-selection move | 223.55 bps | 213.95 bps | 108.97 bps |
| Post-selection close return, 30m | +1.36 bps | +2.02 bps | +2.82 bps |
| UpExcursion, 30m | 58.27 bps | 56.16 bps | 60.52 bps |
| DownExcursion, 30m | 57.82 bps | 55.91 bps | 58.17 bps |
| TwoSidedOpportunity, 30m | 93.76 bps | 90.36 bps | 94.25 bps |
| Cost-adjusted utility, 30m | 83.76 bps | 80.36 bps | 84.25 bps |
| Late-detection candidate rate | 75.61% | 74.96% | 49.36% |

Using equally weighted session means, V3 minus V1 cost-adjusted utility was +1.66 bps with a session-clustered 95% t interval of [-7.04, +10.37]. V3 minus V2 was +5.07 bps with [-4.36, +14.49]. These intervals include zero, so this pilot does not establish a reliable all-selection utility advantage for V3.

The late-detection result is much clearer. The session-level V3 difference was -25.87 percentage points versus V1 and -25.26 points versus V2; the intervals were [-28.81, -22.94] and [-28.62, -21.90]. V3 had a lower late-detection rate on all ten Validation sessions. Development showed the same direction on all 28 sessions.

## Horizon comparison: every selector's actual output

Mean cost-adjusted TwoSidedOpportunity in Validation:

| Horizon | V1 | V2 | V3 |
| --- | ---: | ---: | ---: |
| 1 bar / 5m | 29.40 bps | 27.92 bps | 32.22 bps |
| 2 bars / 10m | 46.16 bps | 44.20 bps | 49.04 bps |
| 3 bars / 15m | 58.28 bps | 55.89 bps | 61.01 bps |
| 6 bars / 30m | 83.76 bps | 80.36 bps | 84.25 bps |
| 12 bars / 60m | 121.53 bps | 117.44 bps | 119.48 bps |

V3 has the highest raw mean from 5 through 30 minutes, while V1 has the highest 60-minute mean. The selected counts differ materially, so this table alone is not a fair capacity-matched winner test.

## Same-capacity diagnostic

This was added as a fairness diagnostic after the preregistered run and is not a replacement winner rule. At every timestamp, V1 and V2 were truncated to the same `K` as V3's Dynamic N.

| Validation metric | V1 Top-K | V2 Top-K | V3 Dynamic N |
| --- | ---: | ---: | ---: |
| Target-ready selections | 2,665 | 2,670 | 2,654 |
| Absolute pre-selection move | 272.38 bps | 245.51 bps | 108.97 bps |
| Post-selection close return, 30m | -1.26 bps | -0.25 bps | +2.82 bps |
| TwoSidedOpportunity, 30m | 120.87 bps | 114.76 bps | 94.25 bps |
| Cost-adjusted utility, 30m | 110.87 bps | 104.76 bps | 84.25 bps |
| Late-detection candidate rate | 73.55% | 71.27% | 49.36% |

On equally weighted sessions, V3 minus V1 utility was -26.53 bps with a 95% interval of [-33.62, -19.43]; V3 minus V2 was -20.23 bps with [-26.86, -13.61]. V3 lost this diagnostic on all ten Validation sessions and showed the same trade-off in all 28 Development sessions.

The directional 30-minute close return moved the other way: V3 exceeded capacity-matched V1 by +4.64 bps and V2 by +3.76 bps on session means, but both confidence intervals included zero. Selector-native two-sided utility and directional return are therefore giving different signals and must not be conflated.

## Direct answer to the late-selection hypothesis

The pilot supports the narrow hypothesis that Current V1/V2 select substantially more extended stocks than V3. It does not support the stronger statement that V1/V2 are merely selecting exhausted stocks with no opportunity left.

- V1/V2 had roughly twice V3's absolute pre-selection move and about 25 percentage points more late-detection candidates.
- Nevertheless, V1/V2 top ranks retained more raw two-sided movement than V3 at matched capacity.
- V1 rank buckets were monotone on 30-minute utility: 98.40, 88.50, 82.26, and 57.26 bps for ranks 1-10, 11-20, 21-30, and 31-40. V2 was also monotone: 91.01, 80.80, and 69.15 bps.
- V3 rank calibration was not monotone in this pilot: ranks 1-10 averaged 81.89 bps, while ranks 11-20 averaged 102.86 bps. The latter had only 261 observations; ranks 21-30 had only ten and are not interpretable.

The most defensible current description is: V1/V2 strongly favor already-active names, but their highest-ranked names often still retain substantial two-sided volatility. V3 suppresses extension and late-selection much more aggressively, at the cost of discarding some high-volatility opportunities.

## Dynamic N and ABSTAIN

Validation selected-count distribution:

| Selector | Min | P10 | Median | P90 | Max | Zero timestamps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V1 | 34 | 35 | 37 | 38 | 40 | 0 / 440 |
| V2 | 29 | 30 | 30 | 30 | 30 | 0 / 440 |
| V3 | 0 | 2 | 5 | 12 | 23 | 11 / 440 |

V3 therefore exercised a real absolute gate and ABSTAIN behavior. V2 remained effectively fixed at 30.

## Overlap diagnostic

Unique Validation symbol-timestamps:

| Group | N | Pre-selection move | 30m utility | Late rate |
| --- | ---: | ---: | ---: | ---: |
| V1 only | 2,685 | 277.00 bps | 98.05 bps | 81.12% |
| V1 and V2 only | 11,183 | 230.23 bps | 78.75 bps | 78.91% |
| V1, V2, and V3 | 1,880 | 117.05 bps | 89.92 bps | 51.49% |
| V1 and V3 only | 255 | 152.49 bps | 107.84 bps | 50.98% |
| V3 only | 519 | 58.33 bps | 52.10 bps | 40.85% |

V3-only discoveries were much less extended but also had substantially less remaining two-sided opportunity than V1-only names. This pilot therefore does not show that V3-only is a superior early-opportunity set. V2 was a strict subset of V1 at every Validation timestamp; `V2_ONLY` and `V2_V3` counts were zero.

## Opportunity Detection Lead Time

The frozen lead-time definition is the first selection of a symbol within a session, not a fully segmented economic episode.

| Pair | Paired session-symbols | Mean `other - V3` | Median | V3 earlier | Opportunity when V3 earlier |
| --- | ---: | ---: | ---: | ---: | ---: |
| V3 vs V1 | 403 | -30.77 min | -5 min | 30 / 403 | 130.10 bps |
| V3 vs V2 | 321 | -24.08 min | -5 min | 22 / 321 | 139.49 bps |

Negative lead means V3 was later. On shared session-symbols, V3 was usually not the first detector. The smaller set of cases where V3 was earlier retained high opportunity, but this is insufficient to claim an overall lead-time advantage.

## V2 persistence diagnostic

In Validation, 12,772 of 13,189 V2 selections were incumbents (96.8%); there were 370 new entrants and 47 re-entries. Target-ready `PERSISTENCE_1` selections averaged 78.20 bps utility, compared with 141.94 bps for `PERSISTENCE_0`. Transition-level new entrants averaged 144.98 bps, incumbents 78.49 bps, and dropped names 91.81 bps.

This is compatible with strong incumbency and with missed remaining opportunity among some dropped names, but it is descriptive rather than causal. New entrants and incumbents have different time-of-day and volatility mixes. The pilot does not authorize removing persistence or changing the sector cap.

## Deterministic replay and integrity

The complete 459,521-record benchmark was replayed independently a second time.

- Compressed selection ledger SHA-256 matched byte-for-byte on both runs: `9ab326d39a7f0180368e3efc301cde3e3ed3296113b40ce26e06cdb514c3942d`.
- Summary JSONs were identical after removing only `generatedAt` and the intentionally different output path. Normalized SHA-256 on both was `de8971bced17683ec18cadd71e520d320e7af4c425589636ac7a3f61934e3f82`.
- Frozen V3.0 digest remained `4f4b02fd7b115759c246bdd0927be09b45f1bbbc41774d9d80e1a6834923c93f`.
- Dataset archive SHA-256: `a56e524568f51ac745bb27a408896f9cd837801730d821c109b0d9ad3c5e46cc`.
- Primary compact summary SHA-256: `5688a7764fc24c4d876e8c38ae2ce960c3a1900113897875d4a447821d7e93b9`.

## Research decision

1. Do not modify Frozen V3.0 from this pilot.
2. Do not declare V3 the winner: its reduction in extension is clear, but its utility edge is not, and capacity-matched utility favors V1/V2 top ranks.
3. Do not declare V1/V2 exhausted-only detectors: their top ranks retain substantial two-sided opportunity.
4. Keep the 19-session Untouched OOS sealed until the release decision and analysis contract are explicitly fixed.
5. After OOS evaluation, run the separate same-Frozen-Entry / EXIT / Capital Allocation benchmark; selector-native two-sided utility is not realized Ark PnL.

## Safety

`executionAllowed`, `brokerWriteAllowed`, `excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`, `paperTradingAllowed`, `automaticPromotionAllowed`, `productionUpdateAllowed`, and `transmitted` all remained `false`.
