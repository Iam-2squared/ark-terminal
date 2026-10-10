# Phase57 MSH-Entry LONG v1 — In-Repository Proportional-Odds Fit Contract Freeze

Date: 2026-09-16 JST  
Branch: `research/phase57-long-only-cash-equity`  
PR: #587

## Decision

`MSH_ENTRY_LONG_V1_FIT_CONTRACT_FROZEN`

The prior `NO_ACCEPTABLE_ORDINAL_DEPENDENCY` blocker is resolved by a small,
reviewed in-repository reference implementation. It translates the already
approved mathematical contract directly; it does not introduce a different
model family or an external ordinal package.

No Ark Terminal Project Data was fitted or predicted. Validation, OOS and EXIT
remain sealed. This freeze authorizes a later implementation/training phase; it
does not perform that phase.

## Frozen mathematics

For classes 0 through 4 and cutpoints `k=0..3`:

\[
\operatorname{logit}(P(Y\leq k\mid x))=\theta_k-x^T\beta
\]

The optimized objective is:

\[
-\sum_i \log P(Y_i\mid x_i)+\frac{1}{2}\lVert\beta\rVert_2^2
\]

The fixed regularization value is `lambda=1.0`. This is a stability penalty
under SUM NLL after training-prefix-only standardization. It was fixed without
Project Data performance comparison. Only slopes are penalized; cutpoints are
not.

Strict ordering exists throughout optimization:

- `theta0 = a0`
- `theta1 = theta0 + softplus(d1) + 1e-8`
- `theta2 = theta1 + softplus(d2) + 1e-8`
- `theta3 = theta2 + softplus(d3) + 1e-8`

Post-fit sorting, probability clipping and probability renormalization are not
used.

## Solver and fail-closed contract

- Runtime: Python 3.12, NumPy 2.3.5, SciPy 1.17.0
- Solver: `scipy.optimize.minimize`, `L-BFGS-B`
- `maxiter=2000`, `ftol=1e-12`, `gtol=1e-8`
- Initialization: zero slopes and deterministic empirical cumulative-frequency
  cutpoint logits
- Required diagnostics: success, status, message, nit, nfev, njev, objective

A fit is valid only when optimizer success is true, every parameter and the
objective are finite, all four cutpoints are strictly ordered, and the five
class probabilities are finite, nonnegative, and sum to one. Failure returns
`FIT_FAILED` and cannot create a promotable artifact.

## Synthetic mathematical verification

All required synthetic gates passed:

- five-class fit, four ordered cutpoints, finite parameters
- five finite nonnegative probabilities summing to one
- expected ordinal level monotonic in the known latent direction
- fixed L2 shrinks the slope norm
- objective checks prove that cutpoints are not penalized
- analytic gradient agrees with central finite differences; maximum absolute
  and relative error were both `1.4210819743176728e-9`, against `2e-5` gates
- repeated fits were bitwise identical for coefficients, cutpoints,
  probabilities and scores
- JSON save/reload predictions were exact
- missing-class and NaN/Inf inputs were rejected
- `maxiter=0` produced `FIT_FAILED` and no artifact

An independent objective calculation reproduced NLL `715.2641170439103`, L2
penalty `2.2946238074944785`, and total `717.5587408514049`.

For an unregularized synthetic cross-check, statsmodels OrderedModel 0.14.5
converged to the same model: maximum probability difference was
`2.0108394455098377e-7` and absolute NLL difference was
`8.503775461576879e-11`. statsmodels remains a temporary audit reference and is
not a repository dependency.

## Final fit and decision contract

- Mandatory core: Frozen Selector Ridge Score and Ridge Rank
- Optional features: none
- Decision Price: reference only
- Primary label: strict wall-clock +30m, same-session, complete continuous 5m
  path, future HIGH ordinal classes 0–4
- Labelable rows already established: 1,828 / 3,800 (48.11%)
- Unlabelable rows: exclude from fit/OOF; never map to class 0; retain ledger
- Supporting diagnostic: completed 5m CLOSE ordinal, separate from the label
- Class weights: unweighted
- CV: session-grouped, chronological expanding window, four fixed folds
- Score: `E[L] = 0P0 + 1P1 + 2P2 + 3P3 + 4P4`, range `[0,4]`
- Threshold candidates: `{1.0, 2.0, 3.0}` only
- State: `ENTER` or `SKIP_THIS_DECISION`; no WAIT or expiry

The contract SHA-256 is:

`64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938`

## Regression and protection results

- Synthetic Python tests: 18 passed
- Contract Node tests: 6 passed
- Predict tests: 2,694 passed
- Discovery tests: 26 passed
- RSS/capture tests: 89 passed, 2 third-party deprecation warnings
- Frozen Selector payload and Ridge artifact hashes: unchanged
- Project Data fit/prediction/CV/OOF/performance calls: 0
- Validation/OOS/EXIT/provider access: 0
- SHORT evaluations: 0
- All execution, broker, Excel/RSS order, live/paper trading, promotion,
  production-update and transmission flags: false

## Stop point

Stop after this freeze. The exact next action requires a separate explicit
instruction: wire the frozen Development inputs, fit only the 76-session
Development set, run the frozen chronological CV/OOF contract, and then perform
Development evaluation. None of those actions occurred here.
