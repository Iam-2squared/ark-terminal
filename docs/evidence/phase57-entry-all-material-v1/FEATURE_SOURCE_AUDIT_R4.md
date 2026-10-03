# Phase57 All-Material — Feature Source Audit R4

The dedicated overlap audit completed successfully in run 36000106394.

The previously audited 3,800-row feature export covers 76 sessions from 2024-09-17 through
2025-01-09. The frozen 2,155 Entry cohort is in 2025-05-30 through 2025-08-25. The overlap audit
found zero shared raw IDs and zero shared session-symbol keys. Therefore that legacy export cannot
be used to admit features into All-Material R1.

A better cohort-native source already exists in the committed repository:
`docs/evidence/phase57-entry-pattern-v2/ci-result/substrate`.

Its `p0-audit.json` is PASS with all144=true, previousCausal=true, todayPrefixCausal=true,
featureNoWHO=true and holdoutOpened=0. The producer creates each feature row from a current-session
prefix whose latest bar is asserted strictly earlier than the decision checkpoint. It persists
`rows.json.gz`, deterministic per-session matrices, `names.json`, source hashes and
`outcomes.json.gz`. The same substrate is already pinned by the 2,155 timing-signal census.

R1 consequence: stop trying to reuse the disjoint legacy export. Exact 2,155 feature coverage should
be built from this cohort-native substrate plus separately proven State/signal outputs. Conditional
families remain excluded until their exact source/known-at/coverage proof is frozen before fitting.

No performance outcome was used for this source disposition.
