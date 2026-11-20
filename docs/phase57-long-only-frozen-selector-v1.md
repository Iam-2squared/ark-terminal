# Phase57 LONG-only Frozen Selector v1

## Status

`FORMALLY_FROZEN_DEVELOPMENT_ONLY`

This freeze prevents further Development-driven changes to the LONG Selector. It is not production-performance confirmation, Validation/OOS PASS, or authorization to integrate Entry, EXIT, or Allocation.

## Frozen selector

- LONG only.
- Saved Development C+D Ridge (`RIDGE_Y30`), lambda `0.1`.
- Exact ordered 15-feature causal universe embedded in the specification.
- Existing short-horizon Y30 target: six closed five-minute trading observations.
- A Decision Price must be the latest causally available closed market price and no more than five wall-clock minutes old.
- Eligibility is applied before ranking; no forward fill, interpolation, or future information is allowed.
- Ridge score descending, symbol ascending tie-break, Top5 at each fixed decision timestamp.
- Decision schedule (JST): `09:30`, `10:00`, `10:30`, `11:00`, `11:30`, `13:00`, `13:30`, `14:00`, `14:30`, `15:00`.
- Future +1/+2/+3/+5 opportunities use same-session future 5m High as primary and future 5m/terminal-auction Close as confirmation.
- Strict wall-clock +30m is the short-horizon evaluator; true MFE/MAE are clipped at zero in the favorable/adverse direction.
- Random baselines preserve the same decision timestamp, eligible universe, and `K=5`.

## Integrity anchors

| Component | SHA-256 / commit |
|---|---|
| Corrected Measurement Contract | `20356553ddece7309a6a00654c3b1e276d1a3466` |
| Eligibility Contract | `2998675a217317e4658272129d8759f16d11cc7e` |
| Frozen payload | `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59` |
| Development session list | `de4a4264a7d78446ff01f72c2f927cc29ec45b18126068ca2e9dc2cfe16c5483` |
| Development session identity | `b15042744a7213b49e43fd956b980b16e075a20ca30aee24b06d9fa5457eca08` |
| Ordered feature list | `31d56fc999210efb2551cb887b3d386f7a4b7c53e58ffd5f99b3fe76845d7800` |
| Model configuration | `feb51cefa401675f412b31426074e9b9a995414f2926515a0060620525dbdf21` |
| Saved Ridge artifact | `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb` |
| Development evidence file | `72f6c8590c94ead0aaa9288584ecd131ee4f363f2b7b3aa2a0128bd0a98c00d1` |
| Development evidence self-hash | `6bee3d44cbf6664886ccc9fd2de0624d1b3936e7e787187887fb912c78a5ae65` |

The machine-readable specification is `predict/research/phase57-long-only-frozen-selector-v1.json`. The exact aggregate evidence is `docs/evidence/phase57-long-only-frozen-selector-v1-development-evidence.json`. Run `python scripts/verify_phase57_long_only_frozen_selector_v1.py` to fail closed on any contract, model, feature-order, session, evidence, implementation, or safety drift.

## Frozen Development evidence

- 76 sessions, 760 decision timestamps, 3,800 Top5 selection events.
- Future +1%: Precision@5 76.39%, mean 3.81 hits, median 4, P(at least one) 98.55%, recall lift 4.15x.
- Future +2%: Precision@5 61.29%, mean 3.06 hits, median 3, P(at least one) 97.24%, recall lift 10.76x.
- Future +3%: Precision@5 47.26%, mean 2.36 hits, median 2, P(at least one) 92.50%, recall lift 18.44x.
- Future +5%: Precision@5 24.99%, mean 1.25 hits, median 1, P(at least one) 72.50%, recall lift 28.41x.
- Close confirmation: +3% Precision 43.58%, P(at least one) 90.92%; +5% Precision 22.95%, P(at least one) 70.00%.
- Median High time-to-hit: +1% 10m, +2% 15m, +3% 20m, +5% 30m.

## Known limitations

- Growth is weaker than Prime/Standard in Development evidence.
- Afternoon is weaker than earlier time groups in Development evidence.
- The five-minute freshness eligibility gate creates liquidity-composition bias.
- High touch is not executable-fill evidence.
- Ten selected events lack a continuous future 5m High path and remain non-hits in lower-bound decision distributions.
- All performance evidence is Development-only; Validation and OOS remain sealed.

## Safety and boundary

`executionAllowed`, `brokerWriteAllowed`, `excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`, and `paperTradingAllowed` are all frozen `false`. The formal freeze performs no fit and no provider request. Entry/EXIT/Allocation remain not started.
