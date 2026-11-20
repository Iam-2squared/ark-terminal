# Phase57 NEW LONG EXIT — Loss Defense v3 Completed-CLOSE -3% Tail Boundary FAST-FAIL Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

## Frozen rule

This is a tail boundary, not a recovery classifier.

- HOLD regardless of ordinary negative movement.
- If a completed regular 5m CLOSE return <= -3% from Entry, signal EXIT.
- EXIT reference = next regular 5m OPEN.
- no re-entry.

-3% is an existing Path Study adverse-depth milestone. No other stop level is tested in this contract.

## Gates

Same Loss Defense gates:
- +3/+5 opportunity preservation >=90% each cohort;
- 106 cohort >=10% relative mean-loss reduction vs Fixed12;
- 21 cohort mean non-worse vs Fixed12;
- INITIAL/DIP own60 mean non-worse;
- identity/causality/safety.

Any fail -> `NEW_LONG_EXIT_LOSS_DEFENSE_V3_FAST_FAIL_KILL`.
All pass -> `NEW_LONG_EXIT_LOSS_DEFENSE_V3_FAST_FAIL_PASS`.
No -2/-4/-5 sweep after measurement.
