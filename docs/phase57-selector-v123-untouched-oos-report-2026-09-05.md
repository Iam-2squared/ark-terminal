# Phase57 Selector V1/V2/V3 Untouched OOS evaluation — 2026-09-05

## Executive decision

The 19-session Untouched OOS evaluation completed under the Analysis Contract frozen before release. The contract-defined decision is:

> **NO STATISTICALLY ESTABLISHED WINNER**

Frozen V3.0 had the highest descriptive all-output 30-minute cost-adjusted TwoSidedOpportunity Utility, but neither of its session-equal paired 95% confidence intervals excluded zero. V3.0 therefore did not establish superiority over V1 or V2.

The OOS evidence did reproduce two distinct findings from Validation:

1. V3 selected materially fewer already-moved names. Its mean absolute pre-selection move was 90.24 bps, versus 193.72 bps for V1 and 190.66 bps for V2, and its late-detection candidate rate was 46.09%, versus 73.65% and 73.91%.
2. At the same selection capacity, V1 and V2 retained substantially more 30-minute two-sided opportunity than V3. V1 Top-K beat V3 on all 19 sessions; V2 Top-K beat V3 on 17 of 19.

The narrow claim that V3 reduces already-moved selection is supported out of sample. The stronger claim that V1/V2 merely select exhausted names with no opportunity remaining is not supported. No selector, threshold, feature, metric, sample, winner rule, or production setting was changed after OOS release.

## Freeze and release integrity

| Item | Frozen value / result |
| --- | --- |
| Repository branch | `research/phase57-selector-v3-large-scale` |
| Draft PR | `#576`; remained open, Draft, and unmerged |
| Frozen V3.0 commit | `5a2edced801a31c8cb578f7f765fca50937b3f4a` |
| Frozen V3.0 SHA-256 | `4f4b02fd7b115759c246bdd0927be09b45f1bbbc41774d9d80e1a6834923c93f` |
| OOS Analysis Contract ID | `PHASE57_SELECTOR_V123_OOS_ANALYSIS_CONTRACT_20260905` |
| OOS Analysis Contract SHA-256 | `1afe5e702088a04e7a5930d653c6e6cc92ba1853bbd5dabb752594844f9b0350` |
| Contract Freeze commit | `877481f2939dababe756441b0dd1ef92f9afbc87` |
| Local test gate | 58 passed, 0 failed |
| GitHub CI gate before release | 3 completed, 3 successful |
| OOS release guard | Exact confirmation plus exact Analysis Contract SHA required |
| OOS contract verified by runner | `true` |
| V3 threshold | `0.70`, unchanged from Validation |
| V1/V2 changed | `false` |
| V3 post-freeze changed | `false` |
| Automatic promotion | `false` |

The OOS dates and dataset identity were checked against the frozen contract before selector evaluation. The release happened only after the Contract Freeze commit existed and all associated GitHub workflows had succeeded.

## Evidence boundary

| Item | Value |
| --- | --- |
| Dataset ID | `PHASE57_SELECTOR_YAHOO_5M_24626FD37F8633F4` |
| Dataset canonical digest | `931e600bd13a491bd8ac12d90548d2ee40f17d092193d85a628fb8003827f43b` |
| Benchmark scope | `REDUCED_UNIVERSE_PIPELINE_PILOT` |
| Evidence classification | `SURVIVORSHIP_LIMITED_RECONSTRUCTION` |
| Historical construction | Later-fetched Yahoo 5-minute OHLCV reconstruction |
| Requested / reconstructed symbols | 200 / 199 |
| Full dataset | 59 sessions; 459,521 complete market-state records |
| Development | 28 sessions, 2026-06-12 through 2026-07-22 |
| Purge | 2026-07-23 |
| Validation | 10 sessions, 2026-07-24 through 2026-08-06 |
| Purge | 2026-08-07 |
| Untouched OOS | 19 sessions, 2026-08-10 through 2026-09-04 |
| OOS market-state records | 154,991 |
| OOS decision timestamps | 836 complete five-minute cross-sections |
| OOS selection outcome rows | 61,238 |

This is not JPX-wide historical performance and not an exact TradingView realtime replay. Current constituents and metadata were applied historically, so delistings, new listings, transfers, and symbol changes can create survivorship bias. Historical spread, depth, tick order, and quote staleness were unavailable and were not zero-filled.

The primary utility is a selector-native opportunity measure, not realized return or PnL:

`30m Cost-adjusted Utility = max(UpExcursion, DownExcursion) - frozen 10 bps cost`

It is direction-independent and does not show whether Frozen Entry, EXIT, or Capital Allocation could monetize the observed path.

## Validation-to-OOS replication

Descriptive all-output means are shown here to compare the pre-release Validation pattern with OOS. The winner decision uses the separately reported session-equal paired deltas.

| Metric | Validation V1 | Validation V2 | Validation V3 | OOS V1 | OOS V2 | OOS V3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Mean selected / timestamp | 36.70 | 29.98 | 6.08 | 36.70 | 29.85 | 6.71 |
| Absolute pre-selection move | 223.55 | 213.95 | 108.97 | 193.72 | 190.66 | 90.24 |
| Late-detection candidate rate | 75.61% | 74.96% | 49.36% | 73.65% | 73.91% | 46.09% |
| 30m post-selection close return | +1.36 | +2.02 | +2.82 | +0.25 | +0.60 | +2.95 |
| 30m TwoSidedOpportunity | 93.76 | 90.36 | 94.25 | 79.68 | 78.37 | 81.65 |
| 30m cost-adjusted utility | 83.76 | 80.36 | 84.25 | 69.68 | 68.37 | 71.65 |

All movement and utility values are in basis points. The OOS result preserved V3's lower-extension characteristic: relative to V1 and V2, V3's mean pre-selection move was lower by 53.42% and 52.67%, while its late-detection rate was lower by 27.55 and 27.81 percentage points.

The all-output V3 utility advantage remained small: +1.97 bps versus V1 and +3.29 bps versus V2 on row-weighted means. These descriptive differences are not the contract's inferential winner test.

## Primary OOS comparison

The frozen Primary uses one mean per selector per trading session, equal session weights, paired left-minus-right deltas, and a two-sided Student t 95% interval over the 19 session deltas.

| Paired comparison | Mean delta | 95% CI | Positive / negative sessions | Decision |
| --- | ---: | ---: | ---: | --- |
| V3 − V1 | +2.88 bps | [-3.01, +8.76] | 9 / 10 | Includes zero |
| V3 − V2 | +4.13 bps | [-2.39, +10.65] | 10 / 9 | Includes zero |
| V1 − V2 | +1.25 bps | [-2.31, +4.81] | 8 / 11 | Includes zero |

Every comparison had all 19 paired sessions. No selector had positive, zero-excluding pairwise intervals against both alternatives with positive-session direction consistency. The frozen winner rule therefore returns `NO_STATISTICALLY_ESTABLISHED_WINNER`.

Secondary metrics, same-capacity results, overlaps, lead time, persistence, time-of-day slices, and rank calibration are prohibited from overriding this Primary decision. The result does not authorize automatic promotion.

## Secondary horizon outcomes

Descriptive mean cost-adjusted TwoSidedOpportunity Utility for each selector's actual output:

| Horizon | V1 | V2 | V3 |
| --- | ---: | ---: | ---: |
| 1 bar / 5m | 23.60 bps | 23.12 bps | 25.39 bps |
| 2 bars / 10m | 37.60 bps | 36.87 bps | 39.86 bps |
| 3 bars / 15m | 47.91 bps | 47.05 bps | 50.29 bps |
| 6 bars / 30m | 69.68 bps | 68.37 bps | 71.65 bps |
| 12 bars / 60m | 100.86 bps | 98.53 bps | 100.33 bps |

V3 had the largest raw mean from 5 through 30 minutes, while V1 was slightly higher at 60 minutes. The selectors produced materially different selection counts, and no secondary horizon can replace the Primary 30-minute winner rule.

At 30 minutes, the detailed descriptive means were:

| Metric | V1 | V2 | V3 |
| --- | ---: | ---: | ---: |
| Target-ready selections | 30,489 | 24,856 | 5,569 |
| UpExcursion | 49.79 bps | 49.08 bps | 52.75 bps |
| DownExcursion | 48.57 bps | 47.85 bps | 48.19 bps |
| TwoSidedOpportunity | 79.68 bps | 78.37 bps | 81.65 bps |
| Cost-adjusted utility | 69.68 bps | 68.37 bps | 71.65 bps |
| Post-selection close return | +0.25 bps | +0.60 bps | +2.95 bps |

## Same-capacity diagnostic

For each timestamp, V1 and V2 were truncated to the same `K` selected by V3. If V3 selected zero, all three selected zero. This diagnostic was frozen before OOS release and cannot replace the Primary all-output winner decision.

| OOS metric | V1 Top-K | V2 Top-K | V3 Dynamic N |
| --- | ---: | ---: | ---: |
| Selected rows | 5,607 | 5,607 | 5,607 |
| Target-ready rows | 5,581 | 5,592 | 5,569 |
| Absolute pre-selection move | 302.56 bps | 262.31 bps | 90.24 bps |
| 30m cost-adjusted utility | 112.77 bps | 100.21 bps | 71.65 bps |
| Late-detection candidate rate | 76.72% | 75.52% | 46.09% |

| Session-equal paired comparison | Mean delta | 95% CI | Positive / negative sessions |
| --- | ---: | ---: | ---: |
| V1 Top-K − V3 | +41.68 bps | [+31.74, +51.62] | 19 / 0 |
| V2 Top-K − V3 | +29.15 bps | [+19.23, +39.07] | 17 / 2 |
| V1 Top-K − V2 Top-K | +12.53 bps | [+6.55, +18.51] | 19 / 0 |

This replicates and strengthens the Validation finding. V1/V2 top ranks were much more extended, but they still contained substantially more subsequent two-sided movement at matched capacity. The evidence rejects the strong exhausted-only interpretation for this pilot reconstruction. It does not prove a market-structure explanation for why continuation remained.

## Rank calibration

Mean OOS 30-minute utility by rank bucket:

| Rank | V1 utility (N) | V2 utility (N) | V3 utility (N) |
| --- | ---: | ---: | ---: |
| 1–10 | 96.98 (8,309) | 88.51 (8,344) | 68.87 (4,937) |
| 11–20 | 73.56 (8,276) | 65.51 (8,305) | 92.02 (584) |
| 21–30 | 57.35 (8,326) | 50.77 (8,207) | 110.02 (48) |
| 31–40 | 41.62 (5,570) | — | — |

V1 and V2 again showed strong monotone rank ordering. This supports the factual statement that their activity-heavy scores contain information about subsequent opportunity magnitude in this reconstruction.

V3 again was not monotone: lower-ranked buckets had higher means. The 21–30 bucket has only 48 target-ready rows, so its level must not be overinterpreted. The repeated non-monotonicity is evidence for investigating V3 rank calibration only in a future version and a new holdout; it does not authorize changing Frozen V3.0.

## Dynamic N and ABSTAIN

| Selector | Min | P10 | Median | P90 | Max | Zero timestamps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V1 | 32 | 35 | 37 | 39 | 42 | 0 / 836 |
| V2 | 28 | 29 | 30 | 30 | 30 | 0 / 836 |
| V3 | 0 | 2 | 6 | 13 | 28 | 7 / 836 |

V3 exercised the frozen absolute threshold and real ABSTAIN behavior. Whether its capacity is too restrictive remains a future-version hypothesis; threshold `0.70` was not changed.

## Selector overlap

Unique target-ready OOS symbol-timestamps:

| Group | N | Pre-selection move | 30m utility | Late rate |
| --- | ---: | ---: | ---: | ---: |
| V1 only | 4,987 | 221.94 bps | 75.11 bps | 76.74% |
| V1 and V2 only | 21,114 | 205.95 bps | 66.35 bps | 78.13% |
| V1, V2, and V3 | 3,742 | 104.40 bps | 79.74 bps | 50.05% |
| V1 and V3 only | 646 | 93.87 bps | 78.50 bps | 39.78% |
| V3 only | 1,181 | 43.39 bps | 42.29 bps | 37.00% |

V3-only selections were much earlier by the extension measures but had the lowest remaining utility. Thus, the OOS data do not support describing V3-only as an independently superior early-opportunity set. The highest-utility V3-containing groups also contained V1, but creating a `V1 AND V3` rule now is explicitly prohibited and remains only a future-version hypothesis.

V2 remained a subset of V1 at each OOS timestamp: the `V2 only` and `V2 + V3 only` groups were empty.

## Opportunity Detection Lead Time

The frozen pilot proxy compares the first selection of a symbol within a session; it is not a fully segmented economic opportunity episode. The lead value is `other selector time − V3 time`, so a negative value means V3 was later.

| Pair | Paired session-symbols | Mean lead | Median | V3 earlier | V3 TwoSidedOpportunity when earlier |
| --- | ---: | ---: | ---: | ---: | ---: |
| V3 vs V1 | 786 | -21.39 min | -5 min | 63 / 786 (8.02%) | 76.32 bps |
| V3 vs V2 | 631 | -14.64 min | -5 min | 64 / 631 (10.14%) | 119.05 bps |

V3 was not generally the earliest detector among shared session-symbols. The smaller set where V3 was earlier retained positive opportunity, especially versus V2, but these cases cannot be turned into a Frozen V3.0 condition after seeing OOS.

## V2 persistence diagnostic

| Transition / persistence group | Target-ready N | 30m utility | Pre-selection move | Late rate |
| --- | ---: | ---: | ---: | ---: |
| New entrant | 708 | 126.86 bps | 137.02 bps | 44.77% |
| Incumbent | 23,979 | 66.72 bps | 192.43 bps | 74.75% |
| Re-entered | 169 | 56.24 bps | 163.18 bps | 76.33% |
| Dropped | 310 | 67.20 bps | 142.62 bps | 67.74% |
| Persistence 0 | 780 | 119.39 bps | 139.70 bps | 48.21% |
| Persistence 1 | 23,569 | 66.62 bps | 192.68 bps | 74.78% |

There were 24,073 incumbent selections among 24,953 V2 selections, or 96.47%. The large descriptive new-entrant/incumbent difference reproduced Validation, but it is not a causal persistence effect. Time-of-day, volatility, market regime, sector, and candidate-state confounding remain. This does not authorize removing persistence or changing the sector cap.

## Time-of-day diagnostic

All selectors showed the largest raw 30-minute opportunity near the open and lower values later in the session.

| Time bucket | V1 utility | V2 utility | V3 utility |
| --- | ---: | ---: | ---: |
| 09:00–09:30 | 125.64 bps | 126.23 bps | 111.79 bps |
| 09:30–10:30 | 92.68 bps | 91.29 bps | 86.16 bps |
| 10:30–11:30 | 69.72 bps | 66.59 bps | 59.17 bps |
| 12:30–13:30 | 52.53 bps | 52.11 bps | 48.42 bps |
| 13:30–14:30 | 47.12 bps | 45.88 bps | 40.06 bps |
| 14:30–close | 45.14 bps | 44.96 bps | 35.60 bps |

This diagnostic was pre-registered but cannot justify excluding a time bucket after OOS release.

## Facts versus hypotheses

### Confirmed by this OOS reconstruction

- V3 substantially reduced pre-selection extension and the frozen late-detection candidate rate.
- V3 did not establish Primary all-output 30-minute utility superiority.
- Capacity-matched V1 and V2 top ranks substantially outperformed V3 on two-sided opportunity.
- V1/V2 rank buckets were monotone; V3 rank buckets were not.
- V3-only selections were earlier by extension but lower in remaining opportunity.
- V3 was usually later, not earlier, on the frozen first-detection proxy.
- V2 was overwhelmingly incumbent-heavy, and new entrants had higher descriptive utility than incumbents.

### Still hypotheses, not observed market-structure facts

- V3 may penalize already-moved names so strongly that it removes valid continuation opportunities.
- Remaining opportunity may require a conditional continuation-versus-exhaustion model rather than an activity-versus-extension opposition.
- V1/V2 activity information may be useful as an input to a future model.
- V3's score-to-opportunity calibration and Dynamic N may need redesign.
- Persistence requires counterfactual replay or matched comparison before causal conclusions.
- Institutional order flow or a generally dominant JPX 5–30 minute momentum-continuation mechanism was not measured by this pilot.

These hypotheses may inform V3.1/V4 research, but they cannot modify V3.0 and cannot be tested on these already-consumed 19 OOS sessions.

## Deterministic replay and artifact integrity

The released OOS benchmark was executed twice with the same dataset, frozen selectors, contract digest, and release confirmation.

| Artifact / check | Result |
| --- | --- |
| First selection ledger SHA-256 | `b2997c88946791ee912c64dc23b589b79cc458fe0f64e9de54fc46e4a29a1ddd` |
| Second selection ledger SHA-256 | `b2997c88946791ee912c64dc23b589b79cc458fe0f64e9de54fc46e4a29a1ddd` |
| Ledger byte comparison | Identical |
| Normalized summary SHA-256, run 1 | `151d2975a8db9a901c234962a4e4bbaf4d198ea624baddb3ee6efc98f8378a85` |
| Normalized summary SHA-256, run 2 | `151d2975a8db9a901c234962a4e4bbaf4d198ea624baddb3ee6efc98f8378a85` |
| Normalization | Removed only `generatedAt` and the intentionally different ledger output path |
| Primary released summary file SHA-256 | `0ea683329124a274dec062a78e8f1214e6f3c2f14209b8b6a316c2e5b02a4a8e` |

The replay is deterministic under the recorded inputs. The released output records `outerOosConsumed=true`, `outerOosReleaseExplicitlyConfirmed=true`, and `outerOosAnalysisContractVerified=true`.

## Final research disposition

1. Keep Frozen V3.0 unchanged.
2. Declare no statistically established selector winner on the contract-defined Primary comparison.
3. Do not use the same-capacity V1 result to override the Primary decision; retain it as strong diagnostic evidence.
4. Do not describe V1/V2 as exhausted-only detectors. They selected more already-moved names, but their top ranks retained substantial opportunity.
5. Do not create `V1 AND V3`, modify persistence, change the sector cap, change threshold `0.70`, or exclude samples from this OOS result.
6. Do not promote any result to Lane Y or main. Keep PR #576 Draft and V3 research-only.
7. Next, evaluate each frozen selector through the same Frozen Entry, EXIT, and Capital Allocation pipeline. That future comparison must separate selector-native opportunity from realized Ark acceptance, Net, PF, MaxDD, Win Rate, MFE, and MAE.
8. Evaluate any V3.1/V4 candidate only on a new future/prospective period or another previously unused historical holdout.

## Safety

The following remained `false` throughout contract freeze and OOS evaluation:

- `executionAllowed`
- `brokerWriteAllowed`
- `excelOrderWriteAllowed`
- `rssOrderFunctionAllowed`
- `liveTradingAllowed`
- `paperTradingAllowed`
- `automaticPromotionAllowed`
- `productionUpdateAllowed`
- `transmitted`

Lane Y main, Current V1/V2, Frozen Entry, EXIT, Capital Allocation, realtime state, durable evidence, ledger, workflows, and production safety boundaries were not promoted or altered by the OOS result.
