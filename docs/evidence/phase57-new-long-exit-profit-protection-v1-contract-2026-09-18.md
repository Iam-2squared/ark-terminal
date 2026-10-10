# Phase57 NEW LONG EXIT — Profit Protection v1 FAST-FAIL Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

v0 is KILLed because two lower CLOSEs were too slow, despite good +5 preservation and non-worse means.

## Frozen v1 rule

- Activate PROTECT only after a completed 5m bar establishes running HIGH >= +3%.
- While PROTECT, any new running HIGH refreshes the peak and does not exit.
- Otherwise, the **first subsequent completed CLOSE lower than the previous completed CLOSE** signals EXIT.
- EXIT reference = next regular 5m OPEN.
- no re-entry.

No percentage giveback threshold, cohort-specific threshold or model.

## Gates

Same as v0:
- +5 preservation >=90% in INITIAL and DIP separately;
- +3 cohort mean policy return non-worse than endpoint baseline in each;
- overall own60 mean non-worse in each;
- >=50% of +3 full-retracement paths rescued before first retracement CLOSE with positive reference;
- identity/causality/safety pass.

Any fail -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V1_FAST_FAIL_KILL`.
All pass -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V1_FAST_FAIL_PASS`.

No adjustment after measurement.
