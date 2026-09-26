# Phase57 LONG-only Top5 Hit Distribution Contract — 2026-09-16 JST

Status: **FROZEN BEFORE DIAGNOSTIC IMPLEMENTATION**  
Contract ID: `ELIGIBILITY-TOP5-HIT-DISTRIBUTION-1`  
Parent eligibility contract: `ELIGIBILITY-MEASUREMENT-1` at `2998675a217317e4658272129d8759f16d11cc7e`  
Source repository state: `667566b5562bddb09af83b18de2c800ddba2bb48`

## Fixed question

For the unchanged eligibility-aware saved C+D Ridge Top5, how many of the five selections at each decision timestamp subsequently reach +1%, +2%, +3%, and +5% from their causal Decision Price before the same session ends?

This is the last Development-only Selector diagnostic before a user Freeze decision. It may return `FREEZE READINESS CONFIRMED` or `FREEZE READINESS CONCERN`; it must not formally freeze or modify the Selector.

## Immutable inputs and prohibitions

- Reuse saved Development inputs and the exact artifacts allowlisted by `ELIGIBILITY-MEASUREMENT-1`.
- Reuse saved Ridge artifact SHA-256 `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb` and existing saved score.
- Use model identity `ELIGIBILITY_AWARE_RIDGE_SAVED_CD`.
- Fit calls and provider requests are zero. No new J-Quants retrieval is permitted.
- Do not change model, weights, Ridge alpha, feature universe, target, decision timestamps, PIT universe, tie-break, Top N, Corporate Action treatment, or eligibility.
- Do not rerun Candidate v2, create Candidate v3, open Validation/OOS, compare old selectors, or begin Entry/EXIT/Allocation.
- Do not create any result-driven time, market, liquidity, volatility, threshold, or capacity filter.

## Ranking and evaluator semantics

- Eligibility is fixed before ranking: latest causally available accepted market price at or before the decision timestamp, finite and positive, with wall-clock age in `[0,5]` minutes.
- No forward-fill beyond five minutes, interpolation, or future-bar eligibility.
- Rank only the eligible universe by saved Ridge score descending, then symbol ascending; select `K=min(5,N_t)`.
- Repeated symbols across decision timestamps are allowed and evaluated independently from each timestamp's own Decision Price.
- Primary outcome: same-session future continuous 5m High reaches Decision Price +1%, +2%, +3%, or +5%.
- Secondary confirmation: future continuous 5m Close or terminal-auction Close reaches the same threshold.
- Overnight carry is prohibited. A missing evaluator path remains unavailable after selection and must never alter ranking.

The +1% fields are evaluator-only additions computed from the same already-saved future path. They are not a target, feature, label used for fitting, or policy change.

## Fixed decision-time groups

The ten existing decision timestamps are grouped before results are observed:

- `MORNING`: `09:30`, `10:00`
- `LATE_MORNING`: `10:30`, `11:00`, `11:30`
- `AFTERNOON`: `13:00`, `13:30`, `14:00`, `14:30`, `15:00`

These groups are diagnostic only and cannot change the Selector.

## Fixed measurements

For High-touch thresholds `1,2,3,5`, report:

1. Precision@5, selected hits, eligible opportunity count and prevalence.
2. Same-timestamp random expected hits/recall/precision, actual recall, recall lift, and precision lift.
3. Per-decision Top5 hit counts `0,1,2,3,4,5`, their decision counts and percentages.
4. Mean and median hits per Top5, `P(hits>=1/2/3/4)`, and `P(5/5)`.
5. Time to first High hit: N, P25, median, P75, P90 and fixed buckets `<=15`, `16-30`, `31-60`, `61-120`, `>120` minutes.

For Close-confirmed thresholds `1,2,3,5`, report Precision@5, mean hits per Top5, `P(hits>=1/2/3)`, `P(5/5)`, and the same time-to-hit summary when available.

For each fixed time group, report threshold Precision@5, mean hits per Top5, and `P(hits>=1)`.

For `PRIME/STANDARD/GROWTH` and `LOW/MID/HIGH`, report selected N, evaluable N, and threshold Precision@5. Segment-specific models or rules are forbidden.

All-selection lower bounds and evaluator coverage must remain explicit. Random expectation preserves each decision timestamp: with eligible count `N_t`, opportunity count `o_t`, and slots `K_t=min(5,N_t)`, expected hits are `sum(o_t*K_t/N_t)`.

## Readiness interpretation

- `FREEZE READINESS CONFIRMED`: strong monotone threshold enrichment remains, +3/+5 decision-level hits are broadly present, Close confirmation retains material edge, and no single fixed time/market segment explains the result.
- `FREEZE READINESS CONCERN`: material edge depends on sparse decisions, transient High touches, one time/market segment, or loses meaningful lift under the unchanged evaluator.

No numeric acceptance threshold may be invented after observing the result. The verdict is a diagnostic restatement of the already-supported Freeze Candidate, not a new optimization gate.

## Workflow and safety

- Commit this contract before implementation.
- Use a dedicated path-scoped measurement workflow with no model library, fit path, or provider client.
- Any unexpected L2 training, Capacity, Missed Opportunity, Candidate v2, Entry/EXIT, or unrelated refit must fail closed; exclude its output and stop.
- Purge private row-level inputs before uploading aggregate evidence.
- Execute once and report. A rerun is allowed only for a mechanical failure without changing this contract.
- `executionAllowed`, `brokerWriteAllowed`, `excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`, and `paperTradingAllowed` remain false.
- Lane Y, `main`, and live circuits remain untouched.

## Stop boundary

After reporting `FREEZE READINESS CONFIRMED` or `FREEZE READINESS CONCERN`, stop for the user's formal Freeze decision. Do not freeze automatically or proceed to Validation/OOS or Entry/EXIT.
