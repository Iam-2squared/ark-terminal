# Phase57 P25.2 - Trade-Frequency / OOS Expansion precommit

Status: **PRECOMMITTED RESEARCH DESIGN - NO OUTER-OOS WINNER SELECTION**

This part compares the Phase57 frozen DAY policy across five universe variants without relaxing Entry thresholds or changing the formal Fixed Horizon default.

## Fixed comparison variants

All five variants are evaluated and retained in the artifact. No variant is deleted after seeing OOS performance.

1. `FIXED_5` - `7203.T, 6758.T, 9984.T, 8306.T, 8035.T` for direct continuity with Phase57 P24.10.
2. `OLD_FIXED_30` - the existing `JP_LARGE_LIQUID_FIXED_30_V1` basket in `predict/daytrade/phase57-expanded-universe.js`.
3. `DYNAMIC_30` - point-in-time DAY head Top 30 from `selectJpxOpportunityUniverse`.
4. `DYNAMIC_40` - point-in-time DAY head Top 40 from the same selector.
5. `DYNAMIC_50` - point-in-time DAY head Top 50 from the same selector.

Dynamic 30/40/50 are a precommitted sensitivity set. **Outer OOS performance may not be used to select the value of N.**

## Frozen Phase57 policy

- Phase57 P24.10 Fixed Horizon baseline remains the formal default.
- Entry, horizon, model family, feature semantics, cost assumptions and inner-only selection rules are inherited unchanged from the P24.10 canonical runner.
- No Entry threshold relaxation is allowed to increase sample count.
- The P24.10 five-symbol benchmark remains the continuity control: 407 frozen Entry trades, after-cost Net +44.4002%, PF 1.2569, Win Rate 58.48%, MaxDD 55.72% on the pinned development OOS snapshot.
- Dynamic Risk remains a conditional overlay and is not substituted for the Fixed Horizon baseline in this experiment.
- Fresh untouched holdout is not consumed.

## Dynamic-universe information boundary

For every decision timestamp, dynamic membership must be produced only from fields known at or before that timestamp. The selector remains direction-agnostic and outcome-independent.

Forbidden inputs to universe ranking include:

- future return / future price / future label;
- trade outcome / win / realized PnL;
- current outer-OOS model performance;
- post-hoc winner lists;
- threshold search results derived from the evaluated outer OOS;
- any screener row timestamp later than the decision timestamp.

The existing P25 poisoning-invariance test remains mandatory. Sector cap and freshness guards remain enabled.

## Comparison window and fairness

- Use one common temporal OOS window for all variants.
- Use the same Phase57 frozen policy and same round-trip cost model for every variant.
- A symbol may contribute a trade only when it was in that variant's universe **before** the frozen Entry decision.
- Missing/stale universe snapshots fail closed; they are not backfilled from later snapshots.
- Bad OOS results are preserved in the artifact.

## Primary trade-frequency KPI

For each variant report:

- `Valid Frozen Entries / Trading Session` = valid frozen Entry count divided by distinct evaluated trading sessions.
- `Observed Days to 400 Valid Entries` = number of chronological trading sessions required to reach the 400th valid Entry; `null` when 400 is not reached in the common OOS window.
- `Pace-estimated Days to 400` = `400 / entriesPerTradingSession`; diagnostic only, never a promotion criterion when the observed 400th Entry is unavailable.

The P24.10 reference pace is approximately 407 trades / 38 trading sessions = 10.7 entries/session.

## Performance and risk metrics - all mandatory

- Hit Rate and Trade Win Rate, reported separately when both labels exist.
- After-cost Net using the existing Phase57 frozen trade-return semantics for direct P24.10 continuity.
- Profit Factor.
- MaxDD.
- Coverage with an explicit denominator.
- Symbol concentration: max share and HHI.
- Sector concentration: max share and HHI.
- Same-time correlation audit.
- Stability by trading session bucket and market regime.

## Same-time correlation / overcount guard

Raw trade count must not be interpreted as independent sample count when many signals fire together.

The P25.2 artifact must therefore include:

1. exact same-time clusters keyed by frozen Entry timestamp;
2. largest cluster size and share of trades occurring in multi-signal clusters;
3. conservative effective independent Entry count, treating one same-time cluster as one independent observation for sample-size diagnostics;
4. pairwise Pearson correlation of aligned horizon returns for symbol pairs with at least three same-time overlaps;
5. weighted mean absolute pairwise correlation and maximum absolute pairwise correlation.

This audit does not delete correlated trades from the P24.10-continuity Net/PF calculation. Instead it prevents the larger raw sample count from being presented as equally many independent observations. A separate session-equal-weight portfolio curve is also reported to show concentration-aware Net and MaxDD.

## Stability reporting

For every variant preserve, at minimum:

- per-session/day counts and returns;
- time-of-day bucket statistics;
- market-regime statistics;
- symbol statistics;
- sector statistics.

No losing bucket may be silently removed.

## Decision rule for this part

P25.2 is an **OOS comparison and measurement part**, not a current-OOS universe-size optimization. It may conclude that expansion is useful, neutral or harmful, but it may not choose Dynamic 30 vs 40 vs 50 by looking at the same outer OOS and then relabel that N as the new tuned default.

A successful expansion result requires evidence that the 400-entry collection time shortens without a material deterioration in after-cost Net, PF, MaxDD and stability, after concentration/correlation diagnostics are considered. Exact promotion thresholds are not invented post hoc in this part.

## Safety lock

The following remain `false` throughout P25.2:

- `executionAllowed`
- `brokerWriteAllowed`
- `excelOrderWriteAllowed`
- `rssOrderFunctionAllowed`
- `liveTradingAllowed`
- `paperTradingAllowed`
- `automaticPromotionAllowed`
- `productionUpdateAllowed`
- `freshHoldoutConsumed`

MARKETSPEED II / Excel / Python remain READ ONLY. `ARK_ORDER` and RSS order functions are out of scope.
