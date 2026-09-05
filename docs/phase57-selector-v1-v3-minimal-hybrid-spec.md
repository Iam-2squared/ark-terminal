# Phase57 Selector V1 × V3 Minimal Hybrid — Phase A specification

## Frozen research question

Can a two-stage selector retain Current V1's broad activity-based opportunity recall while using V3-style extension, path, context, and tradability evidence to estimate how much opportunity remains after selection?

This is not `V1 selected AND V3 selected`. V3 membership is not required, and `Already Moved` is not a rejection label. Stage 2 may adjust a V1-like rank softly and may abstain only under a Development-frozen minimum-quality and Dynamic N policy.

The normative machine-readable contract is `predict/research/phase57-selector-minimal-hybrid-phase-a.json`. Its adjacent SHA-256 file seals the Phase A bytes before any new-dataset outcomes are inspected.

## Evidence boundary

The 59 sessions from 2026-06-12 through 2026-09-04, dataset `PHASE57_SELECTOR_YAHOO_5M_24626FD37F8633F4`, are consumed hypothesis-generation evidence. They cannot supply Hybrid Development, Validation, or OOS rows and cannot be used for weights, targets, thresholds, Dynamic N, rank-band filters, symbol rules, time filters, overlap rules, or case-derived gates.

The following are preserved as hypotheses, not facts: V1 may contain useful remaining-opportunity information; V3 may suppress valid continuation; and activity may carry both opportunity and late-detection risk. Claims about institutional flow, generally dominant JPX continuation, or an expected 75–80 bps outcome remain unproven.

## Two-stage architecture

### Stage 1 — V1-like broad recall

Run frozen Current V1 information on a causally complete cross-section and retain activity, turnover, score, and rank. Stage 1 is intentionally broad. It must not add a V3-membership gate or an extension rejection rule.

### Stage 2 — remaining-opportunity assessment

Measure five feature families using only fields available by the feature cutoff:

1. Momentum quality: MA/VWAP slope, acceleration, path efficiency, breakout persistence, and causally available RVOL persistence or decay.
2. Extension: VWAP/MA/ATR distance, intraday range position, distances from the high and low, breakout age, and consecutive expansion.
3. Path structure: direction-separated bullish/bearish structure plus direction-independent persistence, swing quality, reversal frequency, and efficiency.
4. Market/sector context: breadth, sector relative strength, and stock-versus-sector residual.
5. Tradability: spread, depth, observed price grid, liquidity, turnover stability, and staleness only when historically observed.

Unavailable microstructure remains `UNKNOWN` with an availability mask. It is never zero-filled. Activity cannot be penalized unconditionally; any extension effect must be conditional on momentum quality, context, or tradability.

The initial model family is limited to an interpretable additive score or regularized linear model. Advanced multi-task modeling is forbidden until a frozen Minimal Hybrid improves on a genuinely new OOS.

## Target candidates

For 1/2/3/6/12 bars, build separate UpExcursion, DownExcursion, TwoSidedOpportunity, path-persistence, pre-cutoff-momentum continuation, and reversal-risk targets. Future bars begin strictly after the cutoff and remain within the same session. A simple `Remaining_Move > 0` label is not the Primary.

No Primary target is selected in Phase A. Target choice, feature choice, model/weights, minimum quality, and Dynamic N are compared only inside nested/walk-forward Development. All of them must be frozen before Validation. Validation and OOS cannot cause a change.

## Dataset and split contract

A new dataset must pass the fail-closed admission guard. Minimum requirements are 120 chronological trading sessions, atomic complete five-minute cross-sections, one full purge session at each boundary, provider entitlement attestation, raw SHA-256 provenance, explicit timestamp/availability semantics, and no overlap or ancestry with consumed Selector evidence.

The frozen split is 60% Development, 20% Validation, and 20% untouched OOS, with one whole purge session removed before Validation and OOS. Development is the only released fold at dataset admission; Validation and OOS remain sealed.

The preferred historical lane is J-Quants Minute Stock Prices, aggregated from official one-minute OHLCV/turnover rows into fixed, non-overlapping JST five-minute bars. A point-in-time Listed Issue Master join is required for strong historical claims. No-trade minutes stay missing. If historical membership cannot be joined, the evidence must be labelled survivorship-limited and cannot make a strong claim.

No J-Quants acquisition may run until the Minute-OHLC add-on entitlement and API key are confirmed. Dataset preparation may implement and test parsing, aggregation, pagination, provenance, and admission before credentials exist.

## Evaluation

Compare frozen V1, frozen V3.0, and the frozen Minimal Hybrid on the same market states. Report counts, pre-selection move, Late Detection, every horizon, Up/Down/TwoSided opportunity, remaining opportunity, rank calibration, same-capacity results, and detection lead time.

Then pass each selector through the same Frozen Entry, EXIT, and Capital Allocation pipeline and report Entry acceptance, Net, PF, MaxDD, Win Rate, MFE, MAE, and trades per session. Selector, Entry, EXIT, and sizing responsibilities remain separate.

## Safety and promotion

Lane Y, main, V1, V2, Frozen V3.0, Frozen Entry, EXIT, Capital Allocation, realtime state, and production workflows are unchanged. Execution, broker/Excel/RSS writes, live/paper trading, automatic promotion, production update, and transmission all remain false. A positive result cannot promote the Hybrid automatically.
