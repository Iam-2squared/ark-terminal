# Ark Terminal App v2

Independent read-only operational console: Dashboard, Portfolio, Positions,
Activity, Market, Execution, System, Research, Logs. Dark desktop layout with a
responsive narrow-screen navigation and position details. Polling interval is
one second; requests do not overlap. Failed status requests visibly mark the last
values disconnected. No UI control can ARM, reset, submit, cancel, or alter state.

## Start

Node 22+, npm and Git. In PowerShell from the repository root:

```powershell
.\app-v2\Start-App.ps1 -Demo
```

The launcher installs the locked dependencies, builds the browser client and starts
`http://127.0.0.1:8767`. It does not open market applications. Ctrl+C stops it.
For file-bound status, copy `local-config.example.json` to `local-config.json`, set
explicit authorized paths, then launch without `-Demo`. Missing paths show UNKNOWN.
`npm start -- --demo` works after building on Windows or Linux. This UI server has
no public deployment and only binds localhost.

## Reuse audit

- Existing root index.html/script.js/style.css and API routes are preserved.
- Existing UI is vanilla JavaScript; v2 uses a separate TypeScript browser client
  and Node-core local HTTP server rather than changing its framework or routes.
- #584 source capture / source observer report formats are read through display
  adapters. No strategy engine is imported by the application.
- #585 execution snapshot shape is admitted only with fixtureOnly=true, locked
  transmission and nine false safety flags. Actual external accounts are unbound.
- Legacy UI remains at its original URL/start procedure; v2 does not proxy its APIs.

## Display contract and source roles

`src/contracts.ts` defines ARK_APP_V2_STATUS_V1. The server reads only explicitly
configured files, never discovers protected outcome files. The source adapter
admits only SOURCE_SEMANTICS_ONLY reports. A completed diagnostic summary can show
its upstream observed connection and `fresh` value; a report older than five
seconds is labeled stale for UI observation recency. This is not a change to the
engine's market freshness threshold. Chart age and current feed age are separate.

Optional `sourceCapturePath` reads the bounded last complete JSONL capture and
shows current quotes / RAW metadata. Capture packets do not contain the observer's
computed connection/freshness verdict; those fields remain UNVERIFIED rather than
reimplementing source semantics in the UI. `sourceCapturePath` takes precedence
when both source paths are configured. A continuously published diagnostic report
is required for continuously fresh upstream connection classifications. This app
does not make a static summary a heartbeat or claim full live engine integration.

RAW normalization PASS additionally requires matching latest raw and normalized
time fields. Finalization stays UNVERIFIED. No source value unlocks strategy,
Shadow, OOS, or transmission. Unknown numeric values display dashes, not zero.
Reserved outcomes are not loaded and no strategy result is calculated.

Execution portfolio values are prominently labeled synthetic fixture status, not
real balances. External cash flow and trading PnL are separate; flow-adjusted
returns remain unknown without the necessary series. Equity conservation is
validated. The demo includes full SHORT collateral/nonreusable proceeds in its
synthetic equity identity. Position strategy details unavailable in the execution
snapshot remain UNBOUND. History is a bounded in-memory display buffer, not durable
research evidence, and clears when the source portfolio disappears.

## Verification

- `npm run typecheck`: strict TypeScript.
- `npm run lint`: syntax and read-only architecture checks (custom lightweight lint).
- `npm test`: source boundary, cash flow, conservation, malformed inputs, torn append,
  fixture labeling, HTTP write/origin/path rejection.
- `npm run build`: compile and copy local static assets.
- `npx playwright install chromium` then `npx playwright test`: nine routes, detail
  panel, disabled controls, polling/search, period filter, disconnect, mobile layout.
- `.github/workflows/ark-app-v2.yml`: the same verification on Windows and Linux,
  plus PowerShell syntax and screenshot artifacts.

Real Windows Excel/MSII integration, normal-bar finalization, prospective Shadow,
real account binding and future OOS observations remain separate gates. This PR
is a read-only UI preview, not production readiness. Keep it Draft/unmerged.
