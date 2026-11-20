# Phase57 All-Material Entry v1 — Finite Model Selection Protocol R1

Status: **PRECOMMITTED BEFORE ALL-MATERIAL PERFORMANCE MEASUREMENT**

This protocol defines one finite, leakage-controlled learned Entry research pass. It must not be expanded after R1 performance is seen. The existing 2,155 opportunities are outcome-exposed Development data; all results remain Development evidence, not Fresh/OOS evidence.

## 1. Objective

At each causal decision checkpoint, estimate whether entering on the next valid fill is likely to land in the evaluator-defined Low→strictly-later-High range near the Low side.

Primary training target:

`near_low_25 = 1[EntryPosition_if_next_fill_now <= 0.25]`

Future Low/Later High are permitted **only to construct the training/evaluator label**. They are never model features and never available to the decision policy.

If the evaluator denominator is invalid or no strictly later High exists, the row has a missing training label and is excluded from model fitting only. The underlying opportunity remains in the final 2,155-opportunity evaluation and its missing/unfilled reason is reported.

## 2. Feature set

The model receives **all and only** feature families frozen `ELIGIBLE` before fitting in `FEATURE_AVAILABILITY_CAUSALITY_MATRIX_R1.md` plus any CONDITIONAL family that is upgraded to ELIGIBLE by an append-only source/knownAt/coverage audit **before the first performance run**.

There is no performance-driven feature subset search or post-result feature-family upgrade in R1.

- preprocessing/imputation/scaling is learned on the training fold only,
- missing indicators are allowed,
- exact date ID and symbol ID are grouping/audit keys, not direct predictors,
- original State-v3 and existing 6 Signals are immutable inputs, not rewritten.

## 3. Sequential Entry policy

For each opportunity, starting at T0, score each available active-minute checkpoint using only the closed prefix known by that checkpoint.

Finite wait horizon grid:

`H ∈ {5, 10, 20, 30}` active minutes.

Finite trigger probability grid:

`P25 ∈ {0.40, 0.50, 0.60}`.

Policy for a fixed `(model, H, P25)` configuration:

1. At each active-minute checkpoint from T0 through H, compute `p = P(near_low_25=1)` from the causal prefix.
2. Trigger at the first checkpoint where `p >= P25`.
3. Execution uses the existing next-fill semantics; no same-bar imaginary fill.
4. If no threshold trigger occurs by H, force an Entry at H using the same next-fill semantics.
5. If H cannot be reached/fill cannot occur due to session end or accepted missing-data rules, record the exact unfilled reason. Never fabricate a fill.

The forced horizon prevents the learned policy from becoming a second Selector that simply discards hard opportunities.

## 4. Frozen model family

Exactly these model families may compete in R1:

### M1 — L2 logistic
- standard logistic regression
- L2 penalty
- regularization `C=1.0`
- deterministic solver/random seed
- train-fold standardized numeric inputs

### M2 — L1 logistic
- standard logistic regression
- L1 penalty
- regularization `C=1.0`
- deterministic solver/random seed
- train-fold standardized numeric inputs

### M3 — compact gradient boosting classifier
- scikit-learn gradient boosting / histogram gradient boosting implementation already available in the repository runtime
- `max_depth=3`
- `learning_rate=0.05`
- `max_iter/n_estimators=100`
- deterministic random seed where supported

If M3's required implementation/dependency is not already available before fitting, M3 is marked `SKIP_DEPENDENCY` and **no replacement model is introduced after seeing results**.

No additional model family, hyperparameter, threshold, wait horizon, feature subset, or manual rule may be added in R1 after performance is observed.

Maximum precommitted configuration count: `3 models × 4 horizons × 3 thresholds = 36` (or 24 if M3 is pre-fit unavailable).

## 5. Temporal / grouped nested evaluation

Outer evaluation:

- 5 chronological, session-grouped expanding outer folds,
- all rows from one JPX session stay in the same outer fold,
- one full session is purged between outer train and outer test,
- every opportunity contributes to at most one outer test decision stream.

Inner selection inside each outer training block:

- 3 chronological session-grouped expanding inner folds,
- one-session purge between inner train and inner validation,
- preprocessing/model fit uses inner-train only.

If the available Development session structure cannot create 5 valid outer folds and 3 valid inner folds with non-empty train/test and valid labels, the run terminates `PROTOCOL_INSUFFICIENT` rather than silently changing fold counts or purge semantics.

## 6. Inner configuration selection

For each outer fold, evaluate the precommitted configurations only on inner OOF decisions.

A configuration is inner-admissible only if, under the same evaluator semantics as ONE_MINUTE:

- Fill rate is no worse than ONE_MINUTE by more than **2.0 percentage points**,
- +3 Capture is no worse by more than **5.0 percentage points**,
- +5 Capture is no worse by more than **5.0 percentage points**,
- opportunity denominator is unchanged; no post-hoc opportunity exclusion.

Among inner-admissible configurations, select the one with the lowest inner-OOF mean EntryPosition.

Tie-break when absolute mean EntryPosition difference is <= 0.5 percentage points:

1. M1 before M2 before M3,
2. shorter H before longer H,
3. P25 closer to 0.50, then lower P25.

If no learned configuration is inner-admissible for an outer fold, that outer fold uses the immutable ONE_MINUTE policy as a fail-closed fallback. The fallback is reported and prevents an unsafe learned configuration from being forced into the OOF candidate.

## 7. Primary Development candidate evidence

Concatenate outer-test decisions to form exactly one OOF Development decision stream. This stream is the only All-Material v1 R1 candidate used for the primary completion decision.

Required overall and State-level outputs:

- opportunity N and exact 2,155 denominator accounting,
- Fill N/rate and unfilled/missing reasons,
- Low→Entry price difference and active-minute difference,
- Entry→strictly-later High,
- EntryPosition mean and median,
- rates `<=10%`, `<=15%`, `<=25%`, `<=50%`,
- +3 / +5 Capture,
- 30m / 60m MFE and MAE,
- session/symbol/sector/time concentration,
- aggregate comparison and common-case paired comparison vs Immediate, Entry v1, original State-v3, and saved ONE_MINUTE.

## 8. Hard Entry completion gate

All conditions must pass:

1. OOF Development mean EntryPosition **< 0.25** across the full evaluation semantics.
2. Common-case paired mean EntryPosition is strictly better than saved ONE_MINUTE.
3. Fill rate >= saved ONE_MINUTE Fill rate - **2.0pp**.
4. +3 Capture >= saved ONE_MINUTE +3 Capture - **5.0pp**.
5. +5 Capture >= saved ONE_MINUTE +5 Capture - **5.0pp**.
6. The denominator remains all 2,155 Development opportunities; no outcome-based opportunity deletion.
7. Candidate symbol/session concentration HHI is <= 2× the saved ONE_MINUTE HHI and top-1 symbol/session share is <= baseline top-1 share + 5pp.
8. future-suffix mutation invariance, evaluator isolation, timestamp/knownAt, session/lunch, non-target/transition, and leakage guards PASS.
9. Two identical runs produce identical decision/evidence hashes.
10. Focused tests, ordinary regressions, and dedicated CI PASS.

If mean EntryPosition < 0.15, record `STRETCH_TARGET_MET`.

If all hard gates pass with `0.15 <= mean EntryPosition < 0.25`, record `DEVELOPMENT_ENTRY_CANDIDATE_READY` and freeze the candidate for EXIT integration.

If mean EntryPosition >= 0.25 or any preservation/integrity gate fails, Entry does not advance to EXIT. The 25% threshold is not relaxed after results.

## 9. Stop rule

R1 is one finite protocol pass. After its OOF result is observed:

- do not add models,
- do not add/alter thresholds,
- do not add horizons,
- do not add result-inspired interactions/features,
- do not reopen a CONDITIONAL feature family,
- do not change fold/purge semantics,
- do not consume Fresh/OOS/Validation/Common Holdout/REPORT19/Prospective.

Any further research requires a separately authorized, precommitted R2 based on methodological findings, not threshold-chasing.

## 10. Safety / lineage

- Frozen Selector unchanged.
- Original State-v3 / 9 Pattern unchanged.
- Existing 6 Signals unchanged.
- Provider requests added: 0.
- main / production untouched.
- `executionAllowed=false`
- `brokerWriteAllowed=false`
- `excelOrderWriteAllowed=false`
- `rssOrderFunctionAllowed=false`
- `liveTradingAllowed=false`
- `paperTradingAllowed=false`
- `automaticPromotionAllowed=false`
- `productionUpdateAllowed=false`
- `transmitted=false`
