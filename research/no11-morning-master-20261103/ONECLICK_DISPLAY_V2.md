# OneClick Display V2 — permanent, bilingual, evidence-scoped

## Scope

This is a persistent migration of the installed OneClick presentation, not a
one-day prestart retry, reservation reset, account operation or replacement UI.
The existing white theme, dimensions, button positions, 15-second refresh,
selection header, action callbacks, approval prompts and Enabled expressions
are preserved. No date, symbol count, personal holding or run ID is hardcoded
in the production status logic. Synthetic dates and counts appear only in tests.

The four status rows have separate meanings:

- `TODAY`: today's date and clock phase. `CLOSED / 本日終了` is not overwritten
  by an old reservation. `ENTRY CLOSED / 新規受付終了` does not claim that held
  position management has finished.
- `TRADING`: the recorded result or request. Failed runs, native entry-halt
  records, closed collectors, registered runs, launch requests and reservations
  are distinct. A request/registered run is `稼働未確認`, never `LIVE RUNNING`.
- `DATA`: verified `TODAY` or `NEXT` prepared-day identity and count. It uses
  the registered selection validator after its SHA256 check. `READY` does not
  mean broker approval, complete live connectivity or a successful order.
- `CHECK`: the after-close source repair's journal AND actual current target
  bytes. `APPLIED` is a software-install result, not live-trading certification.

Buttons retain English short labels with Japanese meaning where helpful:
`START TRADING / MAX3`, `UPDATE DATA / 翌日準備`, `REFRESH / 状態更新`,
`REVIEW / 停止を確認`, `LOGS / ログ`. Hovering the status shows the check time,
recorded collector state, redacted failure/halt codes and evidence limitations.

## State rules

The current date selects PREOPEN, execution-claim and Trade receipts. A queued
approval must be for that day, have the original 08:30–08:59 issue window,
09:00 earliest start, 09:02 expiry and exact nonce-linked execution claim.
At 09:02 an unused reservation is expired; an already claimed attempt remains
history and never becomes pending again. Midnight does not reuse yesterday's
reservation or claim. Neither file is deleted to accomplish this.

A same-day active-run pointer is inspected only within its configured private
root. A previous attempt's failure is not proof that a newer collector attempt
failed. Unknown, malformed, duplicate-key, linked or unavailable evidence is
not reported as healthy. Personal amounts, symbols and exception text are not
included in presentation output. No process probe is used to pretend that a
saved marker proves current process liveness.

The original `oneclick_status.py` is kept byte-for-byte. Its returned fields
are unchanged; the wrapper only adds `presentation`. Native safety decisions
still control actions. Presentation cannot grant Trade, schedule a request,
change a recovery route or authorize an order. Unexpected wrapper failures
return a redacted blocked response instead of a false healthy state.

## Implementation and deployment

`no11_oneclick_display_v2.py` is the read-only model and pure copy reducer.
`no11_oneclick_display_transform.py` is the versioned migration. It replaces
only the native status-tool reference and the exact old presentation region,
adds a tooltip, and proves the reverse transformation recovers the full
original launcher. Local theme/selection/customization outside those regions
is preserved, not replaced with repository defaults.

`install_no11_oneclick_display_v2.py --store <existing store>` audits only.
`--apply` requires Windows, an idle application and a time outside
08:00–15:40 JST. Run the verified Python installer directly from an interactive
PowerShell, not through an extra named No11 PowerShell wrapper. The process
check remains enabled and does not kill workers or waive unreadable processes.

Only `oneclick/Start-No11OneClick.ps1` is modified. Two read-only sidecars are
added in that directory: the presenter and `oneclick-display-v2.contract.json`.
A local `oneclick-display-v2-install.json` journal saves the exact previous UI,
new bytes, payload identity and protected-file hashes before installation.
The dependencies are installed before an atomic launcher switch. A known
interrupted install can continue only through the same verified installer;
unknown changes stop it without overwriting or deleting the journal. A damaged
partial sidecar requires review rather than being assumed safe. Repeated
completed installation returns `ALREADY_APPLIED`.

The backend, strategy, EXIT, sender, observer, settings, binding, schedules,
workbooks, data, reservations, claims and ledger are not installation targets.
Normal subsequent launches use V2 automatically; no daily reapplication or
special next-day launch command is needed. The install audit tolerates normal
next-day settings evolution after completion, but rejects changed target bytes.

Historical repository launcher sources remain frozen compatibility fixtures.
Future launcher updates must preserve the V2 migration or explicitly migrate
it; silently overwriting the local launcher with an old repository copy is not
an approved downgrade. This migration does not promise compatibility with
arbitrary future local edits. Unknown display regions or native status code
are rejected, not patched by guessing.

## Verification and limits

The dedicated offline workflow tests Windows and Linux: clock boundaries,
midnight/weekend rollover, reservation expiry and claims, corrupt evidence,
old failure versus newer attempts, native halt visibility, dependency hashes,
redaction, BOM/CRLF, repeat/partial installation and preserved local theme.
The installed wrapper is compared with the actual original inspector across
21 date/time combinations; all original fields must be exactly equal.
Existing data-selection, after-close source repair and opening-source wait
regressions are also run. Windows additionally parses the transformed launcher
with PowerShell 5.1 and measures bilingual text using WinForms in the existing
control dimensions. No CI test opens the user's Excel or broker or trades.

CI is not confirmation that installation succeeded on the user's PC, that a
particular high-DPI monitor renders identically, or that the live engine is
healthy. Readback from the installer and a reopened OneClick screenshot remain
the actual-machine presentation check. Trading operation remains separately
unverified until its own real-machine evidence is obtained.
