# No11 — independent owner-exit collector STOP guardian (2026-11-13)

Related: [Issue #616](https://github.com/Iam-2squared/ark-terminal/issues/616), Draft PR #613 Node/Capital, Draft PR #614 standby, Draft PR #617 read-only incident audit.

## Problem from 2026-11-12

The operator closed the LIVE console window with X. Afterwards, original Collector PID no longer existed and unsaved temporary workbook was manually closed, **but** the immutable attempt was still `CONNECTED` and no genuine `collector-ready.json.closed.json` was produced. The precise Node root error was also lost at the Python subprocess boundary. Closing X cannot be proven to have caused the Node failure; it can prevent Python/Powershell `finally` cleanup and is a separate liveness risk.

## Stage-only design — does not edit the installed PC

`tools/no11_collector_owner_guard.py` is a separate detached Windows process started **before** the native C50 child is even requested. It opens a Windows `SYNCHRONIZE` **HANDLE** to the exact controller process (immune to PID recycling), creates an exclusive sealed `owner-guard-attached.json`, and only then lets the parent start C50. Failure of attachment/verification is fail-closed: the collector does not start.

- Normal closure: original controller waits for collector STOP, native unsaved workbook close and actual closed receipt; only original `Attempt.close_confirmed` marks status CLOSED. The separate guardian exits after observing sealed CLOSED. Guardian does not write anything after closed.
- Abnormal owner termination (console X, parent crash, synthetic kill): the guardian observes the **exact** owner handle signaled. If attempt was `SPAWN_REQUESTED`, `RUNNING`, or `CONNECTED`, the guardian creates **only** the original `collector.stop` with exactly `READ_ONLY_STOP\n`; it writes one separate, sealed `owner-exit-stop-request.json` saying closure **not verified**. It does not kill Excel or overwrite a prior stop. It cannot mark the attempt CLOSED or create a `*.closed.json`.
- If the attempt was `ALLOCATED`, no Collector was even requested and no stop is created.
- If an existing marker is unknown/corrupt or the attempt is not signed/owned, fail closed. No deletion/cleanup of old ledger, orders, source pins, claim files or previous receipts is permitted.
- Existing native STOP behavior can exit via its `finally`. **A STOP request is not a guarantee of workbook closure or confirmation of broker cancellation.** If native cleanup fails or guardian itself is killed, the attempt remains unverified and an operator must inspect safely.

`no11_owner_guard_staging.py` derives **only** four exact, reversible edits to the existing Python controller in an **isolated GitHub Actions checkout**: import guardian, start/ack before C50 spawn, fail closed if guardian dies during tick, and require successful guardian completion after native signed CLOSED. The source transformation refuses unknown spans; original controller is unchanged in repository and not patched on the user PC.

## Offline verification

Python 3.12 regression on Windows and Linux tests: signed original attempt validation, real exclusive STOP only, no synthetic CLOSED, allocation-before-spawn behavior, repeated request not overwriting evidence, corrupt / tampered marker rejection, wrong-day/owner rejection, preserved prior records and exact staged controller derivation.

**Windows-specific synthetic termination:** start a sleeping Python as a fake controller process, launch the detached guardian against its real OS PID, wait for sealed handle handshake, simulate mock `CONNECTED`, terminate **only fake Python**, confirm the guardian wrote the original stop marker while never fabricating a closure receipt or touching Excel/broker. No real broker process or workbook is started.

This is **not yet proven on the user's live Windows desktop**, and the feature cannot reliably protect against OS restarts, catastrophic power loss, a supervisor that the OS terminates along with the controller, filesystem loss, or a broker order that was already transmitted. It reduces one class of owner-exit orphaned collectors and retains fail-closed recovery; it does not close the historical Nov 12 gap or fix the unknown underlying Node error.

## Release blocker / integration steps

1. Both CI environments must PASS on the exact reviewed SHA. Generate and inspect the derived controller-only patch.
2. Build a signed, rollback-safe installer for **the actual pinned Windows controller**, after-hours only. Bind the guardian module hash and enforce the original quiet/process gate. Do not overwrite frozen evidence.
3. Windows workstation no-order dry-run: controlled console close/parent kill, source-pinned owner HANDLE, request marker, original C50 stop and legitimate close receipt, no unwanted Excel workbook close, no rearm or broker commands. Check Windows antivirus/job assignment compatibility of detached guardian.
4. Independent broker orders/fills/positions reconciliation, including manual transactions on Nov 13. Never interpret ledger zeros as a flat broker account.
5. Until successful real-machine gates, **LIVE remains BLOCKED**. This staged code is not a trade authorization, release, or engine restart.
