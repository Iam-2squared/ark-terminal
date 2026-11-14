# Interpretation and limits — no architecture change

The precommitted diagnostic label is MULTIPLE_HIGH_QUALITY_OPPORTUNITIES_COMMON;
the closure disposition is ENTRY_FREEZE_MAINTAIN. This does not mean all candidates
are good, net expected profits are positive, or Entry is independently validated.
It is evidence against removing opportunities merely because four or five appear
together. No Entry/EXIT/Capital implementation was changed.

For 475 four/five-candidate timestamps (2,134 emitted opportunities), witnessed
same-session +3 hits occur in at least two candidates on 163 timestamps (34.316%),
and +5 hits in at least two on 66 (13.895%). The quantitative descriptive test was
committed before this measurement and passes in blocks 2, 3 and 4; block 1 fails
the +5 common-rate condition. Fixed full-population frequency top-three removal
also passes, with the original timestamp denominator retained.

Multiple winners do **not** automatically imply a binding three-position limit.
At least four witnessed +3 winners occur on only 17/475 timestamps (3.579%),
and at least four +5 winners on 2/475 (0.421%). These are lower bounds due to
missing outcomes, not definitive rates. They do not determine simultaneous held
positions, timing of profits, cash availability, fill feasibility or which ranking
would capture them. This work makes no capacity or Capital simulation claim.

Horizon matters: within the fixed30-minute window, observed >=2 +3 is only
43/475 (9.053%) and >=2 +5 is 10/475 (2.105%). Same-session multiplicity must not
be presented as rapid30-minute multiplicity. Among identified first-hit paths,
pooled same-session hit-bar-end medians are 30 minutes to +3 and 65 to +5.
Intrabar timing is an interval, and prior missing bars make the first hit unknown.

Coverage is materially incomplete. There are 2,640 priced references out of3,508
events and only1,872 complete strict30 windows. The full-session complete-case
sample is583:336 in block1,247 in block2, and **zero** in blocks3 and4. Thus its
35.849% +3 and18.868% +5 rates do not represent all76 sessions. Use witnessed-hit
lower bounds for whole-population statements; incomplete non-hits are unknown,
not losses. Full-path, fully identified-label and witnessed-hit panels are distinct.

The field names `completeDistribution` in the measurement breadth objects refer
to fully identified winner counts, including positives established on partial
paths. The report labels them as outcome-identified, not path-complete. The
separate immutable `report/complete-path-breadth.json` supplements them with
strict all-candidates-path-complete distributions from the same saved ledger.
No measurement bytes or verdict were rewritten to add this clarification.

The 30-minute gross mean is +0.084%, but the60-minute mean is -0.155%; these use
different evaluable populations and exclude trading costs. Upside existence is
not profitability. Deep adverse excursions remain. Neither EXIT quality nor
future economic utility is certified by maintaining the frozen Entry.

Next work needs a separate user instruction. Do not automatically begin EXIT,
Capital Prioritization, Fresh/OOS, provider acquisition, or live/paper activity.
All nine Safety flags remain false.
