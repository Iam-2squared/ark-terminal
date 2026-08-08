# Phase52.0-52.5 Pre-Live Safety Validation

Phase52.0-52.5 validates Ark Terminal's pre-live safety boundary before any future real semi-auto use is considered.

## Scope
- 52.0 End-to-end safety audit across Shadow -> Readiness -> Candidate -> Risk -> Approval -> Dry-Run -> Audit.
- 52.1 Failure injection for missing data, API outage, stale prices, outliers, duplicate runs, timeouts, and corrupt state.
- 52.2 Idempotency and duplicate protection.
- 52.3 Checkpoint/restart recovery validation.
- 52.4 Broker boundary verification with zero write/order counters and forbidden-order surface detection.
- 52.5 Human approval integrity: candidate/risk mutation, candidate mismatch, expiry, or missing approval always invalidates the chain.

## Hard safety invariants
All of the following remain fixed:
- executionAllowed = false
- brokerWriteAllowed = false
- excelOrderWriteAllowed = false
- rssOrderFunctionAllowed = false
- liveTradingAllowed = false
- automaticPromotionAllowed = false
- productionUpdateAllowed = false
- humanApprovalRequired = true
- killSwitchRequired = true

Passing Phase52.0-52.5 does not authorize or activate real orders. It only demonstrates that the pre-live safety path remains fail-closed.
