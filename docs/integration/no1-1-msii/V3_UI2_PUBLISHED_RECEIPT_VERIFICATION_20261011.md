# Ark Terminal No.1.1 UI2 — verified V3 publication receipt (2026-10-11)

Offline-only development until the next user Windows PC run. Initial V3 Capital/Ownership one-shot and UI2 localhost start previously passed; repeated 30s refresh is still unverified and reports READ_ONLY_REFRESH_FAILED.

The V3 publisher writes the Snapshot, RSS source health, capital preview and a final SHA256 hash receipt by separate atomic file renames. Without checking the receipt, a mid-write crash could expose mixed-generation inputs to the UI2 read-model exporter.

The new read-only verifier checks every receipt digest against its actual on-disk file, validates recorded V3 capture identity and source-observation provenance, and re-runs the unmodified original RSS 30-second freshness, pending-order, cash and private personal-ownership Gate. It rejects an altered ownership baseline or previous cash preview rather than carrying forward stale state. UI2 checks the receipt before export and again after export but before committing its model, closing most partial-publication windows; no simultaneous multi-file filesystem transaction is claimed.

A mismatch is fail-closed with one of the hardcoded diagnostic stages PUBLISH_RECEIPT or MODEL_VERIFY_RECEIPT, without emitting account values, private file paths or exception messages. Unit tests cover valid receipt, altered/mixed-generation source, changed ownership and stale captures.

NO real trades, Excel/RSS order calls, altered Frozen No.1.1 policies, main merges, ownership edits, model retuning or Safety reset. Actual broker arrival time and live Frozen events remain uncertified.
