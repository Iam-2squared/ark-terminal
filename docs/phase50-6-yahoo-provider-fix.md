# Phase50.6 Yahoo provider ingestion fix

- Allow the read-only `YAHOO_CHART` provider in Phase41 ingestion.
- Preserve fail-closed behavior for unsupported providers.
- Surface Phase41 rejection and integrity details in `rejected.json`.
- Add regression coverage proving Yahoo-normalized records reach `READY_TO_PERSIST`.

Safety remains unchanged: no broker writes, no Excel order writes, no RSS order calls, no live orders, no automatic promotion, and no Production updates.
