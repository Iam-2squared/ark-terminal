# Phase51 Semi-Auto Safety Foundation

Phase51 prepares a human-in-the-loop semi-auto workflow while keeping every real execution surface disabled.

## Implemented scope

- Phase51.1 order candidate builder
- Phase51.2 pre-trade risk gate
- Phase51.3 human approval / reject / expiry state
- Phase51.4 dry-run execution simulation
- Phase51.5 audit and kill-switch enforcement

## Hard safety invariants

- mode = DRY_RUN_ONLY
- executionAllowed = false
- brokerWriteAllowed = false
- excelOrderWriteAllowed = false
- rssOrderFunctionAllowed = false
- liveTradingAllowed = false
- automaticPromotionAllowed = false
- productionUpdateAllowed = false
- humanApprovalRequired = true
- killSwitchRequired = true

Even an explicitly approved candidate can only produce `SIMULATED_ONLY`. No broker, Excel order, MARKETSPEED II RSS order, or live-order action is performed by this Phase51 foundation.

## Progression rule

Do not enable any live execution path merely because Phase50.9 reports READY. READY only permits creation and dry-run evaluation of a candidate. Any future live capability requires a separate explicit phase, separate safety review, and explicit human authorization.
