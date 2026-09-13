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
