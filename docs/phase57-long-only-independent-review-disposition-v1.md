# Phase57 LONG-only Independent Review Disposition v1

Date: 2026-09-15 JST

Status: REVIEW RECEIVED / DISPOSITION FROZEN / ACQUISITION STILL BLOCKED

## Executive decision

Claude independent review verdict was `CONDITIONAL GO`. The review is not adopted blindly. Each material point is either accepted, modified, or rejected with an Ark-specific rationale.

The research must finish the integrated LONG-only candidate and current-Ark comparison this week. Speed is achieved by reusing evidence and one-time acquired raw data, not by weakening PIT, future-leak, OOS, safety or data-integrity controls.

## Disposition

| Review point | Ark disposition | Result |
|---|---|---|
| Zero reserve | ACCEPT | Add 15-session admission-failure reserve inside the existing 205 clean sessions |
| L0 winner-label hypothesis risk | PARTIAL ACCEPT | L0 remains a descriptive census; definitions freeze in Development A and replicate in Development B; no OOS is consumed just to rediscover the census |
| Winner-biased minute acquisition | ACCEPT | Final L2 fit, calibration, validation, OOS and integrated replay require full JPX cross-section on released dates; case-control is diagnostic only |
| Undefined purge/embargo | ACCEPT CONCEPT / MODIFY RULE | No blanket ban on causal past history. Instead, targets must resolve within-session, no cross-close target, fitted statistics stay within authorized development, and sealed outcomes remain inaccessible |
| Development 90 too large | PARTIAL ACCEPT | Reduce to 80 sessions: 25/15/20/20 |
| Validation role ambiguity | ACCEPT | Rename second stage to Validation Replication and prohibit retuning from either validation set |
| Final Confirmation redundancy | ACCEPT | Replace with sealed Contingency OOS that cannot be opened because performance is poor |
| Future realized-volatility normalization | REJECT for decision features | Use decision-time ATR or other causal volatility normalization |
| Current entitlement uncertainty | RESOLVED BY USER SCREENSHOT | Light is active; Tick + OhlcMin is active with cancellation scheduled; end timestamps recorded in the data plan |

## Clean historical accounting

The source inventory exposes 205 clean, outcome-unread historical session identifiers. v3 preserves exact accounting:

| Partition | Sessions |
|---|---:|
| Development A | 25 |
| Development B | 15 |
| Development C | 20 |
| Development D | 20 |
| Validation | 30 |
| Validation Replication | 20 |
| Primary OOS | 30 |
| Contingency OOS | 30 |
| Admission-failure Reserve | 15 |
| **Total** | **205** |

Fresh prospective sessions are outside this historical 205-session accounting and remain sealed.

## Reserve contract

Reserve is not statistical extra data and cannot be deployed because a model performs poorly. A replacement requires:

1. A precommitted admission-failure trigger.
2. A hashed evidence record.
3. Deterministic next-unused reserve identity.
4. No outcome inspection before replacement.

Allowed triggers include raw hash mismatch, provider page corruption, missing mandatory Daily/Master data, unresolved corporate-action ambiguity, and PIT master divergence.

## Purge / embargo contract

Ark does **not** prohibit causal past prices merely because they precede a partition boundary. A model operating on a Validation session may use historical prices that were genuinely available before that decision timestamp.

The actual controls are:

- all supervised targets resolve inside the same JPX trading session or are ineligible;
- no next-session price may be a feature;
- no target may cross the session close;
- scalers, model weights, threshold rules and fitted statistics are trained only on authorized Development blocks and frozen before Validation;
- Validation/OOS outcomes remain inaccessible until their release gate.

## Minute-data conservation and integrated reuse

Minute acquisition is not a Selector-only asset. Any authorized raw minute acquisition must remain reusable for:

`Selector -> Entry -> EXIT -> Capital Allocation -> integrated cash-equity portfolio replay`.

Final L2 model fit and all performance claims use the full point-in-time JPX cross-section on released session dates. Winner/near-winner/control subsets are only allowed for feature feasibility, mechanism ablation and error analysis.

## Human-overfitting controls

Before Validation is opened, the following must be frozen:

- primary L2 target;
- feature set;
- model family;
- threshold rule;
- portfolio comparison metrics;
- GO / NO-GO rules.

Validation, Validation Replication and Primary OOS cannot trigger model or threshold retuning. Bad results are durable evidence. Contingency OOS is not a second chance after poor performance.

## Entitlement evidence

User-provided authenticated account screenshots on 2026-09-15 show:

- **Light**: active, scheduled end `2026-10-06 19:02 JST`;
- **Tick + OhlcMin**: active with cancellation scheduled, end `2026-10-06 19:07 JST`.

No secret/API-key value was observed or recorded.

## Remaining blockers before acquisition

- storage/deletion terms after cancellation must be re-attested;
- Fresh exact dates must be frozen;
- operator must explicitly authorize acquisition outside the committed plan.

Until then `newJquantsAcquisitionAuthorized=false` and all new J-Quants Historical acquisition remains blocked.

## Final review state

The independent-review blocker is considered resolved at the contract level. This does not authorize data acquisition. The remaining gate is operational and contractual: storage terms, exact Fresh dates, and explicit operator authorization.
