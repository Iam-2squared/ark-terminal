# Phase57 NEW LONG EXIT Candidate B — Two-Stage Protection Integration Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

Frozen parents:
- Candidate A: +3 observed -> later completed CLOSE <= +1 -> next-open EXIT; else Fixed12.
- Early Failure Protection v1: +2 observed -> later completed CLOSE <= Entry -> next-open EXIT; else Fixed12.

## Frozen integrated logic

HOLD by default.

Stage 1 — EARLY_PROTECT:
- once running HIGH >= +2% is observed on a completed regular 5m bar, arm EARLY_PROTECT;
- before +3 has ever been observed, a later completed CLOSE <= Entry (0%) signals EXIT.

Stage 2 — PROTECT:
- once running HIGH >= +3% is observed, PROTECT supersedes EARLY_PROTECT permanently;
- a later completed CLOSE <= +1% signals EXIT.

EXIT reference = next regular 5m OPEN.
If neither signal occurs, exact Fixed12 fallback.
0.05pp cost identical to comparator.
No Loss Defense, model, symbol/cohort rule, re-entry or threshold tuning.

+2/+3/+1/0 are pre-existing Path Study milestones and the two parent rules were independently pre-frozen.

## Primary gates

For INITIAL and DIP separately:
- mean >= frozen Candidate A mean;
- PF >= frozen Candidate A PF;
- p05 >= frozen Candidate A p05;
- +3 preservation >=90%;
- +5 preservation >=90%.

Evaluator-only adverse subsets:
- 106 mean non-worse than Candidate A;
- 21 mean non-worse than Candidate A.

Safety/identity/causality pass.

Any failure -> `NEW_LONG_EXIT_CANDIDATE_B_INTEGRATION_KILL`.
All pass -> `NEW_LONG_EXIT_CANDIDATE_B_DEVELOPMENT_PASS`, followed only by robustness/freeze audit. No policy mutation.

Fresh/OOS remains sealed until the full Selector->Entry->EXIT->Capital->Portfolio design is fixed.
