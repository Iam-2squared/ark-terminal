# Phase57 EXIT v4 — J-Quants Stage 1 Minimal Quality / Parity Pilot

Status: `STOP_DATA_SOURCE_NOT_READY`

The precommitted provider probe ran through metadata only and stopped before Tick raw download because the historical Tick transport was month-scoped. Final evidence and the F–T gate report are in `phase57-exit-v4-jquants-stage1-result.md`.

This stage is restricted to source semantics and input-substrate parity. It does not calculate Frozen EXIT v3/v4 performance, MFE/MAE, future labels, winner/loser groups, or Entry capacity. Development, Validation, Protected 180–282, Fresh Validation, and Fresh OOS remain locked.

## Result-blind scope

| Item | Frozen value |
|---|---|
| Eligible sessions | 2025-08-27, 2025-10-09, 2025-11-25 (already exposed PURGE evidence) |
| Tick probe | 2025-08-27, code 86970, predeclared boundary minutes only |
| New session access | 0 |
| Raw persistence | forbidden |
| Sanitized artifact retention | 7 days |
| EXIT outcome access | 0 |

The Tick CSV is streamed in memory and filtered to the predeclared code and minute labels. Raw prices, raw trades, signed URLs, and raw minute rows are never written to the artifact.

## Questions and fail-closed rules

| Question | Evidence | Fail-closed treatment |
|---|---|---|
| Does minute `Time` label the interval start? | Exact OHLCV comparison against ticks floored to `HH:mm` | Fewer than three observed exact matches or an ambiguous hypothesis remains `UNRESOLVED` |
| Can `availableAt` be historical-provider exact? | Minute/Tick update cadence and endpoint schema | No. The provider supplies these historical datasets daily around 16:30 and exposes no per-bar `availableAt` |
| Is an absent minute always no-trade? | Minute, Tick, dated master, daily bar | No. Unresolved absence stays `UNKNOWN`; only Tick-present/minute-absent is a direct provider inconsistency |
| Are intraday prices adjusted? | Tick/minute/daily raw OHLCV parity and daily corporate-action fields | Treat as unadjusted only when selected-session raw parity passes; historical coverage remains partial |
| Is PIT universe exact? | Dated master snapshot | Listed-at-date is supported; exact merger/code-change/delisting lineage is not |

## Candidate 5-minute contract

This contract is frozen only if the Tick hypothesis passes:

| Field | Contract |
|---|---|
| Source minute | `[HH:mm:00, HH:mm+1:00)` |
| First regular 5m bar | 09:00, 09:01, 09:02, 09:03, 09:04 |
| `barStart` | 09:00 JST |
| `barEnd` | 09:05 JST |
| replay `decisionTimestamp` | 09:05 JST |
| provider historical availability | daily, around 16:30 JST; not an intraday fact |
| lunch | never cross 11:30–12:30 |
| missing minutes | never fill or synthesize |
| terminal auctions | separate from regular continuous 5m bars |

`replayAvailableAt = barEnd` is a causal simulation contract, not a claim that J-Quants delivered the historical row at that instant.

## Classification ceiling

J-Quants Historical minute/tick alone cannot be `TIER_1_FULL_GOLDEN_REPLAY`, because historical provider availability is not reconstructable per bar and complete Lane Y input parity has not been established. A passing probe can create only a `TIER_2_RECONSTRUCTED_REPLAY_CANDIDATE`; it does not unlock EXIT Development.

## Official references

- <https://jpx-jquants.com/en/spec/eq-bars-minute>
- <https://jpx-jquants.com/en/spec/eq-trades>
- <https://jpx-jquants.com/en/spec/eq-bars-daily>
- <https://jpx-jquants.com/en/spec/eq-bars-daily/adj>
- <https://jpx-jquants.com/en/spec/eq-master>
- <https://jpx-jquants.com/en/spec/data-update>
- <https://jpx-jquants.com/en/spec/fix-data-info>
- <https://jpx-jquants.com/en/spec/bulk-get>
- <https://jpx-jquants.com/en/help/usage>

All execution, broker/RSS/Excel writes, paper/live trading, automatic promotion, production update, and transmission flags remain `false`.
