# Phase57 Selector V3.0 preregistration

Frozen on 2026-09-05 before any large-scale V1/V2/V3 historical outcome was inspected. The machine-readable contract is `predict/research/phase57-selector-v3-freeze.json` and is the normative source.

## Boundary

V3.0 is a research-only challenger. It does not change Lane Y, Current Dynamic5m V1/V2, Frozen Entry, EXIT v3/v4, Capital Allocation, realtime state, durable evidence, ledgers, production workflows, or any execution boundary. A good benchmark result cannot promote V3 automatically.

All broker, Excel-order, RSS-order, live, paper, promotion, production, and transmission controls remain false.

## Frozen question

Current V1/V2 may be closer to an activity/abnormality detector with liquidity and incumbency bias than a remaining-opportunity selector. V3.0 tests one minimal alternative:

1. causal OHLCV eligibility;
2. structural tradability;
3. direction-agnostic momentum;
4. a separate extension/exhaustion penalty;
5. market and sector breadth context;
6. a fixed interpretable utility score;
7. an absolute validation-fitted gate, dynamic selected count, and ABSTAIN.

There is no price-under-100 rejection and no case-specific symbol rule. V3.0 has no persistence input. Historical microstructure is not silently reconstructed: it is excluded from the primary arm and must remain UNKNOWN in diagnostics when unavailable.

## Fixed score

The score is:

`0.30 * structuralTradability + 0.30 * momentum + 0.25 * remainingHeadroom + 0.15 * marketSectorContext`.

Structural tradability combines point-in-time cross-sectional percentiles of cumulative turnover and the median turnover of the latest six causally closed bars.

Momentum combines absolute ATR-normalized three-bar and six-bar returns with six-bar path efficiency. Extension is not momentum: remaining headroom subtracts a frozen penalty based on VWAP extension, session-open move, and consecutive expansion bars. Context measures alignment with contemporaneous market/sector breadth and penalizes extreme stock-versus-sector separation. Missing sector context is UNKNOWN and available context weights are renormalized; it is never changed to zero.

The raw score is not called a probability.

## Calibration and selection

Candidate score thresholds are fixed at 0.45, 0.50, 0.55, 0.60, 0.65, and 0.70. One threshold is selected on Validation only using the preregistered primary six-bar cost-adjusted two-sided utility objective and sample requirements. Outer OOS cannot affect it. If no threshold satisfies the sample floor, V3 abstains everywhere.

At each timestamp V3 may select at most 30 and at most five per sector, but it never fills to a fixed count. Zero selections is valid.

## Causality and targets

Every bar must expose an `availableAt` timestamp not later than the decision cutoff. A provider BAR_OPEN timestamp may be normalized only by the declared five-minute interval. Conflicting duplicate bars fail closed. Required features with missing inputs fail closed for that symbol.

Selector-native targets are independent of Frozen Entry: UpExcursion, DownExcursion, TwoSidedOpportunity, barrier reachability, and cost-adjusted utility over 1/2/3/6/12 future bars. When both symmetric barriers are touched in one OHLC bar, the result is `AMBIGUOUS_SAME_BAR`; no intrabar order is invented.

Frozen Entry evaluation is a separate downstream benchmark so selector failure and Entry rejection are not conflated.

## Split and evidence labels

The dataset is split chronologically by whole trading sessions: 50% Development, 20% Validation, 30% untouched OOS, with one entire purge session at each boundary and at least 30 sessions total. A complete 5-minute cross-section is atomic and cannot be split across folds.

Every run must identify itself as exact replay, later-fetched reconstruction, or survivorship-limited reconstruction. Later-fetched Yahoo bars are useful for a paired benchmark but may not be described as exact TradingView realtime replay.

## No post-hoc repair

After this freeze, large-sample outcomes cannot be used to add features, alter weights, add a low-price ban, change thresholds outside the fixed grid, or create special filters. Any genuine implementation bug must be documented as semantics-preserving; a semantic change requires a new candidate version and a new untouched OOS set.

