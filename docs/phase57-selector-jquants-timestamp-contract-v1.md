# Phase57 J-Quants Minute timestamp contract v1

Status: `TIMESTAMP_CONTRACT_FROZEN`.

The former `BLOCKED_TIMESTAMP_CONTRACT_UNRESOLVED` status is superseded by direct Tick-to-Minute reconciliation. Earlier immutable evidence remains in history.

## Proof

`SOURCE_VALIDATION_ONLY`: 2025-01-14 and 2025-01-15, two symbols. The GitHub runner streamed one authorized J-Quants Tick gzip without persisting it, retained only the target symbols in memory, and compared every Minute row against competing interval definitions.

- 61,923 unique execution ticks
- 1,303 Minute rows
- `[Time, Time + 1 minute)`: 1,303/1,303 exact OHLC, Volume and Turnover matches; zero orphan Tick bins
- `[Time - 1 minute, Time)`: 0/1,303 matches
- `(Time - 1 minute, Time]`: 4/1,303 matches and is not an equivalent whole-session explanation
- all 16 required 09:00, 11:30, 12:30 and 15:30 comparisons match the start-labelled interval
- invalid target ticks, duplicate TransactionIds, invalid/duplicate Minute rows: zero

The established source contract is `BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES`. A Minute row at `T` represents executions where `T <= execution time < T + 1 minute`. Rows at 11:30 and 15:30 are separate terminal-auction source minutes. They are classified explicitly and are not treated as lunch or shifted backward.

For Ark regular five-minute decision bars, terminal-auction source minutes will not be mixed into a continuous five-minute interval. No-trade minutes remain absent and are never fabricated.

Raw CSV, signed URL, API response bodies, prices and the API key were not persisted or placed in GitHub artifacts. Only this structural evidence is frozen.

Live reconciliation: [run 34028904298](https://github.com/Iam-2squared/ark-terminal/actions/runs/34028904298), job `101474738422`, code `084a10b6fbc2de9cb733d52b3f205f98cf98af24`.

Evidence SHA-256: `74eca1a0b86eb3d5b06b2871dc7f55b7d076ca44e50a4e3a034018045a37d5b6`.

This freezes only source timestamp semantics. Adapter verification and a new source-only Pilot are subsequent gates. Formal data acquisition, Development, Validation and OOS were not opened by this evidence. All safety flags remain false.
