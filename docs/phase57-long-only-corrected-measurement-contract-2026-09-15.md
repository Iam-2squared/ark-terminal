# Phase57 LONG-only corrected measurement contract

Status: PRE-EXECUTION / FROZEN BEFORE DIAGNOSTIC CODE. Contract version:
`CORRECTED-MEASUREMENT-1`. Source HEAD:
`962b96fd74964081d23dcdfc37d87fc00a98200f`. PR #587.

## Purpose and stop boundary

This one-run Development diagnostic corrects measurement semantics and scores the
existing saved C+D Ridge artifact without fitting. It does not create Candidate
v3, change a target, add a feature, tune alpha/threshold/Top N, retry v2, or open
Validation/OOS. Entry, EXIT, Allocation, old selectors, News/Event, Lane Y, main,
live and trading surfaces are out of scope. Report the fixed results, recommend
one next research item and stop.

North Star is additional upside after the decision. Primary practical KPI is
future-high +3% Precision@5; stretch KPI is future-high +5% Precision@5. Future
+2/+3/+5 labels are evaluator-only and never enter fitting.

## Workflow safety gate

Before this contract, remote HEAD, PR, status checks, branch runs and artifacts
were inspected. The four old workflows capable of refit or integration retain a
job-level `github.event_name == 'workflow_dispatch'` guard:

- L2 Selector Development;
- Selector Capacity Diagnostic;
- Missed Opportunity Diagnostic;
- New Selector with CURRENT Entry/Exit.

Their pull-request runs must be `skipped`. Contract-only documentation must not
trigger the dedicated measurement workflow. Diagnostic implementation will use
new, narrowly path-scoped files and one measurement-only workflow. If an old
training/refit/integration job starts instead of being skipped, cancel/contain it
and fail closed before interpreting results. Outputs created by the prior CI replay
incident are forbidden inputs.

The dedicated job may download only the predeclared historical artifacts below,
must have no provider client or provider request step, and must assert zero fit
calls. Its permissions are read-only except artifact upload. It purges private
inputs before uploading aggregate evidence.

## Frozen inputs and model provenance

Use only saved Development Minute/L0 data already allowlisted by the previous
audit: 80 requested sessions across Development A/B/C/D, with the four previously
unavailable L1 sessions left unavailable and never fetched/replaced. Expected
available population is 76 sessions. Validation/OOS paths are rejected.

Allowlisted runs:

- L0 base `34917676944`;
- L1 Minute `34926225832`;
- C+D Minute `34936002178`;
- additional Development Minute `34964031692`;
- saved C+D Ridge artifact `34944665187`, artifact SHA-256
  `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb`.

No output from the 2026-09-15 incidental replay runs may be consumed.

The original C-only Candidate v1 weights/scores and fitted v2 weights/scores were
not saved. They remain unavailable; do not reconstruct them. Use the saved C+D
Ridge unchanged and name it `CORRECTED_MEASUREMENT_RIDGE_SAVED_CD`. Its C/D scores
are in-fit. A/B are outside its fit partitions but are earlier, already-observed
Development, not a forward holdout, Validation or OOS. The historical +117.21bps
is retained only as a legacy six-observation diagnostic and is not directly
comparable to corrected wall-clock metrics.

## Decision price

`decisionPrice` is the latest accepted raw Minute close whose price is causally
available at or before the decision timestamp. A continuous one-minute interval
timestamp is its start; its close is available at start +1 minute. A terminal
auction is available at its timestamp. If several observations share availability,
the terminal auction is ordered after the continuous close.

Freshness is fixed at **age <=5 wall-clock minutes**. This is a market-data
semantic rule carried over from the pre-result audit, not selected from performance.
No forward fill, interpolation, future-nearest observation or stale fallback.
Without a fresh positive decision price the outcome is unavailable and a selected
identity is not replaced.

Report eligible causal rows, fresh evaluable rows, unavailable rows/rate, price-age
distribution and unavailable mix/rates by market, existing liquidity bucket and
decision time. Price freshness means freshness in the saved accepted Minute data;
it is not tick age, delivery latency or executable bid/ask evidence.

## Strict wall-clock 30-minute evaluator

The primary endpoint return is from fresh `decisionPrice` to the latest closed
continuous 5-minute observation available at or before t+30 wall-clock minutes,
strictly after t, whose contributing Minute close is no more than five minutes old
at t+30. A later terminal auction at or before t+30 may serve as an endpoint and
must be labeled as such. No next/favorable bar, interpolation, forward fill,
cross-session continuation or lunch bridging. A missing endpoint is unavailable.

Legacy six-observation forward return remains explicitly named
`legacySixObservationReturn`; it is not called 30m. No active-trading-time 30m
variant is introduced in this run.

Thirty-minute MFE/MAE use future accepted intervals after t whose prices are
available no later than t+30. Same-session MFE/MAE use accepted future intervals
after t through the same session only. Both use the fresh decision price:

- `MFE = max(0, maxFutureHigh / decisionPrice - 1)`;
- `MAE = min(0, minFutureLow / decisionPrice - 1)`.

An empty future path is unavailable. Positive MAE and negative MFE are prohibited.

## Opportunity and time-to-hit semantics

Primary opportunity is a future **5-minute high** touch after the decision through
same-session end. It is true when max future 5m high / decisionPrice reaches
1.02/1.03/1.05. The 5m interval must start at or after t and be available after t.
Secondary confirmation is a future **closed 5-minute close** (or later terminal
auction close, separately counted) reaching the same thresholds. A high touch and
a confirmed close are never merged.

Time-to-opportunity is first qualifying bar availability minus decision time.
Report P25/median/P75/P90 and fixed buckets <=15, 16–30, 31–60, 61–120 and >120
minutes for +3/+5, separately for high touch and close confirmation. Time is not
used as a filter. Final close versus previous close remains reference-only. No
overnight carry.

## Ridge Top5 and capacity-aware evaluation

Score all finite causal feature rows with the unchanged saved C+D Ridge. Rank by
score descending and the frozen symbol tie-break within each session/decision.
Select K=min(5,N_t) from the causal candidate universe. Do not condition selection
eligibility on future legacy-y30 availability. Do not replace selected rows whose
corrected measurement is unavailable.

Report Top5 for full saved Development and separately A/B, C and D. Include:

- strict wall-clock 30m mean/median/positive rate and positive sessions;
- 30m and same-session MFE/true MAE;
- high-touch and close-confirmed +2/+3/+5 Precision and +3/+5 Recall;
- time-to +3/+5;
- reference-only previous-close Final+5 Precision;
- selected/evaluable counts and conservative hits/all-selected lower bounds.

For each threshold and timestamp, N_t is the causal candidate count, K_t=min(5,N_t)
and O_t the corrected-outcome opportunity count. Expected random hits are
sum(O_t*K_t/N_t). Report actual recall, random expected recall, recall lift,
precision, unconditional prevalence and precision lift separately. Never use
total slots divided by total opportunity count.

Top5 is the only policy result. No capacity search or Top-N choice is performed.

## Fixed interpretation and output

Classify A–E exactly as supplied by the user, without creating a numeric tuning
gate. Outcome/target alignment may be reported from fixed corrected data but is
descriptive, since both use future prices. Session is the stability unit; rows are
not treated as independent trials.

The artifact contains aggregate JSON only, with input hashes, data audit, safety
flags and a self-hash. No symbol-level private rows are uploaded. One execution is
permitted; reruns may only correct a mechanical execution defect and may not change
the contract or improve an observed outcome.

Required final report has the user's 17 sections. Then STOP. Do not continue to a
new model, Target, feature, Top-N policy, Validation/OOS, or Entry/EXIT/Allocation.
