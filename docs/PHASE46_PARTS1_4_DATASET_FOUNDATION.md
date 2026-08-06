# Phase46 Parts1-4 — Training Dataset Foundation

## Goal

Create a deterministic, point-in-time training dataset above the Phase45 historical Data Lake without adding Vercel Functions or UI deployments.

## Parts

### Part1 — Dataset versioning

Each dataset stores a version, schema version, horizon, minimum history, row count and SHA-256 checksum.

### Part2 — Initial feature generation

The first compact feature set is intentionally simple and reviewable:

- close
- MA5 ratio
- MA20 ratio
- 5-session momentum
- 20-session volatility
- 20-session volume ratio
- intraday range

### Part3 — Point-in-time labels

Features only use rows at or before `asOfDate`. Labels use a later `futureDate`. Every row records the feature cutoff and label availability date, with `futureDataUsedInFeatures: false`.

### Part4 — Dataset audit

The audit blocks:

- duplicate symbol/date/horizon rows
- invalid temporal ordering
- any future-leak flag
- checksum mismatch

## Vercel usage

This delivery adds no API route, no UI page and no Vercel Function. It is local/CI-only to conserve the Vercel daily deployment and function budget.

## Safety

- broker writes disabled
- Excel order writes disabled
- MARKETSPEED II RSS order functions disabled
- live trading disabled
- automatic Candidate promotion disabled
- Production updates disabled
- human approval required
