# Phase20 Parts5-6 — Candidate Proposal and Forward Validation

## Goal

Turn bounded OpenAI Learning Advisor output into a testable Candidate proposal, then compare it against the current model on unseen Paper-only data.

This phase does **not** promote a model automatically and does **not** enable any real brokerage write path.

## Part5 — Candidate proposal

`predict/learning/phase20-candidate-proposal.js`

The Candidate builder accepts only a previously validated Learning Advisor review.

Required conditions:

- Learning Advisor safety status is `ADVISORY_ONLY`
- `productionUpdateAllowed` is `false`
- `brokerWriteAllowed` is `false`
- `humanApprovalRequired` is `true`
- OpenAI explicitly recommends creating a Candidate
- deterministic directional sample count meets the configured minimum
- an explicit human requester is supplied
- the current model version and current numeric weights are available

### Weight rules

- only weight keys already present in the current model are accepted
- invented or unknown features are rejected
- one requested delta is capped at `0.2`
- negative weights are prevented
- the original total weight is preserved by normalization
- every accepted and rejected change is logged

### Threshold rules

Threshold changes are accepted only when the caller supplies an explicit allowlist policy with:

- minimum value
- maximum value
- maximum permitted delta

Unknown or non-numeric threshold changes are rejected.

### Exclusion rules

OpenAI exclusion-rule suggestions are retained as review text only.

`exclusionRulesExecutable` remains `false`; they cannot silently alter Production behavior.

### Candidate registration

A proposal may be registered with the existing continuous-learning orchestrator only through an explicit call that includes a human registrar.

Registration creates a Candidate record, not a Production model.

## Part6 — paired forward validation

`predict/learning/phase20-forward-validation.js`

The runner executes:

1. the current Champion predictor
2. the Candidate predictor
3. on the same rows
4. with the same symbol/session horizon
5. using the Phase20 label and join policies

Only samples where both models produce resolved directional `BUY` or `SELL` predictions are used for paired comparison.

The runner rejects or reports:

- missing Champion or Candidate samples
- non-directional decisions
- actual-return mismatches
- insufficient paired samples
- non-Out-of-sample datasets
- non-Paper-only validation contexts
- failed future-leak checks
- failed same-symbol/session joins

The paired records are evaluated by the existing Champion-Challenger v2 engine, including:

- minimum samples
- Accuracy improvement
- return improvement
- drawdown regression limit
- calibration regression limit
- paired bootstrap win probability
- comparison score

## Result states

- `READY_FOR_HUMAN_REVIEW`
- `CONTINUE_FORWARD_TEST`
- `REJECTED`
- `BLOCKED_NOT_OUT_OF_SAMPLE`
- `BLOCKED_NOT_PAPER_ONLY`

Even `READY_FOR_HUMAN_REVIEW` means only that the Candidate may be reviewed by a human.

It does not mean the Candidate has been promoted.

## Safety invariants

Every result keeps:

- `automaticPromotionAllowed: false`
- `productionUpdateAllowed: false`
- `brokerWriteAllowed: false`
- `liveBrokerAllowed: false`
- `humanApprovalRequired: true`
- `approved: false`

The connected Rakuten Securities account remains READ ONLY.

No order creation, transmission, cancellation, or account mutation is added.

## Validation order

```text
Deterministic labels and joins
  -> OpenAI advisory review
  -> explicit human Candidate proposal
  -> explicit human Candidate registration
  -> unseen Paper-only forward comparison
  -> Champion-Challenger risk gates
  -> human review
  -> later separate promotion decision
```

## CI coverage

Tests cover:

- unknown feature rejection
- weight-delta caps and total preservation
- threshold allowlist enforcement
- human requester and registrar requirements
- insufficient sample rejection
- OpenAI `shouldCreateCandidate: false`
- paired directional-only comparison
- Out-of-sample gate
- Paper-only gate
- no automatic approval
- no Production or broker write permission
