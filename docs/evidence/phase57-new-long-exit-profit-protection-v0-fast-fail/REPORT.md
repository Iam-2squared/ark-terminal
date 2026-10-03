# NEW_LONG_EXIT_PROFIT_PROTECTION_V0_FAST_FAIL_KILL

Date: 2026-09-18 JST

## Verdict

**KILL**, but retain the PROTECT concept.

Frozen rule: activate after observed running HIGH >= +3%; require two consecutive lower completed CLOSEs without a new running HIGH; exit at next regular OPEN.

### What passed

- INITIAL +5 preservation: **95.12%**
- DIP +5 preservation: **96.30%**
- +3-cohort mean non-worse: PASS both
- overall own60 mean non-worse: PASS both
- INITIAL mean: -0.21556% -> **-0.21197%**
- DIP mean: -0.17896% -> **-0.15587%**

### What failed

The rule was too slow to solve the specific full-retracement problem.

Among +3 winners with a later completed CLOSE <= Entry:
- INITIAL: rescued before retracement with positive reference **12/105 = 11.43%**
- DIP: **4/27 = 14.81%**

Required gate was 50%.

## Retained lesson

Unlike Loss Defense v0/v1, Profit Protection v0 did **not** damage overall means and preserved >95% of +5 opportunities. The architecture is therefore not rejected; the specific two-lower-close confirmation is too slow.

The next structural test may make PROTECT reaction earlier without changing the +3 activation milestone: one lower completed CLOSE without a new running HIGH, then next-OPEN exit. This is a new structural persistence requirement (1 instead of 2), not a percentage threshold search.

No Loss Defense integration, Fresh/OOS, 1m, model, Capital/Portfolio or main merge.
