# Phase57 All-Material Entry v1 — Feature Source Audit R3

2026-09-24 JST / PR #587 / append-only extension of R2

## Result

The first producer-level audit is now separated into **directly reproduced causal prefix features**
and **inherited fields whose upstream knownAt is still unresolved**. Presence in an analyzer or
derived matrix is not admission to the learned Entry model.

No performance outcome was used to promote a feature family.

## Direct producer evidence located

Workflow:
`.github/workflows/phase57-entry-new-information-export.yml`

Producer:
`scripts/phase57_entry_information_export.mjs`

The workflow is an offline Development export using pinned saved minute artifacts. It does not call
a market-data provider. The producer constructs expected completed minute starts through the
decision timestamp and enforces `bar.availableAtJst <= decisionTimestamp`. Missing turnover is not
future-filled. Its built-in suffix mutation adds a synthetic future 09:35 row and requires causal
prefix output invariance.

The following fields are produced directly from the closed prefix by that code:

| feature | producer evidence | R3 admission |
|---|---|---|
| `range6Pct` | completed prefix OHLC range | `SOURCE_CAUSAL_PROVEN / MODEL_ADMISSION_PENDING_FULL_2155_JOIN` |
| `lastCloseLocation` | latest completed bar OHLC shape | `SOURCE_CAUSAL_PROVEN / MODEL_ADMISSION_PENDING_FULL_2155_JOIN` |
| `lastUpperWickFraction` | latest completed bar OHLC shape | `SOURCE_CAUSAL_PROVEN / MODEL_ADMISSION_PENDING_FULL_2155_JOIN` |
| `turnover6Jpy` | completed prefix turnover sum; no missing future fill | `SOURCE_CAUSAL_PROVEN / MODEL_ADMISSION_PENDING_FULL_2155_JOIN` |

The exporter reports a 76-session Development source and 3,800 selection-event output. That is not
the same contract as exact coverage of the 2,155 Frozen Selector opportunities. Therefore these
features are **not yet MODEL_ADMITTED**.

## Inherited / still unresolved

The same exporter carries fields that are not proven by this producer itself:

- `relativeVolume5`
- `directionalVwapDistancePct`
- `priorSelectionCount`
- `ridgeDeltaPreviousSelection`

Their original producer, point-in-time timestamp, missing semantics and exact 2,155 join must still
be traced before model admission.

The R2 conditional families remain unresolved until equivalent proof exists:

- `priorDay20dVol`
- `priorDayTr5`
- `priorDayTr20`
- `priorDayVolumeShock`
- `t0AbnormalTurnover`
- `t0LiquidityLog`
- `marketReturnPct`
- sector context
- tick-size / tradability
- point-in-time symbol profile
- Dictionary-derived descriptors

`selectionHour` does not need an artifact feature if used: it must be deterministically derived from
the already-known decision timestamp. Any separately stored `selectionHour` field is not trusted
without lineage.

An older 277-row architecture inventory contains causal-looking `liquidityBucket`, momentum and
acceleration diagnostics, but that subset is not proof of exact full-2,155 availability and does not
admit them into All-Material v1.

## Required admission gate

A conditional feature can move to `MODEL_ADMITTED` only after all are saved:

1. producer/source identity;
2. raw/source timestamp or as-of field;
3. proof `knownAt <= decisionTimestamp`;
4. exact join key into Frozen Selector opportunity ledger;
5. coverage over all 2,155, with missing-reason counts;
6. no future/backfill imputation;
7. future-suffix mutation invariance where a suffix exists;
8. reproducible hash / source pin.

Until then it stays diagnostic or excluded from the model matrix.
