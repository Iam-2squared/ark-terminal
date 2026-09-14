# Phase57 final integration gates

Frozen #583 remains unchanged. This pass adds a read-only source observer and
operational interfaces, not a new strategy or an OOS unlock.

## Exact boundary

The independent frozen engine can run synthetic complete-universe packets. The
existing A+B historical parity command still uses saved Selector lineage and
current v4 decisions. Its 14,458 / 91 / 85 / 2,470 exact counts do **not** establish
independent full-universe Selector or independent canonical v4 parity on A+B.
Do not combine these two kinds of evidence into a full realtime PASS.

The engine currently requires management `availableAt == decision timestamp`,
and frozen feature/EXIT code requires the exact session grid. Real capture latency
cannot be erased by changing availableAt to barEnd. Source observation is the
first gate; an explicitly reviewed timing adapter and full PIT provider are also
necessary. No actual RSS packet is relabelled as a used fixture.

## Modes and source workbook

`tools/Start-ArkParity.ps1` provides OFFLINE_FIXTURE, SOURCE_SEMANTICS_ONLY,
POST_CLOSE_PARITY, and an explicitly locked REALTIME_SHADOW mode.
The default runs the existing offline Windows gate. With `-InputPacket` it runs
the independent frozen engine. Post-close mode takes `{observed,reference}` stage
packets in the existing comparator schema, only for authorized fixture dates.

The source capture attaches to an already-open Excel instance using the existing
Phase58 GetActiveObject/Value2 approach. It never starts Excel, opens a workbook,
sets a cell, refreshes, calculates, saves, or invokes any RSS function. Read-only
means *the program does not write*; it does not suppress formulas Excel is already
running. Use a dedicated workbook, never an order-enabled workbook or sheet.

One-time preparation: Python/Node versions from the existing preflight and
pywin32 must be available locally. Review `tools/phase57-source-capture.example.json`
and set its exact absolute workbook path and bounded data range. The workbook must
be a dedicated macro-free XLSX with only the allowed source sheets. Put the literal
version `ARK_SOURCE_V1` in ARK_CONFIG!B1. ARK_CHART_5M A:O must have the fields in
the example config, with data beginning at row 2. Date/time and symbol/sourceCode
identifiers must be text; numeric OHLCV must be numeric. A missing or malformed
cell is not coerced into zero. This layout is **not** the old formula-free fixture
workbook; a verified real RSS-populated template is still outstanding.

Direct RssChart, RssMarket and RssTickList formulas alone are admitted by the
reader's allowlist. No nested functions, external links, defined names, macros,
account or order sheets. This narrow allowlist may reject a valid workbook;
review the workbook instead of disabling the guard. It does not prove official
argument correctness or RSS connection health.

## Local source gate: four steps

After the one-time prerequisites and mapping review above:

1. Start MARKETSPEED II and log in normally.
2. Open the dedicated reviewed source workbook in Excel.
3. Run `./tools/Start-ArkParity.ps1 -Mode SOURCE_SEMANTICS_ONLY -Config ./local-source.json -Seconds 60` from PowerShell. For boundary observations, repeat with separately preserved runs around open/lunch/close, or use a longer duration (up to 28,800 seconds).
4. Return the generated `diagnostic/summary.json` and relevant source-only evidence for review. No Entry, direction, EXIT or PnL is calculated.

The source summary reports UNVERIFIED even if values stop changing. MSII
connection is separately UNVERIFIED: Excel attachment is not connection proof.
Two range reads and their differences are retained. Equality is not proof of an
atomic snapshot. Dates 10/22 onward are blocked; reserved-period use is restricted
to source semantics. This process does not supply strategy evidence.

## Operational interfaces

- Reconciliation now fails closed on missing/nonfinite balances, absent position
  lists and duplicate positions. No unknown position is treated as flat.
- SyntheticCashBook separates deposit/withdrawal/manual adjustment from PnL,
  requires event identity, rejects conflicting duplicates and noncausal timestamps,
  and reports the updated equity/3 budget. It is not wired into the frozen ledger:
  historical external flow stays zero. Manual adjustment requires a reason.
- capacityBoundary preserves the frozen shadow quantity and reports unknown
  constraints. `finalExecutableQuantity` is labelled HYPOTHETICAL_SHADOW_ONLY and
  never authorizes transmission. No broker limits or new caps are invented.
- Existing hash-chain restart/export remains unchanged. Torn journals and stale
  crash locks are preserved and require explicit recovery; no automatic removal.

## Remaining required gates

1. Real RSS-populated workbook and observed label/finalization/latency evidence.
2. Complete PIT universe/master provider, symbol coverage and canonical analog
   snapshot bound to the frozen runtime; independent historical upstream parity.
3. Availability-vs-grid timing resolution preserving the frozen information set.
4. Explicit permitted-session admission before realtime strategy execution.
5. End-to-end prospective comparison and local disconnect/sleep/restart evidence.

Passing source semantics alone does not start realtime Shadow automatically.
Future OOS remains the original J-Quants-bound #583 four-arm contract: 10/22,
first 20 eligible sessions. MSII observations cannot replace that contract.
No main merge, Draft conversion, order transmission or production readiness.
