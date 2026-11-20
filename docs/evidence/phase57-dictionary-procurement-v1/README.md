# Prospective Foundation v1

This is an offline, unverified-input capture foundation, not a Frozen Dictionary.
No provider polling, schedule, private store, or production collection has been activated.

## Receipt workflow

1. Allocate dedicated Dictionary dates in a reviewed budget manifest. They must not overlap Entry/EXIT sealed dates. Bind an official exchange-session calendar hash. Verify source entitlement, storage and retention terms first. Existing2026-09-15 account evidence records Light+minute expiry2026-10-06; it is not current entitlement proof.
2. Initialize a private durable store: `python -m scripts.phase57_dictionary_prospective init --store /private/dictionary.sqlite`.
3. Feed an `append` JSON object via `--input`: kind, session, payload, source, budget; optional source_version, publication, parents. Budget requires purpose=DICTIONARY_ONLY, sessions, exchangeSessions, calendarSourceHash, protectedOverlap=false. This is an operator-reviewed allocation, not an automatic proof of non-overlap. No credentials belong in input.
4. Intake stamps acquiredAt and conservative local knownAt itself. Source publication and source version are unverified claims; missing version stays null. Store daily master, identity intervals and action/status evidence separately. Missing status remains UNKNOWN. Evidence hashes reference externally reviewed sources; the foundation does not certify them.
5. Use `summarize --input` with session and single-security rows to produce draft1m-to5m/L2 input. Only complete regular5m buckets aggregate. Lunch, terminal auctions and post2024-11-05 closing pre-auction are excluded; absent prices remain null. Append derived objects with receipt parent hashes. This is a draft normalizer, not a trait calculator.
6. `audit` verifies transaction chain and raw bytes; `export` emits deterministic canonical envelopes. as_of() omits later receipts, including later corrections. Preserve old versions; never update/delete. SQLite triggers are application protections, not adversarial WORM storage. Backups and filesystem access controls remain operational responsibilities.

Accepted kinds: raw1m, raw5m, master, identity, corporate_action, trading_state, daily_l2, future_l3_input. All are INPUT_ONLY_UNVERIFIED. Store payload hashes and receipt evidence before independent admission. No function constructs or promotes a Dictionary profile.

## Maturity and source admission

No captured receipt automatically counts as a verified session. A separate evidence-bound admission review must establish actual source provenance, identity intervals, action-safe metrics and missing-state coverage. Until then admittedSessions=0. A caller-supplied maturity() count is only a diagnostic and never freezes anything.

Basic20, Tier1 minimum60, and20/60/250 windows use distinct admitted exchange sessions. The frozen prior19-session reliability windows and nEff>=12/300-security/coverage gates remain unchanged. Fit and future-use windows must be strictly separated. At least60 sessions and allG0-G8 plus >=1 Tier1 are required to review Freeze; weaker reliability remains a valid STOP outcome. No calendar completion date is promised.250-session metrics remain INSUFFICIENT until mature. All historical seeds are blocked.

## Reproduce

`ARK_TEST_OFFLINE=1 python scripts/offline/kernel_exec.py python -m unittest scripts.test_phase57_dictionary_prospective scripts.test_phase57_dictionary_pit_recovery scripts.test_phase57_behavior_dictionary`

`ARK_TEST_OFFLINE=1 python scripts/offline/kernel_exec.py python scripts/report_phase57_dictionary_procurement.py --verify`

The report scans all218,319 saved audit-ledger rows, not price payloads. Documentation findings are timestamped paraphrase artifacts; their hashes are not hashes of provider HTML. Prior Evidence remains unchanged. Additional product existence is documented; entitlement and archival sufficiency remain unknown. No support inquiry or purchase was made.
