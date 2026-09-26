# Phase57 continuity checkpoint — State-Conditioned Signal Entry v1

## Status

- Study: COMPLETE / NOT ACCEPTED FOR PROMOTION.
- Start HEAD: `c7dfb8e18747e8a263e85a7e185abb964491c87e`.
- Population: 2,155/2,155; no Outcome filtering.
- Policy: pre-result lock preserved; UP=A, DOWN=D, NEUTRAL=C, UNKNOWN=E.
- Result: Entry v1 did not beat Immediate on the required multi-KPI trade-off.
- Recommendation: permit exactly one minimal Entry revision before moving to EXIT.
- STOP: no Entry v2 implementation, EXIT, Allocation, Fresh/OOS/Prospective,
  main merge, paper trading, or live trading was started.

## Key result

| KPI | Immediate | Entry v1 | Paired delta |
|---|---:|---:|---:|
| Fill | 1,963 / 91.09% | 1,857 / 86.17% | -106 / -4.92pp |
| Entry price improvement | — | — | -0.0184% |
| EntryPosition | 0.6540 | 0.6435 | -0.0171 |
| Range Retention | 35.012% | 35.408% | +1.734pp |
| +3 Capture | 649/761 / 85.28% | 542/761 / 71.22% | -14.06pp |
| +5 Capture | 357/408 / 87.50% | 307/408 / 75.25% | -12.25pp |
| 30m MFE / MAE paired | — | — | -0.0328pp / +0.1152pp |
| 60m MFE / MAE paired | — | — | -0.0293pp / +0.1461pp |

## Evidence entry points

- `docs/evidence/phase57-state-conditioned-signal-entry-v1/POLICY_LOCK.json`
- `docs/evidence/phase57-state-conditioned-signal-entry-v1/PROTOCOL.md`
- `docs/evidence/phase57-state-conditioned-signal-entry-v1/REPORT-ja.md`
- `docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/summary.json`
- `docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/lookahead-audit.json`
- `docs/evidence/phase57-state-conditioned-signal-entry-v1/validation/`

## Integrity and safety

- Dedicated tests: 14/14 PASS.
- Deterministic replay: byte-identical PASS.
- Immediate / old Signal parity: PASS.
- Look-ahead audit: PASS; closed-bar 377,450/377,450; pivot violations 0.
- Dedicated GitHub CI: run 35753310526 PASS on implementation HEAD
  `bceaaccd53d6d7243ad23d827047ad8314189aeb`.
- Full Predict regression: run 35753309424 PASS.
- LONG-only foundation: run 35753309014 PASS.
- Safety9: all false.
- Provider requests: 0.
- Protected Holdout/Fresh/OOS/Prospective opened: 0.
