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

## Zero-based, market-first Development contract

The main Development population is reconstructed from market data before either Selection or Entry is known:

1. acquire the widest defensible historical JPX universe and raw five-minute OHLCV;
2. build each decision-time market snapshot using completed bars only;
3. run the current Dynamic5m V1/V2 implementation on that snapshot;
4. apply the unchanged `PHASE57_P21_FROZEN_ENTRY` to each selected event;
5. freeze Entry v2 features;
6. build same-session future-only labels offline.

Downloading only symbols that later became P21 candidates is forbidden because it creates selection bias. The dataset therefore keeps `selectionEligible` and `oldP21SignalEligible` at separate levels. Phase 1 remains anchored to Frozen P21 candidates, while the broader selected-event layer is preserved for a later, explicitly approved filter-only versus full-replacement study.

The previous 41-event substrate is not discarded, but it is no longer the main Development population. It is a golden/parity/regression set for timestamp boundaries, selector parity, Frozen P21 parity, source lineage, Yahoo revisions, and leakage checks. It must not be mined for case-specific Entry rules, weighted specially in Development performance, or added to overlapping reconstructed events to inflate sample size.

## Source classification

Entry Quality v2 keeps these classes structurally separate:

- `ACTUAL_DURABLE`: evidence captured by the production measurement path. Its original completeness and formal-OOS classification are preserved without upgrade.
- `HISTORICAL_REPLAY_ARCHIVED_PIT`: a retained point-in-time artifact with explicit acquisition lineage and SHA-256.
- `HISTORICAL_RECONSTRUCTION_LATER_FETCHED`: historical data fetched after the decision time. It is always `DEVELOPMENT_ONLY`, `NON_PROSPECTIVE`, non-formal OOS, and not an archived point-in-time capture.

A later-fetched series may be replayed point-in-time by slicing at each historical decision timestamp, but that does not turn its source into contemporaneously captured evidence. No class may be promoted or renamed based on good results. Raw and normalized provider responses, query range, fetch timestamp, timezone, provider timestamp, adjusted/unadjusted semantics, parser/normalization version, and SHA-256 are retained so provider revisions can be detected.

Old `DYNAMIC_30`, `DYNAMIC_40`, `DYNAMIC_50`, and `FIXED_5` outputs are never reused as current Dynamic5m selections. Missing bars are not interpolated, fabricated, or replaced by current values. A replay point is blocked in full if a current-selector symbol lacks the fixed six completed-prefix bars. One `(sessionDate, decisionTimestamp, symbol)` is one event; V1/V2 memberships are lineage rather than duplicate rows.

## Historical universe and provider limitations

The first market-first archive uses Yahoo Finance Chart five-minute data, whose observed maximum range is 60 days. Yahoo is a first source, not a permanent requirement. If it cannot supply a defensible history, delisted-symbol coverage, market breadth, or corporate-action semantics, another lawful source must be evaluated with source-specific lineage instead of falling back to the 41 golden events.

The current universe is a JPX snapshot dated 2026-06-30 with 3,709 symbols, known before the replay start. It is explicitly not claimed as a complete historical JPX universe: post-snapshot IPOs can be missing, and delistings, symbol changes, halts, and corporate actions remain separate audit items. Current-listed symbols must not silently be projected backward for longer histories.

Replay starts on 2026-08-13 because the Frozen P21 history pack ends on 2026-08-12. Starting earlier with that pack would expose the scorer to outcomes that were still future at the earlier decision, even if Yahoo can return those bars. Extending the market window therefore requires a date-appropriate frozen prior-history artifact, not merely another data query.

## 2026-09-05 market-first integrity evidence

The immutable Yahoo archive requested all 3,709 universe symbols and fetched 3,705. Four remain explicit failures: 3681.T returned a provider not-found/delisted response; 5903.T, 7317.T, and 7940.T returned no usable five-minute series. The archive covers 17 sessions from 2026-08-13 through 2026-09-04 and contains 2,512,365 normalized regular-session bars.

The replay built 1,156 five-minute market snapshots. Of these, 1,074 met strict universe coverage and 82 were blocked as `HISTORICAL_UNIVERSE_COVERAGE_INSUFFICIENT`. Current Dynamic5m was recomputed on every ready snapshot with 1,074/1,074 internal deterministic parity. It produced 41,232 independent selected events over 397 symbols. No old selector output was substituted.

Applying the unchanged Frozen P21 Entry produced 445 independent candidate events across 16 sessions and 48 symbols: 297 LONG and 148 SHORT. Candidate membership is 107 V1-only, 338 V1+V2, and zero V2-only. There are zero duplicate events and zero PIT violations. Label completeness is 436/445 at +1, 421/445 at +2, 410/445 at +3, 382/445 at +6, and 327/445 at +12; the remainder stay incomplete rather than crossing the JST session boundary.

There are 176 Frozen P21 replay points blocked by `INSUFFICIENT_CLOSED_PREFIX_COVERAGE`. On 2026-08-14, all 63 ready market snapshots are blocked because 4478.T is selected but has at most four completed five-minute bars; 4480.T is also sparse at part of the session. The fixed six-bar policy is not relaxed and no synthetic no-trade bars are added.

The golden audit compares 41 prior events without adding them to the 445 Development count. Provider timestamp sequences match 41/41 golden prefixes, supporting provider-native interval-start semantics. Exact OHLCV context matches only 21/41 and exact completed-bar reference price matches 13/41; Yahoo revision and live-versus-historical differences therefore remain explicit. Twenty-five golden events are independently reconstructed with matching direction. These results establish data lineage and parity limits, not Entry performance.

Market-wide point-in-time breadth context is available for 445/445 candidates. TOPIX/Nikkei context and tick-schedule lineage remain unavailable and are stored as missing, never as zero or neutral. A strict Yahoo daily-history archive and per-decision prior-session slicer are implemented, including raw/normalized hashes and adjusted-close audit fields, but no daily archive is connected to this evidence snapshot; Daily Context coverage is therefore 0/445 rather than fabricated.

Checkpoint A (200 events) is reached; Checkpoint B (500) is 55 events short and Checkpoint C (1,000) is not reached. No Entry v2 model has been fitted and no threshold has been tuned. Model research remains blocked by incomplete Daily Context, incomplete universe/survivorship and corporate-action audits, incomplete golden OHLCV parity, and unfrozen Development/Validation/Untouched-OOS time boundaries. CI success or candidate count alone is not evidence of better trading performance.
