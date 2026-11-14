# State Predictiveness Contract V1

Stage `STATE_PREDICTIVENESS_20261002_V1`. Parent cycle
`STATE9_RC2_MARKET_SEMANTIC_AUDIT_20261001_V1`.
This contract is fixed before this Work opens future prices, future State values,
or forward labels. Neither State9, profile, M0 nor the Path Contract is changed.

## Question and interpretation

Measure incremental Development out-of-fold information from B0 unconditional,
B1 formal current Primary only, B2 full permitted current State9 tuple, and B3
that tuple plus causal Path history. This is research, not a trading decision.
Nine Primary names remain unchanged; formal null is not a tenth State.
Reviewer-local lexical normalization never replaces authoritative frozen fields.

The requested primary formula is retained literally:
`y_h = (raw_unadjusted_Close_JPY[t+h] - raw_unadjusted_Close_JPY[t]) / frozen_U`.
M0 U is a dimensionless log-return scale. Accordingly this label has
JPY-per-log-scale units. It is **not** a percentage return or M0 log-coordinate
increment. Its pooled magnitude can be dominated by nominal share price.
Renaming its unit does not change the formula. A separately registered,
descriptive secondary label `delta_x_h = canonical_x_C[t+h]-canonical_x_C[t]`
is dimensionless; it cannot replace the primary target or rescue its gate.
No double division of canonical x by U is permitted.

## Data scope, eligibility and availability

Use every security/session in the pre-price 2026-10-01 acquisition universe:
12 precommitted Development sessions, at most 36 proposals, the original
168 response hashes and their dated-master/action/calendar bindings. All
original input-quality exclusions and denominator records are retained.
The 29 semantic review cases are not the prediction population or a new draw.
There is no replacement, outcome-driven reacquisition, or new provider request
in V1. Reuse the exact existing encrypted checkpoint and existing runner binding;
raw pages remain temporary. Export only this Work's approved derived research
feature/label/evidence tables, never a public provider-page dump or any secret.

Canonical key is `dated_security_id × session_id × bar_end`. Each scheduled
endpoint occurs once. Dated original calendar and source start-to-end mapping
are inherited, not reconstructed from generic exchange hours. Ordinal t is not
a compressed tradable-minute index. Horizons are **5, 15 and 30 scheduled
continuous tradable minute slots** in the same session. Terminal auction buckets
are not tradable-minute horizon slots. Opening/auction and source boundaries
retain their existing causal-segment meanings. Lunch is excluded from the
tradable index but a return label never crosses its causal break.

Feature rows include observed and formal-null scheduled endpoints. A price
target requires admitted, positive exact raw Close at t and the exact scheduled
horizon endpoint, and all intervening scheduled tradable slots to be admitted
and in the same causal segment. Unknown, rejected, source/auction reset, missing
horizon, session end and gap yield unavailable targets with explicit reasons.
Never jump to a later observed bar or impute price. Non-observed ACCEPTED
INITIALIZING rows can have price labels; their Primary remains formal null.
Missing raw rows cannot have a price label. Quality exclusions are not losses.

Actual historical known_at remains UNKNOWN. `assumed_available_at=bar_end`
is the inherited historical research assumption, not a feed-latency claim.
M0 uses only the bound previous session, with frozen 80/120 precision and Q.

## Features and isolation

The machine-readable FEATURE_SCHEMA contains a closed numeric/categorical
allowlist. B1 uses only formal Primary (NULL as missing-observation category,
not a market State). B2 includes the current tuple, observation/quality flags,
freshness, local/context/direction basis, fast applicability, present Stop/Range
metadata and current frozen analyses. B3 adds endpoint dwell, entered age,
previous run, last transition, the last **K=4** causal transition pairs, segment
age/count, and recent **15 scheduled endpoints** HOLD/transition counts.
All histories stop at t. Reset/null continuity is preserved. No future run closure,
future dwell, future history length, final-session aggregates, label-derived
feature, raw identity/date, future State, or future recognition enters a model.
Identity/time/source pointers are audit/join columns, never fitted features.
Auxiliary S/A/B/C, Membership and velocity remain DEFINITION_INCOMPLETE.

Existing full-session State9 traces are preferred. Missing full-session traces
may be generated once by the frozen candidate engine in an isolated child:
one current slot sent, current response received, then next slot sent. No future
file, raw path, previous-session path, key or identity environment reaches it.
Incomplete old traces need not be replayed as a semantic test. Any overlap
needed to establish frozen-engine memory is separately counted as generation,
not falsely claimed as zero cost or trace reuse. Path endpoints are captured
immediately after each push, before subsequent run closure. Feature snapshots
are saved before target assembly in a separate stage.

## Future structural targets (secondary)

1. Next scheduled tradable endpoint's observed Primary, only if both endpoints
   are observed and causally connected. Missing/null/reset is unavailable.
2. First genuine Primary TRANSITION strictly after t and within 30 scheduled
   tradable slots in an intact segment: from/to, timestamp and elapsed slots.
3. Observed continuation versus Primary change for target 1; directional
   continuation/reversal for target 2 only when both frozen local directions are
   nonzero. Otherwise directional relation is unavailable, not invented.
4. No transition within an entirely observable 30-slot window is censored at 30.
   An incomplete/gapped window is unavailable, not a no-transition success.
No 60-minute, session-close, MFE/MAE, first-hit, profit or trading labels.

## Split, fitting and inference

Use chronological dates that have input-eligible full-session records, including
dates with zero target availability in denominator reporting. The first three
chronological eligible dates are initial training. Split the remaining dates
into three contiguous nearly equal blocks (earlier blocks receive remainder).
Each block is an outer test fold; training is all strictly earlier dates. Every
security/session is in only one outer test fold. No random-row split.
Reject or purge any training row whose label end touches test-start; embargo is
30 scheduled tradable minutes. All labels are within session so distinct-date
folds normally have zero boundary-overlap rows. Still audit exact label bounds.

Fit weights give each training date equal total mass, and each security/session
within a date equal mass. Continuous numerical mean/scale/imputation and
categorical vocabularies are fit on training only. Numeric absence has its own
indicator; exact fractions are converted to binary64 only for modeling, never
for State9/M0 or target token construction. Unseen categories map to all-zero
training vocabulary; this does not change original tokens.

B0: weighted mean; weighted three-direction class prior.
B1: Primary lookup shrunk to B0 with pseudo-count **10**, using training weights
normalized to mean one. Unseen Primary falls back to B0.
B2/B3: weighted ridge linear regression and ridge least-squares one-hot direction
scores, strengths **[0.01, 0.1, 1.0]**, unpenalized intercept. Select each outer
fold/model/horizon strength by primary continuous-target MSE on its last training
date versus strictly earlier training dates. Ties select the larger strength.
Then refit on the entire outer training portion. Direction uses that same
strength, no extra search. Scores are clipped below at 1e-12 and normalized
to sum one; these are empirical linear probability estimates, not guarantees.
No nonlinear challenger and no family expansion.

Secondary next-Primary classification uses B0/B1 and B2/B3 ridge one-hot scores
with fixed strength 0.1, nine observed Primary classes. Secondary transition
occurrence uses the same families/strength, only entirely available 30-slot
windows. Time-to-transition and direction relation are descriptive only,
explicitly conditional/censored. Secondary results cannot pass the primary gate.

## Metrics, uncertainty, controls and gate

Save row-pooled MAE/MSE, date-equal MAE/MSE, R2 against the *same saved B0
OOF predictions*, Spearman average-tie rank IC (constant vectors => unavailable),
direction accuracy/balanced accuracy, multiclass Brier and log loss, probability
calibration, and five prediction-rank buckets (stable key breaks ties; buckets
are descriptive, not thresholds). Save bucket realized mean/median.
Save incremental MSE reductions B1-B0, B2-B1, B3-B2, and B2/B3 against B0/B1.
Do not label frequency as probability evidence or infer unseen events impossible.

Primary uncertainty unit: whole session date. Use **1000** date-cluster bootstrap
replicates with seed **2026100201**, retaining replicate date-index draws.
Security/session leave-one-cluster effects and contributions are also reported.
No iid-row bootstrap conclusion. Show row, date, security/session, security, run,
overlapping target and effective-date-cluster counts.

Negative controls are predeclared: (a) one deterministic date-internal label
permutation (seed 2026100202, preserving the complete label tuple), and
(b) shift the target start by **+60 scheduled tradable slots**, then apply h;
no wrap, gap jump or cross-session shift. Fit controls with the same fold/model
grid; compare to real fits on exactly the control-available rows. Store distinct
control availability and refuse non-comparable row-count claims.

A primary candidate needs at least six OOF dates, three evaluable outer folds,
and at least 50 price targets per fold at its claimed horizon. B2 or B3 must
reduce date-equal MSE by at least **2% against both B0 and B1**, improve both
comparators in at least two of three folds, and have positive bootstrap lower
bounds for both comparisons. Use a **99.1667% two-sided percentile interval**
(tail 1/240), Bonferroni across six model/horizon candidate claims; no post-hoc
horizon selection. No one security or one date may supply over **50%** of gross
positive squared-error improvement; leave-one-date and leave-one-security
aggregate improvement must remain nonnegative. A control with positive
improvement and at least **90%** of the real matched-row improvement triggers
BLOCKED_LEAKAGE_OR_SEMANTIC_INTEGRITY, not a tuning opportunity. A control with
too few available date clusters makes a positive candidate unvalidated.

Leakage/partition audit and independent exact-count/target/fold/metric/bootstrap
recalculation must pass. Float comparisons use abs<=1e-8 or rel<=1e-10 (larger
of the two); identifiers, target decimal tokens, masks and folds compare exactly.
Path incremental evidence additionally requires the B3-B2 MSE effect positive
with its registered interval and multi-fold sign, and the same controls.
No primary positive gate => NO_PREDICTIVE_EVIDENCE_ON_DEVELOPMENT, with
insufficient sample distinguished from a precise null. No silent semantic repair.

## Finite budget and prohibited operations

At most 36 acquisition proposals, 12 current sessions, 512 endpoints/pair;
new provider requests 0; new semantic sample draws 0; kernel generations one
per pair without reusable full trace; up to 18,432 endpoint generation steps.
At most 3 outer folds, 3 ridge strengths, 4 families, 3 price horizons and 3
real/control datasets, plus the two fixed secondary classification tasks.
At most 1000 saved primary bootstrap date draws reused by independent metrics,
never a second full State9/Path semantic suite. Historical budgets/exposures,
RC1 16 FAIL and the 88-workflow incident remain append-only and unreduced.

Read count, reference depth and routine repair count are logged but are not stop
gates. Single isolated Actions fanout=1; never modify/disable existing workflows.
Dedicated branch only, no main merge, no force update or other-branch overwrite.
Common Holdout is **not opened in V1**: there is no inherited stage-specific
one-shot authorization here. Protected/Fresh/OOS/Prospective are never opened.
No Entry/EXIT threshold, Signal, profit, Capital/Portfolio, external AI, order,
RSS/account operation, secret-value exploration, new provider or promotion.

Final status is a Development candidate ready for separately authorized
validation, no demonstrated predictive evidence, or an integrity block. Blind
State/Path answers are inherited evidence, never fabricated or retuned.
