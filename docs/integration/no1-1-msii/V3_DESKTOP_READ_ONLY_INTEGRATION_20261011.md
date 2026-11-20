# No.1.1 READ ONLY desktop: V3 bulk snapshot integration (2026-10-11)

Status: **NEW DRAFT INTEGRATION — Windows PC one-click E2E pending.**
This branch switches only the READ ONLY desktop account *capture* subprocess from the old V2, which took 33.25 sec and failed the fixed 30-second RSS observation gate, to the SHA256-pinned V3 downloaded and demonstrated on the user's PC at 2.86 sec. V2 source/private fallback is preserved on disk but NOT silently executed if V3 fails. This change neither alters Frozen No.1.1/Capital policies, nor adds trading methods, nor enables Excel RSS orders.

Execution:
- Validate old immutable Freeze HEAD and unchanged tracked files.
- Validate new V3 private local source SHA256 against 8B396BF22724ABBCA4BCEB7B93862AE46D40ACBDFE95B385F492E960E9F08DA3. When no pinned private copy exists yet, copy the user's tested Downloads V3 (after hash check) to a different `private-capture-v3.ps1`; keep `private-capture-v2.ps1` intact. Avoid Windows Git worktree CRLF substitution.
- Named mutex prevents concurrent captures.
- Each V3 READ ONLY capture generates its own unique private candidate folder; assert exactly one **new** folder per poll.
- New `no11_v3_desktop_publish.mjs` reads ONLY private candidate snapshot/health and the existing signed Ownership baseline; validates V3 provenance, true <25-second observation interval, RSS four source states and 30-second freshness, unchanged private baseline SHA and broker holdings, no unverified orders, and capital ledger preview using the original `inspectNo11CapitalFunding` through `no11_desktop_cash_preview`.
- Publish the new private `snapshot.json`, `source-health.json`, `desktop-capital-readonly.json`, and a hash receipt only after all gates PASS. Each replace is atomic (not a joint filesystem transaction). Errors produce no validated PASS; existing desktop refresh will latch fail-closed and mark UI refresh as blocked. No stale fallback occurs.
- UI read model continues to use this validated private snapshot; any preexisting private Safety Ledger latch remains visible as a BLOCKED runtime state. No reset or approval is added.

The last verified user's PC result is isolated V3 Capital PASS (READ_ONLY_CAPITAL_PREVIEW), but the new one-click path must still be run on Windows, including six-screen UI 2.0, refresh and failure behavior. Neither this change nor any CI test proves physical broker market arrival time, live Frozen native strategy decisions or real order/fill/cash reconciliation.

Excel order permission remains OFF. All trading-related flags stay false. NO MAIN MERGE, research Freeze untouched, no Excel workbook edits or orders.
