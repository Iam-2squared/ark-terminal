# Phase57 NEW LONG EXIT — Profit Protection v4 +3-to-+1 Floor FAST-FAIL Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

## Frozen rule

- No protection before a completed bar has established running HIGH >= +3%.
- After +3 activation, the first later completed CLOSE <= +1% from Entry signals EXIT.
- EXIT reference = next regular 5m OPEN.
- New highs do not deactivate the +1 floor.
- no re-entry.

Both +3 activation and +1 floor are existing Path Study milestones. No threshold sweep or cohort-specific value.

## Gates

Unchanged:
- +5 preservation >=90% each cohort;
- +3 cohort mean non-worse each;
- overall own60 mean non-worse each;
- >=50% of +3 full-retracement paths rescued before first retracement CLOSE with positive reference each;
- identity/causality/safety.

Any fail -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V4_FAST_FAIL_KILL`.
All pass -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V4_FAST_FAIL_PASS`.
No adjustment after measurement.
