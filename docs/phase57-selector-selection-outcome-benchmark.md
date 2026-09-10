# Phase57 Selector V1/V2/V3 Historical Selection Outcome Benchmark

## Scope

This benchmark executes frozen Current V1, frozen Current V2, and preregistered Selector V3.0 on the same causally reconstructed five-minute cross-section. It then freezes each selection before attaching future-path outcomes. It is research-only and does not modify Lane Y, Entry, EXIT, Capital Allocation, realtime state, ledgers, or production workflows.

Selector V3.0 remains fixed at commit `5a2edced801a31c8cb578f7f765fca50937b3f4a`, with SHA-256 `4f4b02fd7b115759c246bdd0927be09b45f1bbbc41774d9d80e1a6834923c93f`. This outcome work does not add a feature, change a weight or threshold candidate, or introduce a symbol/price exception.

## Causal order

1. Admit only bars with `availableAt <= featureCutoff`.
2. Reconstruct the shared market state at the decision timestamp.
3. Execute V1, V2, and V3 without future fields.
4. Freeze symbol sets, ranks, scores, and selection-time features.
5. Attach outcomes from bars with `availableAt > featureCutoff` in the same session.

## Selection outcome ledger

The runner writes a compressed NDJSON ledger separately from the compact summary JSON. It contains:

- one `SELECTOR_SELECTION_POINT` row per decision timestamp, including V1/V2/V3 symbol sets, selected counts, pairwise/triple intersections, and only-groups;
- one `SELECTOR_SELECTION_OUTCOME` row per selected selector-symbol-timestamp, including selector version, rank, score, selected count, price, sector, market, overlap category, selection-time features, pre-selection diagnostics, and future outcomes.

Pre-selection diagnostics include signed returns over 1/2/3/6/12 bars where available, signed return from session open, VWAP distance, distance from intraday high and low, ATR-normalized VWAP extension, cumulative volume, and cumulative turnover. Historical causal same-time RVOL is recorded as unavailable when the reconstruction cannot support it; it is never replaced by zero.

Post-selection diagnostics include final-close return, UpExcursion, DownExcursion, TwoSidedOpportunity, cost-adjusted utility, and barrier status over 1/2/3/6/12 bars. A bar touching both barriers remains `AMBIGUOUS_SAME_BAR`.

## Comparative reports

Each Development and Validation report contains:

- continuous pre-selection move versus post-selection opportunity diagnostics;
- 1/2/3/6/12-bar outcome summaries;
- time-of-day, sector, market-regime, price, liquidity, rank-decile, and explicit 1-10/11-20/21-30 rank buckets;
- V1/V2/V3 overlap counts;
- V2 `NEW_ENTRANT`, `INCUMBENT`, `DROPPED`, and `RE_ENTERED` outcomes;
- V2 persistence buckets, with warm-up `1/2` kept separate from steady-state thirds;
- first-detection lead time paired with the opportunity remaining at the earlier detection.

The pilot lead-time unit is explicitly a session-symbol first-detection proxy. It is not mislabeled as a fully segmented economic opportunity episode.

## Split and evidence boundary

Sessions are split chronologically into Development, Validation, and Untouched OOS, with whole-session purge boundaries. A complete five-minute cross-section is atomic. The V3 absolute threshold is selected only on Validation under the preregistered rule. Untouched OOS summaries and ledger rows remain sealed unless the runner receives the exact release confirmation.

The initial 200-symbol/60-day job is labeled both `REDUCED_UNIVERSE_PIPELINE_PILOT` and `SURVIVORSHIP_LIMITED_RECONSTRUCTION`. It validates acquisition, reconstruction, selector execution, outcome generation, paired comparison, and deterministic replay. It cannot be described as JPX-wide performance or exact TradingView realtime replay.

## Safety

All execution, broker-write, Excel-order-write, RSS-order, live-trading, paper-trading, automatic-promotion, production-update, and transmission flags remain false. The workflow has read-only repository permissions and no schedule, production persistence, OOS release, promotion, or merge step.
