# Phase42 Part1-3: Feature Store Foundation

## Scope

This phase adds the first read-only Feature Store layer above the Phase41 Data Lake.

## Part1: Feature schema

Each feature record contains:

- `featureSetId`
- `symbol`
- `sessionDate`
- `sourceShardId`
- `sourceChecksum`
- `generatedAt`
- numeric `features`
- deterministic `featureKey`
- deterministic `contentHash`

The unique key is:

```text
featureSetId:symbol:sessionDate
```

## Part2: Immutable storage contract

Feature records are stored in immutable shards with:

- deterministic checksum
- record count
- duplicate-key detection
- newest-generation deduplication
- schema version

A manifest records shard IDs, checksums, counts and immutability flags.

## Part3: Quality audit

The audit fails closed when it detects:

- mutable shards
- empty stores
- duplicate feature keys
- too few features
- excessive missing values
- manifest checksum mismatch
- manifest count mismatch
- missing shards

Warnings are emitted when source provenance is incomplete.

## Safety

Phase42 is `FEATURE_STORE_ONLY`.

- no broker writes
- no live trading
- no order create/transmit/cancel/modify
- no Excel order write
- no order-trigger write
- no automatic Candidate promotion
- no Production update

The highest state in this phase is `VALID` / `canUseForTraining: true`; it does not train, promote or deploy a model.
