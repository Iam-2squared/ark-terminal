# ARK No.1.1 — Flexible same-day standby (2026-11-12)

## Request and explicit safety boundary

The old OneClick **08:30–08:59 JST standby** is unnecessarily narrow.
The proposed source-level change makes it possible to **request same-day standby
at any clock time from 00:00:00 through 08:59:59 JST**, on an eligible weekday
with an existing verified **same-date** handoff and explicit same-day approval.

**This does not widen LIVE order time, broker authorization, or session dates.**
From 09:00, the existing direct Trade request path and all native gates remain
unchanged; from 15:20, entries close; from 18:00, the nightly data button retains
its own workflow. At 21:00, users may have the UI open for **read-only status**
but must not pre-authorize the *next* session's real orders with yesterday's
consent. Weekend/holiday eligibility still depends on the exact same-day handoff
and original policy; no new holiday fallback is added.

## Exact source delta (candidate-only, not installed)

`no11_anytime_preopen.py` checks known source anchors and generates the
reversible, byte-localized modifications for:

1. `Start-No11PreopenStandby.ps1`: widen **IsArmWindow** lower boundary from
   08:30 to 00:00 and extend the offline boundary selftest. Retain **IsLaunchWindow**
   at `[09:00:00,09:02:00)`, original same-day request timestamp, original
   approval and nonce, and existing one-shot durable claim. Do not replay Trade.
2. `Start-No11OneClick.ps1`: allow the existing preopen button to queue from
   00:00; update the visible waiting copy. Original `$trade.Enabled` expression
   and all callbacks stay byte-identical.
3. `no11_oneclick_display_v2.py`: classify genuine early approved receipts as
   valid and show `RESERVED 09:00` also during `BEFORE_OPEN`. Reject
   previous-day/future-day receipts and expired reservations as before.

The standalone program **only stages these changes within a disposable Git
checkout**. It does not update an installed program or attach approval to a
future date.

## Installer implementation and verification

The reviewed after-hours deployment is now
\`Bootstrap-No11AnytimeStandby.ps1\` (PowerShell 5.1) and
\`install_no11_anytime_preopen.py\` (Python 3.12, standard library and pinned
local migration modules). The bootstrap downloads **seven exact Git-blob
SHA1-pinned** modules from a fixed commit; unrecognized bytes block.

The Python **default audit** reads and verifies the existing V2/Overlay sealed
journals, derives their full source transformation and SHA256 sidecar chain,
checks the pinned old standby worker, confirms the existing native status code
family, and refuses unrecognized local changes or existing successor sidecars.
It does not start Excel, Trade or the nightly pipeline.

Explicit \`--apply\` requires a Windows after-hours clock **outside 08:00–15:40
JST**, no identified active ARK/OneClick processes, an exclusive installer
lock and a second identical source verification inside the lock. The
operator-facing bootstrap additionally requires explicit confirmation that
ARK is stopped and the broker order/position state was reviewed.

It writes a sealed **PREPARED** journal containing exact original UI/worker
bytes and separately derived successor bytes before any live source change.
It then creates a **new** versioned display module and contract (leaves
\`no11_oneclick_display_v2.py\` and
\`oneclick-display-v2.contract.json\` unchanged), atomically replaces only
the standby worker and existing white UI, and seals **COMPLETE** after strict
readback and independent audit. This also fixes the misleading early-hour
overlay label without touching any \`Enabled\` assignments or callback.

A lost process or power failure at any point leaves an auditable
\`INTERRUPTED_REQUIRES_APPLY\`; the same pinned release can continue ONLY
when every old/new byte equals the sealed journal. Unknown concurrent
changes block. Do not manually clear or modify the journal.

### Operator procedure — after-hours only

Close **OneClick and ARK** first, confirm the broker's actual orders/fills
and the two existing non-ARK holdings. Do not erase an old attempt marked
CONNECTED, attempt to reuse its order claims, or edit any Excel books.

Open the **version-pinned bootstrap** file from the reviewed GitHub PR
using a pinned commit URL, preferably by a verified local checkout. Run:

\`\`\`powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $bootstrap
\`\`\`

The read-only audit should report
\`NO11_ANYTIME_STANDBY_INSTALL=READY_NOT_APPLIED\` (first install),
\`ALREADY_APPLIED\`, or \`INTERRUPTED_REQUIRES_APPLY\`.
\`BLOCKED|\` means **STOP**; never reset receipts.

After checking the above and the stopped processes, run:

\`\`\`powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $bootstrap -Apply -IConfirmArkStoppedAndBrokerOrdersPositionsReviewed
\`\`\`

Only \`APPLIED_NO_TRADE\` (or exact \`ALREADY_APPLIED\`) plus a fresh
audit certifies the installation. **No command here starts Trade, sends an
order, resumes a stopped session or touches Excel.** Reopen OneClick only
after confirmation; the native broker and daily source checks still apply.

The old V2 and Overlay migration receipts are historical, not a claim that
the old verifier alone recognizes the new UI file after a successor
migration. The new installer verifies the old immutable chain **plus** the
new versioned receipt and successor bytes. The checked-out PR source alone
is not the installed executable; do not copy its generated patch directly.

## Nonnegotiable release gate

The user's installed white OneClick has original, immutable
`oneclick-display-v2-install.json` and
`oneclick-display-v2-overlay-compat-install.json` receipts and a contract
binding to the displayed code. **Do not directly copy these generated scripts
or rehash the old journals**: doing so can invalidate historical V2 and overlay
verification, and could render the UI unsafe or unavailable.

A subsequent, separate after-hours release must:

- Identify the user's actual installed source and verify both complete V2
  and overlay chains plus sidecar bytes and original broker source pins.
- Apply only the reviewed worker/UI/presentation deltas; rebind the display
  contract in a **new journaled migration**, preserving all original receipts.
- Verify atomic readback, PowerShell 5.1 parse, source hash, no live
  worker/collector, no affected ARK-controlled workbook, and no change to
  broker order, trade authorizations, claims or previous ledger.
- Confirm any historical unclosed Chart50 attempt stays **unverified**;
  successful standby is not permission to reset/replay that old session.
- Fail closed on a new deployment mismatch, partial migration or changed
  permitted source. Do not start Trade or Excel as part of installation.

Dedicated Windows/Linux CI validates the original 08:30 package, the exact
proposed transforms, a synthetic 00:00 / 08:29 / 08:59 / 09:00 display
case, and real Windows PowerShell 5.1 offline selftests. CI is not a real
broker order test.

## Operator meaning

**Standby at 06:00**: with tomorrow/current-day handoff properly prepared,
the operator can explicitly approve **today's** 09:00 request. The worker
waits for 09:00 with the PC awake and will request the native launcher once
if all original source, broker, cash, date and no-retry checks pass.

**Standby at previous evening**: read-only UI monitoring may continue,
but **no next-day unattended LIVE order** is requested using previous-day
approval. The operator must approve on the actual session date.

**After 09:00**: use the existing normal Trade entry path only when its original
approval and order requirements are satisfied; no backdated 09:00 trigger.

## Windows process ancestry false positive: safe operator launch

On 2026-11-13, the operator's **read-only** `-ProbeGate` reported
`NO11_GATE_UNREADABLE=0`, `NO11_GATE_MATCHES=1` and
`CLASS=INSTALLER|REL=ANCESTOR`. The original installer quiet gate matches
a broad `No11` command line in an upstream PowerShell shell. The previous
separate PowerShell inspection returned zero because the installer command's
ancestor chain was absent from that inspection; no proof of a current Trade
process was found. An ancestor classification *alone* is not proof that it
is safe to ignore; do not modify the original trading/process gate.

**Preferred workaround (no source changes or safety bypass):**
Start a brand-new `cmd.exe` from **Windows Start / Win+R** (not from the
currently running PowerShell or an ARK window). The fresh `cmd.exe` should
have Explorer, not a `No11` PowerShell wrapper, as its parent. Use the
previously hash-verified bootstrap from that fresh console:

```cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\Bootstrap-No11AnytimeStandby-probe.ps1" -ProbeGate
```

Proceed only if the **fresh independent** probe says
`NO11_GATE_UNREADABLE=0` and `NO11_GATE_MATCHES=0`.
Then, with ARK/OneClick/nightly jobs stopped, within the existing after-hours
window and after independently checking broker orders/fills/positions, run
the same known script in **that same fresh cmd.exe**:

```cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\Bootstrap-No11AnytimeStandby-probe.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\Bootstrap-No11AnytimeStandby-probe.ps1" -Apply -IConfirmArkStoppedAndBrokerOrdersPositionsReviewed
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\Bootstrap-No11AnytimeStandby-probe.ps1"
```

The first audit must return `READY_NOT_APPLIED`; a successful install is
`APPLIED_NO_TRADE`, followed by `ALREADY_APPLIED`. Do not combine these
into an automatic unconditional sequence: **inspect each stage and stop on
a `BLOCKED` result.** The process gate is run repeatedly during the apply
and still blocks unreadable command lines, actual ARK workers, and other
non-exempt processes. Do not use `taskkill`, `Stop-Process`, remove a
reservation marker, or relabel an unclosed collector receipt to pass it.

An independent cmd launched from the *existing PowerShell* can inherit the
problematic ancestor. It must be a fresh shell launched independently by
Explorer or the Windows Start UI. The script must be the already verified,
unchanged source-pinned bootstrap; otherwise repeat source verification first.



## 2026-11-13: no quiet-gate exemption; pinned direct CMD deployment

The operator's latest read-only probe returned one installer ancestor match
and zero unreadable command lines. The original process gate still blocks
a quiet check from that chain, even when the outer console is cmd.

Do not waive the original process gate. A running PowerShell bootstrap
can appear in the installer process ancestry and match the broad historical
No11 predicate. The new -StageForCmd mode prepares a separate, pinned bundle
without modifying the installed OneClick, logs, evidence or order records:

* Download exactly eight Git-blob pinned Python sources from one immutable commit.
* Stage them outside the installed OneClick, under LocalAppData/ArkTerminal/No12/
  anytime-installer-stage/verified-<nonce> with an SHA256 manifest.
* Generate a Run-No11Anytime.cmd file that verifies the bundle and current
  binding/settings then directly invokes the bound Python. The PowerShell
  downloader has exited before CMD launches Python.
* Require an explicit action, never trade on opening the console:
  - probe: read-only. Require NO11_GATE_UNREADABLE=0 and NO11_GATE_MATCHES=0.
  - audit: read-only. Require READY_NOT_APPLIED before first installation.
  - apply: after-hours only, Y/N broker/ARK-stop confirmation, and existing
    original.gate process/time checks repeated throughout. A real ARK worker,
    unreadable command line or any unrecognized process still blocks.

Preparation command from the latest verified downloaded bootstrap:
PowerShell: & powershell.exe -NoProfile -ExecutionPolicy Bypass -File
  $arkGateProbe -StageForCmd

The bootstrap prints NO11_CMD_STAGE_RUNNER=<absolute path>, and
NO11_ANYTIME_BOOTSTRAP=STAGED_FOR_DIRECT_CMD_NO_INSTALLED_WRITES.
In a separate fresh CMD shell, run the printed absolute path in double
quotes, once each with arguments probe, audit and (only after verification)
apply. Inspect the output between commands and never chain unconditional
commands. Finish with a fresh audit that reports ALREADY_APPLIED.

Do not delete or rewrite any prior installation receipt, order claim, broker
record or unclosed collector evidence. This operation changes neither the
native trading window nor original broker safety gates.

CI validates staged source pins, corrupted bundle rejection and actual
Windows CMD direct-Python process probing. It cannot prove live broker or
operator-machine safety; the on-PC probe/audit is still required.
