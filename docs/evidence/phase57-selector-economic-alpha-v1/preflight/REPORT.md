# Phase57 Frozen Selector Economic Alpha v1 - preflight

Status: **PRECOMMITTED / measurement not started**

This diagnostic stops Entry model research and tests the more fundamental question: whether the frozen `FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75` Top5 has model-free, fixed-horizon economic return after cost.

## Frozen population

| Item | Frozen value |
|---|---:|
| Development sessions | 76 |
| Selector cadence | 30 minutes |
| Selector timestamps | 760 |
| Top5 rows | 3,800 |
| Minimum-price eligibility | decisionPrice > JPY75 |
| DEV TEST / Fresh / OOS | sealed |

The Selector, Entry candidates, Candidate A, EXIT, Capital and Portfolio are unchanged. No Entry model is used.

## Predeclared measurement

- Immediate entry reference: first saved regular-session 5-minute open at or after the intended timestamp.
- Fixed exits: completed 5-minute close at the exact 5/10/15/30/60-minute target. No interpolation or next-price repair.
- Entry delays: 0/5/10/15/20/25 minutes.
- Costs: gross, existing canonical 5bps round-trip, and fixed 10bps/20bps sensitivities.
- Baselines: deterministic Random Top5 (`seed=20260919`) and PIT-known 30-minute Momentum Top5.
- Uncertainty: 10,000 session-cluster bootstrap samples (`seed=20260919`).
- DIP: one all-row intent-to-treat comparison only; no adoption or threshold tuning.

Bid/ask, order book, depth and the dated security-specific tick schedule are not saved. The run must not claim actual spread, slippage or executable fills. It may report nominal one-yen/price quantization separately, explicitly not as an observed tick size.

## Stop boundary

The run may classify Selector economic alpha and Entry timing. It may not unfreeze or retrain the Selector, create a new Entry, tune EXIT/Capital/Portfolio, open DEV TEST/Fresh/OOS, request provider data, merge main, or enable any trading path.

The full executable contract is [`protocol.json`](../protocol.json).
