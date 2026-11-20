# Phase57 All-Material Entry v1 — Protocol R2: Upside-Strata + Causal Abstention

Status: **PRE-PERFORMANCE / APPEND-ONLY / FROZEN BEFORE NEW R2 PERFORMANCE**

Freeze-time branch: `research/phase57-long-only-cash-equity`
Freeze-time parent HEAD: `5158abfd195fddc6ae472725c740cba0f8ff6628`
Parent contracts: `PROTOCOL_R0.md`, `FEATURE_AVAILABILITY_CAUSALITY_MATRIX_R1.md`, `MODEL_SELECTION_PROTOCOL_R1.md`

This amendment records the user-authorized evaluator and participation changes before any new R2 performance is consumed. It does not invalidate, rewrite, or retune the completed bounded 9-State trials. Frozen Selector, original State-v3 / 9-Pattern Contract, original six Signals, ONE_MINUTE evidence, and prior rejected/insufficient/no-observation dispositions remain immutable baselines.

## 1. Entry completion gate

Primary Development gate for transition to EXIT:

- whole-development candidate mean `EntryPosition < 0.25`;
- `< 0.15` remains the stretch target;
- common-case paired EntryPosition must improve versus the frozen ONE_MINUTE baseline;
- coverage / Fill / Capture must stay within precommitted preservation bounds;
- causality, known-at, evaluator isolation, leakage, future-suffix mutation, repeatability, regression and required CI must pass;
- the result must not be driven by a thin sample or a single symbol/session/sector concentration.

A candidate at `0.15 <= mean EntryPosition < 0.25` may become `DEVELOPMENT_ENTRY_CANDIDATE_READY` only if every other gate passes. The 25% threshold must not be relaxed after performance is seen.

Frozen reference only (not new R2 performance): 2,155 Selector opportunities, ONE_MINUTE Fill about 81.86%, mean EntryPosition about 67.49%, <=15% about 15.19%, <=25% about 26.73%, +3 Capture about 71.88%, +5 Capture about 73.53%.

## 2. EntryPosition is not the sole quality metric

The normalized metric

`EntryPosition = (Entry - ordered Low) / (strictly-later High - ordered Low)`

remains a primary gate metric, but its ratio can exaggerate apparent entry error when the total available range is small. R2 therefore adds evaluator-only absolute-distance and opportunity-size views. These views must never become decision inputs.

Required absolute metrics:

- Low -> Entry price distance in percent and basis points;
- Entry -> strictly-later High distance in percent and basis points;
- 30m/60m MFE and MAE under the already frozen evaluator semantics.

## 3. Evaluator-only +1/+2/+3/+4/+5 upside strata

For `k in {1%, 2%, 3%, 4%, 5%}`, create a threshold-conditioned evaluator stratum using the same future-path/evaluator convention as the already frozen +3/+5 Capture contract.

For every k, report separately:

1. eligible denominator N: opportunities for which the frozen evaluator says at least +k future upside exists;
2. Fill N / Fill rate within that denominator;
3. +k Capture N / Capture rate under the same contract used by frozen +3/+5 Capture;
4. valid EntryPosition N, mean, median and case rates <=10%, <=15%, <=25%, <=50%;
5. Low -> Entry absolute percent and bps;
6. Entry -> strictly-later High absolute percent and bps;
7. 30m/60m MFE/MAE;
8. missing/unfilled reason counts.

The +1/+2/+3/+4/+5 denominators may differ. Every report must print the denominator beside the rate. Rates from unequal denominators must not be presented as if they were directly paired percentages.

**Contract preservation:** existing +3/+5 definitions are immutable. +1/+2/+4 are extensions of that same contract, not redefinitions. If the exact existing +3/+5 implementation cannot be traced byte-for-byte, implementation must stop before generating a performance claim.

## 4. Future opportunity-range sensitivity buckets

Add evaluator-only buckets to reveal normalized-ratio sensitivity:

- `[1%, 2%)`
- `[2%, 3%)`
- `[3%, 4%)`
- `[4%, 5%)`
- `>=5%`

Bucket membership is computed only by the frozen future evaluator after the decision stream is sealed. Boundaries follow the same price/tick rounding convention as the existing evaluator. Each bucket reports N, Fill, Capture, EntryPosition distribution, Low->Entry absolute distance and Entry->later-High distance.

Example motivation only: if the whole Low-to-High path is +1% and entry occurs +0.5% above Low, normalized EntryPosition is 50% despite only 50 bps absolute slippage from Low. This fact may change interpretation, never the historical decision.

## 5. Causal Entry-layer ABSTAIN / NO-ENTRY

The user has authorized limited non-participation when a NOW-causal signal indicates acute downside / no prospect. This is an Entry-layer action, **not** a retraining or rewrite of Frozen Selector.

Rules:

- the original 2,155 Selector opportunities remain in the master evaluator ledger;
- every abstained row remains present with `participated=false` and an explicit causal reason/prediction;
- future crash, Low/High, MFE/MAE, Capture, PnL, EXIT outcome or future State may not drive abstention;
- abstention predictions must be produced out-of-fold / temporally valid under the R1 fold contract;
- feature family, model family, threshold/ranking rule and any maximum allowable abstention must be frozen before its corresponding performance is inspected;
- abstention cannot be used to erase poor rows from the denominator or to manufacture the <25% gate.

### Coverage-quality diagnostic grid

Before choosing any operational abstention ceiling, report OOF quality at these fixed participation coverage points:

- 100.0%
- 97.5%
- 95.0%
- 90.0%

For each point report excluded N, participation N/rate, Fill, Capture +1/+2/+3/+4/+5, EntryPosition distribution, absolute Low->Entry, MFE/MAE, and concentration diagnostics.

This grid is **diagnostic**, not four post-hoc deployment choices. Because no independently justified maximum abstention percentage has yet been frozen, a filtered result cannot auto-PASS solely because one coverage point looks favorable. If no non-performance basis for a maximum abstention ceiling exists, the filtered candidate is `HOLD_FOR_HUMAN_REVIEW`. A 100%-coverage candidate can still auto-progress under the normal Entry gate.

## 6. Model/search closure

`MODEL_SELECTION_PROTOCOL_R1.md` remains the finite learned-Entry search contract. R2 does not reopen an unlimited model/feature/hyperparameter search after results.

The frozen finite families remain the only automatic learned-entry comparison set unless a new, separately pre-performance protocol is authorized before any additional candidate performance is inspected.

Candidate selection and candidate evaluation must remain separated by the time-ordered / session-grouped / purged nested/OOF design. The 2,155 Development opportunities are outcome-exposed Development and must not be called Fresh/OOS.

## 7. Causality and data boundaries

Decision features may use only values genuinely available by NOW, with producer/source timestamp, `knownAt`, session join, missing semantics and coverage audited before promotion into the feature set.

Forbidden decision inputs remain:

- future Low / High / later High;
- future MFE / MAE / Capture / PnL / EXIT outcome;
- future State;
- post-entry bars not yet closed at decision time;
- future-filled/backfilled missing values;
- any newly opened Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective payload.

Provider requests remain 0 for this phase.

## 8. Required final Entry report

Whole 2,155 ledger and State-level views must include:

- Selector N, participation N/rate, abstain N/rate;
- Fill N/rate and reasons for unfilled/missing;
- EntryPosition valid N, mean, median, <=10/15/25/50%;
- common-case paired EntryPosition vs Immediate, Entry v1, original State v3 and frozen ONE_MINUTE;
- Low->Entry percent/bps and active-minute distance;
- Entry->strictly-later High percent/bps;
- +1/+2/+3/+4/+5 threshold-conditioned denominators and Capture;
- future opportunity-range bucket metrics;
- 30m/60m MFE/MAE;
- session/symbol/sector/time concentration;
- lineage/hashes, decision-feature schema, fold assignments, replay hash, repeatability result, causality/leakage/future-suffix/knownAt/regression/CI results.

## 9. Stage transition

Only when the Entry gate passes may the automation reread the repository's latest accepted/Frozen EXIT baseline/contract/evidence and connect that existing EXIT unchanged first for paired causal replay. EXIT must pass its own completion gate before Capital Allocation is touched.

No main merge, production update, live/paper execution, broker/Excel/RSS order write, automatic promotion or transmission is authorized.

## 10. Freeze statement

No new R2 candidate performance was consumed to author this amendment. The purpose of R2 is to freeze the user's requested evaluation refinement and limited-causal-abstention treatment before those results exist.
