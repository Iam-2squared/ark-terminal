# Design draft only — no new calculation authorization

`close_pullback_row` currently assigns `maxCloseGivebackPp = peak - currentClose` even when every post-anchor Close makes upward progress. Drawdown/giveback should be bounded below by zero while retaining a separate no-pullback/no-pretarget observation indicator. A correction must preserve the fixed milestone, anchor, same-bar, and endpoint contracts.

Synthetic E2E should explicitly include a monotonically rising Close path and assert nonnegative giveback. Main Sanity should recursively reject negative `maxCloseGivebackPp` and its quantiles. Independent audit should verify Close pair N and key giveback quantiles through a separate algorithm. All result files from this cycle remain immutable and INVALID; new finite approval is required before another real-data run.
