# Phase50 Shadow Live Read-Only

Phase50 validates model decisions against live or near-live market observations without transmitting orders.

## Scope

- read-only market snapshots
- deterministic SHADOW_ONLY decisions
- simulated settlement using later observations
- spread, slippage and fee assumptions
- win rate, Profit Factor, maximum drawdown and net PnL
- checksum-backed local reports

## Hard safety invariants

- executionAllowed = false
- brokerWriteAllowed = false
- excelOrderWriteAllowed = false
- rssOrderFunctionAllowed = false
- liveTradingAllowed = false
- automaticPromotionAllowed = false
- productionUpdateAllowed = false
- humanApprovalRequired = true

The implementation does not import or call MARKETSPEED II RSS order, modify or cancel functions. It does not write an order trigger to Excel. Any non-zero transmission or write counter blocks report verification.

## Local CLI

```bash
node tools/run_phase50_shadow_session.mjs input.json artifacts/phase50-shadow-report.json
```

The output is written atomically only after the session and safety audit complete successfully.
