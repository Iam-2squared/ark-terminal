# Phase57 Entry Quality v2 Research Contract

Status: isolated research branch only. This document does not authorize promotion to Lane Y main.

## Baseline protection

The paired baseline is `PHASE57_P21_FROZEN_ENTRY`. Dynamic5m Selection, EXIT v3/v4, Capital Allocation, durable evidence, and realtime Lane Y remain unchanged. Entry v2 research must not modify selector behavior, EXIT behavior, capital allocation, or any execution boundary.

All execution/write/promotion flags remain false. No MarketSpeed II / RSS order function may be introduced.

## Research hypothesis

The current P21 Entry current-row feature feed is dominated by same-session completed 5-minute context. Entry Quality v2 tests whether point-in-time market context, daily structural context, intraday state, microstructure diagnostics, and state change improve paired OOS Entry quality without changing Selection or EXIT.

This is not a claim that Daily Context is beneficial. It is a falsifiable OOS hypothesis.

## Target definition

Entry v2 changes the research question from a single directional probability to conditional entry quality.

For each candidate timestamp, research labels may include path returns at multiple horizons, MFE, MAE, time-to-MFE, and time-to-MAE. These are labels only and must never be present in the current feature vector. LONG and SHORT quality are evaluated asymmetrically.

No single utility function such as `MFE - alpha * MAE` is frozen yet. Return, MFE, MAE, timing, coverage, and cost-adjusted expectancy must be persisted separately before any utility weights are selected.

Triple-barrier labels may be evaluated as diagnostics, but cannot silently replace EXIT v3/v4 in the paired Entry experiment.

## Context hierarchy

1. Market Context: broad-market return, breadth, volatility, and sector-relative context.
2. Universe Diagnostics: price/tick relationship, turnover, liquidity, and spread proxy. No post-hoc low-price cutoff is frozen by this foundation.
3. Daily Context: retain at least 250 daily bars where available; initial feature windows are 5/20/50/100 days. Retention length and feature windows are intentionally separate.
4. Intraday Context: completed same-session 5-minute prefix only, including VWAP distance, relative volume, multi-horizon momentum, acceleration/deceleration, return from open, and range position.
5. Novel Information: state deltas from the prior evaluation so persistent state can be distinguished from genuinely new information.
6. LONG Quality / SHORT Quality: separate research outputs.
7. Calibration / Abstention: only after OOS model design is frozen.

## Point-in-time requirements

- Daily and intraday builders reject bars after `asOf` rather than silently filtering them.
- Future outcome fields are forbidden in feature vectors.
- Daily data for an intraday timestamp must represent only information actually available at that timestamp. Same-day final daily OHLCV must not leak into an intraday decision.
- Any external market/sector inputs must carry their own point-in-time lineage before they can be used in formal OOS evaluation.

## Universe policy

The 2026-09-04 8918.T 10-yen SHORT is a diagnostic case, not justification for a hand-written `price >= 100` rule. Initial research measures tick-to-price ratio and related tradability variables. Hard eligibility thresholds may only be proposed after development/validation separation and must be evaluated on untouched OOS.

## State/novelty policy

Repeated signals for the same symbol must distinguish persistent state from new information. The 336A.T 11:20 and 11:30 LONG cases motivate the diagnostic, but cannot define its threshold. Novelty features are measured generically from state changes.

## Validation contract

Development -> validation -> untouched OOS -> prospective.

The final paired comparison holds constant:

- Dynamic5m Selection
- market data
- EXIT v3/v4
- Capital Allocation
- transaction-cost assumptions

Primary diagnostics include +1/+2/+3/+6/+12-bar path returns, MFE, MAE, time-to-MFE/MAE, cost-adjusted expectancy, precision, coverage, and stratification by LONG/SHORT, price/tick/liquidity, volatility, time-of-day, sector, and selector V1/V2.

No automatic promotion is permitted regardless of measured performance.

## Current implementation stage

The initial module is deliberately feature-vector-only. It emits no LONG/SHORT signal and cannot be wired into Lane Y without a separate explicit research step. This allows data lineage and feature semantics to be tested before choosing the model architecture or thresholds.

## Large-sample source contract

Entry Quality v2 now keeps two evidence tracks structurally separate:

- `ACTUAL_DURABLE` contains only Frozen P21 Entry events already present in durable Dynamic5m B/D evidence. The source artifact's completeness and formal-OOS classification are preserved without upgrade.
- `HISTORICAL_RETROSPECTIVE_REPLAY` reapplies the current `INTRADAY_DYNAMIC_5M_UNIVERSE_V1` selector to retained point-in-time marketwide rows, then applies the unchanged Frozen P21 Entry. It is always `DEVELOPMENT_ONLY`, `NON_PROSPECTIVE`, and excluded from every prospective denominator.

Old `DYNAMIC_30`, `DYNAMIC_40`, `DYNAMIC_50`, and `FIXED_5` memberships are never accepted as current Dynamic5m replay results. A replay point is blocked in full if any symbol selected by the current selector lacks a stored session-bar history or a six-bar closed prefix. Missing bars are not refetched, interpolated, or filled with current values.

Candidate events and selector memberships are different units. One `(sessionDate, selectionTimestamp, symbol)` event is stored once; V1/V2 membership is attached as diagnostic lineage and must not duplicate the candidate or its labels. Actual and replay events with the same event identity are retained in their respective audit trails, but the replay copy is excluded from the independent historical Development count.

## 2026-09-05 integrity evidence

The first all-candidate audit found six `ACTUAL_DURABLE` Frozen Entry events across 2026-09-03 and 2026-09-04: four unique symbols, three LONG and three SHORT. All six are both V1 and V2 selector members, but remain six events rather than twelve rows. Canonical daily-bundle bars reproduce every feature cutoff under `bar.timestamp + 5 minutes <= decisionTimestamp`; PIT violations are zero and +1/+2/+3/+6/+12 labels are complete for all six events.

Both source sessions remain incomplete and non-formal: 2026-09-03 has 13/68 captured points and 2026-09-04 has 15/68. These rows are diagnostics, not formal OOS or prospective performance evidence.

GitHub Actions retained 111 raw marketwide snapshots across 2026-09-01 through 2026-09-04. Reapplying the current Dynamic5m V1 selector reproduces all 111 stored measurements exactly. Strict bar coverage is available for 26 points (12 on 2026-09-03 and 14 on 2026-09-04). The other 85 points fail closed: all 49 points on 2026-09-01 lack a stored session-bar archive, and all 36 points on 2026-09-02 lack bars for part of the current selector membership. No old-selector result is substituted.

Applying the unchanged Frozen P21 Entry to the 26 replayable points reproduces six candidates, with zero scorer-blocked points and zero PIT violations. All six candidate-event identities match the six `ACTUAL_DURABLE` events, so all six replay copies are excluded from the independent historical Development set. The current independent Historical Replay increment is therefore zero, not six.

No Entry Quality model fitting or threshold tuning has started. The next admissible expansion is additional retained current-selector bar coverage or newly accumulated durable Frozen Entry evidence, followed by the same integrity audit.
