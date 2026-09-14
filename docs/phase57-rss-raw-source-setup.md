# Real RSS source workbook setup v1

Run `./tools/Setup-ArkSource.ps1` from this repository's root, with MARKETSPEED II connected and `C:\Ark\Source.xlsx` already open in that Excel instance. Python 3.10+ and Node are required; the script installs pywin32 if missing. It attaches to that workbook only, makes a timestamped original backup, adds two RAW sheets, saves the dedicated workbook, generates `C:\Ark\local-source.json`, and captures 60 seconds through the existing source diagnostic. Evidence paths are printed. Keep Excel open. No strategy is started.

The default `7203.T` is a transport diagnostic sample, **not** a Selector universe. Optional `-Symbols` accepts up to ten distinct numeric TSE codes with `.T`; `-Rows` supports 1–3000. Reruns accept an identical verified RAW layout; changed/partial layouts fail without replacing sheets. Restore the timestamped backup to deliberately change this setup. Existing `ARK_CONFIG!B1 = ARK_SOURCE_V1` and the user's 15-column `ARK_CHART_5M` remain untouched. Unknown/order-enabled sheets, macros, external connections, names, or foreign formulas reject setup before mutation. Setup writes only explicit official information formulas; the capture process never writes, opens, refreshes, calculates or saves Excel.

## Exact source architecture

Official supplied `ms2rss_function(1).pdf`: function arguments RssChart and RssMarket; return fields RssChart 日付/時刻/始値/高値/安値/終値/出来高 and RssMarket 現在日付/現在値詳細時刻/現在値/最良買気配値/最良売気配値.

| Sheet | Purpose |
|---|---|
| ARK_CONFIG | Existing workbook identity B1 preserved |
| ARK_CHART_5M | Existing normalized template preserved; RAW capture does not read it as market data |
| ARK_RAW_CHART | Per slot nine columns; function at row 1, seven exact Japanese headers at row 2, RSS output from row 3 |
| ARK_RAW_MARKET | Five direct RssMarket formulas per symbol; Japanese headers at row 1 |

Example function: `=RssChart(A2:G2,"7203.T","5M",120)`. The function returns below its specified same-sheet header. No cross-sheet formulas, nested functions, tick features, or order functions. RAW sheet names are permitted only under `ARK_RSS_RAW_CONFIG_V1`. The previous flat source config stays supported. Formula/slot/header identity is rechecked every capture.

Python maps slot/generation/symbol/sourceCode from the validated layout and date/time/OHLCV from chart cells. marketTimestamp combines **RssMarket's own current date and detailed current-price time**, never the chart date. currentPrice/bestBid/bestAsk are capture-time diagnostics; they are not historical quotes associated with each old chart bar. Numeric Excel dates use the 1900 date system; 1904 workbooks fail. Serial times and official textual formats are explicitly parsed. Invalid cells become marked parse errors; original raw values remain in raw-reads.jsonl. No forward fill or synthetic OHLCV.

Two reads preserve before/after arrays and capture start/end. Their equality does not prove atomicity, freshness or bar completion. Chart rows outside the capture session are excluded only from today's normalized observer and remain in raw evidence. All current-session rows, including forming/duplicate/revised rows, reach the diagnostic. Finality stays UNVERIFIED; start/end labels are hypotheses, not decisions. MSII connection remains independently unverified by the software, even when the user sees connected locally.

## Verification boundary

`python tools/test_phase57_rss_raw.py` exercises a COM-shaped synthetic workbook through the actual setup, capture, normalization, packet and Node diagnostic. Windows CI also runs `Setup-ArkSource.ps1 -FixtureTest`. These checks do **not** test the installed RSS add-in or actual Excel COM behavior. The real script's first run is the local gate; preserve its backup/error/evidence if Excel rejects a formula or changes its representation. No realtime strategy, reserved strategy outcomes or future OOS are opened. The existing date gate still blocks 2026-10-22+ capture.

## Observed Excel compatibility contract (2026-09-14)

The user reported successful real Windows COM workbook discovery and live RssChart/RssMarket delivery. Record `REAL_RSS_TRANSPORT_PASS` as **user-reported local evidence**, not Work-observed execution. Bar finalization and realtime Shadow remain unverified.

Excel generated one hidden compatibility name after information-formula insertion. The source audit now permits zero names or exactly one name with all three exact properties: Name `_xlfn.SINGLE`, Visible `False`, RefersTo `=#NAME?`. Visible names, different references, scoped/prefixed names, additional names and every other name still fail. The artifact is never evaluated or rewritten by our code.

Both UsedRange.Formula and UsedRange.Formula2 are audited. The only added representation equivalence is direct `=RssChart(...)` / `=@RssChart(...)` (likewise RssMarket and the existing read-only RssTickList allowlist). Formula2 may also equal Formula. After removing at most one leading implicit-intersection marker in Formula2, both strings must match exactly. Nested expressions, external/cross-sheet references, unknown functions and order functions remain rejected. Raw layout formulas still match the generated exact symbol/field contract.

When both RAW sheets already exist, their formulas and chart/market headers must pass the full audit. The verified existing-layout path now calls Save before reporting success or writing local-source.json. This recovers the user-observed first attempt that stopped after RSS insertion but before Save. Missing or mismatched layouts still fail without saving. The same PowerShell launcher then generates config, captures 60 seconds in SOURCE_SEMANTICS_ONLY and writes diagnostic/summary.json. A 60-second run alone does not establish finalization or all session-boundary semantics.

## Feed freshness, retry and bar-observation diagnostic (2026-09-14)

The user reports a successful ten-minute real-time RSS run with active chart and market updates, plus repeated freshness warnings and failures at captures 390/428. `REAL_RSS_TRANSPORT_PASS` and `REALTIME_RSS_UPDATE_PASS` are recorded as user-reported local evidence. The original capture/error files have not been supplied here, so those two failures' root causes are **not confirmed**. No reserved strategy outcomes were evaluated.

The old observer already compared capture time against RssMarket's timestamp, not chart labels. Its problem included counting the same timestamp warning once per historical bar. It now groups current-price/bid/ask/time by slot/symbol per capture and counts freshness once per symbol/capture. Historical chart label age is separate descriptive data and never a freshness rejection. The existing 30-second current-price freshness threshold is unchanged. This is last-price-update age, not a guaranteed transport heartbeat: an inactive price can be old even when RSS is connected. Lunch and after-close observations do not produce active-session stale alarms.

`REAL_SOURCE_CONNECTED_OBSERVED` requires a healthy, consistent read, no explicit disconnect, same-day/nonfuture/fresh market timestamp, valid positive price/bid/ask with bid <= ask, coherent duplicated market fields and at least one valid same-day 5m chart label. Per-feed observations and the aggregate latest connectionState are recorded. This status cannot unlock strategy. Missing quotes, inconsistent reads, conflicting current feed, wrong dates and future timestamps remain unverified.

Capture takes A, waits 50 ms, then takes B, with at most three attempts. Every successful A/B read is durably recorded before the next step, including failed attempts and exception details. Transient COM exceptions retry; safety/contract validation errors immediately fail closed. Only a matching pair is an `atomicCandidate`; equality does not prove atomicity or finalization. Exhausted unequal pairs remain PARTIAL_READ; exhausted COM errors remain failures. The observer preserves such packets in its journal but excludes their bars from timing/revision state updates.

The report now includes latestBars per symbol (and top-level latest fields for a single symbol): latestSourceTime, latestBarFirstAppearance, latestBarLastChange, latestBarRevisions, latestBarAgeMs and candidateFinalizationLatencyMs. Bar records retain START/END hypotheses, first-appearance latency, next adjacent bar appearance and revisions after that appearance. A successor candidate requires a bar already seen in an earlier capture and a newly seen adjacent successor; simultaneous initial backfills and lunch gaps provide no such evidence. Candidate latency uses the START-label hypothesis and is invalidated if the prior bar subsequently changes. The newest bar normally has a null candidate until a successor exists; inspect previous bar records for completed successor observations. No unchanged-value, next-bar or latency observation sets finalized=true: safeCompletedBarTime stays null and finalization stays UNVERIFIED.

For another ten-minute diagnostic, use the same setup launcher with `-Seconds 600`. Existing audited sheets are reused and saved; config generation and SOURCE_SEMANTICS_ONLY remain unchanged.

## Bounded latest-N chart window (2026-09-14)

The user reported 444 successful captures with events=[] on df7f44f, but Excel's latest bar was at row 138 while normalized output stopped at 13:00. Code inspection confirmed the previous reader used A3:G122 for chartRows=120. The original real capture file is not available here, so the precise real-run discrepancy is user-reported; a row-138 synthetic fixture reproduces and verifies the reader correction.

`chartRows=120` now means the latest **up to 120 nonempty valid bars**, not the first 120 Excel rows. The official RssChart formula's Rows argument remains 120; no RSS formula or strategy policy is changed. Each slot uses its fixed audited seven columns, row-2 headers and a maximum row-3..3002 search rectangle (3000 physical data rows). Reader access never expands to unlimited UsedRange. Sheet extent metadata exceeding row 3002 fails with RAW_CHART_SCAN_LIMIT instead of silently omitting later rows. This is a reader safety bound, not a claim that the add-in never grows past it. Blank rows consume search capacity but not selected-bar capacity. Any nonblank malformed or chronologically reversed row fails closed; duplicate timestamps now fail closed under the unpopulated-row correction below. Lunch gaps are retained without synthetic bars.

New local-source.json explicitly uses `chartReadPolicy=LATEST_N_WITHIN_3000_ROW_SCAN_V1` and slot.chart=A3:G3002 (corresponding columns for other slots). Exact legacy configs with A3:G122 remain accepted, but they also use the bounded scanner; altered foreign ranges are rejected. Running the existing setup command updates the local config while retaining the audited RSS formulas and workbook layout.

Full bounded A/B scans remain in raw-reads.jsonl before validation/window selection. capture.jsonl adds `rawWindowMetadata` per slot, including rawFirstSourceTime/date, rawLastSourceTime/date, rawValidRowCount, rawLastExcelRow, selected first/last Excel row, selectedBarCount, scanRange, and requestedLatestBars. Normalization still admits the current capture session only. `rawLatestSessionSourceTime` is measured from the full scan; it must match `normalizedLatestSourceTime` from the selected normalized rows. A mismatch produces RAW_NORMALIZATION_LAG, discards normalized rows from the failed packet, and never enables strategy. No current-session bars produces NO_CURRENT_SESSION_BARS, not PASS. The observer also verifies claimed PASS metadata against actual packet rows.

summary.json retains `rawWindowObservations` and `latestRawWindowMetadata`. For the 60–120 second local check, confirm the same slot/symbol/date, `normalizationParity=PASS`, matching rawLatestSessionSourceTime/normalizedLatestSourceTime, and the expected rawLastExcelRow. With current-day newest data, rawLastSourceTime also matches. Formula Rows remains unchanged. Feed freshness, transport observation, finalization policy, Frozen Main and future OOS remain unchanged.

## Unpopulated RSS rows (2026-09-14)

The 401a007 local gate failed at physical row 15: valid 2026/09/10 15:25 timestamp, blank OHLC and zero volume. This user-reported source-only observation is reproduced in the workbook → capture → latest-window → normalization → diagnostic fixture. It is not a strategy outcome or evidence of bar finalization.

Reuse Phase58's exact recognized display-placeholder characters through `rss_chart_semantics.py`; its existing parser behavior and 17 regression tests remain unchanged. Phase57's narrow allowlist skips all-blank OHLC with blank/zero volume, or all-dash OHLC with blank/dash/zero volume. Mixed blank/dash OHLC is not admitted by this narrower gate. Numeric/date/time parsing remains strict. Validate every timestamp and strict chronological order before excluding any unpopulated row; duplicate timestamps (including skipped rows) fail closed. Partially populated rows, unknown placeholders, malformed numbers and positive volume without OHLC still fail.

`rawValidRowCount`, `rawLastExcelRow`, and the latest-N selection count only valid numeric OHLCV bars. Full raw reads are still preserved. `skippedUnpopulatedOhlcvRowCount` and `skippedUnpopulatedOhlcvRows` expose physical Excel row, source date/time and reason (`UNPOPULATED_BLANK_OHLC` or `UNPOPULATED_DASH_OHLC`). Fully blank spacer rows remain ignored. Excluding an unpopulated row does not create a synthetic bar or establish completion.

From the PR #584 checkout, with Excel/MSII open, run `git pull --ff-only; if ($LASTEXITCODE -eq 0) { .\tools\Setup-ArkSource.ps1 -Seconds 90 }`. Inspect diagnostic/summary.json: latestRawWindowMetadata must show the skipped rows, normalizationParity=PASS and rawLatestSessionSourceTime equal to normalizedLatestSourceTime. Actual patched Windows capture remains to be observed. No finalization or Shadow PASS is claimed. SOURCE_SEMANTICS_ONLY, freshness, #583, future OOS and all safety flags remain unchanged.
