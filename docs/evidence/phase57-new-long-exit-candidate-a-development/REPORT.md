# NEW_LONG_EXIT_CANDIDATE_A_DEVELOPMENT_PASS

Date: 2026-09-18 JST

Candidate A:
- +3 observed -> arm PROTECT;
- later completed CLOSE <= +1 -> EXIT at next regular 5m OPEN;
- otherwise exact Fixed12 fallback;
- 0.05pp cost semantics;
- no Loss Defense / BAR5 / TWO_LOWER_CLOSES.

All pre-frozen Development gates passed.

| Cohort | Fixed mean | Candidate mean | Fixed PF | Candidate PF | p05 Fixed -> Candidate | +5 preserved |
|---|---:|---:|---:|---:|---:|---:|
| INITIAL n=1072 | -0.32857% | **-0.26322%** | 0.76248 | **0.79388** | -5.8558 -> **-5.6078** | **94.48%** |
| DIP n=397 | -0.32780% | **-0.26870%** | 0.74127 | **0.76817** | -5.3436 -> **-5.1891** | **95.12%** |

+3 opportunity preservation is 100% in both cohorts by causal construction.

Protect exits:
- INITIAL 148/1072 = 13.81%
- DIP 40/397 = 10.08%

Candidate A also improves on the previously measured Existing EXIT mean:
- INITIAL Existing EXIT -0.2727% vs Candidate A -0.2632%
- DIP Existing EXIT -0.3407% vs Candidate A -0.2687%

The latter comparison uses the already frozen Existing EXIT diagnostic; Candidate A itself was gated against Fixed12.

This is the first NEW LONG EXIT candidate in this branch to pass all its pre-frozen Development gates.

It is still Development/outcome-exposed, has negative standalone mean/PF<1, and is not Fresh/OOS or Portfolio proof. Loss Defense remains unsolved and is not silently claimed solved.

Next: robustness/freeze audit only. Do not mutate the policy.
