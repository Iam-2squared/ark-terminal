# Phase57 — finite NEW EXIT candidate/model/search protocol R25

Date: 2026-09-25 JST  
Basis HEAD before this append-only checkpoint: `ab5e68a26e628507f765ff5dc05bbffbe574a5df`  
Status: **PRECOMMITTED_BEFORE_ANY_NEW_EXIT_FIT_OR_PERFORMANCE_INSPECTION**

## Objective and decision meaning

At each causal NOW, estimate whether the upside thesis established by Frozen
Selector + Frozen Entry is still worth holding. Optimize causal Entry→Exit value
while keeping Winner Continuation, Profit Retention and Loss Containment separate.
DROP/negative PnL is not itself an EXIT label. Conceptual HOLD_CONTINUE,
HOLD_RECOVERY, DETERIORATING/PROTECT and EXIT_THESIS_BROKEN names remain framing,
not fixed policy classes.

Entry arms remain IMMEDIATE and ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF under Dual
Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d`. Models are fitted separately
per arm/fold, but the same candidate configuration/hyperparameters must govern
both arms. No Entry retraining, threshold change or feature addition is allowed.

## Training labels — future only on the label side

For a decision NOW, define the exact `EXIT_NOW` reference by R24's next scheduled
continuous OPEN. Three numeric targets are incremental gross hold value:

- HOLD5: exact OPEN after five additional active 1-minute bars vs EXIT_NOW;
- HOLD15: exact OPEN after fifteen additional active 1-minute bars vs EXIT_NOW;
- HOLD_TERMINAL: exact endpoint-stamped 15:30 auction vs EXIT_NOW.

Each target is `100*(future sell reference / EXIT_NOW sell reference - 1)`.
The same sell cost cancels in the incremental label and is applied explicitly in
the final scorecard. Missing either exact reference makes that target null/censored;
there is no forward search, stale fill or zero replacement. Future upside/adverse
moves may be audit labels only. No label, future High/Low/State/pivot, final PnL or
oracle EXIT can enter a decision feature or preprocessing fit.

## Fixed temporal split and purge

The exact 58 Opportunity-bearing Development sessions are derived from the pinned
2,155-ID protocol. All rows for a session, Opportunity, Entry arm and sequence stay
grouped; random row split is prohibited. Four expanding walk-forward folds are:

| Fold | Train | Purge | OOF score | Score sessions |
|---:|---|---|---|---:|
| 1 | 2025-05-30…2025-06-30 (22) | 2025-07-01, 2025-07-02 | 2025-07-03…2025-07-16 | 8 |
| 2 | 2025-05-30…2025-07-10 (30) | 2025-07-15, 2025-07-16 | 2025-07-17…2025-07-29 | 8 |
| 3 | 2025-05-30…2025-07-25 (38) | 2025-07-28, 2025-07-29 | 2025-07-30…2025-08-08 | 8 |
| 4 | 2025-05-30…2025-08-06 (46) | 2025-08-07, 2025-08-08 | 2025-08-12…2025-08-25 | 10 |

OOF score sessions are disjoint and cover the last 34 Opportunity-bearing
sessions. The two-session purge is excluded from both fit and score in its fold.
No Common Holdout, REPORT19, Validation, OOS, Fresh or Prospective data is opened.

## Two fixed feature sets

1. `CORE`: R20 State-v3, six tri-state Signals, causal State/Signal history,
   Entry→NOW owned-path/time features, data quality, coverage and missingness.
2. `CORE_PLUS_CURATED_PATTERN`: CORE plus the exact R23 187-column Pattern subset.

The other 259 legally admitted Pattern columns are outside this search; the 30
blocked prior-daily columns remain blocked. “All 476” is never a feature set.
Dictionary outcomes and every old EXIT output are forbidden.

Preprocessing is trained inside each training fold: explicit UNKNOWN categories,
training-median numeric imputation plus missing indicators, and training-only
standardization for Ridge (none for tree models). Weights first equalize sessions,
then Opportunities, then make each Opportunity/arm sequence sum to one so long or
dense sequences do not dominate. Each horizon head fits only rows whose own target
exists; labels are never imputed, and unavailable counts stay reported. Requiring
all three labels as one complete case is forbidden.

## Entire finite candidate grid

The search has exactly 24 configurations:

- Three independent Ridge horizon heads under one configuration: feature set
  {CORE, CORE_PLUS_CURATED_PATTERN} × alpha
  {1,10} × EXIT threshold {0.00,0.10 pp} × fresh persistence {1,2}: **16**.
- Three separate Histogram Gradient Boosting heads, only
  CORE_PLUS_CURATED_PATTERN: max leaf nodes {7,15} × EXIT threshold {0.00,0.10 pp}
  × fresh persistence {1,2}: **8**. Fixed learning rate 0.05, max iterations 100,
  minimum leaf 50, L2=1.0 and seed 5757.

At NOW, thesis-alive score is `max(predicted HOLD5, HOLD15, HOLD_TERMINAL)`.
EXIT is requested only when it is <= the candidate threshold for the fixed number
of consecutive fresh checkpoints. Missing prediction/current observation means
HOLD_NO_ACTION, not SELL. R24 then resolves the exact next OPEN or records no fill
and re-evaluates. Terminal liquidation remains mandatory.

`HOLD_TO_TERMINAL` and `EXIT_FIRST_AVAILABLE_REFERENCE` are non-selectable neutral
diagnostic references only. Fixed12 and Candidate A are absent: they are not
baselines, gates, fallbacks, anchors, labels or training targets.

## Selection and robustness gates

All 24 configurations must finish before any winner declaration. Each candidate
must retain all missing/censored rows and resolve at least 95% of filled Entries
in each arm. Every candidate-versus-neutral-reference gate is paired on the same
Opportunity IDs and availability of the specific metric. The following apply to
both arms:

1. Winner Continuation: in the canonical `>=5%` bucket, median post-Entry capture
   may be at most 10 pp below HOLD_TO_TERMINAL and median early-exit cost at most
   0.25 pp above it; at least 3/4 folds meet noninferiority.
2. Profit Retention: aggregate median certified Owned Peak giveback may be at most
   0.10 pp above HOLD_TO_TERMINAL, and at least 2/4 folds improve it by >=0.10 pp.
3. Loss Containment: aggregate p05 net must improve by >=0.25 pp and worst return
   may be no more than 0.25 pp worse than HOLD_TO_TERMINAL; at least 3/4 folds have
   p10 no worse than terminal hold.
4. Cost robustness: PF >=1.00 at 0.10 pp sell cost and PF >=0.95 at 0.20 pp in
   both arms, without reselecting the candidate.
5. Concentration: the largest trade contributes <=25%, top five trades <=50%, and
   largest session <=35% of gross positive P&L; nonpositive/undefined aggregate
   positive P&L fails rather than receiving a zero share.
6. Reproducibility: independent Run A/B inputs, decisions, scorecard and ranking
   are byte-identical.

Among candidates passing every gate, rank each of the three capability margins;
minimize the worst capability rank, then sum of three ranks. An exact substantive
tie yields no selection rather than a candidate-ID or manual tie-break.
Win rate alone cannot select.

If none pass, outcome is `NO_SELECTION_STOP`. The grid, feature set, threshold,
model family or search budget cannot be expanded in response to results. Any later
research requires a new append-only precommit before seeing more performance.

## Reproducibility and bounded work

`scripts/phase57_exit_research_protocol_v1.py` emits all sessions, folds and all
24 candidate configurations deterministically. The focused CI generates the R23
feature, R24 execution/evaluator and R25 research contracts twice, requires a
recursive byte comparison, runs the R21 and new pre-design tests, and preserves
source/contract hashes. This preregistration itself performs zero estimator fits,
zero policy replays and zero candidate scorecard calculations.

## Freeze, exposure and safety

The 2,155 Opportunities remain outcome-exposed Development, not Fresh/OOS.
Provider requests and protected-partition opens remain zero. Entry Dual Freeze is
unchanged. No EXIT is frozen or promoted. Safety9 remain false; no execution,
broker/Excel/RSS write, live/paper trading, transmission, automatic promotion or
production update is authorized. Main merge and force push remain prohibited.
