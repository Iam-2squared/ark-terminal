# Phase57 NEW LONG EXIT — Profit Protection v5 Lower-Close +2 Floor FAST-FAIL Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

## Frozen rule

- Activate PROTECT after running HIGH >= +3% is observed on a completed 5m bar.
- Track prior completed CLOSE and running HIGH.
- A new running HIGH refreshes strength and does not signal EXIT.
- Otherwise, if current completed CLOSE is lower than prior completed CLOSE **and <= +2%**, signal EXIT.
- EXIT reference = next regular 5m OPEN.
- no re-entry.

+2/+3 are existing Path Study milestones. No cohort-specific values or search.

## Gates

Unchanged:
- +5 preservation >=90% each;
- +3 cohort mean non-worse each;
- overall own60 mean non-worse each;
- >=50% full-retracement rescue before first retracement CLOSE with positive reference each;
- identity/causality/safety.

Any fail -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V5_FAST_FAIL_KILL`.
All pass -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V5_FAST_FAIL_PASS`.
