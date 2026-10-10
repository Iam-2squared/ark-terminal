# State v2 Recognition start-gate draft

Date: 2026-09-22 JST
Status: DRAFT_NOT_APPROVED / RECOGNITION_NOT_STARTED / NO_FITTING / NO_PREDICTIONS
This is a concise repository copy of the detailed delivered draft Ark_State_v2_Recognition_Protocol_Draft_20260922.md (SHA256 56a25f6357847595173c82eedd66641d52b979eeb53f8af275b516f5a91165ff). It does not authorize an experiment or supersede frozen definitions.

## Question and exact targets

Can information admissible at t identify the delayed-confirmation state AT t under fixed H=10 active minutes? The targets are future_resolution_v2.adjudicatedStructureAtT.value (UP_STRUCTURE/DOWN_STRUCTURE/RANGE_STRUCTURE/NONE) and adjudicatedPhaseAtT.value (the five-bit multilabel set PROGRESSION/CORRECTION/RECOVERY/BALANCE/RESTRUCTURING).

NOW is a deterministic causal descriptor, not Ground Truth. Direction is already causally computable and is not a prediction label. Future adjudication is not state at t+10, return, PnL or an Entry policy. Effective pivots must have effectiveAt<=t and confirmedAt within the frozen cutoff. Empty Phase is an evaluated all-zero finding, not unavailable data.

## Fixed source and exposure

Accepted R3 artifact10692617487/run35721458178/execution b784e97ac6a5bd1b97a62af4923423596a1258c6; ZIP SHA256 ef3e3a631d43702ac7072fb02885c199b92e65378105b651255aca56834db9c4. Preserve all2155 Opportunities/77214 checkpoint identities. No reference regeneration, State/Scale/H10/Selector change.

All dates2025-05-30 through2025-08-25 are already outcome-exposed Development. Neither the proposed REPORT block nor this census is fresh/OOS. Historical receivedAt/announcement latency is not proven. No Common Holdout/Fresh/OOS/Prospective opening or new market-provider request is permitted.

## Feature and label firewall

Candidate inputs: D-5 through D-1 Daily; actual previous-session observed1m; today's Open-through-t closed1m and causal aggregations; allowed NOW descriptors, Scale and ObservationQuality. Each must satisfy frozen admission and timestamp constraints. No forward-fill, replacing missing days or rolling to the latest existing five bars. No Dictionary.

Forbid ALL Future records, adjudicated targets, lateConfirmedPivots, futureMissingEnds, futureScheduledEnds, futureCutoff, resolutionStatus, censorFlags, future-derived scoring eligibility, future returns, PnL and Entry/EXIT outcomes from features. Symbol/Opportunity IDs are grouping/join/audit keys, not learned identity features.

The delivered checkpoint_census.csv.gz joins NOW and Future for EVALUATOR_ONLY tabulation. Do not feed all its columns to a model. A next-stage feature builder must read a separately allowlisted causal input path, with no Future file access. Mutating/removing future data must leave its output unchanged. Audit maxSourceTimestamp<=t, prior-session identity and maturity of fitted artifacts. Do not invent missing historical receivedAt.

## Axis-specific evaluation eligibility

Require ten same-session scheduled active minutes fully observed, no futureMissingEnds/censorFlags, and resolutionStatus!=CENSORED. Then require the corresponding target axis.status==DEFINED. This gives9302 Structure and16509 Phase rows in this cohort; full-H alone gives20941. A full-H NOT_RESOLVED_WITHIN_H row with a DEFINED axis is retained; do not select only resolved examples.

CENSORED is not a negative class. Keep INSUFFICIENT/NOT_EVALUATED/NONE/EMPTY_SET distinct. Since the scoring mask uses future information, it is label/evaluator-side only: it cannot select which real-time Opportunities receive predictions or are retained. Report causal input unavailability, model abstention and missing evaluation labels with separate denominators over the conserved population.

## Chronological split proposal, not approval

|Block|Period|Session slots/nonempty|Opportunities|Rows|Structure eligible|Phase eligible|
|---|---|---:|---:|---:|---:|---:|
|FIT|2025-05-30–07-18|35/34|1268|45348|5267|9464|
|TUNE|2025-07-22–08-06|12/12|434|15762|2209|3744|
|REPORT|2025-08-07–08-25|12/12|453|16104|1826|3301|

Exact dates are in delivered run1/split_proposal_NOT_STARTED.json. The35/12/12 chronological cut uses session identities, not outcome optimization. Keep the empty2025-07-14 slot. Do not random-split checkpoints or separate overlapping examples within a session. Fit preprocessing/normalization/calibration/feature selection only on FIT. Use TUNE for the precommitted finite selection process; never tune on REPORT then claim independent success there.

For each training cutoff, purge labels whose H10 maturity/confirmation lies later. Fixed H is same-session, so these session-block boundaries do not create cross-session H labels. Any future change to a crossing target would require its own predeclared maturity-aware embargo. Prior causal input overlap is not permission for future-label or all-period preprocessing leakage. All blocks remain exposed Development after this census.

## Comparisons and metrics — specified, not executed

Proposed baselines: FIT majority/Phase-frequency baseline, causal NOW rule, persistence based only on previously available NOW information. Persistence cannot read previous Future teachers. Specify missingness/abstention and the same evaluation scope for every candidate before scoring.

Structure: per-class precision/recall/F1, macro-F1, balanced accuracy, confusion matrix and coverage; overall accuracy is secondary. Phase: per-label precision/recall/F1, macro-F1, exact-set match, Hamming loss, empty-set rate and coverage. Include opportunity-equal and session-equal summaries, not only row weighting. Report zero-support metrics explicitly rather than hiding them. Prespecify paired session-level uncertainty/cluster resampling rather than treating repeated rows as independent.

NOW-versus-delayed differences (Structure788/9302, Phase3364/16509) are evaluator-only diagnostic strata. Do not use future knowledge of this stratum at inference. Their complements are not measured prediction accuracies. No baseline or predictor was executed in the census.

## Start gate and STOP

Before ANY fitting/prediction: obtain human confirmation; precommit exact source/target/feature/mask/split/metric hashes; precommit model family, finite candidate/trial budget, preprocessing and hyperparameters; pass feature-firewall/maturity and all2155/77214 identity tests. The current draft does not select a trained model or relax the gate.

After the later experiment, preserve all outcomes/coverage/class support. Any leakage, lost identity or unexplained mismatch blocks a performance PASS. No class/threshold redefinition to rescue results. Recognizability does not establish profit or prospective/live parity. Human review is required before State x Signal.

No Selector retrain/rerank/refilter or State-based Opportunity rejection. Entry is not a second Selector. No Dictionary/Signal/BUY-WAIT/Entry/EXIT/Capital, main merge or trading. Safety9 all false; providerRequests0/protectedDataOpened0/modelFittingStarted=false/predictionsProduced0/recognitionStarted=false. Stop here.
