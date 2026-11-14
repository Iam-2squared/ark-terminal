# Phase57 North-Star measurement audit contract

Status: PRE-EXECUTION / EVALUATOR ONLY. Contract version: NS-MEASUREMENT-1.
Source HEAD: 9d29ad7688677124ec584da346846c68fc6a40a0. PR #587.

## Scope and irreversible boundaries

North Star is additional upside AFTER selection, not final close versus previous close.
Use saved Development only. No provider requests, fitting, refitting, training,
hyperparameter search, feature additions to a model, policy changes, threshold
optimization, or new candidates. v1/v2 artifacts, target and timestamp Top5 remain
unchanged. Validation/OOS remain sealed. Entry/EXIT/Allocation, old selectors,
News/Event, Lane Y, main and live circuits are out of scope. Safety flags remain
false. Execute this fixed diagnostic once; report missing evidence as unavailable;
stop after reporting. Synthetic tests and corrections of execution defects are not
additional hypothesis searches. No rerun to improve an observed result.

## Data and model provenance

Read only allowlisted sessions in the existing L1 first-20 Development A contract,
the fixed v2 additional-20 contract, and Development C/D (40). These are 80
requested sessions; L1 previously had four unavailable sessions. Missing raw
sessions are reported, never fetched or replaced. Read no Validation/OOS outcome
files. Verify response hashes, session identity, contract hash and manifest counts.
Saved Minute runs: L1 34926225832, L2 34936002178, v2 34964031692.
L0 base: 34917676944. Saved v1 freeze evidence: 34944665187.

Primary measurement population: all existing finite causal feature rows emitted
by the L1 pipeline for these available sessions, not only selected rows. Report
existing finite-y30 eligible rows separately (strict finite check: null is NOT zero).
Retain existing PIT common-equity, market, corporate-action and price-scale rules;
do not claim this universe has an explicit execution/limit-up/halt filter.
Full saved Development aggregates and per-partition/session summaries are diagnostic,
not new holdouts. Target alignment uses common evaluable rows where required.

No model may be reconstructed by refitting. Original C-only v1 held-out D scores
and v2 scores are usable ONLY if their saved weights/scores can be verified.
If absent, their new North-Star KPIs are UNAVAILABLE. The saved v1 C+D finalArtifact
may additionally be scored unchanged, explicitly named V1_SAVED_CD_REFIT, never
identified as the C-only model underlying +117.21 bps. Report its C/D in-fit and
Development A outside-fit diagnostics separately. None are unbiased new validation.
Artifact SHA and training provenance must accompany all score-based metrics.

## TEST 1: horizon, price freshness and MAE

Keep legacy y30 and its denominator unchanged. Measure decision to target timestamp
elapsed minutes and reference bucket-end age, including missingness, by time of day.
Quantiles: min, P1/5/10/25/50/75/90/95/99, max.
Horizon buckets: <30, exactly30, (30,35], (35,45], (45,60], (60,90], >90 minutes.
Freshness buckets: [0,5], (5,10], (10,20], >20 minutes; negative ages are errors.

Existing Minute timestamps represent bar START, continuous close available at
Time+1 minute; terminal auction available at its exact timestamp. Reconstruct
source-minute provenance of the legacy last closed 5m bar: its last contributing
minute close is the legacy reference price. Audit actual source age separately
from bucket-end age. The minute normalizer must reproduce current acceptance,
deduplication and auction handling. Missing/invalid provenance is an audit failure.

Strict wall-clock B: latest closed continuous 5m observation at/before t+30m,
whose actual contributing close is no more than 5 minutes old at t+30m. It must
be strictly after t. Use legacy decision denominator to isolate the horizon
effect; no future-nearest observation, interpolation, cross-session continuation
or lunch bridging. Missing endpoints remain NA. Also compute B with valid fresh
North-Star reference as explicitly separate denominator sensitivity, not a target change.
Compare A and B on common finite rows: Pearson, Spearman, mean/median absolute
bps difference, sign disagreement, >=50/100/200bps membership disagreement.
Show coverage and all matching-population differences rather than conflating cohorts.

For legacy 30m and same-session MAE report raw minimum-low return, clipped
min(0, raw MAE), positive-MAE count and mean distortion. No retraining/correction
of historical outputs. Same-session new true MAE uses the valid reference below.

## TEST 2: North-Star evaluator and alignment

Valid decision reference = latest accepted raw minute close available at/before t
(or auction at t), positive and age <=5 minutes. This evaluator-only freshness
rule does NOT remove or replace a model's selected identities. Report unscorable
selected events and denominator coverage. Current-return matching/bins continue
using the existing causal feature; denominator sensitivity is identified separately.

Future path: same-session accepted continuous minute intervals starting >=t and
terminal auctions strictly after t. FutureUpsidePct=100*(max future high/ref-1).
Future +1/+2/+3/+5 means a high TOUCH, not guaranteed executable fills/profit.
True MAE=min(0,100*(min future low/ref-1)). Empty future path is unavailable,
not a negative outcome; observed-path coverage is reported (no price imputation).
Time-to-hit is the first qualifying minute CLOSE-availability minus t (conservative
one-minute interval bound), or exact later-auction time. Final close additional
return uses official same-scale final close/ref; previous-close Final+5 is secondary.

Compute cross-sectional percentiles per session/decision on finite values using
average rank for ties. Bands are nested Top1/5/10/20%, Middle20-80%, Bottom20%.
Apply independently to observed legacy y30, strict B, and verified saved scores.
Observed-return alignment is descriptive outcome-to-outcome alignment, NOT proof
of predictive skill. Report per-band count, Future+1/2/3/5 rates, +5 lift versus
unconditional prevalence in the same analyzable population, mean MFE, true MAE,
and final additional close return. Also report partition/time stability.

Existing current-return bins: <0, [0,1), [1,2), [2,3), [3,5), >=5 percent.
The user's terminal '=5%' is interpreted as >=5%, not omission of above-5 rows.
Show Opportunity counts/shares and prevalence in each, including current return<3%.

## TEST 3: feature sufficiency

Use ONLY the saved v1 model feature universe (15 selected features) for contrast.
No diagnostic values are fitted into a model. Match 1:1 without replacement within
same session, exact decision time, market, existing current-return bin, existing
liquidity bucket, and volatility quintile. Volatility quintiles are causal same-
timestamp cross-sectional ranks; missing volatility is a separate bucket. Within
stratum select pairs deterministically by SHA256('NS-MEASUREMENT-1|row identity').
Drop unmatched observations from the matched analysis and report their count/mix;
never silently relax matching. Repeat the same fixed matching for Early Big
Opportunity (current return<3%); controls in that comparison also have return<3%.

Per feature: opportunity/control N, median/P25/P75, mean, pooled-SD standardized
mean difference (signed), distribution overlap = sum of minimum histogram
probabilities using 20 pooled quantile bins, with duplicate edges collapsed.
Constants have overlap1 and effect0 if equal. Binary features use their two bins.
Report match-rate and common-support limitations. Large overlap alone cannot
prove lack of all multivariate/interaction information. No p-value fishing.

## TEST 4: selection and capacity-aware evaluation

Use original policy eligibility (finite legacy y30 and finite model features) and
Top5 per timestamp; saved v1 contract ranking/tie-breaks are preserved. No replacement
when reference stale. Report total selected, scorable selected and missing fraction.
Primary North-Star precision among evaluable selected events; also give conservative
hits/all-selected lower bound, not treat missing as known negatives. Recall denominator
is scorable opportunity events in the same original policy-eligible universe.

At each t, N_t=original policy-eligible candidates, K_t=min(5,N_t), O_t=observed
scorable opportunities. Expected random hits=sum_t O_t*K_t/N_t; random recall=
expected hits/sum_t O_t. Report actual recall, random expected recall, recall lift,
precision, unconditional prevalence and precision/prevalence lift separately for
+1/2/3/5. Also report capacity-matched random expected precision conditional on
evaluability to expose varying cross-sections/freshness. No 900/opportunity shortcut.

Daily diagnostic: retain first selected event per session/symbol, no best-of-day
scores. Report decisions/session, selections/session, distinct symbols/day, repeats,
first detection minutes after09:00, distinct hits/day, precision, and future upside
of first-detection hits. Do not reinterpret timestamp Top5 as daily Top5.
Show per-session KPIs; symbol rows are not independent statistical replications.

## Interpretation / STOP

Rank Measurement, Target, Feature, Model/Ranking and Evaluation explanations.
Do not pre-assign empirical verdicts or adopt new gates. Report unavailable historical
model versions prominently. Select ONE next research recommendation based on these
fixed diagnostics, not a new model/policy. Report contract commit and code/run SHA.
STOP: no training, new target/features, Validation/OOS, trading or further research.
