# Phase57 Capital Allocation v3 — Phase A Independent Technical Review

## Scope

Review only the Entry-time, EXIT-independent Capital Allocation v3 Phase A on `research/phase57-capital-allocation-v3-entrytime`. No main integration, no EXIT interaction, no protected OOS/Fresh opening, no realized-PnL winner selection.

## Verdict

**CONDITIONAL PASS → HARD STOP after CI.** The Phase A foundation is adequate for structural diagnostics. It is not adequate for choosing a production allocator or claiming portfolio performance.

## Review findings

### 1. Reproducibility defect found and fixed before Phase A readout

Contract v1 named `V3_A_RANK` and `RECENT_REALIZED_VOLATILITY` but did not freeze the rank basis or volatility lookback. That left two degrees of freedom that could be changed after seeing data. Contract v2 now freezes:

- `V3_A_RANK` = MSH probability ordinal rank **within the simultaneous First ENTER set**.
- Risk window = **exact last 7 completed 5m closes available by decision time**, 6 log returns, population standard deviation.
- Missing/invalid risk window = fail closed.

The seven-close choice is inherited from the existing Frozen MSH seven-completed-bar availability requirement rather than tuned from outcomes.

### 2. Phase A source barrier is strong enough

The source manifest pins MSH run `34292703804`, source head `86d4fa839a097d73a36169df88001bacd4022387`, candidate model SHA-256 `f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a`, and the six feature artifact digests.

Phase A admits only label-free `*.features.json.gz`, causally filtered pre-entry bars, and the exact candidate model. Label-bearing measurement members, training events, fold reports, threshold results, EXIT and protected OOS/Fresh evidence are not Phase A inputs.

### 3. Structural readout says simultaneous cross-sectional competition is rare

The 58-session development structural replay contains:

- 203 First ENTERs across all 58 sessions.
- 119 unique symbols.
- 27 LONG / 176 SHORT.
- 195 exact decision-time opportunity sets.
- 187 singleton sets and only 8 two-candidate sets.
- Simultaneous competition rate: 8 / 195 = 4.10%.

This is a structural exposure result only. The final refit is replayed on the same development feature rows, so no predictive or OOS claim is allowed.

### 4. Do not tune v3-C or concentration caps from eight competition sets

On the 8 simultaneous two-candidate sets:

- `V3_0_EQUAL`: mean top-1 = 50.0%, mean HHI = 0.5000.
- `V3_A_RANK`: mean top-1 = 66.67%, mean HHI = 0.5556.
- `V3_B_RISK`: mean top-1 = 62.02%, mean HHI = 0.5394; maximum observed top-1 = 75.95%.

The Risk-only concentration observation is worth retaining, but eight competition sets are not enough to justify inventing a volatility floor, cap, or Rank×Risk blend. Adding those now would be result-dependent parameterization.

### 5. Legacy and Adaptive v2 are references, not valid Phase A numeric competitors

Legacy `MAX_N` depends on portfolio equity, open-position count, cash constraints and EXIT-driven cash recycling. Phase A can retain nominal slot fractions (10%, 25%, 33.3%, 50%) but cannot reproduce actual portfolio allocations without EXIT.

Frozen Adaptive v2 expects `confidence`, `probability`, `selectionOpportunityScore`, and `selectionV2Score`. MSH First ENTER does not expose semantically identical fields. Mapping MSH/hybrid scores into the old Adaptive v2 inputs would create a new, unfrozen adapter and must not be done implicitly.

## Decision

1. Keep PR #582 Draft.
2. Run focused CI on Contract v2, the causal Phase A runner, and tests.
3. If CI is green, freeze this structural readout as Phase A evidence.
4. Do **not** implement v3-C, score calibration, Kelly, sector/direction caps, volatility floors, outcome-based tuning, winner selection, or promotion from this readout.
5. The next valid performance comparison is Phase B after a Frozen EXIT is available, so Legacy/v3 candidates can share the same event-time cash ledger and EXIT-driven recycling semantics.

All execution, broker, Excel-order, RSS-order, live, paper, automatic-promotion, production-update and transmission permissions remain false.
