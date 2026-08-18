# Phase57 P25.3D — Autonomous Lineage-Pinned Evidence Evaluation

P25.3D connects the immutable evidence prepared by P25.3C to the already-frozen P25.2I end-to-end evaluator without adding a new performance-selection step.

The new evaluation layer reconstructs the evidence lineage before evaluation and fails closed unless the rebuilt P25.3B manifest head exactly matches the stored dated manifest. The expected trading-session denominator comes from the outcome-independent P25.3A integrity ledger. Ready whole-union captures become P25.2I session inputs; blocked confirmed trading sessions and unresolved dates remain in the conservative operational denominator as zero-Entry days rather than disappearing.

The evaluation still retains all five precommitted variants together: `FIXED_5`, `OLD_FIXED_30`, `DYNAMIC_30`, `DYNAMIC_40`, and `DYNAMIC_50`. Current outer-OOS performance cannot choose Dynamic N, relax Entry thresholds, filter losing symbols after the fact, consume the fresh holdout, promote a model, or update production.

A GitHub Actions workflow now starts after a successful `Phase57 P25 Evidence Lineage Prep` run (or by explicit manual dispatch). It loads the dated immutable integrity/lineage snapshot, copies only the daily capture artifacts named by that lineage, rebuilds the exact pinned P24 historical pack from canonical run `31785422471`, runs the P25.3D evaluator, and writes one dated result to the separate `automation/p25-evaluation-data` branch. A same-date rerun with the same lineage head is a no-op; a different lineage head fails closed instead of rewriting the dated evaluation.

Routine evaluation therefore remains independent of the user's PC and does not require MARKETSPEED II, Excel, board, Tick, or Microstructure input. Those sources remain separate milestone/final verification surfaces and cannot rewrite frozen prospective evidence.

P25.3D does not claim that the prospective strategy is profitable. CI green verifies code/workflow integrity only. Performance conclusions must wait for real pre-open universe captures plus complete post-close 5-minute session data and must preserve all five variants and bad sessions in the evidence set.
