# Strict 30m MAE tail attribution — pre-measurement contract

2026-09-18 JST. Start HEAD a6824fb56e688355235af5fade91472a2eb157a0.
PR #587 directly confirmed open / Draft / unmerged. Diagnostic only.
No Entry, Selector, EXIT, risk rule, sizing or model modification.

## Population identity correction established from existing records

The quoted -1.5337423313 / -10.2564102564 / -35.2941176471% MAE
belongs to OLD MSH v1: 277 saved ENTER identities, 181 strict30m-observable.
Source: phase57-msh-entry-long-v1-upstream-freeze/manifest.json and historical
ENTER ledger; reference is frozen decision CLOSE, not new Entry OPEN.
Do not assign these statistics to the newer two-opportunity Entry.

Primary current panel: all saved NEW Entry parity opportunities, 2,743 INITIAL
plus 541 DIP = 3,284 opportunities over 76 Development sessions. Preserve all
identities and reference-status exclusions. Current frozen Entry source is
6fabde7dfe208e19d5611e0a290b4df6724e562e. Do not rerun Entry or fit a model.
Secondary provenance panel: all old 277 ENTER identities, reproducing strict181
and identifying every tied worst case. Join current/old anchors for lineage,
but never pool their different reference prices or opportunity identities.
Current overall is opportunity-weighted, not independent trades or portfolio.

Pin and reuse saved 5m paths, conditional ledger, Candidate A comparator ledger,
frozen selector, parity ledger, old strict path ledger and saved selector
rank/score snapshots. Verify source hashes and exact timestamp/identity joins.
All development data 2024-09-17 through 2025-01-09; no Fresh/OOS/provider/1m.

## Observation windows and missingness

Strict30 = exactly six consecutive completed 5m bars in 30 wall-clock minutes
from each actual frozen reference timestamp, same session segment, no missing
bucket; MAE=min(0,minLOW/reference-1)*100, MFE=max(0,maxHIGH/reference-1)*100.
Underlying-minute sparsity is disclosed separately; do not require 30 observed
minute prints as a retrospective filter. Report full-minute sensitivity.
Unknown reference, provider gaps, lunch and session boundaries stay explicit.

Three separate horizons for recovery after a strict30 tail:
1. STRICT30: complete six bars; primary, same comparable horizon for every row.
2. FIXED12_WINDOW: exact existing calendar-capped twelve regular bars, which can
   cross lunch; retain clock elapsed time and require all expected bars.
3. SESSION: every remaining expected regular 5m bar, dated session end; exclude
   auction substitution. If incomplete, negative/no-recovery claims are UNKNOWN.
Also retain OBSERVED_SESSION evidence: positive witnessed events may be reported
despite gaps, but absence is never a confirmed failure. This is not full-session
coverage. Never label the last available bar as a completed session terminal.
Post-30 further worsening compares later LOW with strict30 MAE; false is known
only for a complete session, true can be a witnessed event in a partial session.

## Descriptive buckets; no stop optimization

Disjoint intervals: (-1,0], (-2,-1], (-3,-2], (-5,-3], (-10,-5], <=-10.
Boundary equality goes to the interval with that upper bound; -10 goes to <=-10
(thus the preceding interval is (-10,-5]). Cumulative <=-3/5/10 are separate.
Report n / strict-observed denominator AND n / entire opportunity denominator.

For each bucket and deep threshold report any-time strict30 +1/2/3/5 separately
from AFTER-MAE and AFTER-FIRST-THRESHOLD-TOUCH events. Do not equate MFE presence
with recovery after decline. Recovery times use earliest known attaining bar's
[start,end] interval and completed-close timestamps, from Entry and from breach.

## Order and labels (evaluator-only, never PIT decision inputs)

The first global MAE bar and first global MFE bar determine
MAE_BEFORE_MFE / MFE_BEFORE_MAE / UNKNOWN_INTRABAR_ORDER / NO_POSITIVE_MFE.
Repeated extrema and later highs are retained. A same-bar HIGH/LOW does not prove
recovery. A later bar HIGH>=k proves opportunity after the adverse bar; completed
trigger-bar CLOSE>=0 is known to follow its LOW but is reported separately from
the conservative primary later-bar CLOSE reclaim definition. No assumed H/L order.

For each deep threshold d=3,5,10, locate first LOW<=-d WITHIN strict30. Hold that
same breach anchor for all horizons. Ordered labels, in this priority:
- RECOVERY_WINNER: strictly later bar HIGH>=+3 by the selected horizon. +5 subset
  separate. This means opportunity recovery, NOT profitable realized EXIT.
- INCONCLUSIVE if trigger bar HIGH>=3 but no definite later +3 (order ambiguity).
- RECOVERY_BUT_NO_MAJOR_WIN: definite post-breach CLOSE>=0 (including the known
  trigger-bar closing mark), no +3 above. Report later-only reclaim separately.
- CONTINUED_FAILURE: at least one later bar, no above recovery, complete selected
  window and its terminal CLOSE<=-d. This does not require monotonic declines.
- INCONCLUSIVE otherwise, including missing follow-up or last-bar breach.
Negative terminal after RECOVERY_WINNER remains that class and is cross-tabulated
as recovered opportunity then giveback. Do not conceal this overlap.
All label denominators and unknowns explicit, including label changes with horizon.

Additional drop>=2/5%: minimum LOW in strictly later bars relative to completed
breach CLOSE, 100*((1+laterLOW/100)/(1+breachCLOSE/100)-1), not entry-relative
MAE and not a re-used DIP D30 tag. Include pp displacement and same-bar excluded.
For bucket-level post-MAE statistics, anchor at first global strict30 minimum;
no later bar means UNKNOWN, not zero further decline. Terminal30 and session
terminal are different. Giveback=MFE minus horizon terminal CLOSE.

## EXIT attribution and selector linkage

Current Fixed12 and A outcomes reuse exact saved ledgers for the same identities.
Keep all strict30 rows, with missing paired EXIT outcomes explicitly censored.
Report paired n, mean, median, PF, p05, Win for Fixed12 and A; .05pp cost.
If A exits at OPEN before later intrabar LOW, that LOW is post-exit counterfactual
path risk, not realized MAE. For each threshold report breach BEFORE / AFTER /
UNKNOWN_SAME_BAR relative to A exit; an exit OPEN already below threshold is known.
Old277 Fixed12 reuses saved replay ledger; applying unchanged A to this old
reference is explicitly a DIAGNOSTIC POLICY PROJECTION, not its frozen population.
Only project A where exact Fixed12 is available; otherwise keep NULL.

Join saved selector rank/score and timestamps by exact selector anchor. Verify
feature timestamp and availableAt <= selector decision <= Entry. Report score
distributions by MAE bucket/class, ranks1..5, fixed-direction rank AUC (deep vs
nondeep), chronological blocks and frequency-top3 sensitivity. No cutpoint
search, fitted model, filtering or counterfactual claim of causal culpability.
Saved future selector opportunity is evaluator-only and separately named.

## Predeclared aggregate attribution verdict

Primary deep cohort = current strict30 MAE<=-3, including all classes/unknowns.
For EACH panel/horizon: n<30 or INCONCLUSIVE>1/3 => INCONCLUSIVE; otherwise
RECOVERY_WINNER>=2/3 => DEEP_MAE_PRIMARILY_RECOVERY_PATH;
CONTINUED_FAILURE>=2/3 => DEEP_MAE_PRIMARILY_ENTRY_FAILURE;
both classes >=10% and >=5 cases => DEEP_MAE_MIXED_RECOVERY_AND_FAILURE;
otherwise INCONCLUSIVE. These are descriptive interpretation rules, not tests
of statistical significance or optimized trading thresholds.
Report strict30 and complete Fixed12 follow-up verdicts separately. If a primary
dominant verdict changes on an adequately covered Fixed12 follow-up (>=half the
strict30 deep cohort, >=30 cases), final verdict is MIXED when both classes exist
at >=10%/5 cases in either adequately observed panel; otherwise INCONCLUSIVE.
Do not generalize a strict30 failure label into permanent session failure.
Old181 verdict stays a separate provenance result and cannot replace current.
The label ENTRY_FAILURE identifies unrecovered adverse paths, not proof that an
Entry filter can identify them beforehand or that Selector is wrong.

## Integrity / completion

Outputs append-only; existing sources unchanged. Tests cover bucket boundaries,
same-bar ambiguity, high-before-low, recovery then giveback, missingness/session,
post-exit lows, cost, identity and label/future separation. Regenerate into a new
directory and compare bytes. Source pins and all original evidence remain fixed.
All nine safety flags false, cash LONG only; no SHORT/margin/leverage, rule
implementation, thresholds, model fit, Capital/Portfolio, merge or promotion.
After attribution Evidence, audit, tests and CI receipt, STOP.
