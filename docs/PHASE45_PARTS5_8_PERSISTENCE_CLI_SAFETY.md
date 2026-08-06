# Phase45 Parts5-8 — Persistence, CLI, tests and safety

## Part5: Phase41 persistence integration

- accepts only `READY_FOR_PHASE41` historical batches
- reuses the existing Phase41 ingestion, manifest and checkpoint contracts
- blocks persistence when historical inspection or Phase41 integrity fails
- preserves immutable shard and checksum behavior

## Part6: daily historical CLI

`tools/run_phase45_historical_pipeline.mjs` reads CSV or JSON input, runs normalization and quality gates, then atomically persists the Phase41 shard, manifest, checkpoint and rejected report.

Example:

```powershell
node tools/run_phase45_historical_pipeline.mjs `
  --input data/historical/prices/7203.T.csv `
  --provider CSV `
  --output-dir data/data-lake
```

## Part7: fixture-based tests

Tests cover valid persistence plans, fail-closed invalid data behavior and safety invariants without network access.

## Part8: execution safety regression

The pipeline is data-only.

- broker writes: disabled
- Excel order writes: disabled
- MARKETSPEED II RSS order calls: disabled
- live orders: disabled
- automatic Candidate promotion: disabled
- Production updates: disabled
- human approval: required

No order, modify, cancel, trigger or broker mutation path is imported or called.
