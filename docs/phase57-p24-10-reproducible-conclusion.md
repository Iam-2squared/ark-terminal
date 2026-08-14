# Phase57 P24.10 reproducible development conclusion

## Canonical data identity

- OOS canonical source run: `31785422471`
- OOS snapshot SHA-256: `10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a`
- Data end: `2026-08-12T06:30:00.000Z`
- Canonical OOS window: 56 days
- P23.50 training source: pre-existing P23.46 byte-frozen snapshots from run `31639594728`
- Measurement replay is offline with intercepted network access.

P24.10 requires two independent replicas to produce byte-identical integrated result JSON before any Phase57 completion decision is accepted.

## Reproducible development result

On the pinned canonical snapshot, both replicas produced result SHA-256 `ee25cc798afb8cf80e2a7ce992ad51bc252f5ec08b0c5db1ae7febf226124df1` with 407 identical frozen Entry trades.

| Metric | Fixed horizon baseline | P24.7 integrated overlay |
|---|---:|---:|
| Trades | 407 | 407 |
| Cost-adjusted Net | +44.4002% | +31.3531% |
| Profit Factor | 1.2569 | 1.2129 |
| Win rate | 58.48% | 61.43% |
| MaxDD | 55.72% | 50.90% |
| Final equity | 1.4440 | 1.3135 |
| Mean MFE | +1.0590% | +0.9509% |
| Mean MAE | -0.9066% | -0.8097% |
| Mean bars held | 23.79 | 17.40 |

Dynamic Risk is genuinely active: 31 risk-ready observations, 11 risk-ready trades, and 5 risk-triggered trades. Fresh P23.51 holdout is unconsumed.

## Decision

The integrated overlay is reproducibly profitable and improves MaxDD and win rate, but it does **not** beat the identical fixed-horizon baseline on Net return or Profit Factor. Eligible stability partitions also include losing LONG, symbol, and time-of-day groups. Phase57 therefore does not claim that Dynamic Risk caused the aggregate profit improvement and does not promote the integrated overlay as the default.

The Phase57 development default is frozen as the **fixed-horizon baseline**. P23.50 Dynamic Risk remains a research/conditional overlay for later fresh validation. This is a development conclusion only; it is not production readiness and does not authorize paper or live trading.

## Safety and methodology

Entry/horizon semantics remain frozen; P23.50 uses prior sessions only; there is no same-OOS threshold sweep, post-hoc symbol filtering, Entry retuning, or Fresh P23.51 holdout consumption. `executionAllowed`, `brokerWriteAllowed`, `excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`, `paperTradingAllowed`, `automaticPromotionAllowed`, and `productionUpdateAllowed` remain false.

## Next stage

Run the precommitted one-shot Fresh P23.51 holdout only after its readiness conditions are satisfied. Phase58 should begin only after that validation decision; do not treat the reproducible historical OOS result alone as production evidence.
