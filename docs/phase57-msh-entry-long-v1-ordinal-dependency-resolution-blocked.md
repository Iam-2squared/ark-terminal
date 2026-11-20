# Phase57 MSH-Entry LONG v1 Ordinal Dependency Resolution Audit

**Decision: `MSH_ENTRY_LONG_V1_FIT_CONTRACT_BLOCKED`**

**Blocker: `NO_ACCEPTABLE_ORDINAL_DEPENDENCY`**

The dependency-only audit did not find one maintained, repository-compatible implementation that simultaneously provides the required proportional-odds logit model, native slope-only L2, unpenalized cutpoints, class probabilities, and a fail-closed convergence result. The model family, label, Core, CV, decision score, thresholds and state were not changed. No dependency was pinned and no Final Contract SHA was issued.

## Candidate comparison

| Candidate | Version / release | License | PO logit + 5-class probabilities | Slope-only L2 / unpenalized cutpoints | Convergence contract | Result |
|---|---|---|---|---|---|---|
| `statsmodels.OrderedModel` | 0.15.0 / 2026-08-27 | BSD-3-Clause | PASS; `F(theta[k+1]-xβ)-F(theta[k]-xβ)` | FAIL; no native regularized fit for `OrderedModel` | available only for its unregularized generic fit | reject |
| `mord.LogisticAT` | 0.7 / 2023-05-26 | BSD-3-Clause | probability form PASS; objective is All-Threshold margin surrogate, not ordered categorical likelihood | PASS; `sum(loss)+alpha/2||β||²`, thresholds excluded | FAIL; optimizer result is discarded and failed convergence is not surfaced | reject |
| `sklearn.LogisticRegression` | 1.8.0 | BSD-3-Clause | FAIL; binary/multinomial, not proportional odds | not applicable | not applicable | prohibited substitution |

Primary implementation evidence:

- [statsmodels 0.15.0 package metadata](https://pypi.org/project/statsmodels/0.15.0/) and [OrderedModel source](https://github.com/statsmodels/statsmodels/blob/v0.15.0/statsmodels/miscmodels/ordinal_model.py)
- [mord 0.7 package metadata](https://pypi.org/project/mord/0.7/) and [threshold implementation source](https://github.com/fabianp/mord/blob/master/mord/threshold_based.py)
- [scikit-learn LogisticRegression documentation](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html)

`statsmodels==0.15.0` is compatible on paper with the repository's Python 3.12, NumPy 2.3.5, SciPy 1.17.0 and pandas 2.2.3 pins. That compatibility does not repair the missing native L2 path. Adding a custom penalty/subclass would be a new implementation and is outside this audit.

`mord==0.7` imported and ran against the audited Python 3.12.14 / NumPy 2.3.5 / SciPy 1.17.0 / scikit-learn 1.8.0 runtime, but its package metadata does not declare a Python version and its latest source push was in 2023. More importantly, `threshold_fit` returns only coefficients and thresholds. It does not return `scipy.optimize.OptimizeResult`; `LogisticAT.fit` therefore cannot enforce convergence.

## Synthetic-only candidate test

No Ark project row was loaded. A deterministic 500-row, two-feature, five-class ordered synthetic dataset was used only to characterize `mord==0.7`.

| Check | Result |
|---|---:|
| finite fit / ordered four cutpoints | PASS |
| five finite nonnegative probabilities | PASS |
| maximum row-sum error | `1.11e-16` |
| expected level moves with fitted latent direction | PASS (`r=0.9885`) |
| fixed L2 slope shrink | PASS (`1.4929 → 1.4840`) |
| objective increment equals `alpha/2||β||²` | PASS |
| repeated fit exact determinism | PASS |
| class order 0–4 | PASS |
| pickle reload same probabilities | PASS |
| fail-closed convergence | **FAIL** |

The critical failure is concrete: a fit with `max_iter=0` returned normally, while the estimator exposed none of `success`, `status`, `message`, `n_iter`, or `converged`. Successful probability tests cannot satisfy the required convergence gate.

## Unchanged candidate fit contract

- Core: Frozen Selector Ridge score + Ridge rank; optional features none.
- Decision Price: reference only.
- Label: strict wall-clock +30m, same-session, complete-path future HIGH ordinal classes 0–4.
- Unlabelable: exclude from fit/OOF, never Class 0, retain audit ledger.
- Supporting diagnostic: completed 5m CLOSE ordinal kept separate.
- Model: one proportional-odds ordinal logistic model with logit link; no binary/multinomial fallback.
- Class weight: unweighted.
- CV: session-grouped expanding chronological folds `1–16→17–31`, `1–31→32–46`, `1–46→47–61`, `1–61→62–76`.
- Decision score: `E[L]=0P0+1P1+2P2+3P3+4P4`, range `[0,4]`.
- Threshold candidates: exactly `1`, `2`, `3`.
- State: `ENTER` or `SKIP_THIS_DECISION`; no WAIT/expiry.

## Conservation and safety

- Project Data fit calls: 0
- Project predictions / OOF / CV performance: 0 / 0 / 0
- Threshold performance: 0
- Validation new access: 0
- OOS new access: 0
- EXIT access: 0
- Market-data provider requests: 0
- SHORT evaluation: 0
- Frozen Selector and CURRENT Entry changes: 0
- Execution, broker, Excel/RSS order, live/paper, promotion, production, transmission, SHORT, margin and leverage remain false.

## Exact next action

STOP. Do not implement or train. A separate explicit architecture decision is required before allowing either a reviewed in-repository proportional-odds implementation or any relaxation of the native slope-only-L2 and fail-closed convergence requirements.

