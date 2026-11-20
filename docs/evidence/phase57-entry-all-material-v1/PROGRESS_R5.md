# Phase57 All-Material R5

The cohort-native source audit was extended without fitting or candidate selection.

- Entry-pattern substrate p0 audit: PASS; all144=true; todayPrefixCausal=true;
  previousCausal=true; featureNoWHO=true; holdoutOpened=0.
- State-v3 causality audit: PASS; population=2,155; State decisions=14,906;
  future-bar violations=0; T0 classification coverage=100%.
- Timing-signal completion: 65,910 causal signal decisions; future-pivot violations=0;
  completed census regeneration is deterministic; holdoutOpened=0.
- State checkpoints and minute-census files are committed and pinned by manifests.
- The old 3,800-row feature export remains unusable for the current cohort because overlap is zero.

These committed cohort-native sources are sufficient to replace the disjoint legacy-export route.
The unresolved dependency is now the exact joined-column coverage/missingness table before any fit.
