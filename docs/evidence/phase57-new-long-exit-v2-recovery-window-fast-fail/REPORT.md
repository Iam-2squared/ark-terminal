# NEW_LONG_EXIT_LOSS_DEFENSE_V2_FAST_FAIL_KILL

The 10-minute reclaim-window state-history rule is KILLed.

It preserved INITIAL winners well (+3 93.26%, +5 94.31%) but failed DIP and materially worsened the target deterioration cohorts:
- 106: -1.48489% -> -1.87364% (relative -26.18%)
- 21: -4.00144% -> about -4.84%
- DIP own60 mean also worsened.

This is strong evidence that waiting for a recovery window before acting is too slow for DIP deterioration. Do not retune the window.

With v0/v1/v2 all failing in different ways, the next Loss Defense test changes responsibility: use a rare hard deterioration floor as a **tail boundary**, not as a predictor of ordinary pullbacks. The Path Study already measured -3% and -5% adverse milestones. Test one pre-existing milestone once; do not sweep.
