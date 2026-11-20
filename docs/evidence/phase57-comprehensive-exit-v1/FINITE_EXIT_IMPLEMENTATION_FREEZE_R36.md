# Phase57 — finite NEW EXIT implementation freeze R36

Date: 2026-09-26 JST  
Basis HEAD before this append-only checkpoint: `640ab18790ef8bdfb18f179bed8d0499cbe3cbc0`  
Status: **PRECOMMITTED BEFORE THE FIRST R25 PERFORMANCE-BEARING FIT**

## Current state and reused evidence

GitHub was re-read at Work start. PR #587 was open, Draft and mergeable; branch
HEAD was the basis above. The dedicated R33 run `36219218944`, R34 run
`36219834621` and R35 run `36220335998` were all successful. R35 artifact
`10899151845` had GitHub digest and independently downloaded ZIP SHA-256
`a12852e36f270e247a9a0bb7f0f7f618da934297c05f7c687fccb7ceade40434`.
Its CORE Run A/B projection and member hashes and rank Run A/B bytes agree.
Those successful computations are reused; they are not repeated.

No finite NEW EXIT estimator has yet been fitted, no candidate performance has
been inspected, and no protected partition/provider data has been opened.

## Exact finite implementation

`scripts/phase57_exit_finite_r36.py` is the one-shot runner. It must reject any
R35 A/B projection/hash disagreement and recheck the pinned raw-path,
Pattern-opportunity and evaluator hashes before computation.

- R35 CORE contains 656,247 rows: IMMEDIATE 345,893 and R1 310,354.
- The R1 `(Opportunity,NOW)` Pattern keys must be a subset of IMMEDIATE keys;
  their union must be exactly 345,893. Pattern-v2 is calculated once per union
  key through the canonical R23 `pattern_now` closed-prefix adapter, never from
  an Entry-arm suffix.
- HOLD5/HOLD15/HOLD_TERMINAL labels are built only by the isolated R35 label
  module from exact scheduled references. Null targets are neither searched
  forward nor imputed.
- The R31 post-Entry-best-High anatomy must reproduce, before any fit, the exact
  IMMEDIATE `N=1,963 / mean=3.2759536262693145 / median=1.853834987268277`
  and R1 `N=1,885 / mean=3.08034166631174 / median=1.6673793687348892`.

For each arm/fold/head, preprocessing is fitted on that head's target-available
training rows only. Categorical values use train-only one-hot encoding with
unknown-ignore. Numeric CORE and, where registered, the exact 187 curated Pattern
columns use train-only median imputation plus missing indicators. Ridge scales
the combined sparse matrix with train-only `StandardScaler(with_mean=False)` and
uses deterministic `lsqr`, tolerance `1e-6`, maximum 2,000 iterations and the
already-registered alpha. HGB uses an unscaled dense float32 matrix,
`early_stopping=False`, and exactly the frozen R25/R33 parameters/seed.

Weights equalize target-eligible sessions, then eligible Opportunities in a
session, then eligible rows in each arm/Opportunity sequence, and are rescaled
to mean one. Representation codes are transport-only; one-hot categories are
still learned from the relevant training rows.

The six fitted prediction specifications share predictions across the four
threshold/persistence mappings each. Exactly:

`6 specs × 3 heads × 2 Entry arms × 4 folds = 144 fits`.

There is no 145th fit, no 25th policy and no fit after inspecting performance.
Every one of the 24 policies is nevertheless replayed and scored separately.

## Replay and score details fixed here

The policy walks only its OOF score-session checkpoints in causal order. A stale
current observation or missing prediction is HOLD with no persistence advance;
a fresh false condition resets persistence. An EXIT intent resolves only the
exact R24 next scheduled OPEN. A missing OPEN creates no fill and no queued
intent; the next checkpoint is evaluated anew. Still-open positions use only the
minute-930 auction; missing auction remains unresolved/censored.

Owned peak/giveback comes from the R35 causal position prefix at the triggering
checkpoint (or final checkpoint for terminal), and is certified only when
`fullOwnedPrefix` is true. The EXIT OPEN candle is not owned. Post-EXIT High is
early-exit missed opportunity, never owned giveback. Primary sell cost is 0.05
pp; 0.10/0.20 pp are mandatory stresses.

Full scorecards retain OOF population, no-Entry, filled, resolved, missing and
censored accounting; every R24 metric has its own denominator. They cover both
arms, four folds, six canonical buckets plus not-evaluable, and metric-specific
paired R1-minus-IMMEDIATE common cases.

The HOLD_TO_TERMINAL diagnostic is non-selectable. Candidate-versus-neutral
R25 comparisons use only paired Opportunity IDs with the specific metric
available in both. Concentration uses unit-notional positive primary-net OOF
trade contributions: top trade, top five trades and largest session share.

R31 aggregate +2.00% and bucket floors are hard completion gates in each arm,
in addition to every R25 coverage, Winner Continuation, Profit Retention, Loss
Containment, cost, concentration and reproducibility gate. Capability ranking
uses, in order only after all gates pass, the minimum across arms of the fixed
winner/retention/loss margins. Each axis receives a descending rank; minimize
the worst rank, then rank sum. Exact equality of all three substantive margins
at the best rank is `NO_SELECTION_STOP`, never a candidate-ID/manual tie-break.

## Reproducibility meaning

The 144 fits occur once. Their immutable OOF prediction file is then consumed by
two separately executed replay/score/selection passes. Every decision ledger,
scorecard, selection result and ranking must be byte-identical. This satisfies
R25 Run A/B without doubling fits merely for threshold/persistence variants.
All fitted model/preprocessor bundles and SHA-256 identities are retained in the
CI artifact. Any mismatch fails the run before SELECT can exist.

## Capital/Portfolio boundary

Capital adapters may be developed and synthetically tested while this CI runs,
but no historical Portfolio performance may be calculated before a SELECT and
EXIT Freeze. A formal `NO_SELECTION_STOP` prohibits Capital performance and any
automatic expansion of the EXIT search.

## Exposure, safety and next plan

The 2,155 Opportunities are outcome-exposed Development only. Common Holdout,
REPORT19, Validation, OOS, Fresh and Prospective remain sealed. Provider requests
remain zero. Frozen Entries and old EXIT historical evidence are unchanged.
Safety9 remain false. No main merge, force push, live/paper execution, broker/
Excel/RSS write, transmission, automatic promotion or production update is
authorized.

Next: run the focused synthetic suite, execute this finite workflow once, and
freeze either SELECT or `NO_SELECTION_STOP` from the precommitted gates. Only a
SELECT permits the already-precommitted MAX3/MAX4/MAX5 Development Portfolio
connection.
