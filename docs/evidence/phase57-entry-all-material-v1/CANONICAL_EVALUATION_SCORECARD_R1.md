# Phase57 Entry — Canonical Evaluation Scorecard Contract R1

Date: 2026-09-24 JST
Scope: Development research only / PR #587

## Purpose

Every new Entry version/candidate MUST be evaluated with the same canonical scorecard before any
promotion/freeze decision. A version report is incomplete if any applicable section below is omitted.
This contract is additive to the existing All-Material R0/R1/R2/R3 contracts and does not change
Frozen Selector, original State-v3/9Pattern, existing six Signals, or historical Evidence.

## A. Population / participation

Report selector denominator, entered N, Fill rate, no-entry N, ABSTAIN N, participation/coverage,
missing/evaluation-ineligible N and exact reasons. Never remove ABSTAIN/no-entry opportunities from
the original selector denominator.

For research-only coverage diagnostics report the precommitted finite coverage points
100%, 97.5%, 95%, 90% when available. Future outcomes may not determine ABSTAIN.

## B. Relative Entry location

Using the frozen ordered-Low -> strictly-later-High evaluator contract report:
- EntryPosition mean and median;
- <=10%, <=15%, <=25%, <=50% rates;
- valid denominator and invalid/missing reason counts.

Primary EXIT-transition target remains mean EntryPosition <25%. <15% is stretch evidence.

## C. Absolute Entry location / remaining upside

Report:
- Low -> Entry absolute percent and bps: mean/median plus useful quantiles where supported;
- Entry -> strictly-later High remaining percent and bps: mean/median plus useful quantiles;
- valid denominator.

These are evaluator-only future-path metrics and MUST NOT be decision features.

## D. Opportunity-size buckets

For mutually exclusive future opportunity-size buckets:
- <1%
- [1%,2%)
- [2%,3%)
- [3%,4%)
- [4%,5%)
- >=5%

report N, Fill N/rate, EntryPosition mean/median, <=10/15/25/50 rates, Low->Entry %/bps,
Entry->later-High %/bps, and 30m/60m MFE/MAE where defined.

Future bucket membership is evaluator-only and cannot be used to decide Entry/ABSTAIN.

## E. Cumulative +1/+2/+3/+4/+5 opportunity panels

For each >=1%, >=2%, >=3%, >=4%, >=5% eligible opportunity threshold report:
- eligible denominator;
- Fill N/rate;
- canonical +k Capture N/rate;
- EntryPosition mean/median and <=10/15/25/50 rates;
- Low->Entry %/bps;
- Entry->later-High %/bps;
- 30m/60m MFE/MAE and returnNet where defined.

Denominators may differ and MUST be printed explicitly. Do not compare rates as if denominators were
identical. +1/+2/+3/+5 must retain canonical semantics; +4 uses the identical contract extension.

## F. Post-entry path quality

Report 30m and 60m MFE, MAE and returnNet, with valid N. Preserve existing cost/fill/active-minute
semantics.

## G. State / concentration / stability

Report the above core metrics by the nine State-v3 labels where support exists:
REBOUND, RISE, SHARP_RISE, DROP, PULLBACK, RANGE, SHARP_DROP, DROP_STOP, RISE_STOP.

Also report session, symbol, entry-clock and sector concentration/stability when the field is
causally available. Mark unavailable fields explicitly; never silently impute them.

## H. Baseline and paired comparison

Every candidate report must compare, under the same evaluator contract, against:
- Immediate;
- Entry v1;
- original State v3;
- accepted ONE_MINUTE;
- the immediately preceding candidate/version when applicable.

Separate aggregate differences from common-case paired differences. Report paired N and avoid
claiming improvement caused only by a changed Fill set.

## I. Causality / leakage / reproducibility

Required checks where applicable:
- knownAt <= decision timestamp;
- closed bars only;
- future-suffix mutation invariance;
- evaluator/decision isolation;
- no future Low/High/MFE/MAE/PnL/EXIT outcome/future State as decision input;
- no future backfill/interpolation;
- session/lunch/active-minute semantics;
- next-fill semantics;
- deterministic two-run replay;
- focused tests, ordinary regression and dedicated CI;
- input/source hashes and candidate/version lineage.

## J. Candidate disposition

A Development Entry candidate may transition to EXIT only if it was frozen before final whole-2,155
measurement and:
1. mean EntryPosition <25%;
2. common-case paired EntryPosition improves versus accepted ONE_MINUTE;
3. Fill/Capture/coverage do not violate precommitted preservation limits;
4. no material concentration dependency invalidates the result;
5. causality/leakage/repeatability/regression gates pass.

Mean <15% is stretch evidence, not required for EXIT transition.
Do not weaken the <25% gate after observing results.

## Required version artifact

Each Entry version must persist a machine-readable scorecard (JSON preferred) plus a human-readable
summary containing every applicable section A-J. Missing metrics must be explicit as
UNAVAILABLE / NOT_EVALUABLE with reason, not silently omitted.

Safety remains research-only:
executionAllowed=false; brokerWriteAllowed=false; excelOrderWriteAllowed=false;
rssOrderFunctionAllowed=false; liveTradingAllowed=false; paperTradingAllowed=false;
automaticPromotionAllowed=false; productionUpdateAllowed=false; transmitted=false.
