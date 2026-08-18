# Phase57 P25.3C — Autonomous Evidence Preparation

P25.3C removes the remaining daily manual step from prospective evidence preparation while keeping performance evaluation separate.

At 17:30 JST on weekdays, after the 16:45 routine non-RSS 5m capture, GitHub Actions:

1. copies every immutable daily capture from `automation/p25-day-data`;
2. downloads the exact pinned P24 canonical artifact from run `31785422471`;
3. verifies its canonical SHA through the P25.2K history-pack builder;
4. rebuilds the conservative P25.3A session-integrity ledger;
5. rebuilds the P25.3B chronological evidence lineage manifest;
6. persists a dated manifest and integrity snapshot to `automation/p25-evidence-data`;
7. uploads the history/integrity/lineage preparation artifacts for audit.

A dated lineage snapshot is not overwritten. A rerun with the same manifest head becomes a no-op; a different manifest head for the same evidence date fails closed.

This workflow intentionally does **not** run performance selection, choose Dynamic30/40/50, relax Entry thresholds, consume the fresh holdout, or promote anything. Its job is only to preserve the evidence inputs before later evaluation.

It also does not invoke MARKETSPEED II, Excel, board, Tick, Microstructure, or any broker/write surface. Routine data and lineage preparation therefore remain autonomous from the user's PC.

CI green validates workflow/code integrity only. The first prospective trading results are still unknown until real frozen-universe sessions and 5m data are collected.
