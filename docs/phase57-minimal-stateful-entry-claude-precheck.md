# Independent Validation-precheck packet — Claude

Status: READY FOR REVIEW, NOT YET REVIEWED BY CLAUDE. This document is a handoff, not a claim that an external reviewer was invoked.

Review one architecture only: `PHASE57_MINIMAL_STATEFUL_HYBRID_ENTRY_PHASE1`. Do not propose indicator/model zoos, side-specific models, hand price gates, MFE100bps targets or expected win rates. Preserve Frozen Hybrid and existing P21; no live/paper integration.

Review inputs:

- `scripts/lib/phase57-minimal-stateful-entry.mjs`: pure state/feature/target/logistic inference APIs
- `scripts/tests/phase57-minimal-stateful-entry.test.mjs`: synthetic boundary/property checks
- `scripts/audit_phase57_minimal_stateful_sanity.mjs`: outcome-blind17-session audit and read-only legacy formula parity
- `predict/research/phase57-minimal-stateful-entry-contract.json`: fixed10 features / binary+3 target / one shared model
- `predict/research/phase57-minimal-stateful-entry-fresh-allocation.json`: explicit15 Validation/1 embargo/10 OOS reservations and failure rules
- `predict/research/phase57-minimal-stateful-entry-sanity-audit.json`: actual availability and safety evidence

Answer PASS / CHANGE REQUIRED / BLOCKED with concrete file/function evidence for:

1. Completed-bar availability, exact current price, same-session windows and no feature/label leakage.
2. Direction transforms and shared Logistic feature order; single threshold, tie handling and missing-model fail-closed behavior.
3. WATCHING expiry only on complete observed selection absence. Is terminal EXPIRED-until-next-session acceptable for this minimal phase? Missing snapshots cannot prove absence.
4. All selected events retained, including P21 ABSTAINs, feature-blocked rows and later EXPIRED selections. No reentry after ENTERED.
5. Separate feature freeze and target attachment: exact+3 grid, net5bps, zero negative class, missing null, no overnight substitution.
6. Sanity has1,346 feature-ready/4,542 events,3,076 missing exact09:00 open and120 recent-grid gaps. Do these conditions require better source admission? Do not weaken conditions using outcome results.
7. Baseline17 cannot train; protected190 cannot be accessed; Fresh Validation/OOS cannot become training by relabeling. **There is no authorized training dataset.** Does every real-model/Validation path stay blocked?
8. Fresh reservations are not CLEAN attestations or access permissions. Are the cross-research ledger and winner rule sufficient to prevent peeking, result-based rescheduling and model proliferation?
9. Stop rules retain P21 on failure; no automatic winner promotion/main change. Is the single paired-session criterion implemented/frozen sufficiently before any evaluation? Evaluation engine and threshold-selection procedure are not yet implemented or authorized.

Do not read protected/raw fresh outcomes for this review. Return only code/contract findings and the minimal changes needed for safe Validation admission. Independent review must not be represented as approving missing training authority.

Milestones after this review: one post-Validation review before winner freeze; one pre-OOS leakage/governance/stop-rule audit. No additional research branches or consultation loop is authorized by this packet.
