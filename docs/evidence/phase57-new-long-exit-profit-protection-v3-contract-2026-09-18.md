# Phase57 NEW LONG EXIT — Profit Protection v3 50%-MFE Giveback FAST-FAIL Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

## Frozen rule

- Activate PROTECT after a completed 5m bar establishes running HIGH >= +3%.
- Track running MFE (percentage points above Entry) using only completed bars.
- On a later completed bar, if CLOSE return <= **50% of the current running MFE**, signal EXIT.
- EXIT reference = next regular 5m OPEN.
- running MFE may update before the test on each completed bar.
- no re-entry.

The 50% event is not selected from v0-v2 outcomes; it was already included in the completed Path Study giveback diagnostics.

## Gates

Unchanged:
- +5 preservation >=90% each cohort;
- +3 cohort mean non-worse each;
- overall own60 mean non-worse each;
- >=50% of +3 full-retracement paths rescued before first retracement CLOSE with positive reference each;
- identity/causality/safety.

Any fail -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V3_FAST_FAIL_KILL`.
All pass -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V3_FAST_FAIL_PASS`.
No adjustment after measurement.
