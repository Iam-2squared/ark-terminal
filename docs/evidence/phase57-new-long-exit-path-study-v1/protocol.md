# NEW LONG EXIT Path Study — evaluator contract

2026-09-18 JST. Start HEAD and exact source hashes: protocol.json.
No NEW EXIT rules, architecture implementation, model, threshold search or old
DEFENSIVE-two-lower-CLOSE proposal. Existing runtimes/evidence are read-only.

## Populations / clocks / reference

All 2743 saved INITIAL opportunities plus exactly 541 emitted DIP opportunities
are retained separately. Preserve the full anchor identity and original primary
878 / dip328 / non-dip550. Source is saved Development 5m OHLC only.
Saved reference OPEN is a location reference, not a certified executable fill.
No quantities, funding decisions, EXIT returns or portfolio aggregation.
Returns are gross path percent from that exact reference; this study has no
executed trade or cost-adjusted PnL. INITIAL and DIP must not be summed.

- OWN60_COMPLETE: own-entry +60 wall-clock, a single continuous session, all 12
  expected 5m bars observed. All +1/+2/+3/+5 winner analyses use this SAME panel.
- ALL_OPPORTUNITIES_PREFIX_COVERAGE: +5/10/15/20/30/45/60 independently audited;
  endpoint-specific Ns must never be presented as the full population.
- MATCHED_OWN60_COMPLETE: same anchors with both complete own60 paths; equal
  elapsed horizon, but DIP endpoint occurs later in clock time. Descriptive only.
- COMMON_T0_60_PRIMARY_DIP328: original328 primary dip anchors, same absolute
  cutoff t0+60; INITIAL has60 minutes and DIP55. Used for same-clock comparison
  and to keep every exact106/21 case. Not silently called equal elapsed time.
- Exact106/21: use saved primary328, cheaper reference299 and saved secondaryD30
  >=2%106 / >=5%21. Original membership is immutable and evaluator-only.

Position start is the exact saved INITIAL referenceTimestamp / DIP opportunity
timestamp, matched to the saved bar start. Never infer t5 by adding300 seconds.
DIP excludes every earlier bar. No crossing lunch for fixed wall-clock windows.
Safe continuous cutoff: morning11:30, afternoon15:00 before2024-11-05 and15:25
thereafter; auctions are excluded, not silently repaired. Missing expected bars
are UNKNOWN; boundaries are BOUNDARY_EXPIRED. An incomplete prefix cannot become
complete again by skipping its missing bar. Subsequent isolated observed bars
do not establish complete path labels. Do not fill/interpolate or infer no-trade.
Future windows with no remaining interval are WINDOW_ENDED/NULL, not zero.

## Causal-prefix versus evaluator-only fields

At each requested completed-bar timestamp, save separately:

- causalPrefix: current CLOSE return, running HIGH MFE / LOW MAE, running peak
  giveback in entry-denominated pp and peak-relative %, completed-close decline
  streak, previous CLOSE, positive-close history, recovery-attempt counts
  (rising completed CLOSE while still below Entry), and prior adverse reclaim.
- evaluatorOnly: suffix maxHIGH/currentCLOSE remaining upside, suffix minLOW/
  currentCLOSE downside, additional high beyond running peak, next-interval
  CLOSE direction, endpoint labels and event sequences. No decision consumer.

Prefix invariance under suffix mutation must be tested. Completed HIGH/LOW in a
prefix are known after that bar closes; future HIGH/LOW never enter the prefix.
No future outcome or risk-cohort tag selects an action; no action exists here.

## Winner / timing / adverse ordering

Winner level means horizon MFE>=level; it is HIGH opportunity, not realized
profit. MFE=max(0,maxHIGH return), MAE=min(0,minLOW return). First extrema time
is a 5m [barStart,barEnd] interval; no exact intrabar time. Ties use first bar.
MAE strictly before the MFE bar is guaranteed pre-peak; including the peak bar
is a conservative bound. Save BOTH, flag intrabar ordering uncertainty.

For adverse -1/-2/-3/-5 then winner +1/+2/+3/+5, count strictly later-bar hits
as confirmed sequence; same-bar possible order separately. Report both
P(later winner|adverse) and adverse incidence within winners with denominators.
At t+5/+10/+15 negative CLOSE, separately count subsequent level hits and
not-yet-first-hit winners. Save remaining upside, not simulated exit PnL.
No early-exit policy is implemented by this evaluator counterfactual.

## Recovery

For each fixed adverse depth, first completed CLOSE>=Entry in a strictly later
bar is Entry reclaim. Prior-close reclaim compares against the completed CLOSE
before the first adverse bar (Entry reference0 if it is the first bar).
Record adverse depth to reclaim, elapsed-duration bounds from the adverse bar,
time to first strictly later new running HIGH, and upside after reclaim using
strictly later bars. Save post-reclaim +1/+2/+3/+5 hits and same-bar unknowns.
No-reclaim means not observed within a COMPLETE panel horizon, not never recovers.

## Giveback / later outcomes

For each MFE opportunity level, record first completed-CLOSE giveback from the
then-running HIGH:1/2/3pp,50% of running MFE, full to Entry(CLOSE<=0), and negative
(CLOSE<0). These are descriptive events requested by the user, not EXIT levels.
Same-bar HIGH-to-final-CLOSE giveback is observable; HIGH/LOW order still unknown.
After each event, record strictly later HIGH above the event's running peak and
endpoint sign independently. Four outcomes: rehigh+nonnegative endpoint,
rehigh+negative endpoint, no-rehigh+nonnegative endpoint, no-rehigh+negative
endpoint. The last is only a transparent deterioration proxy, not an invented
collapse threshold. Events at panel end have NO_POST_EVENT_WINDOW, not failure.

## Comparisons / robustness / questions

Exact106/21 snapshots at5/10/15/20 retain all IDs. Compare106 vs other cheaper193,
and21 vs other cheaper278 using fixed snapshots, distributions and overlap.
Report positive-then-breakdown versus never-positive-CLOSE patterns. No fitted
separation time or classifier; any distribution separation is descriptive only.

Four chronological blocks of19 of the76 original sessions; top-frequency1/3
symbol exclusions based only on all2743 anchor counts (never performance);
per-symbol concentration; fixed time-of-day groups09–10,10–11:30,12:30–14,14–end;
winner/deep-adverse and saved observedMinutes==5 coverage-complete sensitivities.
All tables include n/denominator. INITIAL versus DIP unpaired differences are not
causal treatment effects; paired panels are supplied separately.

Answer Q1–Q14; give state concepts as needed/unneeded/indistinguishable, without
assigning states to actions. Architecture Review handoff is at most10 points.
Five-minute ordering/sparsity limitations may motivate a future data question,
but this study cannot demonstrate1m would solve it and cannot reopen1m research.

## Finish and STOP

Save evaluator, tests, full ledger, summary, Japanese report, hashes and CI.
Outcome NEW_LONG_EXIT_PATH_STUDY_COMPLETE unless data truly block the study.
Stop after this Evidence. All trading/write/promotion flags false. No Selector,
Entry, timing, runtime, Allocation/Portfolio mutation, new model, Fresh/OOS,
provider acquisition,1m research, production, paper/live execution or main merge.
