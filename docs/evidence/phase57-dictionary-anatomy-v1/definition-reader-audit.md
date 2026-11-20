# Definition and Reader audit

Source commit: 573a0bfebf87319cdc07f93ee6db533f74457c69. All old code, registry, Gates and results remain unchanged.

## Confirmed semantic defect requiring a separate version if corrected

`phase57_research_dictionary_v0.intraday_traits` computes `pullback_depth` from every adjacent element of the full-session `swings` list. `swings` resets its state at missing bars/lunch, but the returned list has no phase segmentation applied to these adjacent ratios. A morning upward confirmed swing of amplitude 2 and an independent afternoon downward swing of amplitude 4 produce `pullback_depth=2`, despite no connected prior impulse. A direct synthetic call to intraday_traits reproduces this in `test_pullback_ratio_crosses_phase_and_direction`.

Additionally, the scalar mixes both swing directions; it does not specifically identify a LONG upward impulse followed by its downward correction. The registry describes correction/previous impulse, but does not sufficiently disambiguate directional semantics. Cross-phase pairing is a confirmed defect; restricting to LONG correction would also require an explicit new definition. Neither issue proves that a corrected trait would pass, and it does not explain the insufficient sample count of all the other swing/rebound traits.

No new registry was created or measured. A bounded vNext proposal is warranted for pullback semantics, with explicit same-phase/contiguous impulse-correction linkage, direction, confirmation timestamp and denominator contract. Freeze that specification before any new measurement, preserve v0 as the baseline, and use only authorized Development data. Do not change 0.5S/1.5S thresholds merely to raise event counts.

## Reader integration blockers (not scalar Gate failures)

1. `phase57_expansion_measure.collect` history contains `daily.Date`, `tr`, and `barValue`; it does not contain `session`. Reader `context` immediately indexes `h['session']`. Direct use raises KeyError. Synthetic actual-schema fixture confirms this.
2. The v0 history uses `barValue` with integer minute keys. Reader expects `barValues` with string keys. Supplying only a session adapter leaves rvol_value silently missing. Synthetic paired calls demonstrate the difference.
3. Reader accepts morning data ending at minute 610 as `RESEARCH_CONTEXT_AVAILABLE` at minute 755. There is no stale-bar/phase-validity rejection. This is especially material at lunch and missing recent data. Baseline behavior is recorded by test, not approved as desired behavior.
4. Reader features and Dictionary scalars differ in units: wick/S versus wick/range, causal instantaneous distance versus historical conditional response probability. `personality.features` is not an adapter for the saved profile schema. A same-name z-score join is not a valid inference interface.

Tests preserve existing Reader behavior as counterexamples. This audit does not silently fix the Reader and claim new readiness.

## Other limitations, not proven scalar implementation defects

- Swing/rebound session summaries have extremely few event-bearing days. n_sessions/episodes are symbol-session summaries, not counts of every swing/trade. The existing 8-observation rule must not be interpreted as 8 independent individual events. No event threshold is relaxed.
- `range_CL` has zero finite A/B observations in saved profiles. The closing bucket is absent before the calendar change; positive-log transform excludes nonpositive ranges. Current artifacts cannot identify the complete causal breakdown of those zeros/missing rows without an authorized raw diagnostic. It is not labelled 'no market behavior'.
- A shared global completion rule cannot pass on the daily-only lane because it includes an intraday minimum. The expansion decision actually follows the intraday lane, which independently fails usable count, family count and daily-trait count. This reporting mismatch is not grounds for overturning that failure.
- S/R touches, compression context, and volume-confirmed breakout composites are not independently tested scalar personalities. Existence of an atom/composite is not USABLE evidence.
- A failed calibration slope does not establish a code error. No slope was recalibrated on B. Bootstrap, shrinkage, transformations and FDR were left untouched.
