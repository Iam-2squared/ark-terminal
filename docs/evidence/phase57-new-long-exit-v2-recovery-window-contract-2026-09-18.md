# Phase57 NEW LONG EXIT — Loss Defense v2 Recovery-Window FAST-FAIL Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

Loss Defense v0 lower-CLOSE persistence and v1 prior-bar-LOW breakdown are KILLed.

## Evidence basis

Path Study recovery evidence:
- t+5 negative can later become +3;
- -1% -> reclaim -> later +3 recovery-winner duration upper median was about 10 minutes in both INITIAL and DIP;
- deep-drop cases materially deteriorate by t+15.

v2 therefore tests **state history and a finite reclaim window**, not a stricter breakdown event.

## Frozen rule

- First completed CLOSE < Entry -> DEFENSIVE; freeze that CLOSE as `defensive_start_close`.
- Observe the next **two completed 5m CLOSEs** (10 minutes).
- If any completed CLOSE >= Entry during that window -> reclaim -> HOLD and reset.
- Before the two-bar window completes, do not exit merely because price worsens.
- At the second completed bar after entering DEFENSIVE:
  - if still below Entry **and** current CLOSE < `defensive_start_close`, signal EXIT;
  - otherwise remain DEFENSIVE, reset the two-bar observation window from the current CLOSE, and repeat.
- EXIT reference = next regular 5m OPEN.
- no re-entry after EXIT.

The 10-minute window is tied to the pre-existing Path Study recovery-duration evidence; it is not selected from v0/v1 results.

## Frozen gates

Same Loss Defense gates:
- +3/+5 preservation >=90% each cohort;
- 106 evaluator-only cohort >=10% relative mean-loss reduction vs Fixed12;
- 21 evaluator-only cohort mean non-worse vs Fixed12;
- INITIAL/DIP own60 mean non-worse;
- identity/causality/safety.

Any fail -> `NEW_LONG_EXIT_LOSS_DEFENSE_V2_FAST_FAIL_KILL`.
All pass -> `NEW_LONG_EXIT_LOSS_DEFENSE_V2_FAST_FAIL_PASS`.
No adjustment after measurement.
