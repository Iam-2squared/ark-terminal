# Phase57 offline parity preparation

The offline build replays the frozen MAX_3 system on already-used A+B fixtures. Real capture remains locked. This is implementation parity evidence, not OOS, Validation, a strategy selection, or daily operational readiness.

## What is connected

| Component | Implementation and verified scope |
| --- | --- |
| Excel | Dedicated seven-sheet `tools/templates/ArkParityOffline.xlsx`; synthetic transport rows; no formulas, macros, external links or accounts |
| Field map | `tools/phase57-parity-field-map.json`; official chart OHLCV mapping, RssMarket/RssTickList diagnostic names; no invented intraday RssChartPast support |
| Reader | Python standard-library XLSX reader; pinned workbook hash; no Excel COM or workbook writes |
| Slots | Stable dynamic symbol mapping with generation checks and atomic capacity failure; no five-symbol restriction or Selector universe reduction |
| Bars | Explicit source START/END label, JST source, UTC normalized start/end, source availability and capture/observed time; no filling missing OHLCV |
| Selector | Saved frozen reference selection lineage. Independent universe/Selector parity is NOT measured |
| MSH | Rebuild all ten features from causal prefixes, reuse authorized frozen model inference, verify First ENTER probabilities/direction/risk |
| Allocation/ledger | Frozen V3_B_RISK and MAX_3 event loop port, exact 12 invariants and full per-timestamp trace compared to untouched reference |
| EXIT | Incremental bar5 state manager consumes only the current saved v4 decision; independent v4 analog scoring is NOT connected |
| Reporting | Six-stage comparison functions, explicit missing denominators, time/price/equity deltas and mismatch causes; daily/cumulative schema |
| Evidence | Exclusive writer, append-only hash chain, fsync, corruption detection; each launcher invocation creates a new directory |

The official uploaded RSS PDF was read before implementation; SHA-256 is recorded in the contract. It establishes 5M RssChart and row limits, but does not establish live bar-label/finalization semantics. Diagnostic function names in JSON do not create active Excel calls. The offline chart table uses a normalized field map, not the official function's spill layout.

Prior Phase58 capture files were inspected. Stable slot planning was retained as a pure port; old V1/V2 watchlist size restrictions and market-query writes were not imported into this isolated path. Existing `ArkMarket`/`ArkTicks` scripts and order workbooks remain untouched.

## Offline Windows command

With Node 22+ and Python 3.12+ available in PATH, run from this checkout:

```powershell
.\tools\Start-ArkOfflineParity.ps1
```

The launcher runs focused tests, reads the fixed offline workbook, normalizes its rows, then writes an evidence chain and JSON/Markdown report beneath a new temporary run directory. It does not start MSII, connect Excel, query a broker, or open reserved data. There is no live/unlock option. Excel does not need to be running; the workbook may be opened separately for inspection, without refreshing external data.

If the already-authorized local Phase B artifact directory exists, the optional historical pass is:

```powershell
.\tools\Start-ArkOfflineParity.ps1 -UsedFixtures 'C:\ArkFixtures\phase57-phase-b'
```

Expected layout is the existing `features/` directory, model at `features/10084158820/candidate-model.json`, and `artifacts/block-a/trades.json`, `artifacts/block-b/trades.json`, `artifacts/dev-final/report.json`. All accepted inputs are hash-bound. The runner does not download missing artifacts. Do not put reserved or new-session data in this directory.

Portable equivalents:

```text
node --test scripts/tests/*.test.mjs
python tools/test_phase57_offline_excel_reader.py
python tools/phase57_offline_excel_reader.py --output NEW_PACKET.json
node scripts/phase57-offline-workbook-check.mjs NEW_PACKET.json NEW_REPORT_DIRECTORY
```

The workbook has a synthetic `0000.T` transport example, not a selected security or an executed trade. Its UTC-prefixed timestamp text prevents spreadsheet exporters from losing timezone information through date-serial coercion. The explicit field map removes only that prefix on read; both the source workbook hash and parsed raw packet are retained. Saving a modified workbook intentionally invalidates its pin.

## Evidence interpretation

The A+B fixture run covers 38 used sessions, 89,292 normalized bars, 14,458 directional feature rows, 91 First ENTER events and 85 eligible EXIT paths. Only those 85 existing eligible paths enter the cash-ledger comparison; this does not establish coverage for the other six First ENTER events. MAX_3 accepts 64 and reproduces the frozen final equity of JPY 1,350,919.8. This number is a regression check, not a new performance claim.

The saved EXIT path contains non-contiguous wall-clock observations. The frozen historical engine counts observed path rows, not synthetic elapsed 5-minute slots. The historical runner preserves that meaning and discloses every gap. The default incremental manager rejects a management gap; only the two pinned used A/B path identities allow disclosed ordinal replay. No grid gaps are filled and no realtime safety conclusion follows from historical parity. Investigating whether an RSS absence is a true no-trade interval or a capture loss remains necessary before any real-data adapter could be declared ready.

MSH JSON parity uses the same JSON serialization as the saved artifact (`-0` serializes as `0`); there is no numeric tolerance or feature rounding. The ledger compares all traces, decisions, closed trades and MTM curves exactly against the existing reference. All 12 invariant definitions remain unchanged; the original Phase B library is not edited.

## Remaining gates

- Real MSII/Excel connectivity, live freshness, source timestamps and finalization are untested and locked.
- Full-universe Selector execution and independent frozen-v4 causal analog scoring need dedicated current-input adapters; saved reference decisions are explicit inputs here.
- The historical sparse-path clock must be distinguished from missing capture data before any realtime claim.
- Actual local Excel behavior, sleep/recovery and RSS updates cannot be inferred from a Linux run or a Windows CI test without Excel.
- No next-session capture, daily prospective evidence, OOS or Validation data was opened. The Entry reservation through 2026-10-21 and future Integrated OOS from 2026-10-22 remain intact.

Health tests cover disconnected/closed/error/stale conditions as fixture inputs. They are not tests of a user's actual terminal. A torn evidence tail or stale writer lock is preserved; start a new version instead of overwriting or silently repairing it. A failure halts further ledger decisions. The original failed evidence is retained for review.

Status: `OFFLINE_FIXTURE_PARITY_READY`, `REAL_CAPTURE_LOCKED`, `ORDER_TRANSMISSION_DISABLED`. Do not label this build `READY_FOR_DAILY_REALTIME_PARITY` until the remaining gates are actually satisfied.

Historical CI attempt on PR #584: run `34760321140` failed before runner/test steps, with no job logs. A retry also failed before steps on both Linux and Windows. The available connector did not expose the cause; billing is not asserted. At that attempt local relevant tests were green (112 Node, 3 Python), but GitHub CI was not green and Windows execution was unconfirmed. The completion-block recovery below supersedes that operational status. See `ci-attempt.json` for the exact tested head and jobs.

The full Predict suite was also run: 2,595 passed, one failed (`learning.test.mjs`, history filtering/pagination, 39 records versus expected 40). The identical isolated failure was reproduced on an untouched `84b2961` worktree. It is an inherited failure outside the offline parity modules; no unrelated behavior or test expectation was changed to manufacture a green result.


## Completion block (2026-09-13)

The same `585e260` source passed Linux and Windows after one retry (run 34760561728, attempt 2). The Windows launcher step ran successfully. Initial jobs had no steps/logs; their precise platform cause remains unavailable. This is evidence of recovery without a strategy or workflow fix, not a claim about billing. `ci-recovery.json` preserves both facts. The next completion commit must also pass its own checks.

The one-command launcher now checks Python >=3.12, Node >=22, workbook identity, source hashes, configuration and safety before starting. It then runs failure tests, the pinned XLSX transport, a synthetic stateful ledger/restart test, a source-only timestamp diagnostic and daily export. Optional `-UsedFixtures` adds the exact frozen-model A+B pass. No artifacts are downloaded automatically. Without the used model bundle the default smoke run does NOT claim MSH/Selector parity.

New offline outputs beneath `local-gate/`:

| Output | Meaning |
| --- | --- |
| `session/session.jsonl` | Fsynced hash chain: identity, input/output commits, terminal seal |
| `daily/*.jsonl` | Raw, normalized, decisions, ledger, health, mismatches, reference and report channels |
| `daily/manifest.json` | Freeze, repo, workbook/source identities and every channel hash |
| `daily-report.md`, `cumulative.json` | Comparison with unmeasured stages left empty; repeated session versions cannot inflate cumulative rates |
| `source-semantics-input.json`, `source-semantics-report.json` | Synthetic observations at open, lunch and close; no strategy calculation |

On clean restart, committed input replays rebuild reducer state and repeat capture IDs are suppressed. Different content under the same ID halts permanently. Identity/code changes, torn JSONL and stale crash locks fail closed while retaining the original evidence. A sealed journal can be exported to a NEW directory after an interrupted export. This tests software recovery; it does not establish actual PC sleep or Excel recovery.

The source diagnostic preserves both START/END hypotheses, first/last observed time, last changed time, repeated rows, numeric/cell errors, source timestamp freshness and observation coverage. It never infers finalization from unchanged OHLCV. Identical tick rows are counted diagnostically, not deleted: identical time/price/volume can represent separate trades. No tick becomes an MSH feature.

The seven-sheet workbook remains byte-identical and formula-free. `workbook-audit.json` pins its field map/version/hash. ARK_HEALTH truthfully shows NOT_CONNECTED/UNVERIFIED/LOCKED; generated health reports do not write into the workbook. There is no live workbook or broker connection launcher.

A+B recheck: 14,458 feature rows, 91 First ENTERs, 85 bar5 paths and 2,470 ledger events still match exactly. All 12 invariants pass. All 58 recorded gaps across 13 trades classify as FIXTURE_LIMITATION; none is an exact lunch/session transition. Whether each omission is a genuine no-trade interval or source loss remains unproven. No gap is filled or treated as safe realtime input.

`dependency-boundary.json` fixes the honest scope. Selector reconstruction requires a separate hash-pinned frozen-selector checkout, PIT full-universe admission/master metadata and full-universe completed bars. The current A+B selected-symbol bundle and Excel slots do not establish those inputs. Frozen v4's existing scorer requires a hash-bound causal analog pool, context bars and accumulated state. Saved management scores/decisions are not substitutes for that pool. Full independent Selector/v4 parity therefore remains unmeasured. The current build is DOWNSTREAM OFFLINE PARITY with explicit reference dependencies, not full end-to-end parity.

Local validation: 124 relevant Node tests and 3 XLSX tests pass, preflight passes, synthetic daily export/restart passes, and A+B exact parity passes. `pre-existing-failure.json` and both original logs preserve the unchanged-base history-pagination failure; no unrelated fix was made.

Build scope: WINDOWS_OFFLINE_GATE_READY / SOURCE_SEMANTICS_DIAGNOSTIC_CODE_READY / OFFLINE_DAILY_EVIDENCE_PIPELINE_READY. Real data remains locked. Remaining gates are actual local Windows execution, independent upstream Selector/analog input identity, real source-label/finalization evidence and live capture transport. Consequently this is not yet a "connect Excel and everything runs" build, and it is not DAILY_REALTIME_PARITY_PASS. No reserved/future data has been opened and all nine safety flags remain false.


## Offline provenance hardening

The final-integration request remains only partially fulfilled. No broker login, live RSS reader, account connection or executable-order interface was added. Independent Selector and v4 scoring remain unconnected; prior downstream parity is not relabelled as end-to-end coverage.

`selector-input-map.json` records full-universe membership, master metadata, completed bars, code/model identity and decision schedule separately. Rank, score and Dynamic N are derived outputs, not additional RSS fields. No alternate realtime source is claimed verified.

`phase57-offline-provenance.mjs` validates offline source metadata: bytes/hash, freeze, safety, session/date, availability, completion and strict prior-session/fully-realized analog timing. This checks metadata consistency only; it does not establish analog support, full-universe coverage or content correctness. Explicit coverage gates keep unmeasured upstream work visible and never unlock realtime execution. Tests cover future/forming inputs, equal-time analogs, duplicate IDs, wrong hashes, reserved dates and false promotion.

For a connection-free local check:

1. Open this checkout in PowerShell with Node available.
2. Run `node --test scripts/tests/phase57-offline-provenance.test.mjs`.
3. Return the test summary if anything fails.

This command uses synthetic metadata only and does not access market data, an account or Excel. Full research reference source files and all reservation boundaries remain unchanged.
