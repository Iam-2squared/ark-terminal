# No11 Operational Hardening / 継続運用向け修正

## Release boundary

Base: `75f2c43248c4f5b168fb41c2e5f55f8fb7749886`.
Work branch: `fix/no11-durable-decision-audit-20261112`.

This branch contains reusable runtime helpers, exact reversible source transforms,
and Windows/Linux integration regressions. The workflow derives five modified
sources in an isolated checkout and exports their review patch. Frozen originals
are retained in the repository. This is NOT a deployment to the user's installed
runtime, not a same-day rearm, and not permission to send any order.

**PC未適用。稼働中のファイル・台帳・既存候補・予約は変更しない。**

The local execution container was unavailable during authoring. Compilation,
real SQLite tests and real Windows PowerShell/WinForms checks run in GitHub
Actions; successful jobs must be checked for the exact reviewed commit.

## 1. Candidate decision audit / 見送り理由を永続保存

Previously `capital.consumed` remembered candidate IDs but not the reason for a
skip. The in-memory `last_decision` and latest report could replace an earlier
allocation/rejection with a later empty calculation. Consumed never meant bought.

`tools/no11_capital_decision_audit.py` preserves the existing calculation and
submission boundaries while adding ledger checkpoint EVENTS before consumption
and before `submit_intents`. Each event contains the candidate hash, H235
admission, decision/evaluation clocks, same-minute result, age, allocation and
safe rejection/failure reason. A latest pointer does not erase prior events.

Dispositions distinguish:

- `SKIPPED_MINUTE_BOUNDARY` / `SKIPPED_AGE_LIMIT`;
- `H235_NOT_ADMITTED`;
- `CAPITAL_REJECTED` with the native safe reason;
- `ALLOCATED_ZERO_QUANTITY`;
- `BUY_INTENT_CREATED` (NOT broker submission, acceptance or fill);
- `CAPITAL_CALCULATION_FAILED` / `CAPITAL_RESULT_NOT_EXPLAINED`.

The same-minute AND 90-second predicate is unchanged. For example, crossing
10:30:59 -> 10:31:00 remains ineligible even though only one second elapsed.
No old candidate is reintroduced, no consumed key is removed, and no automatic
order retry is added. If an audit write fails, consumption/submission does not
proceed through this function. The outer native failure handling remains intact.

Existing consumed IDs without these new records are explicitly historical
unknowns. Today's supplied records do NOT establish whether the previously
admitted candidate was skipped for timing, rejected by the slot policy, or
allocated zero quantity. This patch must not invent that explanation.

## 2. Complete Display V2 -> Overlay verification

`no11_display_install_chain.py` verifies the original V2 source derivation,
known presentation payload, matching contract/native-status hashes, all actual
sidecar bytes, and the overlay's preserved parent journal and final launcher.

The base verifier recognizes a proven COMPLETE overlay instead of treating it
as an unknown concurrent edit. The overlay verifier checks missing or modified
presentation/contract dependencies rather than certifying only its launcher.

Both the exact previously shipped presentation SHA256 and the current reviewed
payload are supported. Merely editing a journal and recomputing its checksum
cannot authorize an arbitrary presentation program. Historical receipts remain
unchanged; interrupted/unknown states still fail closed.

## 3. Failure attribution after collector closure

An old `controller-failure.json` plus a newer CLOSED attempt is no longer enough
to label the latest attempt as failed. Without attempt-specific chronology the
new state is `FAILURE_SCOPE_UNVERIFIED`, rendered as `CLOSED / 停止理由要確認`.
It does not claim success or healthy live execution. A current failure still
wins; all original failure files stay preserved.

## 4. Preopen overlay

`launcher_preopen()` is a narrow additional presentation transform for the
already migrated local white launcher. During PREOPEN the disabled overlay uses
the validated presentation's trading text (e.g. `RESERVED 09:00`) instead of
interpreting the native `NEW_ENTRY_WINDOW_CLOSED` pre-09:00 reason as a failed
reservation. All Enabled expressions, callbacks and timer actions are unchanged.

Keep this final delta separate from the frozen historical V2/Overlay recipes:
a consolidated PC installer must record its own before/after receipt and include
all required helper files. Do not overwrite the installed launcher ad hoc or
re-run an old installer against this extra delta. The CI reproduces the old
incorrect label and executes the actual repaired RefreshUi under StrictMode.

## 5. One read-only diagnostic

`no11_decision_audit_readonly.py` reads UTF-8 explicitly and emits only bounded
status/decision fields, never raw account JSON or exception source text. Invoke
as a script file, not Python `-c` from Windows PowerShell. It uses SQLite
`mode=ro`, `query_only=ON` and one read transaction; it does not use `immutable=1`
against a changing WAL database. It reports missing historical reasons as
`legacyConsumedWithoutReason`, not as zero signals or zero buying power.

The ledger and separately updated pipeline report are explicitly NOT certified
as one atomic snapshot. SQLite may use shared-memory/WAL machinery during a
logical read-only query; no database writes, checkpoints or mode changes are
requested by the diagnostic.

## 6. Redacted Node tick failure provenance (2026-11-12 follow-up)

The 2026-11-12 live session reported `NO11_SERVICE_NODE_TICK_FAILED`
at 12:53:32. The last published pipeline report was 12:52:45,
and the collector log continued through 12:53:29. The operator then reported
closing the window with X. This does **not** prove the window action caused
the Node failure.

The native service ran `node no11_received_pipeline_tick.mjs` with
`capture_output=True`. The preexisting nonzero-return path surfaced its
`stderr` only if it was EXACTLY one `NO11_*` token; empty, multiline,
runtime-exit and warning-prefixed stderr all collapsed to the same generic
`NO11_SERVICE_NODE_TICK_FAILED`. The original raw stderr was discarded.
Therefore this incident's underlying Node process cause cannot honestly
be reconstructed from the supplied snapshots.

The staged, source-pinned `pipeline_node` transform adds one bounded,
private, non-overwriting `node-tick-failure-<random>.json` for each
nonzero Node subprocess result (except the unchanged partial-write retry).
It records the original return code, stderr/stdout byte lengths and SHA256
digests, a bounded allowlisted single-line error-code list and timestamp.
It **never** records raw stdout/stderr, arbitrary exception contents,
private paths, account contents or securities. Writing failure fails closed.
The original `NO11_SERVICE_NODE_TICK_FAILED` behavior and exact
`NO11_PIPELINE_CAPTURE_WRITE_IN_PROGRESS` handling are unchanged.
This evidence cannot be produced retroactively and cannot survive a process
being killed before Python's error handler runs.

This is not a blanket fix for arbitrary UI-window termination. The
observed attempt remained CONNECTED without a closure receipt; it must
remain unverified until actual owned-workbook/receipt evidence is checked.
Do not synthesize a CLOSED receipt or rewrite the old claim/ledger.

## Integration / remaining deployment gate

The workflow applies `no11_operational_hardening.py --staging-checkout` only to
an isolated Git checkout. The derivation refuses unknown source spans and
proves all native service methods except `fund`/`summary` remain AST-identical.
It does not replace the frozen models, threshold, allocation, EXIT, dispatch,
ledger schema, funding policy, schedules or user data.

A reviewed consolidated after-hours installer for the ACTUAL installed source
set remains a separate release gate. It must include the new runtime helper and
chain verifier, pin their bytes, preserve all prior receipts, and transactionally
bind any changed presentation byte to its contract. No LIVE deployment, restart,
merge into the running branch, or legacy candidate replay is authorized here.

CI passing establishes the tested code paths only. It does not prove that a
real broker order is safe, accepted, filled, or that today's past missing order
has been retrospectively explained.
