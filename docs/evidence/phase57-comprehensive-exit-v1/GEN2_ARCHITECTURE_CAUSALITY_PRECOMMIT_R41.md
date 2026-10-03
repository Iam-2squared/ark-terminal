# R40 closure → Generation 2 pre-performance architecture freeze R41

Saved at 2026-09-26 18:20 JST. Basis/latest verified HEAD:
`43b91e50ba9c14277ed51961e132485ed1f0b42e`; PR587 open, Draft, unmerged.
No running/queued branch Actions at this save. This is a newly authorized,
separately bounded generation. R36 remains an immutable negative result.

## Completed and reused evidence

R38/R39 already repaired the NumPy-scalar owned-giveback reporting defect with
zero refits and zero policy replays. Its successful CI and artifacts are reused.
The original R36 archive, all144 model hashes, OOF prediction hash,24 candidate
configs and50 Run A/B files were independently verified again. Original and
corrected archives are pinned in `r40-result/receipt.json`. Retention correction
never changed a prediction, decision, fill, return or NO_SELECTION_STOP.

R40 newly joins656,247 checkpoints in exact R36 prediction order and analyzes
11,928 unique saved EXIT/checkpoint keys. All24 candidates have two Entry arms,
six evaluable buckets plus not-evaluable, metric-specific paired cases, sessions,
symbols, State/quality/transitions/dwell/churn, all6 tri-state Signals,187 canonical
Pattern values, owned-prefix missingness, three-head trajectories/disagreement,
exact post-EXIT5/15/30/60 active-minute prices, observed recovery, execution delay,
fixed-horizon target/prediction differences and post-EXIT opportunity gaps.
No new fit, policy replay, candidate or Portfolio evaluation was performed.
13 focused tests pass; independent code review found no blocking defect.
A failed initial serialization of NumPy scalars was repaired and tested before
the successful complete output. No original evidence was overwritten.

Full overall/winner results are in `r40-result/summary.json.gz`; all24 complete
bucket/paired/session/symbol summaries are under `r40-result/candidates/`.
`complete-derived-output-hashes.json` also identifies detailed rows and complete
trajectories. Those larger derived exports are reconstructible with the R40
script and the three pinned R35/R36/R38 Actions artifacts; their original
artifacts expire2026-10-26. Committed summaries do not rely on local scratch.

## Findings, without retrospective selection

The following examples describe the originally best overall mean candidates in
one arm (#17 IMMEDIATE,#22 R1); neither is adopted as an EXIT or Gen2 baseline.
All24 results, including unfavorable cases, remain available.

| >=5% MODEL_EXIT only | #17 IMMEDIATE | #17 R1 | #22 IMMEDIATE | #22 R1 |
|---|---:|---:|---:|---:|
| N |304|318|285|297|
| Median active holding minutes |29|6.5|25|10|
| Mean post-EXIT missed upside pp |6.257|6.269|6.258|5.977|
| Post-Entry best High known strictly after EXIT N |239|286|220|256|
| Median first observed recovery above EXIT, active minutes |2|2|2|2|
| Bullish State AND quality OK N |81|66|71|77|
| Any State quality OK N |111|110|103|109|

#17's observed future HOLD5/15/terminal targets average only
+0.096/+0.272/+0.052pp for IMMEDIATE and +0.211/+0.467/+0.109pp for R1 at these
model exits, despite much larger intrapath upside. Fixed endpoint value and
path continuation are different targets. Many subsequent observed paths recover,
but this does not make an oracle High actionable. Low State-quality coverage and
Signal UNKNOWN prevent interpreting every bullish label as reliable recognition.
Execution close-to-fill averages around−0.051/−0.019pp in those #17 groups,
far smaller descriptively than the missed upside; no execution ablation was run.

R40's A–H hypothesis dispositions distinguish measured associations from causes.
MAX permits HOLD when any head is optimistic; MAX alone cannot explain early
Winner exits. Label objective, selected prediction errors, missingness and
one-score architecture can motivate a test but are not independently identified
causes. No universal HGB superiority is claimed. Claude's user-relayed summary
and finding dispositions are saved separately in R40.

## Exact new hypothesis

`GEN2_PRECOMMIT_R41.json` is the machine contract and contains the complete grid,
parameters,folds,feature names,labels,source hashes,gates and tie rule.
Protocol SHA256:
`5fdc059936ba31466a7dace520f218353c634e6c8444d20d5ab21069c745deb4`.

Two independently learned binary event scores:

- Continuation: any completed High reaches1.00% above exact EXIT-NOW OPEN within
  at most60 future scheduled active bars.
- Failure: any completed Low reaches0.75% below that OPEN within at most15 bars.
  This is an adverse-excursion proxy, not proof of structural thesis failure.

Each horizon is capped to remaining scheduled continuous bars, with three
calendar-derived features identifying remaining time and effective horizons.
Calendar counts never depend on observed market-row availability. Both positive
and negative labels require the entire head-specific selected OHLC window.
Missing exact OPEN/interior bars produce null labels, never FALSE or searched
quotes. Heads have independent eligibility masks. Future target knowledge is
last target bar start+1, confined to the training label module and same session.
The first selected candle may trigger both labels; (1,1) asserts no intrabar order.
Auction is outside these labels;925 bypasses prediction/action and forces930.

These are variable-horizon occurrence scores, not calibrated probabilities,
hazard estimates or survival functions. Complete-window training has a missingness
selection limitation. The finite test, not this design, will assess performance.

## Causality and leakage audit before implementation

| Boundary | Fixed requirement |
|---|---|
| Entry | Both original Frozen Entries and prices unchanged |
| CORE | Exactly21 categorical +83 numeric R35 fields; State quality and UNKNOWN retained |
| Added features | Only3 known-calendar fields, no label availability |
| Pattern | Existing187 admitted columns from strict closed R23 prefix; blocked30 remain excluded |
| Label input | Pinned Development path, exact future references, training-only module |
| Decision input | Only frozen current features→OOF scores, fresh flag,persistence,NOW |
| Prohibited | Future High/Low/State/Pivot,bucket,finalPnL,oracle EXIT,capture,R36 outcomes/predictions |
| Split | Four existing expanding session folds,2-session purge,34 OOF score sessions |
| Preprocessing | Per-fold/arm/head train-only imputation,one-hot,scaling and weights |
| Execution | R24 exact next OPEN;690→750;missing no fill/no queue;auction930 or censored |
| Ownership | Exit-candle H/L excluded; incomplete prefix not certified; numeric transport fixed locally |

Independent contract review found no blocking design/leakage defect. It checked
all16 unique policies,4 specs,64 expected fits,187 names and7 pinned baseline
source hashes. API constructors only were inspected; no Gen2 fit/performance was
run. Implementation must still prove these boundaries with synthetic/focused
checks and required CI before learning authorization.

## Finite search and completion

Logistic C1 and HGB7-leaf classifiers each use CORE+calendar or the same plus
Pattern187. Their four shared prediction specs produce exactly64 model fits:
4specs×2heads×2arms×4folds. Each maps to two fixed threshold pairs and persistence
1or2, producing16 policies. EXIT requires weak Continuation (<=.35or.50) AND
strong Failure (>=.60) at the required fresh observations. All other valid
combinations HOLD/reset; stale/unknown scores HOLD without advancing. There is
no added stop-loss, state-only sell, negative-PnL-only sell or 17th candidate.

All R25/R31 numeric Completion Gates remain required in both arms, including
mean net>=2%,bucket floors,Winner Continuation,Retention,Loss Containment,cost,
concentration and paired denominators. Among passing candidates, minimize worst
capability rank then rank sum; any best tie is NO_SELECTION_STOP. No hidden
tertiary margin or candidate-ID tie breaker is permitted.

This Work performs no Gen2 scorecard/selection. After precommit implementation
and successful exact-source CI, a separate launch-only commit starts one finite
fit/replay workflow. After fitting begins, save executionSHA/runID/protocolhash/
counts/artifactplan/Safety and stop without waiting for model results. The next
Work audits artifacts, generates both scorecard passes, selects or stops, then
only on SELECT freezes EXIT and connects CapitalMAX3/4/5.

## Safety, exposure and next

Safety9 all false. Provider requests0,protected opens0. All2155 Opportunities
remain outcome-exposed Development, never Fresh/OOS. Entry Dual Freeze
`4878a1cc53430e816261dea0fb16aeb53b3c238d` unchanged. No main merge,force push,
live,paper,production,orders or transmissions. CapitalR37 stays preparation only.
Gen2 performance inspected0,real model fits0 at precommit. R39's authorization
block is superseded only by the user's explicit Gen2 request; its negative
results and trading prohibitions remain controlling. Next: implement exactly
this contract,focused tests,required contractCI,then one-shot launch.
