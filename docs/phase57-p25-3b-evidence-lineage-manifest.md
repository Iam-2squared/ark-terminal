# Phase57 P25.3B — Evidence Lineage Manifest

## Purpose

P25.3B makes the prospective P25 evidence chain auditable before performance is observed.

The manifest anchors every daily non-RSS capture to the exact frozen P24 historical training source and to the outcome-independent P25.3A session classification. It does not contain a performance winner, selected Dynamic N, or any post-hoc filtering decision.

## Frozen history anchor

The manifest requires:

- P24 canonical source run `31785422471`;
- canonical snapshot SHA-256 `10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a`;
- a valid P25.2K pinned history pack;
- `freshHoldoutConsumed=false`.

Any drift in the frozen history identity fails closed.

## Daily capture nodes

Every P25.2J daily capture artifact must have its own SHA-256 fingerprint and a matching P25.3A integrity-ledger row. Nodes are sorted by session date and chained as:

`history seed -> session 1 -> session 2 -> ... -> manifest head`

Each node identity contains only pre-performance lineage information:

- session date;
- capture artifact SHA-256;
- session-integrity classification;
- capture-ready flag;
- frozen target-union size;
- frozen universe fingerprint when available.

Performance fields such as Net, PF, Win Rate, Hit Rate, MaxDD, winner variant, or selected Dynamic N are forbidden from the lineage identity.

## Why the chain matters

If a past daily capture is replaced, removed, reordered, or reclassified, the manifest head changes. This makes silent rewriting of the prospective evidence history detectable before P25.2 performance conclusions are drawn.

## CLI

```bash
node scripts/build_p25_evidence_lineage_manifest.mjs \
  --history-pack <p25-pinned-history-pack.json> \
  --capture-dir <immutable-daily-capture-directory> \
  --integrity-ledger <p25-session-integrity-ledger.json> \
  --output data/p25-evidence-lineage-manifest.json
```

## Operating policy

No MARKETSPEED II, Excel, board, Tick, or Microstructure input is required. MARKETSPEED remains separate milestone/final verification only and cannot rewrite already frozen lineage.

CI green validates implementation integrity only, not trading performance.

## Safety

All execution, broker-write, Excel-order-write, RSS-order, live/paper trading, promotion, production, transmission, and fresh-holdout flags remain false.
