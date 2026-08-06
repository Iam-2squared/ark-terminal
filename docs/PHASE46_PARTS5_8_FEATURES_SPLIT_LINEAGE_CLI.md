# Phase46 Parts5-8: Features, Split, Lineage and CLI

## Scope

This grouped delivery completes the first training-dataset builder without adding Vercel Functions or UI deployments.

### Part5: extended features

Adds deterministic point-in-time features for RSI approximation, ATR approximation, VWAP, Bollinger z-score, volume ratio and volatility.

### Part6: chronological split

Creates train, validation and test partitions strictly in time order. Random shuffle is not permitted.

### Part7: lineage

Stores dataset version, source manifest checksum, feature version, row count and a SHA-256 lineage checksum.

### Part8: local CLI

`tools/run_phase46_dataset_pipeline.mjs` builds, audits and atomically writes a local training dataset.

Example:

```powershell
node tools/run_phase46_dataset_pipeline.mjs `
  --input data/data-lake/shards/latest.json `
  --dataset-version phase46-v1 `
  --source-manifest-checksum <checksum> `
  --output data/training/phase46-dataset.json
```

## Fail-closed rules

The pipeline blocks duplicate rows, future-data flags, invalid feature cutoffs, temporal split violations and missing lineage.

## Vercel budget

No API route, serverless function, UI page or deployment-only feature is added. The implementation is local/CI-only.

## Safety

- broker writes: disabled
- Excel order writes: disabled
- MARKETSPEED II RSS order calls: disabled
- live orders: disabled
- automatic Candidate promotion: disabled
- Production updates: disabled
- human approval: required
