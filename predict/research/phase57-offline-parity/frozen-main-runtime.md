# Phase 57 frozen-main shadow runtime

Status: **end-to-end offline shadow runtime complete**.

The runtime now executes the unchanged frozen chain:

`complete PIT point → Frozen Minimal Hybrid v1 → MSH-Entry v1 → V3_B_RISK → MAX_3 → causal EXIT v4 → EXIT v5 bar-5 overlay → shadow ledger → hash-chain evidence export`.

## Run

1. Convert a formula-free generic workbook and a separately pinned causal analog-pool JSON:

   `python tools/phase57_generic_excel_reader.py --workbook INPUT.xlsx --analog-pool ANALOG_POOL.json --output packet.json`

2. Run or resume the event-sourced session:

   `node scripts/phase57-frozen-main-runner.mjs --input packet.json --journal-dir evidence/session-v1 --export-dir evidence/export-v1`

The output has separate raw, normalized, decisions, ledger, health, mismatch, reference and report channels plus a hash manifest. Existing capture IDs are idempotent; a conflicting payload halts the session.

## Generic workbook contract

The sheet order is fixed: `ARK_CONFIG`, `ARK_MASTER`, `ARK_BARS`, `ARK_HEALTH`. `ARK_CONFIG` must declare `universeComplete=true` and `masterComplete=true`; the reader never invents those claims. It accepts values only and rejects formulas, macros, external relationships, connections, embedded objects, query tables, pivot caches, cell errors, order/broker/account sheets, duplicate members, partial rows and unsupported source modes.

Every decision point carries the complete master and a SHA-256 of the sorted member set. Bars are admitted only when their stated `availableAt` is no later than the decision timestamp. The runtime independently rechecks timestamp, bar-finalization, OHLCV, member-set and health rules.

## Boundary

This completes the software path for synthetic and already-authorized historical fixtures. It does not claim that any real Excel/RSS source has the required timestamp, bar-finalization, universe-completeness or freshness semantics. It contains no broker/account adapter and creates no order payload. All execution, paper/live-trading, Excel order-write and transmission flags remain `false`.

The exact machine-readable boundary and pins are in `frozen-main-runtime-contract.json`.
