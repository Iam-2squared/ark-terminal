# Phase49 — Full Paper Forward Cycle

Phase49 implements a deterministic, local-only paper trading cycle for forward validation.

## Flow

Prediction input → paper-only order idea → simulated fill → cost-aware settlement → metrics summary → audit → atomic local persistence.

## Included metrics

- trade count
- win rate
- net PnL
- Profit Factor
- maximum drawdown
- equity multiple

## Safety guarantees

The following remain hard-disabled:

- broker writes
- Excel order writes
- MARKETSPEED II RSS order functions
- live orders
- automatic Candidate promotion
- Production updates

All generated orders are marked `PAPER_ONLY`, `transmissionAllowed: false`, and `transmitted: false`.

## CLI

```bash
node tools/run_phase49_paper_forward.mjs --input ./input.json --output ./data/phase49-paper-forward.json
```

The output is written atomically only after checksum and safety audit succeeds.
