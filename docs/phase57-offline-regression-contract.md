# Test-only offline regression contract — v1

Scope: preserve Development commit `772c4ed40a43590c6198f6f34ab18b5e9226df18`,
not continue Entry research. Production defaults and research semantics are unchanged.
No canonical repository-wide no-network test flag existed; offline cloud queues and paper
replay flags were unrelated. The single activation flag is `ARK_TEST_OFFLINE=1`;
`ARK_OFFLINE_AUDIT_DIR` is an audit-output path, not another mode switch.

## Inventory (static source inspection; no provider request)

| Path / component | Possible communication | Offline disposition |
| --- | --- | --- |
| `predict/tests/p23-17-exit-quality-recovery.test.mjs` importing `predict/daytrade/run-phase57-p23-17-exit-quality-recovery.mjs` | Top-level Yahoo chart acquisition on import | Test now evaluates only the actual canonical constant declaration in an isolated VM. Original assertions retained; runner not imported or modified. No EXIT run. |
| `predict/data/phase50-historical-downloader.js` | Yahoo via injected/default fetch | Existing injected fixtures; default fetch blocked |
| `predict/market-intelligence/market-data-provider.js` | fetchHistory adapter | Existing mock provider tests |
| `predict/long-only/phase57-long-only-jquants-client.js` | J-Quants v2 via fetch | Existing synthetic/injected provider fixtures |
| `server/providers/jquants-tdnet-provider.js` | J-Quants via fetchImpl | Existing mocked responses; no API key use |
| `server/providers/finnhub-news-provider.js` | Finnhub via fetchImpl | Existing mocked responses |
| `server/screener-data.js` | GitHub-hosted screener data via fetchImpl | Discovery tests use mocks; default fetch blocked |
| `tools/phase58_excel_*`, MSII capture tests | Local Excel/MarketSpeed interfaces | Existing Python fixtures/mocks; no real terminal, orders or Project data |
| HTTP/HTTPS, global fetch, HTTP2, DNS, TCP/TLS, UDP, WebSocket | Transport paths, including indirect axios/urllib/requests if used | Node/Python guard plus inherited kernel prohibition |

TradingView is not added as a new provider/test. No axios/requests/urllib outbound call was
found in the executed test files during inventory; transport protection still covers
ordinary clients using sockets. Mock request counters in tests are not provider requests.

## Guard and fail-closed contract

Use `python scripts/run_offline_regression.py --output-dir <new-directory>`.
Only Linux x86_64 with installed system `libseccomp.so.2` is supported; missing support
is a hard failure, never an unguarded fallback. The launcher loads a seccomp filter
before exec: non-AF_UNIX socket creation and every connect syscall cause process
termination. Filters survive fork/exec; child descriptors are closed. AF_UNIX socketpair
is retained for in-process event-loop wakeup/IPC, not network proxy connections.
No system firewall or production default is changed.

Node preload blocks fetch, HTTP(S), HTTP2, TCP/TLS, UDP, DNS and WebSocket before I/O.
Python audit hooks block socket connect/DNS/sendto. Every unexpected attempt is logged;
catching the exception still produces exit97. Explicit test-injected mocks remain allowed,
but cannot create a real Internet socket underneath. Kernel termination cannot be caught
as a normal provider failure and reported as test success.

Six preflight probes test caught fetch, caught HTTPS, caught Python DNS, raw IPv4,
raw IPv6, and explicit synthetic mock success. Probe requests use no real provider;
all are stopped before transport. Probe denials are separate from unexpected suite attempts.
Raw kernel probes must terminate with SIGSYS. A failed probe blocks the entire suite.

The runner uses exactly the same Predict/Discovery file globs as existing npm test,
plus the existing Foundation subset, existing 30 Python synthetic tests and 89 RSS tests.
No project training/evaluation runner is called. Foundation's39 tests overlap Predict
and must not be counted as39 additional unique tests. Existing historical synthetic
SHORT/EXIT fixtures are regression checks, not this line's Project SHORT/EXIT evaluation.

Suite output, test totals/PASS/FAIL/SKIP, guard-load records and denied attempts are saved.
SKIP is disclosed, never silently treated as PASS. Guarded process-tree transmitted
Yahoo/J-Quants/other-provider requests are zero when all tests and guard probes pass.
This attestation does not retroactively resolve the previous turn's unknown network count.

## Integrity / CI

`verify_phase57_development_preservation.py` compares the original pinned manifest and
every model/OOF/report/ledger byte hash, plus protected contracts and implementations.
It does not import the model, create predictions, fit a scaler, or recompute performance.
The Ridge artifact SHA is checked against the frozen reference; raw provider/model
archives are not reacquired. All three threshold results and BORDERLINE remain unchanged.

Predict Tests, Foundation and Phase52 regression steps use the guarded launcher.
Dependency installation / checkout / artifact upload / GitHub publication occur outside
the regression sandbox and are not market-data acquisition. They do not receive any
permission to run project training or a provider. Existing non-regression workflow
steps retain their source semantics; Phase52's fail-closed zero-candidate record is local
and does not fetch market data. PR runs cannot persist that record to main.

No selected threshold. No Validation/OOS/Project EXIT/Project SHORT access. All research
safety flags remain false. Evidence Freeze is separate from Candidate Freeze.

System-call behavior reference: [libseccomp rule API](https://man7.org/linux/man-pages/man3/seccomp_rule_add.3.html)
and [Linux seccomp inheritance](https://man7.org/linux/man-pages/man2/seccomp.2.html).
