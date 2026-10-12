# Phase57 NEW LONG EXIT Candidate C — Entry-Source Routed Protection Contract

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

This is one final architecture-level routing test, not a threshold search.

Mechanistic basis:
- INITIAL and DIP_REPRICE are distinct, frozen, PIT-known Entry sources.
- Candidate A passed Development/robustness and remains the default.
- Universal Candidate B failed only because the +2->0 pre-protection conflicted with INITIAL; the same frozen element materially improved DIP and all DIP gates.

## Frozen logic

INITIAL_ENTRY_OPPORTUNITY:
- exact frozen Candidate A only:
  +3 observed -> later completed CLOSE <= +1 -> next-open EXIT; else Fixed12.

DIP_REPRICE_OPPORTUNITY:
- two-stage protection:
  - after +2 observed and before +3: later completed CLOSE <= Entry -> next-open EXIT;
  - after +3 observed: Candidate A PROTECT supersedes early protection; later completed CLOSE <= +1 -> next-open EXIT;
  - else Fixed12.

Same 0.05pp cost.
No Loss Defense, model, symbol rule, re-entry or further cohort-specific thresholds.

## Gates

Against frozen Candidate A, each cohort separately:
- mean non-worse;
- PF non-worse;
- p05 non-worse;
- +3 preservation >=90%;
- +5 preservation >=90%.

Evaluator-only DIP 106/21 means non-worse than Candidate A.
Safety/identity/causality pass.

Any failure -> `NEW_LONG_EXIT_CANDIDATE_C_KILL`.
All pass -> `NEW_LONG_EXIT_CANDIDATE_C_DEVELOPMENT_PASS`, then robustness/freeze audit only.

If Candidate C passes robustness, freeze it and stop EXIT architecture mutation on exposed Development data. Fresh/OOS remains sealed until full pipeline is fixed.
