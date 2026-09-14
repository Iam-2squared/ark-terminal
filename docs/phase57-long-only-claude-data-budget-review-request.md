# Claude independent review request — Phase57 LONG-only Data Budget

You are the independent adversarial reviewer for Ark Terminal Phase57 LONG-only Cash Equity research. Do not endorse the Ark proposal by default. Search actively for reasons it could waste scarce J-Quants data, contaminate holdouts, leak future information, or create an invalid LONG Momentum / Continuation result. Separate facts, inferences, and recommendations. Do not use Ark's existing LONG+SHORT performance as evidence that this design is sound.

## Non-negotiable research boundary

- Japanese cash equities, LONG only.
- Margin buying, short selling, SHORT positions, leverage, live/paper order transmission are prohibited.
- Existing LONG+SHORT selector, Lane Y, MSH Entry, EXIT, allocation and live circuitry remain frozen.
- No new J-Quants Historical request has been authorized.
- The acquisition gate must remain closed until your review is received and every critical blocker is resolved.

## Objective and research sequence

1. L0 Opportunity Census: count point-in-time eligible Prime/Standard/Growth domestic common equities returning at least +3%, +5%, +10% per session; report count and eligible-universe rate distributions.
2. L1 Early Winner Discovery: at 09:30, 10:00, 10:30, 11:00, 11:30, 13:00 and 14:00 measure recall of eventual winners, remaining upside, future MFE/MAE, time-to-detection and late-detection rate.
3. L2 LONG Selector: compare predeclared target definitions and ablatable feature families, then freeze candidate and threshold.
4. Validation, Validation Confirmation, Untouched OOS, Final Confirmation and prospective Fresh.
5. Only after selector evidence, connect frozen LONG Entry/EXIT/allocation and evaluate a cash-constrained 100-share-lot portfolio with zero SHORT contribution.

Future session outcomes are labels only. They must never enter point-in-time selector features.

## J-Quants facts currently recorded

| Item | Recorded fact |
|---|---|
| API | v2, `x-api-key` |
| Daily | `/v2/equities/bars/daily` |
| Minute | `/v2/equities/bars/minute`; TSE only; past two years; absent when no trade |
| Master | `/v2/equities/master`, dated point-in-time query supported |
| Pagination | replay identical query with returned `pagination_key` until absent |
| Plan depth | Free 2 years delayed; Light 5; Standard 10; Premium 20 |
| Rate limits | Free 5, Light 60, Standard 120, Premium 500 requests/minute |
| Minute add-on | planning limit 60 requests/minute |
| Account evidence | Repository records user-attested Light + minute/tick add-on on 2026-09-10, scheduled to end 2026-10-06; current account screen was not authenticated, so current entitlement and storage/deletion terms require operator re-attestation |

Do not assume the recorded subscription is still active merely because it was active four days earlier.

## Repository and artifact audit

The earlier statement “current J-Quants implementation is TDnet only” was true only for `main` and was incomplete for the repository as a whole. Historical research branches contain reusable minute/master/daily acquisition, pagination, point-in-time filtering, sparse 1m→5m aggregation, timestamp-boundary handling, checksums and safety code.

An exact metadata inventory covers 487 sessions from 2024-09-10 to 2026-09-09. Of these, 205 have metadata-only exposure with outcomes and future labels uninspected; 179 were exposed in prior research. For 205 audited sessions, minute required 2,899 pages; daily and master required one page per session. Across 384 sessions with row metadata, minute rows averaged about 453,524 per session. Raw provider responses and reconstructable 5-minute data were not persistently retained. Old short-lived GitHub Actions acquisition shards have expired. Therefore code, metadata, checksums and split identifiers can be reused, but formal price payloads cannot.

## Proposed dataset split

This proposal preserves the existing outcome-blind higher-level allocation and only subdivides its 90 Development sessions without viewing outcomes.

| Block | Sessions | Dates | Permitted use | Model selection | Threshold selection | Final performance claim |
|---|---:|---|---|---|---|---|
| Development A | 30 | 2024-09-10–2024-10-24 | L0 definition, initial census | No | No | No |
| Development B | 20 | 2024-10-25–2024-11-22 | L0 replication, L1 label feasibility | No | No | No |
| Development C | 20 | 2024-11-25–2024-12-20 | L1 ablation, L2 fitting | Yes | No | No |
| Development D | 20 | 2024-12-23–2025-01-24 | inner temporal selection and threshold freeze | Yes | Yes | No |
| Validation | 30 | 2025-01-27–2025-03-11 | one frozen evaluation | No | No | No |
| Validation Confirmation | 25 | 2025-03-12–2025-04-14 plus 2026-06-12/15 | second frozen check | No | No | No |
| Untouched OOS | 30 | 2026-06-16–2026-07-28 | one-time outer evaluation | No | No | Yes |
| Final Confirmation | 30 | 2026-07-29–2026-09-09 | final historical confirmation | No | No | Yes |
| Fresh prospective | target 25 | no earlier than 2026-09-10; exact dates not yet frozen | prospective final confirmation | No | No | Yes |
| Prior-exposed diagnostic | 179 | 2025-04-15–2026-01-07 | source/parity diagnostics only | No | No | No |

No sealed block may be opened merely because an earlier block failed. A failed candidate must be versioned; any already viewed validation block becomes development for that successor, and a new untouched block is required.

## Data budget

The formal L0 needs daily OHLCV/adjustment fields plus dated master only. It must not download minute data.

| Scenario | Sessions | Estimated eligible symbol-sessions | API requests/pages | Minute rows | Notes |
|---|---:|---:|---:|---:|---|
| 252-session daily what-if | 252 | 932,400 | 504 = 252 daily + 252 master | 0 | 0.34–0.75 GB uncompressed JSON planning band; 12–20 min on Light planning rate |
| Clean allocation daily layer | 205 | 758,500 | 410 | 0 | acquisition remains blocked |
| Development intraday, only after L1 authorization | 90 | JPX-wide | 1,188 minute pages + 180 daily/master = 1,368 | 37,903,800 observed previously | about 5.46 h sequential or 0.9–1.4 h with six bounded shards |
| All clean intraday upper bound | 205 | JPX-wide | 2,899 minute pages + 410 daily/master | 92,131,136 | explicitly prohibited as an upfront acquisition |

Sizes are planning bands because previous raw responses were not retained. Exact bytes must be recorded from authorized immutable responses, without a disposable probe against a new research session.

## Intraday conservation proposal

Use two tiers:

1. Case-control data may support feature feasibility, mechanism ablation and error analysis: all daily winners, near-winners, high-volume non-winners, sector/segment/ADV-matched controls, and seeded random liquid controls. Sampling probabilities and inverse-probability weights must be recorded. Case-control data cannot support population precision, prevalence, threshold calibration or a performance claim.
2. Full point-in-time cross-sections are mandatory for Early Winner Recall, precision, cross-sectional ranks, market/sector breadth, threshold calibration, portfolio opportunity cost, Validation and every outer evaluation. Session selection may use only frozen calendar rules or prior-day causal regime attributes, never same-day opportunity density.

The current preferred acquisition shape is date-wide only for an explicitly released partition, cached once in private encrypted user-only storage, then causally aggregated to 5-minute bars. Winner-only training and winner-only evaluation are prohibited.

## L0 contract to challenge

- Universe: TSE Prime/Standard/Growth domestic common equity, point-in-time; exclude ETFs/ETNs/REITs/preferred/foreign/PRO Market unless separately predeclared.
- Key: session date + code.
- Primary return: adjusted close at t divided by adjusted close at t−1 minus one.
- Preserve raw close, adjustment factor and ex-rights type for audit.
- Report both counts and rates over the eligible universe.
- Treat IPO/no-previous-close, zero-volume/suspension, null OHLC, limit-up/special quote and corporate-action cases as explicit strata or fail-closed states, never silently delete them.
- Regime extension may only use a predeclared prior-day-causal TOPIX/volatility rule.

## Questions requiring an adversarial answer

1. Is 90 clean Development sessions enough for L0/L1/L2, given the number of symbol-sessions but strong within-session cross-sectional dependence? State effective sample-size concerns.
2. Is the 205-session clean split scientifically preferable to a 252-session design, or does its large 2025-04 to 2026-06 gap create unacceptable regime/seasonality bias?
3. Should L0 inspect all four Development blocks, or would that prematurely consume blocks needed for L1/L2 hypothesis confirmation?
4. Are 30 Validation, 25 Validation Confirmation, 30 OOS and 30 Final sessions sufficient for stable session-level uncertainty intervals and regime claims?
5. Does reusing a split created for earlier EXIT research cause selection bias even if outcomes were not accessed? What proof is required to call it outcome-blind?
6. Does the prior 179-session exposure contaminate adjacent clean sessions or human expectations enough to require embargoes wider than one session?
7. Is daily adjusted-close return the correct L0 opportunity definition? Address dividends, splits/reverse splits, rights, prior-close conventions, IPOs, limit-up states and tradability.
8. Does dated master fully solve survivorship and segment-history bias? Identify delisting, code change, market transfer and product-category edge cases.
9. Are the L1 labels well defined at every decision time? Specify exact MFE, MAE, remaining-upside, late-detection and winner denominators, including lunch and closing-auction treatment.
10. Can case-control sampling recover useful feature conclusions without distorting continuation probability and calibration? Specify valid estimands and weighting diagnostics.
11. Is JPX-wide date retrieval truly more data-efficient than code/date sampling once request rate, pagination, storage, cross-sectional breadth and repeated controls are considered?
12. Which L2 feature families require full-market intraday state at the same timestamp, and which can be developed safely from sampled symbols?
13. What corporate-action and historical trading-hours joins are mandatory before any cross-session feature is valid?
14. Where can future leak enter through daily winner preselection, volume normalization, VWAP, market breadth, universe membership, adjustment factors, missing-bar handling or session selection?
15. How should multiple target, horizon, feature, model and threshold trials be logged and corrected so that Validation/OOS are not indirectly optimized by humans?
16. What predeclared falsification criteria should stop L1 or L2 because opportunity is too sparse, detected too late, too illiquid, too concentrated or too regime-dependent?
17. Is the storage/manifest contract sufficient for provider corrections, pagination non-snapshot consistency, reproducibility and deletion obligations?
18. Propose a materially more data-efficient design if one exists, with a request/page/row budget and the statistical claims it can and cannot support.

## Required response format

Return these sections in order:

1. Verdict: `PASS`, `PASS WITH CHANGES`, or `BLOCKED`.
2. Critical blockers — each with evidence, failure mode and required remediation.
3. Major and minor concerns.
4. Bias/leak table covering future leak, selection, survivorship, corporate actions, regime, missingness and human OOS overfitting.
5. Recommended split table with exact session counts and opening rules.
6. Recommended L0 and intraday budgets with request/page/row estimates.
7. Required label and feature-contract changes.
8. Falsification/stop criteria.
9. Acquisition Gate checklist: mark every item PASS/BLOCKED and state whether any J-Quants acquisition may begin.

Do not propose opening Validation, OOS, Final or Fresh to answer uncertainties. Do not infer the user's current subscription from old repository evidence. Prefer a smaller defensible design, but do not trade away the all-market denominator required for a deployable JPX-wide selector.
