# Phase57 LONG-only Candidate Eligibility Contract — 2026-09-16 JST

Status: **FROZEN BEFORE ELIGIBILITY-AWARE MEASUREMENT**  
Contract ID: `ELIGIBILITY-MEASUREMENT-1`  
Parent measurement contract: `CORRECTED-MEASUREMENT-1` at `20356553ddece7309a6a00654c3b1e276d1a3466`  
Source repository state: `43eea3391491005c1a6be06081952e0e912b5cd1`

## Question fixed before measurement

Does the saved Corrected-Measurement C+D Ridge retain material Decision Price to same-session Future +3% and +5% enrichment when causal price freshness is applied before ranking, so that ranking and evaluation begin from the same observable candidate universe?

This run may assess whether Ridge is a Selector Freeze Candidate. It may not freeze the Selector automatically.

## Inputs and boundaries

- Use saved Development only. Expected available sessions: 76; four previously unavailable Development A sessions remain unavailable.
- Reuse only the immutable artifacts already allowlisted by `CORRECTED-MEASUREMENT-1`:
  - L0 base run `34917676944`
  - L1 Minute run `34926225832`
  - C+D Minute run `34936002178`
  - additional Development Minute run `34964031692`
  - saved C+D Ridge run `34944665187`
- Reuse the saved Ridge artifact SHA-256 `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb` and its existing scores.
- Do not fit or tune any model. The historical C-only v1 weights/scores remain unavailable; call the evaluated model `ELIGIBILITY_AWARE_RIDGE_SAVED_CD`, not original v1.
- Feature universe, target, model weights, Ridge alpha, decision timestamps, PIT universe, score tie-break, Top N, Corporate Action treatment, and corrected measurement semantics remain unchanged.
- Validation and every OOS partition remain sealed.
- Provider requests, fit calls, new features, new targets, Candidate v3, Candidate v2 retest, Entry/EXIT/Allocation, old selectors, News/Event, and trading are forbidden.

## Causal eligibility rule

For each `(sessionDate, decisionTimestamp, symbol)` row, eligibility is determined before ranking using only information available at the decision timestamp.

1. Find the latest accepted market-price observation whose availability timestamp is at or before the decision timestamp.
2. Its wall-clock age must be in `[0, 5]` minutes inclusive.
3. The price must be finite and strictly positive.
4. Otherwise mark the row `INELIGIBLE_NO_FRESH_DECISION_PRICE`.
5. Do not forward-fill beyond five minutes, interpolate, use a future bar, or substitute another price.
6. The five-minute limit is fixed from market-data semantics and must not be changed after results are observed.

The eligible candidate universe at each decision timestamp is exactly the rows satisfying this rule. The saved Ridge score ranks only this eligible universe. Sort score descending with the existing deterministic symbol ascending tie-break. Select `K=min(5, eligible N_t)`; do not replace a selection after observing future-outcome availability.

Future-path presence is an evaluator property and is not allowed to determine causal ranking eligibility. Any selected row lacking a future path must remain selected, be reported as evaluation unavailable, and be classified by reason.

## Outcome and metric rules

- Primary opportunity: future continuous 5m High from Decision Price through same-session end.
- Primary KPI: Future +3% Precision@5.
- Stretch KPI: Future +5% Precision@5.
- Secondary confirmation: future continuous 5m Close or terminal-auction Close reaches +3%/+5%.
- Strict 30m return: corrected wall-clock `t+30m` definition from `CORRECTED-MEASUREMENT-1`.
- MFE: `max(0, maximum future return from Decision Price)`.
- MAE: `min(0, minimum future return from Decision Price)`.
- Overnight carry is prohibited.
- Precision denominators and outcome coverage must be explicit. If every eligibility-selected row has a same-session future evaluator path, evaluable precision and all-selected precision are identical.
- Recall and unconditional prevalence use the same pre-ranking eligible universe.
- Random expected hits preserve each decision timestamp: opportunity count in timestamp `o_t`, eligible count `N_t`, and slots `K_t=min(5,N_t)` give `sum(o_t*K_t/N_t)`. Derive random recall, precision, and lifts from these timestamp-level expectations.

## Fixed reports

Report once, without result-driven additions:

1. Pre/post eligibility counts and coverage.
2. Pre/post Market, Liquidity, current-return, and decision-volatility distributions.
3. Eligible count and selected Top5 count.
4. Future +2/+3/+5 High precision, recall, prevalence, same-timestamp random expectation, recall lift, and precision lift.
5. Future +3/+5 Close-confirmed precision.
6. Strict wall-clock 30m mean, median, positive rate, MFE, and true MAE.
7. Same-session MFE/true MAE and time to +3%/+5%.
8. Positive sessions.
9. Prime/Standard/Growth and Low/Mid/High diagnostics: eligible N, selected N, High +3/+5 precision, strict-30m return, and true MAE.
10. Outcome coverage for session opportunities and strict 30m; reasons for selected unavailable outcomes.
11. Reference comparison with the post-ranking-freshness result from run `34985364169`, with semantic differences stated.
12. `FREEZE CANDIDATE SUPPORTED` or `NOT READY`, followed by exactly one next-research recommendation and STOP.

No segment-specific model, threshold, eligibility rule, or policy may be created from these diagnostics.

## Workflow safety and publication

- Contract documentation must be committed before measurement implementation.
- The measurement implementation must use a dedicated path-scoped workflow with no provider client and no model fitting.
- Any automatically triggered L2 development, capacity, missed-opportunity, Candidate v2, Entry/EXIT, or other research job must fail closed or be skipped. If an unexpected training/refit job runs, stop and exclude its output.
- Private raw and row-level data must be purged before artifact upload. Upload aggregate evidence only.
- The measurement executes once. A rerun is permitted only to repair a mechanical execution/reporting error without changing this contract, ranking, score, threshold, or metric semantics.

## Safety invariants

`executionAllowed=false`, `brokerWriteAllowed=false`, `excelOrderWriteAllowed=false`, `rssOrderFunctionAllowed=false`, `liveTradingAllowed=false`, and `paperTradingAllowed=false`.

Lane Y, `main`, and all live circuits remain untouched.

## Stop boundary

After the aggregate eligibility-aware Ridge result and Freeze-Candidate verdict are reported, stop. Do not automatically freeze, open Validation/OOS, change Top N, retrain, or begin Entry/EXIT integration.
