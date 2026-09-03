# Phase57 Lane M — MarketSpeed II Prospective Full-Session Runbook

This runbook is for the READ ONLY / shadow-research Lane M path. It does not create, modify, cancel, or transmit orders.

## Recommended architecture: dynamic market-data slots

Lane Y runs independently in GitHub Actions. At each 5-minute boundary it durably stores the point-in-time TradingView raw snapshot immediately, and later stores the immutable Lane M decision capsule after Yahoo finalized-bar ingestion.

The Windows dynamic launcher:

1. starts MarketSpeed II/Excel capture before the first 09:05 decision and writes a session heartbeat,
2. syncs Lane Y raw TradingView snapshots from the durable branch as soon as they appear,
3. runs the same frozen Dynamic5m V1/V2 selector locally on that raw snapshot,
4. writes only the selected market-data query symbols into bounded `ArkControl` observation slots,
5. keeps RssMarket/RssTickList formulas fixed and waits until each slot reports the newly assigned symbol,
6. captures only settled MarketSpeed evidence prospectively,
7. retains recent selections as coverage buffer and pins already-observed Lane M inventory when possible,
8. syncs the later immutable Lane Y decision capsules,
9. runs the existing ShadowOrderIntent / ShadowFill / execution-aware trade engine,
10. updates the 28-strategy dashboard,
11. stays alive through the 16:10 JST delayed final drain.

A newly selected symbol that had no pre-decision MarketSpeed observation can still fail the existing stale-reference rule. The system does not fabricate an earlier quote. Retention improves coverage but does not change Selection, Entry, EXIT, or Allocation decisions.

## Safety boundary

The dynamic path deliberately permits one narrow Excel write surface:

`excelMarketDataQueryWriteAllowed=true`

This permission applies only to `ArkControl` symbol cells that feed READ ONLY market-data formulas. The following remain false:

- `executionAllowed`
- `brokerWriteAllowed`
- `excelOrderWriteAllowed`
- `rssOrderFunctionAllowed`
- `liveTradingAllowed`
- `paperTradingAllowed`
- `automaticPromotionAllowed`
- `productionUpdateAllowed`

The generated workbook contains only `ArkControl`, `ArkMarket`, and `ArkTicks`. Runtime does not write formulas. Order-capable RSS functions such as RssStockOrder / RssModifyOrder / RssCancelOrder are rejected by formula-surface validation.

## One-time clean workbook creation

From the repository root, create a fresh Lane M workbook. The default is 80 dynamic slots with 100 recent ticks per slot:

```powershell
powershell -ExecutionPolicy Bypass -File tools\phase57_msii_setup_dynamic_workbook.ps1 `
  -WorkbookPath "$HOME\Desktop\ArkLaneM.xlsx" `
  -Slots 80 `
  -TickRows 100
```

Use `-Overwrite` only when intentionally replacing an existing Lane M workbook.

The setup process creates:

- `ArkControl` — the only runtime-writable market-data query symbol cells,
- `ArkMarket` — fixed RssMarket formulas for top-of-book and depth,
- `ArkTicks` — fixed RssTickList spill blocks.

Keep the generated workbook dedicated to Lane M. Do not add order sheets or order-capable RSS formulas.

## Prerequisites before the session

- Windows PC is awake and connected.
- MarketSpeed II is open and connected.
- Excel is open with the generated `ArkLaneM.xlsx` workbook.
- MarketSpeed II RSS add-in is active.
- Python RSS dependencies are installed from `tools/requirements-rss.txt`.
- Repository is on the latest `main`.
- Start the launcher before 09:05 JST if the session is intended to be eligible for full-fresh classification.

## Start the dynamic prospective session

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File tools\phase57_msii_windows_dynamic_session.ps1 `
  -Workbook ArkLaneM.xlsx
```

The default launcher uses 80 slots, 100 tick rows per slot, one-second MarketSpeed capture, three recent V1 points as best-effort coverage retention, and a 16:10 JST final drain.

The launcher fails closed if the dynamic capture cannot attach to the active Excel workbook, if a forbidden RSS order-capable formula is detected, if current V1 plus pinned Lane M inventory exceeds slot capacity, or if the existing causal evidence requirements are not met.

## Causal dynamic-selection timing

The dynamic watchlist is built from the immediate point-in-time TradingView raw snapshot, not from the later Yahoo-finalized Lane Y result. Therefore the Excel symbol change itself is causal with respect to the observed selection snapshot.

However, a symbol that first appears at the current 5-minute decision cannot have a MarketSpeed quote from before that same decision unless it was already retained in a slot. The current Lane M engine keeps its pre-decision reference requirement; first-appearance symbols may therefore be blocked rather than receiving invented evidence.

Recent-selection retention is coverage-only. It does not keep a symbol selected for research, create an Entry, prevent an EXIT, or alter Capital Allocation.

## Keep running

For Lane M prospective evidence, the Windows PC, MarketSpeed II, Excel/RSS, dynamic capture, and launcher must remain running through the market session. Lane Y itself remains independent because it runs in GitHub Actions.

After 15:30, the launcher stays alive until 16:10 JST by default only to receive the delayed immutable Lane Y capsules. MarketSpeed evidence for those event times must already have been captured prospectively.

## Dynamic outputs

Local root:

`data/phase57-msii-dynamic-live/<YYYY-MM-DD>/`

Important files include:

- `lane-y-raw/*.json` — immediate point-in-time TradingView snapshots synced from the durable branch,
- `dynamic-watchlist-latest.json` — current V1/V2/pinned/retained observation set,
- `dynamic-watchlist-state.json` — causal prior-selection state,
- `msii-dynamic-p32.jsonl` — original dynamic-slot capture with assignment provenance,
- `msii-runtime-p31.jsonl` — settled compatibility projection consumed by the existing Lane M runtime,
- `lane-m-output/full-session-state.json` — durable local Lane M execution state,
- `lane-m-output/latest-score.json` — execution-aware score,
- `lane-m-output/latest-pair.json` — exact Lane Y/M pair diagnostics,
- `lane-m-output/coverage-latest.json` and `coverage-final.json`,
- `lane-m-output/dashboard-latest.json`,
- `lane-m-output/dashboard-history.json`,
- `lane-m-output/full-session-final.json`.

The p32 source row hash is retained in every p31 compatibility projection. Unsettled slots are not projected as MarketSpeed market evidence.

## Dashboard

`dashboard-latest.json` exposes, without decision recomputation:

- fill / partial / no-fill / expired / source-not-ready rates,
- average decision-to-first-fill latency,
- spread cost and slippage,
- execution-aware closed trades and Net PnL,
- exact Lane Y / Lane M pair counts,
- MarketSpeed symbol coverage,
- all 28 `matrixCell × allocationProfile` strategy rows with Net%, PF, MaxDD, WinRate, open positions and pair/fill counts.

Coverage and dashboard diagnostics are descriptive only. They cannot rescue, backfill, retune, promote, or upgrade a blocked point.

## Session-quality interpretation

- `FULL_FRESH_MSII`: local prospective capture was active by the predeclared boundary, no sticky missing capture remained, and no backfill was used.
- `PARTIAL_INCOMPLETE_MSII`: capture started late or the session accumulated a permanent missing point/coverage gap.
- `SOURCE_NOT_READY`: no usable MarketSpeed capture start/evidence was established.

A later file arriving after a causal deadline cannot convert a blocked or partial point into Full Fresh.

## Legacy preconfigured registry path

The earlier fixed preconfigured multi-symbol path remains available for diagnostics and backward compatibility:

- `phase58_excel_multisymbol_microstructure_capture.py`
- `phase58_validate_msii_multisymbol_registry.py`
- `phase57_msii_windows_full_session.ps1`
- `phase57_msii_windows_full_session_dashboard.ps1`

For the current Dynamic5m research lane, the dynamic slot launcher above is the recommended path.

Frozen selector, Frozen Entry, EXIT v3/v4, Capital Allocation, thresholds, weights, and Lane Y behavior are unchanged.
