# Development pre-outcome checkpoint

This is NOT a fitted model, Development measurement, or Claude review-ready packet.

## Frozen scope

Exactly 58 sessions from the existing full-source-parity precommit: Reserve121–149
and151–179, 2025-10-09 through2026-01-07. Purge2025-11-21 is excluded.
Dates are copied from committed evidence, never generated from a calendar.
Formal-recovery provenance identifies allocation artifact10041559531 and its
original JSON SHA295466a4d29eb48ad8926d60cb1ceb03962aeb63e136a3c9758afabba2b70a95.
Ordinal assignment follows the two explicit29-session original allocation blocks.
The user-supplied aggregate original independently hashes to
cb6dacddd6d9088598ba8d174976ee4b57ffa2b9956e5c7c884e01d0b83b03b9.
Source parity remains PASS; rawPersisted=false is not an archive failure claim.

The separate Allocation and Fit manifests preserve the existing10-feature,
target5bps/net+3, and state contracts byte-for-byte by reference. Existing source
contracts are not rewritten to erase their historical no-training authorization.
Development outcome access has not occurred at this checkpoint. Do not mark USED
until actual outcome access is appended to the access ledger.

## Single precommitted fitting recipe

Shared weighted L2 Logistic; lambda0.01; unpenalized intercept; fold-training-only
weighted mean/population-standard-deviation; no class rebalancing or imputation.
Observation weights equalize session then symbol-session then paired event mass.
Four expanding folds have26/34/42/50 training sessions, one embargo session each,
and seven evaluation sessions each. No within-fold session overlap. OOF results
used for threshold selection are Development selection-biased, not untouched OOS.
Thresholds are0.50/0.55/0.60 only; the manifest fixes admissibility and selection.
No admissible candidate means NO-GO, not a new grid or a new model.

## Implemented and unimplemented

Implemented: exact-session/contract verifier, fold partitioning and deterministic
weighted Newton solver. Synthetic convergence and failure tests are not market
performance evidence. Existing real-artifact inference and Validation remain
fail-closed; the numerical solver does not bypass those guards.

The subsequent First Development Fit workflow connects source reconstruction,
immutable hashes, frozen Hybrid replay, all-event feature fingerprints, a global
58-session feature barrier, labels, weighted Logistic, stateful OOF evaluation,
the fixed threshold rule, candidate freeze and a review JSON packet. Its existence
is not evidence of a successful real-data run. Check that run's results separately.
The workflow has no Fresh Validation or OOS job, and no broker integration.

No source-recovery investigation is required merely to redo the PASS gate.
The remaining work is execution/integration, not a claimed new data-integrity failure.
No historical model fit or market performance has been produced in this checkpoint.

Reserve92–120 and180–282 and all Fresh reservations remain outside permitted inputs.
All9 safety flags stay false. No changes to main, #579, #572, Selector or P21.
Fresh Validation and OOS remain closed even after a future successful Development fit.
