# Entry / EXIT Development reuse contract

The same 144 authorized sessions remain Development for future Entry/EXIT work. No Common Holdout244, REPORT19, Validation, OOS or Fresh payload access is authorized. Prior Exposure Ledger remains intact.

For every decision, rebuild sparse Dictionary features from strictly prior information, including raw observations, security master, peer prior, normalization, shrinkage, drift, sample confidence and temporal reliability. Require computedThrough < decisionTime and artifact availableAt <= decisionTime. Daily observations require the prior closed session; intraday observations require closed bars available before the decision and Reader freshness/session semantics. Preserve definitionHash, source hashes and artifact timestamps.

Temporal reliability computed using a future validation target must never be attached to earlier decisions. Missing historical reliability is UNAVAILABLE, not a copied final PASS. Full144 final snapshots, final H/M membership and survivor identity cannot be backfilled into past rows. Prior cohort/registry decisions based on later Development are ex-post research choices, not historical availability evidence.

For any claimed walk-forward or out-of-fold comparison, trait selection and learned Dictionary/calibration/normalization artifacts must be refitted or frozen using that fold's past training data only. Future labels are evaluator-only. Reusing Development is not independent out-of-sample evaluation. Persist decisionTime, computedThrough, availableAt and training cutoff so these conditions can be checked mechanically.

Future feature materialization must pass future-poison/prefix-invariance, missing-artifact, availability-boundary, security identity and deterministic regeneration tests before Entry/EXIT training. This task tests underlying past-source invariance and documents the downstream contract; it does not claim an Entry/EXIT feature pipeline has been built or certified.

Frozen Selector, old registry/Gate/Evidence, Capital Allocation and execution paths remain unchanged. All safety flags false. No Entry/EXIT implementation/training and no main merge in this task.
