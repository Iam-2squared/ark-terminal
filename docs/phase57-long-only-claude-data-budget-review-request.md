# Phase57 LONG-only — Claude Independent Review Request

Status: COMPLETED / REVIEW RECEIVED 2026-09-15 JST

This file preserves the independent-review request that was sent to Claude before J-Quants acquisition. The review returned `CONDITIONAL GO` and has been dispositioned in:

`docs/phase57-long-only-independent-review-disposition-v1.md`

## Review scope that was requested

Claude was explicitly asked to act as an adversarial Independent Reviewer rather than endorse Ark's plan. The requested review covered:

- L0 -> L1 -> L2 research ordering;
- J-Quants Daily / Minute / Master data budget;
- Development / Validation / OOS / Fresh separation;
- reserve / contingency design;
- purge / embargo;
- winner / control sampling bias;
- full-cross-section requirements;
- survivorship and corporate actions;
- minute-data conservation;
- human overfitting after Validation inspection;
- Fresh prospective design;
- liquidity and cash-equity constraints;
- the risk that apparent LONG momentum edge is actually microstructure, auction, regime or liquidity artifact.

## Key questions posed

1. Is the LONG-only problem definition itself valid?
2. Is Daily + PIT Master sufficient for L0?
3. How much clean historical data should be spent on Development?
4. Should there be a reserve, and how should it be deployed without performance bias?
5. What purge / embargo is actually required?
6. How should minute data be acquired without winner-only contamination?
7. Which stages must use the full JPX point-in-time cross-section?
8. How should Validation/OOS be protected from human retuning?
9. Is the existing Validation / Confirmation / OOS / Final structure redundant?
10. What is the smallest data plan that still supports a credible integrated Selector -> Entry -> EXIT -> Allocation portfolio test?

## Review result

Claude returned `CONDITIONAL GO` and identified four principal blockers:

- reserve = 0;
- L0-to-L2 outcome-hypothesis risk;
- minute winner-bias risk;
- undefined purge / embargo.

It also raised major concerns about Development size, Validation role ambiguity and redundant final confirmation.

Ark then independently audited the review rather than adopting it verbatim. The accepted, modified and rejected points are frozen in the disposition document cited above.

## Important note

The original long-form prompt is intentionally replaced by this archival summary now that the review has been completed. Future Claude requests should target the next frozen research milestone rather than re-running the same design review.
