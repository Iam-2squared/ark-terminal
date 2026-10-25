# Phase57 Nine-State Entry Audit — Exposure Ledger R1

2026-09-23 JST / Draft PR #587 / Development-only research.

This ledger is append-only and records outcome/evaluator exposure that affects the interpretation of later semantic reviews. It does not change any classifier, Entry rule, label, threshold or data split.

## E1 — REBOUND

REBOUND semantic review was fixed before sealed baseline scoring and before the new 15% completion target was introduced. The 34-case blind review was therefore valid under the recorded masking protocol. After the review was frozen, REBOUND aggregate evaluator anatomy was inspected. This is permitted for post-review diagnosis and does not retroactively contaminate the fixed semantic review.

## E2 — RISE aggregate exposure before its semantic review

While locating the REBOUND block in the existing Development `baseline-comparison.json`, aggregate RISE State-v3 evaluator metrics were displayed before the dedicated RISE blind semantic review had been completed. Individual Opportunity identities and individual future outcomes were not inspected, but State-level aggregate EntryPosition / Fill / horizon metrics were exposed.

Disposition: the forthcoming RISE chart review may still use masked case identities/labels and prefix-only inputs, but it MUST NOT be represented as fully outcome-blind. Report it as `AGGREGATE_OUTCOME_EXPOSURE_CONTAMINATED_SEMANTIC_REVIEW`. Do not change the fixed sample after seeing aggregate metrics.

## E3 — RANGE aggregate exposure before its semantic review

During the same Development file inspection, aggregate RANGE State-v3 evaluator metrics were displayed before RANGE semantic review. Individual identities/futures were not inspected.

Disposition: any later RANGE semantic review must carry the same `AGGREGATE_OUTCOME_EXPOSURE_CONTAMINATED_SEMANTIC_REVIEW` qualification. Sampling must remain prefix-only and precommitted; no attempt may be made to reconstruct blindness by re-splitting the same Development data.

## Unexposed semantic-review states at this checkpoint

No state-level outcome/anatomy metrics were intentionally inspected for SHARP_RISE, DROP, PULLBACK, SHARP_DROP, DROP_STOP or RISE_STOP during this incident. Their future semantic packets must remain outcome-blind until review decisions are frozen. If subsequent exposure occurs it must be appended here before interpretation.

## Research boundary

All 2,155 Opportunities are already outcome-exposed Development globally; this ledger is specifically about preserving honest ordering claims for the new semantic chart audits. It does not convert any subset into Fresh/OOS. Protected Validation/OOS/Fresh/Prospective data remains unopened.
