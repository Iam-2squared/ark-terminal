# Candidate C robustness / freeze audit method

Date: 2026-09-18 JST
Source HEAD: `52c2a11b3f38b1f3d1e4146a0e42b18a0748beda`
PR #587 remains Draft/unmerged.

This is an audit, not another EXIT candidate. A/B/C policy bytes, their contracts,
Selector, Entry, and existing evidence must remain unchanged. The original
Candidate C Development workflow `35313475902` is preserved, not rerun manually.

## Timing and provenance

This method is recorded after static inspection identified possible first-arm-bar
signals and an INITIAL ledger route/result inconsistency, but before this audit's
new batch measurements. It is not an independent preregistration or OOS result.
No thresholds are selected from its results.

## Fixed checks

- Reproduce the existing Candidate C cohort mean/PF/p05 and legacy +3/+5 counts.
- Retain the original C gates against A: mean/PF/p05 non-worse, +3/+5 >=90%,
  and evaluator-only adverse 106/21 mean non-worse.
- Inherit A's robustness method without retuning: the same chronological
  19-session blocks, >=3/4 nonnegative mean deltas vs Fixed12 in each cohort;
  excluding each cohort's top three frequency symbols, mean delta vs Fixed12 >=0.
  Report deltas vs A too, without selecting another block layout or exclusion.
- Report each block/cohort's mean/PF/p05, symbol concentration, and adverse identities.
- Check source blobs, saved input SHA256 pins, unique anchor/cohort identity,
  PIT Entry-source identity, and exact selected-route ledger consistency.
- The existing C contract says LATER completed CLOSE after first +2 or +3 observation.
  A signal on the first observed arm bar fails contract conformance. Test direct
  +2, direct +3, and +2-to-+3 promotion; do not repair or reinterpret the policy.
- An OPEN exit does not capture a HIGH reached later in that bar. Retain legacy
  counts and separately report time-ordered counts, accepting an equal-bar touch
  only when the exit OPEN already reaches the level. Fixed12 CLOSE semantics
  remain exact and can include that completed bar's HIGH. Apply the existing 90%
  preservation floor to the time-ordered counts; this is a causal measurement audit,
  not a new policy or threshold.
- Check next-regular-OPEN ordering and perturb fill-bar future H/L/C without
  changing its OPEN to verify those future values cannot change the EXIT decision.
- Regenerate the new audit twice into fresh temporary directories and compare
  summary, detailed ledger, and manifest bytes. Never overwrite previous evidence.

The INITIAL effective-route projection in the audit is explicitly derived from
unchanged Candidate A. It is not a repair to Candidate C's stored ledger.

## Terminal decision

All checks PASS: freeze-ready only, pending explicit freeze attestation; no promotion.
Any FAIL: `NEW_LONG_EXIT_CANDIDATE_C_KILL`; preserve the existing Candidate A freeze
artifact as fallback, without claiming this audit revalidates or promotes A.
Record findings, stop, and do not create a repaired C or Candidate D/E.

## Execution scope

Only existing saved Development data; no Fresh/OOS, 1m research, providers,
model fit/prediction, Capital/Portfolio tuning, runtime integration, main merge,
broker/RSS/Excel writes, paper/live trading, or automatic promotion.
All existing trading/write/promotion flags remain false. GitHub CI has contents
read permission only. The new audit writes exclusively to new temporary outputs.
