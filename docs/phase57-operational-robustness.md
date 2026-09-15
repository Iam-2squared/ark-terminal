# Phase57 Operational Robustness Layer

Status: research/shadow software infrastructure only.

This layer is intentionally source-agnostic and does not connect to an account, broker, order API, or order-capable RSS function. It exists to harden the realtime state machine before any external integration is considered.

## Implemented primitives

### Connection state

`DISCONNECTED → CONNECTING → HEALTHY`

Failure states include `STALE`, `UNKNOWN`, and terminal `HALTED`.

Strategy evaluation is fail-closed unless the source state is `HEALTHY` and required reconciliation has passed.

### Freshness

`classifyFreshness()` distinguishes:

- `FRESH`
- `STALE`
- `FUTURE_TIMESTAMP`

Future/stale timestamps cannot be treated as valid decision input.

### External cash flow accounting

`applyExternalCashFlow()` keeps external deposits/withdrawals separate from trading PnL.

This prevents a deposit/withdrawal from being misclassified as strategy profit or loss in a shadow/research ledger.

### State reconciliation

`reconcileState()` compares a model state and an observed state using explicit tolerances. Mismatches move the operational state to `UNKNOWN` and lock further evaluation until reconciled.

The comparison is generic and covers balances, exposure, position presence, direction, and quantity.

### Quantity constraints

`constrainQuantity()` separates:

- desired quantity
- lot rounding
- maximum quantity
- maximum notional
- available-cash constraint
- final permitted quantity

This is a pure software primitive. It does not transmit or construct an executable order.

## Tests

`node --test scripts/tests/phase57-operational-robustness.test.mjs`

The parity workflow also runs this test on Linux and Windows.

Coverage includes:

- fail-closed connection transitions
- stale/future timestamps
- external cash flows remaining separate from trading PnL
- reconciliation mismatch → UNKNOWN state
- deterministic lot-safe quantity constraints
- reconciliation + source-health gate

## Safety boundary

This layer does not add or enable:

- account login
- account connection
- broker write access
- RSS order functions
- live/paper order transmission
- automatic promotion
- production update

The existing Phase57 safety flags remain unchanged.
