# NEW_LONG_EXIT_EARLY_FAILURE_PROTECT_V0_FAST_FAIL_KILL

Rule: observed +1 HIGH -> later completed CLOSE <= Entry -> next-open EXIT.

It materially improved mean/PF/p05 and adverse tails, but destroyed too many later winners.

INITIAL:
- mean -0.32857% -> -0.17929%
- PF 0.76248 -> 0.83437
- p05 -5.85576% -> -5.03481%
- +3 preservation 87.26% FAIL
- +5 preservation 88.28% FAIL

DIP:
- mean -0.32780% -> -0.19034%
- PF 0.74127 -> 0.80201
- p05 -5.34362% -> -4.15039%
- +3 preservation 83.96% FAIL
- +5 preservation 82.93% FAIL

Adverse evaluator-only subsets improved:
- 106: -1.48489% -> -1.43627%
- 21: -4.00144% -> -3.33791%

Retain the concept that failed favorable excursion carries useful loss information. Kill +1->0 as too early.

One final pre-existing milestone bridge (+2 observed -> later CLOSE <= Entry) may be tested once. If it fails winner-preservation or quality gates, close this family; do not sweep activation levels.
