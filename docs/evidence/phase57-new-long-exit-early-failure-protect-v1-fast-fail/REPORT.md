# NEW_LONG_EXIT_EARLY_FAILURE_PROTECT_V1_FAST_FAIL_PASS

Frozen rule: observed +2% HIGH -> later completed CLOSE <= Entry -> next regular OPEN EXIT; otherwise Fixed12.

All pre-frozen gates passed.

INITIAL n=1072:
- mean -0.32857% -> **-0.25023%**
- PF 0.76248 -> **0.79668**
- p05 -5.85576% -> **-5.40069%**
- +3 preservation **97.13%**
- +5 preservation **94.48%**

DIP n=397:
- mean -0.32780% -> **-0.18252%**
- PF 0.74127 -> **0.82850**
- p05 -5.34362% -> **-4.53339%**
- +3 preservation **96.23%**
- +5 preservation **95.12%**

Evaluator-only adverse subsets:
- 106: -1.48489% -> **-1.26297%**
- 21: -4.00144% -> **-3.04415%**

This validates one complementary element: a trade that has already demonstrated +2% favorable excursion and then loses Entry has a useful causal failure state. It is not a general Loss Defense rule.

The +1->0 predecessor is permanently KILLed. No activation sweep is authorized.

Next authorized step: integrate this frozen +2->0 early-failure element with frozen Candidate A (+3->+1) under a separate contract.
