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
