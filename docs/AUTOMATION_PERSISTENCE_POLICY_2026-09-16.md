# Ark Terminal — Automatic Persistence Policy (2026-09-16)

## Purpose
Reduce scheduled GitHub Actions persistence to the minimum current operational research line while preserving historical evidence and manual reproducibility.

## Automatic durable persistence whitelist
Only the current Phase57 realtime line remains automatically durable:

- `.github/workflows/phase57-lane-y-raw-capture.yml`
- `.github/workflows/phase57-realtime-live.yml`
- durable branch: `automation/phase57-realtime-live-data`

These workflows remain research/shadow data paths. They do not enable broker writes, Excel order writes, RSS order functions, paper trading, live trading, automatic promotion, or production update.

## Archived persistence families
Automatic triggers are retired for historical writers targeting:

- `automation/p25-*`
- `automation/p57-us-free-5m-data`
- `automation/home-paper-equity-data`
- `automation/screener-data`

Their existing durable branches are not deleted or rewritten. Historical evidence remains available. Writer workflows keep explicit `workflow_dispatch` entry points where applicable so an intentional manual replay remains possible.

## Phase52
`.github/workflows/phase52-daily-persistence.yml` no longer runs on a weekday schedule or main push. PR regression and explicit manual execution remain available. This prevents routine evidence commits to `main` while preserving the fail-closed regression gate.

## Scope guard
The maintenance rewrite targets actual repository-mutating legacy persistence workflows and automatic dispatchers that can invoke them. Pure readers, PR audits, and diagnostics that merely reference historical durable branches are not disabled by this policy.

## Restoration rule
Restoring automatic persistence for an archived family requires an explicit code change and review. Do not delete historical automation branches as part of routine cleanup.
