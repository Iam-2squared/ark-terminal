# Phase57 NEW LONG EXIT — Early Failure Protection v1 (+2 -> 0) FAST-FAIL Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

This is the single final bridge test for the failed-favorable-excursion family. It is not permission for an activation-threshold sweep.

Frozen rule:
- arm after a completed regular 5m bar establishes running HIGH >= +2%;
- first later completed CLOSE <= Entry (0%) signals EXIT;
- next regular 5m OPEN reference;
- otherwise exact Fixed12 fallback; same 0.05pp cost; no re-entry.

+2 and 0 are pre-existing Path Study milestones.

Gates are identical to v0:
- mean/PF/p05 non-worse than Fixed12 in INITIAL and DIP;
- +3/+5 preservation >=90% in each;
- 106 and 21 adverse evaluator-only means non-worse;
- identity/causality/safety.

Any failure -> `NEW_LONG_EXIT_EARLY_FAILURE_PROTECT_V1_FAST_FAIL_KILL` and this early-failure family closes.
All pass -> `NEW_LONG_EXIT_EARLY_FAILURE_PROTECT_V1_FAST_FAIL_PASS` and only then may it be integrated with frozen Candidate A under a separate contract.
