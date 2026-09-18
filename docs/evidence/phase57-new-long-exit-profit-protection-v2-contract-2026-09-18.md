# Phase57 NEW LONG EXIT — Profit Protection v2 Activation-Close Break FAST-FAIL Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

## Frozen rule

- Enter PROTECT after a completed 5m bar establishes running HIGH >= +3%.
- Freeze that bar's completed CLOSE as `protect_activation_close`.
- A later new running HIGH refreshes the running peak but does **not** change the activation-close reference.
- While no new exit has occurred, the first later completed CLOSE strictly below `protect_activation_close`, with no new running HIGH on that bar, signals EXIT.
- EXIT reference = next regular 5m OPEN.
- no re-entry.

No percentage giveback threshold or cohort-specific threshold.

## Gates

Same frozen gates as v0/v1:
- +5 preservation >=90% each cohort;
- +3 cohort mean non-worse each;
- overall own60 mean non-worse each;
- >=50% of +3 full-retracement paths rescued before first retracement CLOSE with positive reference each;
- identity/causality/safety.

Any fail -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V2_FAST_FAIL_KILL`.
All pass -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V2_FAST_FAIL_PASS`.
No adjustment after measurement.
