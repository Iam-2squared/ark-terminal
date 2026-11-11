# 2026-11-11 | After 09:00 LIVE source-validator stop

## Verified physical facts (not a trade fill confirmation)
- 08:30 standby authorization was claimed exactly once; 09:00 native Trade requested once. Same-day `PREOPEN-2026-11-11.execution-claimed` and `TRADE-2026-11-11.launch.json` are present and MUST NOT be removed.
- The already installed 2026-11-10 locale/template fix worked in physical Excel: `AUTOMATIC_TRANSPORT_CONTROL_ORIGIN=EXACT_INERT_TEMPLATE`, `AUTOMATIC_TRANSPORT_FORMULA_GENERAL=ALREADY_VALID_NO_FORMAT_WRITE`, `AUTOMATIC_TRANSPORT_SESSION_INITIALIZED=True`.
- Same-day candidate intake 44, machine source-filter PASS 42, excluded 2; the initial broker launch reached a new native process.
- Engine process exited around 09:02 with `NO11_BOOTSTRAP_SOURCE_EXPORT_OR_VALIDATION_FAILED` and observer cleanup nonzero. The export wrapper intentionally redacts the underlying Node.js stderr.
- An **independent, unchanged, Git-blob-verified native validator** (`no11_verified_weekly_shadow_scope.mjs` blob `b777b944379c7c6dda15eac10ddda5959ab181c8`) reproduced `NO11_WEEKLY_SHADOW_SCOPE=BLOCKED|NO11_WEEKLY_SHADOW_RECEIPT_HASH_MISMATCH`; exit 2.
- Separately, the reported installed `no11_received_pipeline_tick.mjs` raw Git blob is `974f3da4473cdcd37cc6218d0b675cff28cfa9ab`. The November 11 follow-up reproduced this exact blob by converting the repository original (`1e7c7353efde2b2a3016ca72dd3ea04673ed2484`) from LF to Windows CRLF, without any content changes. This reported snapshot is therefore explained by line endings; it is not evidence of an unknown code patch or data corruption. Do not overwrite the installed file. A later change on the PC would require a new identity check.
- Shared logs alone do not establish broker state. During the November 11 follow-up the operator explicitly reported no ARK open orders, fills or positions. The new retry still requires a fresh machine observation of empty order, execution, position and RSS order-ID tables; the statement is not substituted for machine evidence.

## Code-level cause (deterministic naming contract mismatch)
- Original daily source exports `no11-chart50-private-<SHA256 first 16>.json` from `no11_export_chart50_prescreen.mjs`.
- `no11_verified_weekly_shadow_scope.mjs` intentionally accepts and verifies **only** the original 16-hex receipt. Keep this original independent source check unchanged.
- The same-day source eligibility filter in `automatic_morning.py` correctly constructs an immutable `no11-chart50-private-<FULL SHA256 64>.json` through `morning_master.immutable()`, marking it `automaticVerifiedExclusion`, with parent-original SHA256 and a SHA-pinned exclusion report.
- `no11_received_session_bootstrap.py:export_scope` used to pass the **filtered** full-64 receipt directly to the original 16-hex native source gate. On a day with nonzero rejected symbols this necessarily hits the receipt-name check before later model/strategy checks, regardless of whether source contents are otherwise valid. This is a plumbing defect, not proof the original RSS history is corrupt.

## Scoped draft fix, NOT deployed to the user's PC
- `no11_weekly_filtered_lineage.py` transforms exactly one helper and source-argument selection in the installed bootstrap. It requires the filtered 64-hex bytes to match the full hash, obtains the exact original 16-hex source from the filtered record's parent SHA256, and verifies both records against an immutable same-day exclusion report and narrowed dated master.
- Replays the original native-filter deterministic array and protected chart operations: only known rejected symbols can be excluded; no unauthorized symbol can be added; held/pending protected chart symbols are retained for EXIT.
- Sends the original 16-hex receipt into the **unchanged** `no11_verified_weekly_shadow_scope.mjs` for complete original-RSS lineage checking; returns the filtered 64-hex receipt to the **unchanged** downstream `validate_scope` for native plan hash and dated-master validation. Neither validator is relaxed.
- `install_no11_weekly_filtered_lineage.py` is default audit only; any explicit code installation is transactional, pinned to known source blob, journaling first, requires no OneClick/ARK workers and is blocked 08:00–15:30 JST. Does not touch Excel, settings, ledger, order/marker, white UI, original receipts, broker approval, native sender or strategy. Unknown local source means **BLOCK**; do not force-overwrite. In particular, the engine's original bootstrap may have other locally installed changes; inspect its Git blob before attempting deploy.
- The installer remains restricted to legitimate out-of-session preparation. A separately implemented, isolated pre-registration retry is described below; it does not change the installer's time gate, redate inputs, replay an order or reset the original one-shot claims.

## Independent checks
- `test_no11_weekly_filtered_lineage.py` exercises valid original/full-hash exclusion and missing or tampered report/master/original, protected-chart mutation, and verifies the patched export passes the original to source checker but preserves the filtered child downstream.
- `test_no11_weekly_filtered_install.py` exercises audit-only, strict known-source identity, idempotence, crash recovery, unknown source refusal, broker/UI frozen-file guards, no marker deletion.
- CI: `.github/workflows/no11-filtered-weekly-receipt-lineage.yml` on Windows/Linux. Do not count release as PASS until the current HEAD completes all checks.

## Required operational follow-up
1. Keep the original `TRADE-`/`PREOPEN-`/ledger markers and all failed-session evidence. The ordinary START path remains consumed for November 11.
2. Use only the explicit isolated retry below if every pre-registration, source-identity and current broker check passes. It is one attempt, not an automatic restart loop. An eligible audit is not a launched collector or confirmed fill.
3. Apply the permanent installer after market with no ARK workers, once exact installed source compatibility is proven. Do not assume an unmodified repository blob when official local patches are installed.
4. A later session requires its own legitimately generated, date-correct handoff and explicit same-day approval. Never reuse or redate November 11 materials.

## Follow-up: repair CI execution before deployment
- The dedicated installer suite previously could not import because its final forbidden-token tuple had an extra closing parenthesis. Remove only that syntax error; preserve every installer assertion.
- The broader No12 Node suite was missing `no11_weekly_g1_refresh.completed-test.mjs`, a generated test fixture. Generate it with the same real `install_no11_completed_session_update.transform('planner', original)` used by the dedicated completed-session workflow; do not replace the import with the untransformed production planner or skip the tests.
- Local Linux checks after these two CI-only repairs: lineage 11/11, installer 8/8, transformed completed-session planner 15/15 PASS. All seven applicable remote workflow runs on `ae4415057bea9ce6e2e99cf3fec3387f96617de4` subsequently completed successfully, including the dedicated Windows/Linux lineage job and broader No12 suite. These results do not prove physical deployment or a same-day restart.
- The reported pipeline CRLF identity was independently reproduced from exact repository bytes. The reported PC bootstrap blob `011171c82c960e3b2a8f520439e3e609b2578607` exactly matches the original bootstrap after the official `no11-rss-funding-live-20261103/patches.py:change_bootstrap` transformation (26,633 LF bytes; SHA256 `dab361b91a7d98cfd83f74ff768cc7374ff307e3b5051de000acf93a4886c41f`). Installer compatibility now recognizes this exact official variant, including its BOM/CRLF equivalents, while preserving the funding code and existing gates.
- Current deployment and restart capabilities remain unchanged: the installer refuses apply from 08:00 through 15:30 JST, and the existing same-run collector recovery does not cover a failure in `bootstrap.prepare()` before `recovery.register()`. A request to resume that failure later the same day needs a separately implemented, reviewed path that retains the original attempt evidence and reconciles current broker state; the CI fixes do not add that path.

## Follow-up: isolated pre-registration retry

`no11_prestart_source_retry.py` and `Request-No11PrestartSourceRetry.ps1` implement that separate path. The default command audits only. LIVE entry additionally requires `-Start -IConfirmNoOrdersFillsOrPositions`, a current-session window, and all of these observed conditions:

- The original same-day TRADE marker hashes the unchanged LIVE bootstrap config, and the original PREOPEN request/nonce/claim match. All original markers remain byte-for-byte intact.
- Every same-day native run contains only `controller-failure.json` with the exact source-export failure code. Registered runs, active pointers, prepared inputs, inference/collector state, dispatch history or a prior retry claim block this route.
- Installed bootstrap/operator/controller/recovery/native weekly-validator identities are known. The operator accepts only official original, RSS-funding and XLSB-compatible variants. All installed Python, Node and PowerShell files and selected source inputs are pinned again before entry; unknown source is not overwritten.
- No ARK worker or white OneClick process is active. A fresh read-only account observation contains no orders, executions, positions or RSS order IDs. Physical Excel PID/start/window/session match the original transport, all three registered books remain open, RSS add-ins are connected and dedicated send controls are idle. The script does not initialize, write, save or reformat Excel.
- A unique package receives only the exactly derived bootstrap, a small controller entry, the original operator with its four resource paths adjusted, and pinned verification helpers. The installed engine, white UI, sender, strategy and original configs are not replaced. The native controller's exclusive lock, `RunRecovery.check_new()`, model/source preflight, registration and broker protections still execute.
- A separate create-new retry claim is flushed before requesting one native operator process. A second create-new controller claim prevents re-entry. Neither claim is automatically cleared after failure. The process-start receipt explicitly distinguishes a requested process from collector operation and from any order or fill.

Offline regression coverage is in `test_no11_prestart_source_retry.py`; `.github/workflows/no11-prestart-source-retry.yml` runs it with the lineage/installer suites on Windows and Linux, then parses the actual derived operator and tests the request script in Windows PowerShell 5.1 without Excel or broker access. The pinned release bootstrap downloads only hash-verified immutable source files. Physical readiness still must be observed on the operator's Windows PC.

## Physical audit follow-up: retain the officially installed controller family

The first PC invocation of release `fd247109aae85ef743d6d3db76595fe8305399cf` verified the downloaded source, then stopped with `NO11_PRESTART_RETRY_UNKNOWN_CONTROLLER_SOURCE`. That invocation did not reach the native launch or create its retry claim. This was an incomplete compatibility list, not evidence that the PC controller was corrupt.

The November 3 handoff's physical output records `NO11_ORDER_TO_EXIT_WIRING_INSTALL=PASS` and `C50_TEMPORARY_BOOK=HASH_PINNED_READY`. Its pinned `live_collector_order_patch.py` blob `2c28f12c48d5f0f63729962b72159eb331921443` is identical to the repository recipe. This official V3 recipe adds the verified collector READY path/hash relay to the controller. The later same-run recovery handoff explicitly records that Draft PR #605 had not been applied to the PC. The first retry release incorrectly recognized only the newer unpatched repository controller/recovery pair.

The compatibility correction recognizes only these exact normalized controller/recovery pairs. The actual PC pair must still match one of them during its local audit; the prior install record is not substituted for that check.

| Official controller variant | Controller Git blob | Matching recovery Git blob |
| --- | --- | --- |
| Prior original | `5a2fe9f6eb785f66412cc4cd09015eb37966c58c` | `8195a1f6970ccca71f1f382403d884447a113003` |
| Prior original plus V3 READY relay | `d186384ef5040e55953caacf5deb9a23b8ba134f` | `8195a1f6970ccca71f1f382403d884447a113003` |
| Current original | `329dbb216025b31c629f6e5fcc64d628edf29e05` | `8ded9d67f0b5187eaa1fa52bdd0d03aea0512fa8` |
| Current original plus V3 READY relay | `f5dd7c5d6579da498eb1ce9471bc02292a297d1a` | `8ded9d67f0b5187eaa1fa52bdd0d03aea0512fa8` |

The old originals were retrieved from Git objects and independently reconstructed from the exact inverse of the official same-run patch; both reproduce their fixed blob identities. The initial new-run APIs are shared. The V3 relay leaves `execute`, its exclusive service lock, `RunRecovery.check_new`, native preflight and registration intact. The older recovery lacks only the later postmortem collector-cleanup receipt support, which this pre-registration, no-collector route does not use. Mixed old/new pairs and modified sources remain blocked. No controller, recovery, sender or original UI file on the PC is upgraded or overwritten by this correction.
