# After-close source repair — 2026-11-11

## Scope

The prestart retry used an isolated bootstrap. It did not install the filtered
weekly-receipt lineage correction into the ordinary next-day runtime. This
release combines that source correction with the narrowly classified opening
RSS-observation wait. It does NOT resume the failed November 11 run.

Only these existing installed files may change:

1. `tools/no11_received_session_bootstrap.py`: exact original RSS-funding
   bootstrap, with the verified filtered-weekly receipt derivation.
2. `tools/no11_rss_buying_power.py`: exact historical funding module, with a
   bounded initial-observation reread and sanitized nested failure reasons.

Original normalized inputs are pinned by Git blob. The exact already-installed
weekly derivation is accepted; markers alone do not establish compatibility.
Unknown edits to either target are refused before any target is replaced.
Other local fixes are included in a frozen inventory and left byte-for-byte
unchanged, rather than replaced with the repository version.

The white OneClick, observer, sender, controller, model/strategy/EXIT modules,
settings, automatic-input binding, workbooks, broker config, cash receipts,
ledger, claims, daily data and recorded executions are not installer targets.
The installer never starts Excel, MarketSpeed II, Trade, a collector, a funding
resolver, an order sender or a next-day scheduled task. Existing schedules are
not edited. The default Python operation is a file-only audit.

## Apply contract

`install_no11_afterclose_source_repair.py --store <existing store> --apply`
requires Windows and an off-market time outside 08:00–15:40 JST. The existing
`unified-refresh-install.lock` is held while applying. Process inspection
rejects ARK workers/UI and command lines that remain unreadable after bounded
full-list resampling. No process is killed or forcefully terminated.

Before replacement, the durable local journal
`afterclose-source-repair-v1-install.json` records exact before/after bytes,
derivation and hashes. Each replacement is atomic and followed by readback.
The two-file transaction is not globally atomic: interruption after one file
is represented by a PREPARED journal and requires rerunning the SAME verified
installer while idle. It must not be bypassed by deleting the journal.
Unrelated or unknown concurrent source changes stop recovery without being
overwritten. A fully completed repeat returns `ALREADY_APPLIED`.

Statuses:

- `READY_NOT_APPLIED`: audit passed; sources have not been installed.
- `INTERRUPTED_REQUIRES_APPLY`: known partial install; do not start Trade.
- `APPLIED_NO_TRADE`: both target sources read back exactly; no live start.
- `ALREADY_APPLIED`: exact target bytes remain installed.
- `BLOCKED|...`: no success claim; preserve the journal and original evidence.

An apply failure can leave one verified patch installed. Preserve all files and
investigate the reason; a partial state is never reported as a completed repair.

## Opening-observation behavior

Only the explicit double-read account/table change and capture-duration reasons
are eligible for a bounded reread. Generic or unidentified unavailability,
identity, schema, hash, stale data and row-completeness failures remain blocked.
Every successful observation goes through the original native normalizer and
is bound to the approved Excel PID/start and RSS session key. Both the first
attempt and later attempts check the elapsed budget and actual clock after I/O;
cutoff/expiry is rechecked after normalization. The original funding resolver
rechecks freshness with that return clock before writing its one-time receipt.

There is no cached-good-sample substitution, invented amount, changed funding
policy, adoption of personal holdings, order retry or new trading authorization.
An underlying blocking call retains its own timeout; the wait budget is checked
around calls, not a promise of preempting arbitrary I/O.

## Verification and limits

Offline tests use synthetic directories and observations. They exercise the
actual Node normalizer, frozen-source derivation, Windows encodings, installer
interruptions, journal tampering, unknown targets, concurrent edits, repeat
installation, process/time guards and preservation of other local fixes.

CI completion is separate from PC installation and live verification. No test
uses the user's Excel/account or sends an order. The final unavailable sample
from November 11 was not retained, so the precise transient reason is NOT
proven. This repair may expose a more specific blocker rather than cure it.

The first future session must use that session's data and approval. Do not reuse
November 11's prestart retry, delete its claims, or represent successful source
installation as a successful live trading session. Collectors, account-source
freshness, transport readiness and order attribution still require real-machine
verification before declaring daily operation ready.
