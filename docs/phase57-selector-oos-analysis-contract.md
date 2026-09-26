# Phase57 Selector OOS Analysis Contract

## Status and purpose

This contract is frozen before the 19-session Untouched OOS is released. Its machine-readable normative source is `predict/research/phase57-selector-oos-analysis-contract.json`; the adjacent SHA-256 file seals its exact bytes.

The purpose is to separate facts established on Development and Validation from hypotheses suggested by external review, then evaluate frozen Current V1, frozen Current V2, and frozen Selector V3.0 without post-OOS adaptation.

Frozen V3.0 remains commit `5a2edced801a31c8cb578f7f765fca50937b3f4a`, SHA-256 `4f4b02fd7b115759c246bdd0927be09b45f1bbbc41774d9d80e1a6834923c93f`. Nothing in this contract changes its features, weights, threshold, architecture, sector handling, or selection logic.

## Evidence separation

### Validation facts

- All-selection 30-minute cost-adjusted utility was 83.76 bps for V1, 80.36 bps for V2, and 84.25 bps for V3.
- The session-equal-weight V3-V1 delta was +1.66 bps with 95% CI [-7.04, +10.37]. The V3-V2 delta was +5.07 bps with [-4.36, +14.49]. V3 utility superiority was not established.
- Absolute session-open-to-selection move was 223.55 bps for V1, 213.95 bps for V2, and 108.97 bps for V3.
- Late-detection candidate rates were 75.61%, 74.96%, and 49.36%. V3 was lower on all ten Validation sessions.
- At V3-matched capacity, V1 Top-K utility was 110.87 bps, V2 Top-K was 104.76 bps, and V3 was 84.25 bps. V3 trailed on all ten Validation sessions.
- V1/V2 rank buckets were substantially monotone. V3 rank 1-10 versus 11-20 was not monotone, but the latter had only 261 observations.
- V3-only selections were less extended and less late, but had lower remaining utility than V1-only selections.
- Shared-symbol first-detection did not show V3 leading overall.
- V2 incumbents dominated selection counts, but the persistence outcome difference is descriptive and confounded rather than causal.

These facts support the narrow statement that V1/V2 are more activity- and extension-heavy. They do not support the stronger statement that V1/V2 select only exhausted names with no remaining opportunity.

### Future-version hypotheses only

The following may be preserved for V3.1 or V4 research, but they are not facts and cannot alter V3.0 or this OOS analysis:

1. Already-moved names may retain continuation opportunity when momentum quality, volatility persistence, market/sector alignment, and exhaustion evidence are considered jointly.
2. Continuation versus exhaustion may be a better conditional question than Activity versus Extension.
3. V1/V2 activity scores may contain useful future-opportunity information and should not automatically be discarded.
4. A future candidate may need better rank calibration.
5. Persistence requires counterfactual or matched replay rather than a raw entrant/incumbent mean comparison.
6. Frozen V3.0 Dynamic N may be too restrictive.

Claims about institutional order flow or dominant JPX 5-to-30-minute momentum continuation were not directly observed in this Pilot and remain external hypotheses.

## Evidence boundary

- Dataset: `PHASE57_SELECTOR_YAHOO_5M_24626FD37F8633F4`
- Dataset canonical digest: `931e600bd13a491bd8ac12d90548d2ee40f17d092193d85a628fb8003827f43b`
- Scope: `REDUCED_UNIVERSE_PIPELINE_PILOT`
- Evidence: `SURVIVORSHIP_LIMITED_RECONSTRUCTION`
- Acquisition: later-fetched historical reconstruction
- Untouched OOS: 19 sessions, 2026-08-10 through 2026-09-04

This is not an exact TradingView realtime replay and not JPX-wide historical performance.

## Primary metric

The immutable Primary Metric is 6-bar / 30-minute cost-adjusted TwoSidedOpportunity:

1. `UpExcursion = max(0, maxFutureHigh / anchorPrice - 1)`
2. `DownExcursion = max(0, 1 - minFutureLow / anchorPrice)`
3. `TwoSidedOpportunity = max(UpExcursion, DownExcursion)`
4. `Utility = TwoSidedOpportunity - 10 bps`

The anchor is the last causally closed bar price at selection. This is a selector-native opportunity metric, not realized PnL.

For every selector and session, take the arithmetic mean over target-ready selected symbol-timestamps. Give every trading session equal weight. Pairwise deltas are computed from the same sessions as left selector minus right selector, with no missing-session imputation.

## Statistical inference and winner rule

For every ordered selector pair, report:

- session-equal-weight mean paired delta;
- two-sided 95% Student t interval over paired session deltas;
- positive, negative, and tied session counts;
- paired and missing session counts.

A selector is a `STATISTICALLY_ESTABLISHED_WINNER` only if, against each of the other two selectors:

1. all 19 OOS sessions form valid pairs;
2. its mean paired delta is positive;
3. the lower bound of the two-sided 95% CI is strictly greater than zero; and
4. positive-delta sessions outnumber negative-delta sessions.

If no unique selector meets every condition, the result is `NO_STATISTICALLY_ESTABLISHED_WINNER`. Secondary metrics and diagnostics cannot override this rule, and no result can trigger automatic promotion.

## Secondary metrics

The following are fixed as Secondary before OOS release: 5m, 10m, 15m, and 60m utility; pre-selection absolute move; late-detection rate; UpExcursion; DownExcursion; TwoSidedOpportunity; post-selection close return; selected count; and rank calibration.

They must be reported but cannot be promoted into the Primary winner rule after results are seen.

## Pre-registered diagnostics

1. Same-capacity: at every timestamp set K to Frozen V3's selected count; compare Frozen V1 Top-K, Frozen V2 Top-K, and all Frozen V3 selections. K=0 selects none for every arm.
2. Overlap outcome groups: V1 only, V2 only, V3 only, V1+V2, V1+V3, V2+V3, and all three.
3. Opportunity Detection Lead Time: session-symbol first detection, paired with post-selection opportunity. It is a Pilot proxy, not a fully segmented economic episode.
4. V2 persistence: entrant, incumbent, dropped, re-entered, and frozen persistence buckets. These remain descriptive rather than causal.
5. Dynamic N and ABSTAIN: min, nearest-rank P10, median, nearest-rank P90, max, and zero-timestamp count.
6. Frozen time-of-day buckets: 09:00-09:30, 09:30-10:30, 10:30-11:30, 12:30-13:30, 13:30-14:30, and 14:30-close.

## Forbidden adaptations after OOS release

After the Untouched OOS is opened, this evaluation may not change V3.0 features, threshold, weights, architecture, metrics, Primary horizon, sample membership, symbols, time windows, sectors, or winner rule. It may not introduce V1 AND V3, remove persistence, or alter the sector cap.

Any V3.1/V4 hypothesis must use a new untouched historical holdout or future/prospective data. The current 19-session OOS cannot be reused to evaluate a next-generation candidate.

## Release guard and next stage

The OOS runner must verify both the V3.0 freeze digest and this contract digest. Releasing OOS additionally requires the exact irreversible-consumption confirmation and the exact contract SHA-256 on the command line. Dataset identity, canonical digest, selected V3 threshold, and the complete 19-session split must match this contract.

After OOS reporting, no selector is automatically merged or promoted. The separate downstream study passes every selector through the same Frozen Entry, EXIT, and Capital Allocation and compares Entry acceptance, Net, Profit Factor, Max Drawdown, Win Rate, directional MFE, and directional MAE.

## Safety

Lane Y Main and all production components remain unchanged. `executionAllowed`, `brokerWriteAllowed`, `excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`, `paperTradingAllowed`, `automaticPromotionAllowed`, `productionUpdateAllowed`, and `transmitted` remain false.
