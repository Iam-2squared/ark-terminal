# Phase57 J-Quants SOURCE_VALIDATION_ONLY Pilot — FAIL

The bounded source pilot stopped before dataset allocation, formal acquisition, training, or Validation.

Entitlement passed: authentication and Minute Stock Prices both returned HTTP 200 with non-empty data. Four bounded Minute requests produced 1,298 rows for two symbols and two sessions. Field presence, OHLC order, non-negative volume/turnover, duplicate, and pagination checks passed.

The current source adapter assumes the J-Quants `Time` field is a bar-open timestamp. The pilot observed four rows at `11:30`—one for each symbol/session pair. The adapter consequently classified them as lunch violations and rejected aggregation. No five-minute bars were emitted.

This result does not prove the complete timestamp contract, but it is strong evidence that the current `BAR_OPEN` assumption is wrong at the morning boundary and that `Time` may represent bar end. The adapter must not be changed on inference alone.

Required next work:

1. Confirm bar-start/bar-end meaning through an authoritative contract or a bounded edge probe.
2. If bar-end is confirmed, normalize `09:01…11:30` and `12:31…15:30` into causal bar-open timestamps with `availableAt` equal to the source time.
3. Add explicit open, morning-close, afternoon-open, and market-close boundary fixtures.
4. Re-run a new SOURCE_VALIDATION_ONLY pilot using permanently excluded sessions.

The original pilot sessions, 2025-01-06 and 2025-01-07, remain permanently ineligible for Development, Validation, and untouched OOS. Raw payloads, future returns, and selector outcomes were not persisted or inspected.

Untouched OOS remains sealed. Every safety flag remains false.
