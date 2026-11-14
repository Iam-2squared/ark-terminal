# Phase57 MSH-Entry LONG v1 Final Fit / Decision Contract Freeze Audit

**Decision: `MSH_ENTRY_LONG_V1_FIT_CONTRACT_BLOCKED`**

**Blocker: `ORDINAL_IMPLEMENTATION_BLOCKED`**

The repository does not currently pin a maintained penalized proportional-odds ordinal logistic implementation. Replacing the requested model with five binary logistic models or multinomial logistic regression would change the model semantics. Writing a new optimizer is expressly outside this freeze task. The Final Fit Contract is therefore not effective and no training may start.

## Dependency audit

- `predict/package.json` has no runtime dependency.
- `tools/requirements-rss.txt` does not include `statsmodels`, `mord`, or another ordinal package.
- Existing Phase57 research workflows pin NumPy, pandas and SciPy; one separate comparison lane also pins scikit-learn. None pins an ordinal logistic package.
- scikit-learn `LogisticRegression` is binary or multinomial logistic regression, not a proportional-odds ordinal model.
- `statsmodels` and `mord` were unavailable in the audited runtime.
- Consequently, L2 objective scaling, slope-only penalty behavior, solver compatibility, convergence reporting and determinism cannot yet be frozen.

## Non-effective candidate decisions

These decisions were made before fit, prediction or performance inspection, but do not become an operative training contract until the blocker is resolved.

| Item | Candidate decision |
|---|---|
| Core | Frozen Selector Ridge score + Ridge rank |
| Optional feature policy | Option A; no market-bar feature in v1 |
| Decision Price | Reference only |
| Primary label | strict wall-clock +30m, same-session, complete-path future HIGH ordinal 0–4 |
| Unlabelable rows | Exclude from fit/OOF; preserve identity, time and reason in the audit ledger; never Class 0 |
| Supporting diagnostic | completed 5m CLOSE ordinal from the same path, kept separate |
| Model | one proportional-odds ordinal logistic model with logit link |
| Class weight | unweighted |
| CV | four expanding evaluation folds; 16-session initial train then four 15-session evaluation blocks |
| Decision score | `E[L] = 0P0 + 1P1 + 2P2 + 3P3 + 4P4`, range `[0,4]` |
| Threshold candidates | exactly `1.0`, `2.0`, `3.0`; derived from interior integer landmarks before results |
| State | `ENTER` or `SKIP_THIS_DECISION`; fresh Selector reselection required for reevaluation |

The two Core inputs are both Selector outputs. Ridge rank is derived from within-decision ordering. The v1 candidate can therefore only recalibrate/filter Selector strength and does not observe independent market state. This is an explicit architecture risk, not a hidden assumption.

## Why four expanding folds are not four 19-session blocks

Four contiguous 19-session blocks yield only three expanding evaluation steps after the first block is used for training. To obtain four actual evaluation folds without random splitting, the candidate structure is:

1. train sessions 1–16; evaluate 17–31;
2. train 1–31; evaluate 32–46;
3. train 1–46; evaluate 47–61;
4. train 1–61; evaluate 62–76.

Every JST session stays whole, so each symbol-session also remains in one evaluation fold. The initial 16-session warmup receives no OOF prediction.

## Decision objective and gates

The three threshold candidates would be compared only on chronological OOF Development rows. The predeclared scalar is the equal-axis geometric mean of:

1. mean +1/+2/+3/+5 precision;
2. mean +1/+2/+3/+5 opportunity preservation;
3. first-entry coverage.

The selected candidate must also materially improve CURRENT Entry preservation/throughput, hold or enrich Selector-only quality, avoid dependence on one opportunity threshold, remain directionally stable across folds, and avoid destructive latency or consumed return. Precision-only, coverage-only and +5-only selection are prohibited.

## Data and safety

- Model fits: 0
- Predictions / OOF rows: 0 / 0
- Threshold or L2 searches: 0
- Validation new access: 0
- OOS new access: 0
- Provider requests: 0
- Selector and CURRENT Entry changes: 0
- SHORT evaluation: 0
- Every execution, broker, Excel/RSS order, live/paper, promotion, production, transmission, margin and leverage flag remains `false`.

## Exact next action

Perform a dependency-only ordinal implementation review. Select and pin one maintained penalized proportional-odds implementation; verify logit-link probability semantics, L2 objective scaling, slope-only penalty, convergence reporting and deterministic behavior without fitting project data. Then rerun this freeze audit. Until that succeeds, implementation and training remain prohibited.

STOP: Final Fit Contract was not frozen.
