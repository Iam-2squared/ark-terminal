# Phase57 V1 × V3 Minimal Hybrid — Implementation Completion

Date: 2026-09-05 JST  
Branch: `research/phase57-selector-v1-v3-minimal-hybrid`  
Mode: research-only; no promotion or order path

## Completion scope

The Minimal Hybrid is complete as an executable five-minute research Selector pipeline:

1. Frozen current V1 produces the broad candidate set.
2. Causal five-minute OHLCV/turnover features are extracted at a fixed cutoff.
3. Separate UpExcursion and DownExcursion ridge interfaces are trained.
4. Their inference is combined into a direction-agnostic Remaining Opportunity score.
5. That score produces a bounded soft adjustment to the V1 base score.
6. A Development-configured minimum quality and maximum count produce Dynamic N or soft ABSTAIN.
7. Ranked rows, selected rows, deterministic diagnostics, and a SHA-256 evidence digest are emitted.

This completion is functional, not a performance winner declaration. Synthetic fixtures make no performance claim. Real fitting and policy tuning remain restricted to an admitted Fresh Development split.

## Phase A amendment v1.1

The original Phase A file is retained byte-for-byte with SHA-256:

`7ca1b53a25ea756785ed0320e3887fb78ec6be557df53f0840638aeba14dafda`

The v1.1 amendment records these implementation-critical clarifications before Fresh Development outcomes are used:

- V1 Activity is preserved through broad recall.
- Stage 2 uses bounded soft rank adjustment, not V1/V3 intersection or V3 hard rejection.
- Raw extension remains diagnostic; it has no direct coefficient or threshold. Only predeclared extension × persistence/reversal interactions are trainable.
- UpExcursion and DownExcursion are separate training targets. TwoSidedOpportunity remains an evaluation quantity.
- Minimal execution uses five-minute OHLCV/turnover/context only.
- One-minute and microstructure enrichment, advanced models, specific bps expectations, and causal flow explanations are deferred.

## Frozen implementation boundaries

- Maximum trainable feature count: 12.
- Model family: two independent ridge regressions with one causal feature interface.
- Maximum absolute Stage 2 adjustment: 0.25.
- Missing values never become zero.
- Bars after the feature cutoff cannot affect inference.
- Morning and afternoon segments are not bridged for recent-path features.
- V3 symbols may appear only as external diagnostics and cannot affect output.
- Selector does not determine direction, entry timing/price, exit policy, or position sizing.
- The previously inspected 2026-06-12 through 2026-09-04 window is not admitted for Hybrid fitting, selection-policy tuning, or final evaluation.

## Safety

All execution, broker/RSS/Excel writes, live trading, paper trading, automatic promotion, production update, and transmission flags remain `false`. Lane Y, main, current V1/V2, and Frozen V3.0 are not modified.

## Next research gate

The next gate is Fresh Development data admission and Development-only screening/tuning, followed by frozen paired Validation and a separately untouched OOS. This implementation must not be promoted automatically even if later results are favorable.
