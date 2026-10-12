# Phase57 NEW LONG EXIT — Early Failure Protection v0 FAST-FAIL Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

Candidate A (`NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1`) is frozen and must not be mutated. This experiment tests one independent complementary element.

## Motivation

Dedicated Loss Defense v0-v3 failed. Candidate A proved that a previously achieved favorable milestone can provide safer protection context than raw adverse movement.

This test asks whether a **failed early favorable excursion** can identify a useful subset of losses without destroying later winners.

## Frozen rule

- HOLD by default.
- When a completed regular 5m bar first establishes running HIGH >= **+1%** from Entry, arm EARLY_PROTECT.
- After EARLY_PROTECT is armed, the first later completed CLOSE <= **Entry (0%)** signals EXIT.
- EXIT reference = next regular 5m OPEN.
- Otherwise use exact frozen Fixed12 terminal reference.
- 0.05pp cost semantics identical to Fixed12.
- No re-entry.

+1 and Entry/0 are pre-existing Path Study milestones, not newly fitted thresholds.

## Frozen gates

For INITIAL and DIP_REPRICE separately:

- mean net return >= frozen Fixed12 mean;
- PF >= frozen Fixed12 PF;
- p05 >= frozen Fixed12 p05;
- +3 opportunity preservation >=90%;
- +5 opportunity preservation >=90%.

Evaluator-only adverse subsets:
- 106 additional-drop >=2% mean non-worse than Fixed12;
- 21 additional-drop >=5% mean non-worse than Fixed12.

Identity/causality/safety must pass.

Any failure -> `NEW_LONG_EXIT_EARLY_FAILURE_PROTECT_V0_FAST_FAIL_KILL`.
All pass -> `NEW_LONG_EXIT_EARLY_FAILURE_PROTECT_V0_FAST_FAIL_PASS`.

No threshold adjustment after measurement. A PASS authorizes only a pre-contracted integration test with frozen Candidate A.

## Scope

No Selector/Entry/Candidate-A mutation. No model, Fresh/OOS, provider, 1m, Capital, Portfolio, main merge or trading/write path.
