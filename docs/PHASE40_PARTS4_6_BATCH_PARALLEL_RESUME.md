# Phase40 Parts4-6 — Batch, Parallel, Resume

## Scope

This phase wraps the existing walk-forward backtest engine with a historical-only batch runner.

### Part4 — Batch execution

- accepts many symbol/horizon tasks
- normalizes task contracts
- isolates one task failure from the rest of the batch
- summarizes completed and failed tasks

### Part5 — Controlled parallelism

- bounded `concurrency`
- independent task workers
- no shared mutable market state
- no external broker or Excel writes

### Part6 — Checkpoint and resume

- completed task IDs are skipped on resume
- failed task IDs are skipped unless `retryFailed=true`
- completed/failed summaries are persisted in an immutable checkpoint payload
- a restarted run can continue only the missing tasks

## Safety contract

The batch runner is `HISTORICAL_BACKTEST_ONLY`.

- broker writes: forbidden
- live trading: forbidden
- create/transmit/cancel/modify orders: forbidden
- Excel order writes: forbidden
- `ARK_ORDER!B9` writes: forbidden
- automatic Candidate promotion: forbidden
- Production updates: forbidden

The runner returns `brokerWrites: 0` and `liveOrders: 0`.

## Runtime usage

A caller may provide its own `runner(task)` for tests or alternate historical engines. Without one, each task is passed to `runWalkForwardBacktest`.

The result includes:

- `completed`
- `failed`
- `groupedBySymbol`
- `checkpoint`
- `rawResults`

Large local runs should persist `checkpoint` after each batch boundary and reuse it on restart.
