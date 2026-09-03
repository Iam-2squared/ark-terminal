# Phase57 Lane M — MarketSpeed II Prospective Full-Session Runbook

This runbook is for the READ ONLY / shadow-research Lane M path. It does not create, modify, cancel, or transmit orders.

## What is automatic

Lane Y runs independently in GitHub Actions and persists immutable per-point Lane M capsules to:

`automation/phase57-realtime-live-data/data/phase57-realtime-live/<YYYY-MM-DD>/msii-envelopes/`

The Windows launcher:

1. starts the preconfigured Phase58 p31 MarketSpeed II multi-symbol capture,
2. verifies that the new capture process is producing fresh raw evidence,
3. polls the durable Lane Y branch for immutable causal capsules,
4. runs the Lane M full-session watcher locally,
5. preserves permanent no-backfill blocking when evidence is missing,
6. keeps running until 16:10 JST by default so Lane Y's delayed Yahoo final drain can deliver the 15:30 capsule.

## Prerequisites before the session

- Windows PC is awake and connected.
- MarketSpeed II is open and connected.
- Excel is open with the RSS add-in active.
- The workbook already contains the preconfigured READ ONLY market/tick sheets referenced by the registry.
- The registry uses only dedicated `marketSheet` / `tickSheet` mappings; runtime symbol switching is not used.
- Python RSS dependencies are installed from `tools/requirements-rss.txt`.
- Repository is up to date before starting the prospective session.

A registry has this shape:

```json
{
  "schemaVersion": 1,
  "workbook": "ArkMarketSpeed.xlsx",
  "symbols": [
    {"symbol": "7203", "marketSheet": "Market7203", "tickSheet": "Ticks7203"}
  ]
}
```

Do not interpret a valid registry as proof of future Dynamic5m coverage. A symbol selected later by Lane Y but absent from the preconfigured MarketSpeed capture must remain missing and the affected Lane M point must fail closed.

## Offline registry freeze / preflight

This validates the registry without opening Excel and produces a canonical registry hash:

```powershell
py tools/phase58_validate_msii_multisymbol_registry.py `
  --registry .\path\to\msii-registry.json `
  --manifest .\data\phase57-msii-live\registry-preflight.json
```

Expected status:

`PHASE58_MSII_REGISTRY_PREFLIGHT_READY`

The preflight explicitly reports `futureDynamicSelectionCoverageGuaranteed=false`. Actual coverage is measured prospectively during the session.

## Start the prospective Lane M session

Start before 09:05 JST if the session is intended to be eligible for `FULL_FRESH_MSII` classification. Starting later is allowed operationally, but the session remains partial.

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File tools\phase57_msii_windows_full_session.ps1 `
  -Registry .\path\to\msii-registry.json `
  -Workbook ArkMarketSpeed.xlsx
```

The launcher fails immediately if the new MarketSpeed capture process exits or does not append fresh raw evidence within the startup timeout. A per-session exclusive lock prevents two launchers from running accidentally at the same time.

## Keep running

For Lane M prospective evidence, the Windows PC, MarketSpeed II, Excel/RSS, capture process, and launcher must remain running through the market session. The launcher remains alive after the 15:30 close until 16:10 JST by default only to receive Lane Y's delayed causal capsules; MarketSpeed evidence for those points must already have been captured at the original event times.

Lane Y itself is independent of the Windows PC because it runs in GitHub Actions.

## Outputs

Local Lane M output root:

`data/phase57-msii-live/<YYYY-MM-DD>/lane-m-output/`

Important files:

- `full-session-state.json` — durable local Lane M state
- `latest-score.json` — latest execution-aware score, including session quality
- `latest-pair.json` — exact-timestamp Lane Y / Lane M pair diagnostics
- `coverage-latest.json` — current required/observed symbol coverage
- `coverage-final.json` — final coverage summary
- `full-session-final.json` — final session summary
- `session-points/*-COMMITTED.json` — committed causal points
- `session-points/*-BLOCKED.json` — permanently blocked points

Coverage diagnostics are descriptive only. They cannot rescue, backfill, or upgrade a blocked point.

## Session-quality interpretation

- `FULL_FRESH_MSII`: local prospective capture was active by the predeclared boundary, no sticky missing capture remained, and no backfill was used.
- `PARTIAL_INCOMPLETE_MSII`: capture started late or the session accumulated a permanent missing point/coverage gap.
- `SOURCE_NOT_READY`: no usable MarketSpeed capture start/evidence was established.

A later file arriving after a causal deadline cannot convert a blocked or partial point into Full Fresh.

## Safety invariant

The following remain false throughout this path:

- `executionAllowed`
- `brokerWriteAllowed`
- `excelOrderWriteAllowed`
- `rssOrderFunctionAllowed`
- `liveTradingAllowed`
- `paperTradingAllowed`
- `automaticPromotionAllowed`
- `productionUpdateAllowed`

Only MarketSpeed II READ ONLY market/tick evidence is consumed. Frozen selector, Frozen Entry, EXIT v3/v4, and allocation research semantics are unchanged.
